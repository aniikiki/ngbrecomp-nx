/* Included by runtime.c: a single host CPU runs the guest threads in turn.
 * Each suspended call chain has its own host stack and emulated registers. */
#include "../../../src/host_context.h"

#define WORKER_LIMIT 16
#define WORKER_HOST_STACK (1024u * 1024u)
#define THREAD_HANDLES 0x51000000u
/* Synchronization and notification events opened by the Win32/XAPI wrappers. */
static struct named_event {
    uint32_t token;
    int manual, signalled;
} events[128];

static struct worker {
    void *stack, *sp;
    RecompRegs regs;
    uint32_t va, ordinal, tib, object, ctx1, ctx2, routine, allocation, token, id;
    int waiting, suspended, exited, open, priority, disable_boost;
    unsigned references;
    uint64_t wake_tick, wait_until;
    uint32_t wait_key; /* named handle or dispatcher object address */
    int wait_named;
} workers[WORKER_LIMIT];
static unsigned running_worker;
static uint32_t next_worker_id=2;
static void release_owned_fibers(unsigned owner);
/* XAPI may hold a completed thread's dispatcher object or handle while
 * starting its successor. Such objects are waitable, not runnable workers. */
static struct retired_worker { struct worker object; struct retired_worker *next; } *retired;
static struct worker *worker_handle(uint32_t handle)
{
    for (unsigned i=1;i<thread_count;i++)
        if (workers[i].token==handle && workers[i].open) return &workers[i];
    for (struct retired_worker *r=retired;r;r=r->next)
        if (r->object.token==handle && r->object.open) return &r->object;
    return NULL;
}
static void reap_thread_objects(void)
{
    for (struct retired_worker **p=&retired;*p;) {
        struct retired_worker *r=*p;
        uint32_t a=r->object.allocation,zero=0;
        if (!r->object.open && !r->object.references && !ngb_vm_free(&a,&zero,0x8000)) {
            *p=r->next;free(r);
        } else p=&r->next;
    }
}
static uint64_t fiber_switches, skipped_event_waits;

/* Xbox workers are cooperative. Examine a parked waiter's condition before
 * restoring an entire fiber just to discover that the event is still clear.
 * Dispatcher events live in guest RAM and can be signalled by guest stores;
 * inspect the current mapping, never retain a pointer across a context switch. */
static int event_wait_pending(const struct worker *w, uint64_t now)
{
    if (!w->waiting || now >= w->wait_until) return 0;
    if (atomic_load_explicit(&cancel, memory_order_relaxed) ||
        (startup_deadline && now >= startup_deadline / 100)) return 0;
    if (w->wait_named) {
        const struct named_event *event = &events[w->wait_key & 127];
        return event->token == w->wait_key && !event->signalled;
    }
    uint32_t signal;
    const void *p = ngb_ram_span(w->wait_key + 4, sizeof(signal));
    if (!p) return 0; /* Resume the original checked read. */
    memcpy(&signal, p, sizeof(signal));
    return !signal;
}

static unsigned next_worker(uint64_t now)
{
    unsigned parked = running_worker;
    for (unsigned n = 1; n < thread_count; ++n) {
        unsigned i = (running_worker + n) % thread_count;
        const struct worker *w = &workers[i];
        if (w->suspended || w->exited) continue;
        /* If the current worker exits, even a delayed worker can pump
         * interrupts and sleeps until the first event or timeout. */
        if (parked == running_worker) parked = i;
        if (w->wake_tick > now) continue;
        if (!event_wait_pending(w, now)) return i;
        ++skipped_event_waits;
    }
    return workers[running_worker].exited || workers[running_worker].suspended
        ? parked : running_worker;
}

static void yield_worker(void)
{
    if (!interrupt_enabled || delivering_callback || thread_count <= 1 || MEM8(g_fs_base + 0x24) >= 2)
        return;
    unsigned next = next_worker(now_ns() / 100);
    if (next == running_worker) return;
    struct worker *old = &workers[running_worker], *dest = &workers[next];
    old->regs = g_regs;
    old->ordinal = pending_ordinal;
    old->va = current_va;
    running_worker = next;
    g_regs = dest->regs;
    current_va = dest->va;
    pending_ordinal = dest->ordinal;
    ++fiber_switches;
    ngb_ctx_switch(&old->sp, dest->sp);
}

/* Sleeping the host pauses every guest thread. Only back off when all
 * live guest contexts are blocked or delayed. */
static void idle_if_all_waiting(void)
{
    uint64_t now = now_ns() / 100;
    for (unsigned i = 0; i < thread_count; ++i) {
        const struct worker *w = &workers[i];
        if (!w->suspended && !w->exited && !w->waiting && w->wake_tick <= now)
            return;
    }
    struct timespec nap = {0, 250000};
    uint64_t start = ngb_scene_active ? ngb_elapsed_ns() : 0;
    nanosleep(&nap, NULL);
    if (start) ngb_scene_idle_time(ngb_elapsed_ns() - start);
}

static void worker_entry(void)
{
    struct worker *w = &workers[running_worker];
    PUSH32(g_esp, w->ctx2);
    PUSH32(g_esp, w->ctx1);
    PUSH32(g_esp, 0);
    note("[THREAD] started id=%u routine=%08x target=%08x", w->id, w->routine, w->ctx1);
    recomp_lookup(w->routine)();
    write32(w->object + 0x120, g_eax);
    write32(w->object + 4, 1);
    w->exited = 1;
    yield_worker();
    ngb_stop("no runnable guest thread", running_worker);
}

static void create_worker(void)
{
    unsigned index = thread_count;
    reap_thread_objects();
    for (unsigned i=1;i<thread_count;i++) {
        struct worker *old=&workers[i];
        if (i==running_worker || !old->exited) continue;
        struct retired_worker *r=malloc(sizeof(*r));
        if (!r) ngb_stop("retired thread allocation failed",i);
        release_owned_fibers(i);
        free(old->stack); old->stack=old->sp=NULL;
        r->object=*old; r->next=retired; retired=r;
        *old=(struct worker){0};
        reap_thread_objects();
        index=i;break;
    }
    uint32_t stack_size = arg(2), tls_size = arg(3);
    if (index >= WORKER_LIMIT || !stack_size || stack_size > 4 * 1024 * 1024 || tls_size > 0x7000 || arg(1) ||
        arg(8) || !recomp_lookup(arg(9)))
        ngb_stop("unsupported guest thread request", arg(9));
    stack_size = (stack_size + 4095) & ~4095u;
    uint32_t size = stack_size + 4096 + tls_size, base = 0;
    if (ngb_vm_allocate(&base, &size, 0, 0x3000, 4))
        ngb_stop("guest thread allocation failed", size);
    struct worker *w = &workers[index];
    w->allocation=base;
    w->id=next_worker_id++;
    if (w->id>=0x1000000u) ngb_stop("thread id space exhausted",w->id);
    w->token=THREAD_HANDLES+w->id-1;
    w->stack = malloc(WORKER_HOST_STACK);
    if (!w->stack)
        ngb_stop("worker host stack allocation failed", index);
    w->sp = ngb_context_stack(w->stack, WORKER_HOST_STACK, worker_entry);
    w->tib = base + stack_size;
    w->object = w->tib + 0x100;
    uint32_t tls = w->tib + 4096;
    write32(w->tib, UINT32_MAX);
    write32(w->tib + 4, tls + tls_size);
    write32(w->tib + 8, base);
    write32(w->tib + 0x18, w->tib);
    write32(w->tib + 0x20, w->tib + 0x400);
    write32(w->tib + 0x28, w->object);
    write32(w->object + 0x28, tls);
    write32(w->object + 0x120, 0x103);
    w->routine = arg(9);
    w->ctx1 = arg(5);
    w->ctx2 = arg(6);
    w->suspended = arg(7) != 0;
    w->open = 1;
    RecompRegs saved = g_regs;
    memset(&g_regs, 0, sizeof(g_regs));
    g_esp = w->tib;
    g_fs_base = w->tib;
    g_fp_control_word = 0x37f;
    g_fp_cc = 0x4000;
    w->regs = g_regs;
    g_regs = saved;
    write32(arg(0), w->token);
    if (arg(4))
        write32(arg(4), w->id);
    if (index==thread_count) ++thread_count;
    note("[THREAD] created id=%u target=%08x suspended=%d", w->id, w->ctx1, w->suspended);
    g_eax = 0;
    g_esp += 44;
}

static void reset_workers(void)
{
    for (unsigned i = 1; i < WORKER_LIMIT; ++i)
        free(workers[i].stack);
    while(retired) { struct retired_worker *r=retired;retired=r->next;free(r); }
    memset(workers, 0, sizeof(workers));
    running_worker = 0; next_worker_id=2;
    fiber_switches = skipped_event_waits = 0;
}

static int thread_object_call(uint32_t ordinal)
{
    if (ordinal == 246) {
        uint32_t handle = arg(0), type = arg(1);
        if (type && (type < THUNK_BASE || (type - THUNK_BASE) % 4 || (type - THUNK_BASE) / 4 >= thunk_count ||
                     thunk_ordinals[(type - THUNK_BASE) / 4] != 259))
            return 0;
        struct worker *w = handle == 0xfffffffeu ? &workers[running_worker] : worker_handle(handle);
        if (!w)
            g_eax = 0xc0000008u;
        else {
            write32(arg(2), w->object);
            ++w->references;
            g_eax = 0;
        }
        g_esp += 16;
        return 1;
    }
    if (ordinal != 250 && ordinal != 143 && ordinal != 144 && ordinal != 124)
        return 0;
    uint32_t object = ordinal == 250 ? g_ecx : arg(0);
    struct worker *w=NULL;
    for (unsigned i=0;i<thread_count;i++) if (workers[i].object==object) { w=&workers[i]; break; }
    if (!w) for (struct retired_worker *r=retired;r;r=r->next)
        if (r->object.object==object) { w=&r->object;break; }
    if (w) {
        if (ordinal == 250) {
            if (!w->references)
                ngb_stop("unbalanced thread reference", object);
            --w->references;
            g_esp += 4;
        } else if (ordinal == 124) {
            g_eax = w->priority;
            g_esp += 8;
        } else if (ordinal == 144) {
            g_eax = w->disable_boost;
            w->disable_boost = arg(1) != 0;
            g_esp += 12;
        } else {
            g_eax = w->priority;
            w->priority = (int32_t)arg(1);
            g_esp += 12;
        }
        return 1;
    }
    return 0;
}

static uint32_t event_serial;

static int event_call(uint32_t ordinal)
{
    if (ordinal == 189) {
        if (arg(1) || arg(2) > 1)
            ngb_stop("unsupported named event", arg(1));
        unsigned i = 0;
        while (i < 128 && events[i].token)
            ++i;
        if (i == 128)
            ngb_stop("event table exhausted", i);
        uint32_t token = 0x52000000u | ((++event_serial & 0xffffu) << 7) | i;
        events[i] = (struct named_event){token, arg(2) == 0, arg(3) != 0};
        write32(arg(0), token);
        g_eax = 0;
        g_esp += 20;
        return 1;
    }
    if (ordinal != 225 && ordinal != 186 && ordinal != 233 && ordinal != 234 && ordinal != 187)
        return 0;
    uint32_t handle = arg(0);
    if ((handle >> 24) != 0x52)
        return 0;
    struct named_event *e = &events[handle & 127];
    uint32_t argc = ordinal == 234 ? 4 : ordinal == 233 ? 3 : ordinal == 225 ? 2 : 1;
    uint32_t status = 0;
    if (e->token != handle)
        status = 0xc0000008u;
    else if (ordinal == 187)
        e->token = 0;
    else if (ordinal == 225 || ordinal == 186) {
        if (ordinal == 225 && arg(1))
            write32(arg(1), e->signalled);
        e->signalled = ordinal == 225;
    } else {
        uint32_t deadline_ptr = arg(argc - 1);
        if (arg(argc - 2))
            ngb_stop("unsupported alertable event wait", handle);
        uint64_t end = UINT64_MAX;
        if (deadline_ptr) {
            int64_t delay;
            memcpy(&delay, (const void *)ngb_guest_pointer(deadline_ptr, 8), 8);
            if (delay > 0)
                ngb_stop("unsupported absolute event deadline", handle);
            end = now_ns() / 100 + (uint64_t)(-(delay + 1)) + 1;
        }
        while (!e->signalled) {
            if (now_ns() / 100 >= end) {
                status = 0x102;
                break;
            }
            workers[running_worker].wait_key = handle;
            workers[running_worker].wait_until = end;
            workers[running_worker].wait_named = 1;
            workers[running_worker].waiting = 1;
            yield_worker();
            poll_runtime(true);
            idle_if_all_waiting();
            workers[running_worker].waiting = 0;
            if (e->token != handle) {
                status = 0xc0000008u;
                break;
            }
            if (startup_expired())
                ngb_stop("event wait budget", handle);
        }
        if (!status && !e->manual)
            e->signalled = 0;
    }
    g_eax = status;
    g_esp += 4 * (argc + 1);
    return 1;
}

int ngb_io_event(uint32_t handle, int signalled)
{
    struct named_event *e = &events[handle & 127];
    if (!handle || e->token != handle)
        return 0;
    e->signalled = signalled;
    return 1;
}

/* XAPI stores its fiber record at the top of the kernel stack. Preserve the
 * lifted C call chain as well as x86 registers when switching guest stacks. */
static struct fiber {
    uint32_t record, seh, owner;
    void *stack, *sp;
    RecompRegs regs;
} fibers[128];

static void release_owned_fibers(unsigned owner)
{
    for (unsigned i=0;i<128;i++) if (fibers[i].record && fibers[i].owner==owner) {
        free(fibers[i].stack);
        fibers[i]=(struct fiber){0};
    }
}

static struct fiber *find_fiber(uint32_t record)
{
    if (!record)
        ngb_stop("null fiber record", record);
    struct fiber *vacant = NULL;
    for (unsigned i = 0; i < 128; ++i) {
        if (fibers[i].record == record)
            return &fibers[i];
        if (!fibers[i].record && !vacant)
            vacant = &fibers[i];
    }
    if (!vacant)
        ngb_stop("fiber table exhausted", record);
    vacant->record = record;
    vacant->owner = running_worker;
    return vacant;
}

static uint32_t fiber_slot(void)
{
    uint32_t tls = read32(g_fs_base + 4);
    return read32(tls + read32(0x45e84c) * 4) + 8;
}

static void start_fiber(void)
{
    uint32_t record = read32(fiber_slot());
    g_esp = record - 8;
    g_ebx = g_esi = g_edi = g_seh_ebp = 0;
    write32(g_fs_base, UINT32_MAX);
    sub_0032A1AF();
    ngb_stop("fiber start routine returned", record);
}

void ngb_switch_fiber(void)
{
    uint32_t dest = arg(0), slot = fiber_slot(), current = read32(slot);
    g_esp += 8;
    if (dest == current)
        return;
    struct fiber *old = find_fiber(current), *next = find_fiber(dest);
    if (old->owner != running_worker || next->owner != running_worker)
        ngb_stop("fiber belongs to a different thread", dest);
    if (!next->sp) {
        next->stack = malloc(WORKER_HOST_STACK);
        if (!next->stack)
            ngb_stop("fiber stack allocation failed", dest);
        next->sp = ngb_context_stack(next->stack, WORKER_HOST_STACK, start_fiber);
    }
    old->regs = g_regs;
    old->seh = read32(g_fs_base);
    if (next->regs.r_fs_base) {
        g_regs = next->regs;
        write32(g_fs_base, next->seh);
    }
    write32(slot, dest);
    ngb_ctx_switch(&old->sp, next->sp);
}

static void release_fiber(uint32_t record)
{
    for (unsigned i = 0; i < 128; ++i)
        if (fibers[i].record == record) {
            free(fibers[i].stack);
            fibers[i] = (struct fiber){0};
            return;
        }
}

static uint32_t kernel_stack_sizes[(NGB_VM_END - NGB_VM_BEGIN) / 4096];
static void kernel_stack(uint32_t ordinal)
{
    if (ordinal == 169) {
        uint32_t size = arg(0), rounded = size, base = 0;
        if (arg(1) || !size)
            ngb_stop("unsupported kernel stack", size);
        g_eax = 0;
        if (!ngb_vm_allocate(&base, &rounded, 0, 0x3000, 4)) {
            g_eax = base + size;
            kernel_stack_sizes[(base - NGB_VM_BEGIN) / 4096] = size;
        }
    } else {
        uint32_t top = arg(0), base = arg(1), zero = 0;
        if (base < NGB_VM_BEGIN || base >= NGB_VM_END || (base & 4095) || top <= base ||
            kernel_stack_sizes[(base - NGB_VM_BEGIN) / 4096] != top - base)
            ngb_stop("invalid kernel stack release", base);
        release_fiber(top - 16);
        kernel_stack_sizes[(base - NGB_VM_BEGIN) / 4096] = 0;
        if (ngb_vm_free(&base, &zero, 0x8000))
            ngb_stop("kernel stack free failed", base);
        g_eax = 0;
    }
    g_esp += 12;
}

static void report_workers(void)
{
    for (unsigned i = 0; i < thread_count; i++) {
        struct worker *w = &workers[i];
        note("[THREAD] id=%u active=%u function=%08x ordinal=%u suspended=%d exited=%d open=%d refs=%u", w->id,
             i == running_worker, i == running_worker ? current_va : w->va,
             i == running_worker ? pending_ordinal : w->ordinal, w->suspended, w->exited, w->open, w->references);
    }
}

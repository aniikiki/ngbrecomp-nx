/* The guest owns handles, guest memory and events. The native reader owns a
 * separate stream on the immutable disc and writes only to request storage. */
#include <pthread.h>
#include <stdatomic.h>
#include <stdlib.h>

struct disc_read {
    struct disc_read *next, *work_next;
    uint32_t handle, event, ios, target, length, received, status;
    int64_t offset;
    int cancelled, timed;
    uint64_t issued, started, finished, warmed;
    atomic_bool ready;
    char path[1024];
    uint8_t data[];
};
static struct disc_read *disc_head, **disc_tail = &disc_head; /* guest only */
static struct disc_read *work_head, **work_tail = &work_head;
static pthread_mutex_t disc_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t disc_work = PTHREAD_COND_INITIALIZER;
static pthread_t disc_thread;
static int disc_started, disc_stopping;
static size_t disc_bytes;
unsigned ngb_pending_disc_reads;

static const char *disc_leaf(const char *path)
{
    const char *slash = strrchr(path,'/');
    return slash ? slash + 1 : path;
}
static void *disc_reader(void *unused)
{
    (void)unused;
    FILE *file = NULL;
    char path[1024] = "";
    for (;;) {
        pthread_mutex_lock(&disc_lock);
        while (!work_head && !disc_stopping) pthread_cond_wait(&disc_work,&disc_lock);
        if (disc_stopping) { pthread_mutex_unlock(&disc_lock); break; }
        struct disc_read *r = work_head;
        work_head = r->work_next;
        if (!work_head) work_tail = &work_head;
        pthread_mutex_unlock(&disc_lock);

        if (r->timed) r->started = ngb_elapsed_ns();
        if (!file || strcmp(path,r->path)) {
            if (file) fclose(file);
            strcpy(path,r->path);
            file = fopen(path,"rb");
        }
        r->status = ngb_disc_stream_read(file,r->data,r->length,r->offset,&r->received);
        if (r->timed) r->finished = ngb_elapsed_ns();
        if (!r->status) ngb_file_disc_textures(disc_leaf(path),r->offset,r->data,r->received);
        if (r->timed) r->warmed = ngb_elapsed_ns();
        atomic_store_explicit(&r->ready,1,memory_order_release);
    }
    if (file) fclose(file);
    return NULL;
}
static int queue_disc_read(const char *path, const uint32_t *a, int64_t offset, int timed)
{
    /* Bound private staging on the handheld. Under memory pressure the
     * bridge can still perform the original read after preceding requests. */
    const size_t budget = 16u << 20;
    size_t allocation = sizeof(struct disc_read) + (size_t)a[6];
    if (allocation > budget - disc_bytes) return 0;
    struct disc_read *r = malloc(allocation);
    if (!r) return 0;
    if (!disc_started) {
        if (pthread_create(&disc_thread,NULL,disc_reader,NULL)) { free(r); return 0; }
        disc_started = 1;
    }
    r->next = r->work_next = NULL;
    r->handle = a[0]; r->event = a[1]; r->ios = a[4]; r->target = a[5];
    r->length = a[6]; r->offset = offset; r->cancelled = 0; r->timed = timed;
    r->issued = timed ? ngb_elapsed_ns() : 0;
    strcpy(r->path,path);
    atomic_init(&r->ready,0);
    store32(r->ios,NGB_FS_PENDING); store32(r->ios + 4,0);
    ngb_file_disc_submitted(r->handle);
    *disc_tail = r; disc_tail = &r->next;
    ++ngb_pending_disc_reads; disc_bytes += allocation;
    pthread_mutex_lock(&disc_lock);
    *work_tail = r; work_tail = &r->work_next;
    pthread_cond_signal(&disc_work);
    pthread_mutex_unlock(&disc_lock);
    return 1;
}
void ngb_disc_reads_poll(void)
{
    while (disc_head && atomic_load_explicit(&disc_head->ready,memory_order_acquire)) {
        struct disc_read *r = disc_head;
        if (!r->cancelled) {
            uint64_t start = r->timed ? ngb_elapsed_ns() : 0;
            if (r->received) {
                memcpy((void *)ngb_guest_pointer(r->target,r->received),r->data,r->received);
                if (!r->status) ngb_warning_file_read(disc_leaf(r->path),r->offset);
            }
            store32(r->ios + 4,r->received); store32(r->ios,r->status);
            ngb_file_disc_completed(r->handle,r->offset,r->received,r->status);
            if (r->event) ngb_io_event(r->event,1);
            if (start) {
                uint64_t end = ngb_elapsed_ns();
                if (ngb_scene_active) ngb_scene_file_time(r->received,end-start);
#ifdef NGB_NATIVE_DIAG
                if (ngb_combat_enabled) {
                    ngb_combat_file(0,0,r->received,end-start);
                    uint32_t hash = 2166136261u;
                    for (const char *p=disc_leaf(r->path); *p; ++p) hash = (hash ^ (uint8_t)*p) * 16777619u;
                    uint64_t row[] = {r->issued/1000,r->started/1000,r->finished/1000,r->warmed/1000,
                        end/1000,(end-start)/1000,r->handle,hash,(uint64_t)r->offset,r->length,r->received,r->status};
                    ngb_combat_row('I',row,sizeof(row)/sizeof(*row));
                }
#endif
            }
        }
        disc_head = r->next;
        if (!disc_head) disc_tail = &disc_head;
        --ngb_pending_disc_reads; disc_bytes -= sizeof(*r) + r->length;
        free(r);
    }
}
static void finish_prior_disc_reads(uint32_t handle)
{
    while (ngb_pending_disc_reads) {
        struct disc_read *r = disc_head;
        while (r && (r->handle != handle || r->cancelled)) r = r->next;
        if (!r) return;
        ngb_io_yield();
    }
}
static void cancel_disc_reads(uint32_t handle)
{
    ngb_disc_reads_poll();
    for (struct disc_read *r=disc_head; r; r=r->next) {
        if (r->handle != handle || r->cancelled) continue;
        r->cancelled = 1;
        store32(r->ios+4,0); store32(r->ios,0xc0000120u); /* STATUS_CANCELLED */
        if (r->event) ngb_io_event(r->event,1);
    }
}
static void stop_disc_reads(void)
{
    if (!disc_started) return;
    pthread_mutex_lock(&disc_lock);
    disc_stopping = 1;
    pthread_cond_signal(&disc_work);
    pthread_mutex_unlock(&disc_lock);
    pthread_join(disc_thread,NULL);
    while (disc_head) {
        struct disc_read *next = disc_head->next;
        free(disc_head); disc_head = next;
    }
    disc_tail=&disc_head; work_head=NULL; work_tail=&work_head;
    disc_started=disc_stopping=0; disc_bytes=0; ngb_pending_disc_reads=0;
}

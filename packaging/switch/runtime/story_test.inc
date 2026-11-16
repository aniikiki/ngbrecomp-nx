/* Host-only: replay New Game from the retail DVD. No save, patched game
 * state, or host teleport. The position is read only (same vector as the
 * upstream F8 debug display); all movement goes through the Xbox USB pad. */
static int story_verified;
static void check_story_pad(uint32_t physical, uint64_t now)
{
    static uint64_t start, next;
    static unsigned last=UINT32_MAX, tick, cycle;
    static int held;
    static float px[5],pz[5];
    if (!start) start=now;
    if (now-start>1200000) ngb_stop("story input verification timeout",tick);
    if (!ngb_scene_active) {
        if (now>=next) {
            ngb_ohci_pad_sample(held ? 0 : 256,0,0,0,0);
            held=!held;
            next=now+(held ? 160 : 1700);
        }
        return;
    }
    if (physical==last) return;
    last=physical;
    if (!tick) ngb_ohci_pad_sample(0,0,0,0,0);
    unsigned at=tick++%144;
    if (at%24 || at>96) return;
    unsigned slot=at/24;
    px[slot]=MEMF(0x4B5710); pz[slot]=MEMF(0x4B5718);
    int stick=slot==1 ? 28500 : slot==3 ? -28500 : 0;
    ngb_ohci_pad_sample(0,stick,0,0,0);
    fprintf(stderr,"[STORY] scene_flip=%u pos=(%.3f,%.3f) stick=%d\n",tick,px[slot],pz[slot],stick);
    if (slot!=4) return;
    float dx=px[2]-px[1], dz=pz[2]-pz[1], rx=px[4]-px[3],rz=pz[4]-pz[3];
    float idle=hypotf(px[1]-px[0],pz[1]-pz[0]),fwd=hypotf(dx,dz),rev=hypotf(rx,rz);
    /* Two independent sequences, starting still, and opposite responses
     * to opposite input. Camera pans alone cannot move this guest vector. */
    bool passed=idle<0.1f && fwd>0.25f && rev>0.25f && dx*rx+dz*rz < -0.4f*fwd*rev;
    cycle=passed ? cycle+1 : 0;
    if (cycle==2) {
        story_verified=1;
        ngb_stop("verified first chapter player control",tick);
    }
}

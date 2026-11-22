/* Guest opens the panel; only the pad owner edits it. The framebuffer owner
 * renders a snapshot. No filesystem reads or writes in the gameplay loop. */
#include "recomp_settings.h"
#include "direct/display.h"
#include "../../../src/launcher_font.h"
#define PREF_FILE "sdmc:/switch/ngb-runtime/recomp-settings.ini"
#include "settings_catalog.h"
#include "../../../src/quick_select.h"
enum { PANEL=1u<<16,SAVE_ERROR=1u<<17, COUNT=sizeof settings/sizeof settings[0] };
static atomic_uint panel, revision, aim;
enum { EXIT_PANEL=1u<<18, EXIT_CONFIRM=1u<<19, EXIT_ERROR=1u<<20 };
static atomic_bool exit_preview,exit_resume,exit_return_boot;
static const char *exit_program_path;
static atomic_uchar value[85];
static int launch_aspect,launch_thread;
static int choices(const Preference *p) {int n=1;for(const char *s=p->choices;*s;s++)n+=*s=='|';return n;}
static int pref(unsigned i){return atomic_load_explicit(&value[i],memory_order_relaxed);}
int ngb_switch_setting(unsigned i) {
    if (i>=sizeof value/sizeof value[0]) return 0;
    int v=pref(i);
    switch(i){
    case 0:return (int[]){1,NGB_RENDER_720P,2}[v];
    case 1:return v?1<<v:0;
    case 2:case 10:return 1<<v;
    case 20:return v*25;
    case 30:return launch_thread;
    case 47:return (int[]){50,75,100,125,150,200}[v];
    default:return v;
    }
}
static bool prefs_save(unsigned,unsigned);
/* The original file stores 1x as 0 and 2x as 1. Swap 720p and 2x between
 * menu order and file order on both read and write. */
static unsigned file_choice(const Preference *p,unsigned v){
    return p->id==0 && v<3?(unsigned[]){0,2,1}[v]:v;
}
static unsigned saved_choice(const Preference *p,unsigned id,unsigned v){return id==255 && p->page==CONTROLS?p->initial:p->id==id?v:(unsigned)pref(p->id);}
void ngb_switch_toggle_hud(void){if(prefs_save(24,!pref(24)))atomic_fetch_add(&revision,1);}
int ngb_settings_glow(void){return pref(18);}
int ngb_settings_standard_aspect(void){return launch_aspect;}
int ngb_settings_skip_intro(void){return pref(8) || atomic_load(&exit_return_boot);}
int ngb_bind_third_person_start(void){return pref(46);}
float ngb_bind_camera_boost(void){int pct=ngb_switch_setting(47);return pct>100?pct/100.f:1.f;}
int ngb_movie_active(void){return ngb_movie_owns_input();}
static void prefs_load(void)
{
    for(unsigned i=0;i<COUNT;i++)atomic_store(&value[settings[i].id],settings[i].initial);
    FILE *f=fopen(PREF_FILE,"r");
    if(!f) f=fopen(PREF_FILE ".bak","r");
    if(!f)return;
    char line[128],key[48],extra;unsigned v;
    while(fgets(line,sizeof line,f))if(sscanf(line,"%47[^=]=%u %c",key,&v,&extra)==2)
        for(unsigned i=0;i<COUNT;i++){
            const Preference *p=settings+i;
            if(!(p->flags&(SESSION|FIXED)) && !strcmp(key,p->key) && v<(unsigned)choices(p))
                atomic_store(&value[p->id],file_choice(p,v));
        }
    fclose(f);
}
static bool prefs_save(unsigned id,unsigned v)
{
    FILE *f=fopen(PREF_FILE ".tmp","w");
    if (!f) return false;
    int n=1;
    for(unsigned i=0;i<COUNT;i++)if(!(settings[i].flags&(SESSION|FIXED)) &&
        fprintf(f,"%s=%u\n",settings[i].key,file_choice(settings+i,saved_choice(settings+i,id,v)))<0) n=0;
    int err=fclose(f);
    if (n<=0 || err) { remove(PREF_FILE ".tmp"); return false; }
    if (rename(PREF_FILE ".tmp",PREF_FILE)) {
        /* Some SD filesystem drivers cannot rename over an existing file.
         * Keep the old settings recoverable across an interrupted swap. */
        struct stat st;
        if (stat(PREF_FILE,&st)) { remove(PREF_FILE ".tmp"); return false; }
        remove(PREF_FILE ".bak");
        if (rename(PREF_FILE,PREF_FILE ".bak")) { remove(PREF_FILE ".tmp"); return false; }
        if (rename(PREF_FILE ".tmp",PREF_FILE)) {
            rename(PREF_FILE ".bak",PREF_FILE);
            remove(PREF_FILE ".tmp");
            return false;
        }
    }
    remove(PREF_FILE ".bak");
    if(id==255){for(unsigned i=0;i<COUNT;i++)if(settings[i].page==CONTROLS)atomic_store(&value[settings[i].id],settings[i].initial);}
    else atomic_store(&value[id],v);
    return true;
}
extern void ngb_camera_frame(void),ngb_intercept_frame(void),ngb_ut_charge_frame(void),ngb_responsive_frame(void),ngb_switch_cheat_tick(void);
extern int ngb_bow_aiming(void),ngb_cheat(int);
extern void ngb_cheat_set(int,int),ngb_set_all_difficulties(int),ngb_set_all_costumes(int),ngb_set_unlock(int,int);
void ngb_switch_sync_settings(void){
    static unsigned applied=~0u;
    unsigned r=atomic_load(&revision);if(applied==r)return;
    static const unsigned id[]={11,12,13,15,21,22,32,37,38,39};
    for(int i=0;i<10;i++)if(ngb_cheat(i)!=pref(id[i]))ngb_cheat_set(i,pref(id[i]));
    ngb_set_all_difficulties(pref(14));ngb_set_all_costumes(pref(16));
    for(int i=0;i<3;i++)ngb_set_unlock(i,pref(26+i));
    applied=r;
}
void ngb_switch_frame(void){
    ngb_switch_sync_settings();ngb_camera_frame();ngb_quick_tick();ngb_intercept_frame();
    ngb_ut_charge_frame();ngb_responsive_frame();ngb_switch_cheat_tick();
    atomic_store(&aim,ngb_bow_aiming());
}
static uint32_t bow_art[64*64];
static int bow_loaded;
void ngb_settings_open(void)
{
    atomic_store(&aim,0);
    atomic_store(&panel,PANEL);
    while (atomic_load(&panel) && !ngb_stop_requested()) svcSleepThread(4000000);
    ngb_switch_sync_settings();
}
static bool settings_input(PadState *pad)
{
    static bool armed,closing;
    unsigned view=atomic_load(&panel);
    if (!view) return false;
    u64 held=padGetButtons(pad), down=padGetButtonsDown(pad);
    u64 controls=HidNpadButton_A|HidNpadButton_B|HidNpadButton_X|HidNpadButton_Plus|HidNpadButton_Minus;
    /* Drain the opening and closing presses rather than delivering them to
     * the setting or the game. The guest remains on the selected menu row. */
    ngb_switch_sample_quick(0);
    ngb_ohci_pad_sample(0,0,0,0,0);
    if (closing) {
        if (!(held&controls)) { armed=closing=false;atomic_store(&panel,0); }
    } else if (!armed) {
        if (!(held&controls)) armed=true;
    } else if(view&EXIT_PANEL){
        unsigned row=view&3;
        if(down&HidNpadButton_B){
            if(view&(EXIT_CONFIRM|EXIT_ERROR))view=EXIT_PANEL|row;else closing=true;
        }else if(view&EXIT_ERROR){ /* B returns to the choices. */ }
        else if(!(view&EXIT_CONFIRM) && (down&(HidNpadButton_AnyUp|HidNpadButton_AnyDown))){
            view=EXIT_PANEL|((row+((down&HidNpadButton_AnyUp)?2:1))%3);
        }else if(down&HidNpadButton_A){
            if(!row){atomic_store(&exit_resume,true);closing=true;}
            else if(!(view&EXIT_CONFIRM))view|=EXIT_CONFIRM;
            else if(row==1){
                char args[1024];int n=snprintf(args,sizeof args,"\"%s\" --return-to-title",exit_program_path);
                struct stat file;
                if(n<0 || (size_t)n>=sizeof args || stat(exit_program_path,&file) || !S_ISREG(file.st_mode) || !envHasNextLoad() ||
                   R_FAILED(envSetNextLoad(exit_program_path,args)))view=EXIT_PANEL|EXIT_ERROR|row;
                else atomic_fetch_or(&commands,EXIT_GAME);
            }else atomic_fetch_or(&commands,EXIT_GAME);
        }
        atomic_store(&panel,view);
    } else {
        unsigned page=(view>>8)&255,row=view&255,start=0,n=PAGES;
        if(page){while(start<COUNT && settings[start].page!=page-1)start++;
            n=0;while(start+n<COUNT && settings[start+n].page==page-1)n++;}
        if(down&HidNpadButton_Plus)closing=true;
        else if(page==CONTROLS+1 && (down&HidNpadButton_X)){
            if(prefs_save(255,0)){view&=~SAVE_ERROR;atomic_fetch_add(&revision,1);}else view|=SAVE_ERROR;
        }
        else if(down&HidNpadButton_B){if(page)view=PANEL|(page-1);else closing=true;}
        else if(down&(HidNpadButton_AnyUp|HidNpadButton_AnyDown)){
            row=(row+n+((down&HidNpadButton_AnyUp)?-1:1))%n;view=PANEL|(page<<8)|row;
        }else if(down&(HidNpadButton_A|HidNpadButton_AnyLeft|HidNpadButton_AnyRight)){
            if(!page)view=PANEL|((row+1)<<8);
            else {const Preference *p=settings+start+row;
                if(!(p->flags&FIXED)){
                    int count=choices(p),v=(pref(p->id)+count+((down&HidNpadButton_AnyLeft)?-1:1))%count;
                    if(p->flags&SESSION)atomic_store(&value[p->id],v);
                    else if(!prefs_save(p->id,v)){atomic_store(&panel,view|SAVE_ERROR);return true;}
                    atomic_fetch_add(&revision,1);view&=~SAVE_ERROR;
                }
            }
        }
        atomic_store(&panel,view);
    }
    return true;
}
static void panel_text(u32 *dst,unsigned stride,int x,int y,const char *s,u32 fg)
{
    for (;*s;s++) {
        unsigned c=(unsigned char)*s-32,w=launcher_font_w[c];
        const uint8_t *glyph=launcher_font_px+launcher_font_off[c];
        for(unsigned j=0;j<32;j++)for(unsigned i=0;i<w;i++){
            unsigned a=glyph[j*w+i];if(!a)continue;
            u32 *d=dst+(y+j)*stride+x+i;
            u32 v=(a+(*d>>24)*(255-a)/255)<<24;
            for(int k=0;k<24;k+=8)v|=((((fg>>k)&255)*a+((*d>>k)&255)*(255-a))/255)<<k;
            *d=v;
        }
        x+=w;
    }
}
/* Only the guest USB consumer reads retail RAM. Intercept the select
 * press before the original Exit action closes the pause menu. */
int ngb_switch_exit_report(int tab,uint8_t *report){
    static bool held;
    bool select=report[4]!=0;
    bool edge=select && !held;held=select;
    atomic_store_explicit(&exit_preview,tab,memory_order_relaxed);
    if(!tab)atomic_store(&exit_resume,false);
    if(tab && atomic_load(&exit_resume)){
        memset(report+2,0,18);report[2]=16;return 1;
    }
    if(tab && edge && !atomic_load(&panel))atomic_store(&panel,EXIT_PANEL);
    if(atomic_load(&panel)&EXIT_PANEL){memset(report+2,0,18);return 1;}
    return 0;
}
static void exit_contents(u32 *dst,unsigned stride,unsigned view){
    const char *rows[]={"Return to Game","Return to Main Menu","Quit Game"};
    unsigned row=view&3;
    for(unsigned y=215;y<505;y++)for(unsigned x=345;x<935;x++)
        dst[y*stride+x]=view && y>=277+row*50 && y<320+row*50?0xff424143:0xff211d1d;
    panel_text(dst,stride,380,227,"EXIT",0xff80c7eb);
    for(unsigned i=0;i<3;i++)panel_text(dst,stride,388,280+50*i,rows[i],~0u);
    const char *hint=!view?"A: Choose     Left / Right: Tabs":view&EXIT_ERROR?"Cannot restart here. B: Back":
       view&EXIT_CONFIRM?"Unsaved progress will be lost. A: Yes   B: No":"Up / Down: Select     A: Confirm     B: Back";
    panel_text(dst,stride,355,455,hint,0xff80c7eb);
}
static void draw_exit_panel(Framebuffer *fb,unsigned view){
    u32 bytes,*dst=framebufferBegin(fb,&bytes);ngb_scanout_blit(dst,bytes/4,1280,720);
    exit_contents(dst,bytes/4,view);framebufferEnd(fb);
}
static void settings_contents(u32 *dst,unsigned stride,unsigned view)
{
    unsigned page=(view>>8)&255,row=view&255,start=0,n=PAGES;
    if(page){while(start<COUNT && settings[start].page!=page-1)start++;n=0;while(start+n<COUNT && settings[start+n].page==page-1)n++;}
    unsigned first=row>=8?row-7:0;
    for(int y=54;y<669;y++)for(int x=132;x<1148;x++){
        unsigned line=151+(row-first)*50;
        dst[y*stride+x]=(y==54||y==668)?0xff649dbc:
            ((unsigned)y>=line && (unsigned)y<line+44)?0xff424143:0xff211d1d;
    }
    char title[96];snprintf(title,sizeof title,"RECOMP SETTINGS%s%s",page?"   /   ":"",page?categories[page-1]:"");
    panel_text(dst,stride,170,84,title,0xff80c7eb);
    for(unsigned r=first;r<n && r<first+8;r++){
        int y=156+(r-first)*50;
        if(!page)panel_text(dst,stride,180,y,categories[r],~0u);
        else{const Preference *p=settings+start+r;const char *z=p->choices;
            for(int j=0;j<pref(p->id);j++)z=strchr(z,'|')+1;
            char choice[44];snprintf(choice,sizeof choice,"%.*s",(int)strcspn(z,"|"),z);
            panel_text(dst,stride,180,y,p->label,~0u);
            panel_text(dst,stride,752,y,choice,p->flags&FIXED?0xffaaa9a8:~0u);
        }
    }
    const char *hint="In play: Minus + left stick click opens settings.";
    if(page){const Preference *p=settings+start+row;hint=(p->id==7 || p->id==30)?"Takes effect next launch.":p->flags&FIXED?"Fixed by this Switch build.":p->flags&SESSION?"This play session only.":"Changes are saved to the SD card.";}
    panel_text(dst,stride,170,566,view&SAVE_ERROR?"SD card write failed.":hint,0xffbcbab8);
    panel_text(dst,stride,170,610,page==CONTROLS+1?"Left / Right: Change    X: Defaults    B: Back    +: Close":page?"Left / Right: Change      B: Back      +: Close":"Up / Down: Select      +: Close",0xff80c7eb);
}
static void draw_settings(Framebuffer *fb,unsigned view){
    u32 bytes,*dst=framebufferBegin(fb,&bytes);
    ngb_scanout_blit(dst,bytes/4,1280,720);
    settings_contents(dst,bytes/4,view);
    framebufferEnd(fb);
}

/* Only touched HUD rectangles are cleared, uploaded and blended each frame. */
static void overlay_region(NgbScreenFrame *frame,u32 *pixels,NgbScreenRect r){
    if(!frame)return;
    frame->rects[frame->count++]=r;
    for(unsigned y=r.y;y<r.y+r.h;y++)memset(pixels+y*NGB_SCREEN_W+r.x,0,r.w*sizeof(*pixels));
}
static const NgbScreenRect exit_region={0,215,NGB_SCREEN_W,290};
static void game_overlay(u32 *dst,unsigned stride,NgbScreenFrame *frame){
    bool preview=atomic_load_explicit(&exit_preview,memory_order_relaxed);
    if(preview){overlay_region(frame,dst,exit_region);exit_contents(dst,stride,0);}
    unsigned bow=atomic_load(&aim);
    if(bow && bow_loaded && pref(44) && pref(24) && !ngb_movie_owns_input()){
        int offset=bow==2?0:9;
        if(!preview)overlay_region(frame,dst,(NgbScreenRect){630+offset,350+offset,20,20});
        for(int y=0;y<20;y++)for(int x=0;x<20;x++){
            u32 px=bow_art[((y*64+32)/20)*64+(x*64+32)/20],a=px>>24;
            if(!a)continue;
            u32 *d=dst+(360+offset-10+y)*stride+640+offset-10+x;
            u32 v=(a+((*d>>24)*(255-a)+127)/255)<<24;
            for(int k=0;k<24;k+=8){
                unsigned c=((px>>(16-k))&255)+(((*d>>k)&255)*(255-a)+127)/255;
                v|=(c>255?255:c)<<k;
            }
            *d=v;
        }
    }
    static u64 then;static unsigned baseline;static char fps[20];
    if(!pref(5)){then=0;return;}
    u64 now=armGetSystemTick();
    unsigned displayed=ngb_scanout_display_count();
    if(!then){then=now;baseline=displayed;fps[0]=0;}
    else if(now-then>=armGetSystemTickFreq()/2){
        snprintf(fps,sizeof fps,"%u FPS",(unsigned)((displayed-baseline)*armGetSystemTickFreq()/(now-then)));
        then=now;baseline=displayed;
    }
    if(!fps[0])return;
    overlay_region(frame,dst,(NgbScreenRect){16,16,240,34});
    panel_text(dst,stride,17,17,fps,0xff000000);panel_text(dst,stride,16,16,fps,~0u);
}

#ifdef NGB_GPU_PRESENT
static int present_screen(unsigned view,uint64_t *times){
    static u32 overlay[NGB_SCREEN_W*NGB_SCREEN_H];
    NgbScreenFrame frame={0};
    frame.gpu=ngb_scanout_is_gpu();
    frame.blank=ngb_scanout_is_blank();
    frame.standard=ngb_settings_standard_aspect();
    if(!frame.gpu && !frame.blank)frame.cpu_bgra=ngb_scanout_last_pixels();
    frame.overlay_rgba=overlay;
    if(view&EXIT_PANEL){
        overlay_region(&frame,overlay,exit_region);
        exit_contents(overlay,NGB_SCREEN_W,view);
    }else if(view){
        overlay_region(&frame,overlay,(NgbScreenRect){0,54,NGB_SCREEN_W,615});
        settings_contents(overlay,NGB_SCREEN_W,view);
    }else game_overlay(overlay,NGB_SCREEN_W,&frame);
    return ngb_display_present(&frame,times);
}
#endif

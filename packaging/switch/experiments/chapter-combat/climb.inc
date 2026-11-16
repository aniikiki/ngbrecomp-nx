/* Only issue normal controller inputs. All world and health reads are read-only. */
static unsigned fight_tick,stage,certified;
static int fight_live;
static int xaxis,yaxis;
static float prev_x,prev_z,heading=0.56f,old_stick;
static unsigned damage_hits,enemy_hits;
void fight_damage(unsigned target,unsigned attacker,unsigned before,unsigned after){
    if(!fight_live || !before || after>=before)return;
    int is_enemy=target>0x4b4e50u && target<0x4b4e50u+64u*0x2800u && (target-0x4b4e50u)%0x2800u==0;
    if(is_enemy && attacker==0x4b4e50u)++damage_hits;
    if(target==0x4b4e50u && attacker>target && attacker<target+64u*0x2800u && (attacker-target)%0x2800u==0)++enemy_hits;
    fprintf(stderr,"[C1_DAMAGE] t=%u target=%08x attacker=%08x hp=%u->%u dealt=%u received=%u\n",fight_tick,target,attacker,before,after,damage_hits,enemy_hits);
}
static void fight_pad(void){
 unsigned t=++fight_tick;
 if(t>1700)ngb_stop("chapter encounter observation ended",t);
 float x=MEMF(0x4b5710),y=MEMF(0x4b5714),z=MEMF(0x4b5718);
 unsigned button=0;float tx=26.2f,tz=-2.75f,ty=0.4f;
 unsigned enemy=0,hp=0;
 float best=1e20f;
 for(unsigned i=1;i<64;i++){
    uint32_t obj=0x4b4e50+i*0x2800,h=MEM8(obj+0x27f0);
    if(!h||h>=32||!MEM32(obj+0x26d8)||MEM8(obj+0x278e))continue;
    unsigned v=MEM16(0x58a3a0+0x210*h+0x1c6);if(!v||v>9999)continue;
    float ex=MEMF(obj+0x8c0),ey=MEMF(obj+0x8c4),ez=MEMF(obj+0x8c8);
    float dist=hypotf(x-ex,z-ez)+1.5f*fabsf(y-ey);
    if(dist<best){best=dist;enemy=i;hp=v;if(stage>=3){tx=ex;ty=ey;tz=ez;}}
 }
 if(!stage){
    xaxis=0;yaxis=31000;if(x>15.4f)stage=1;
 }else if(stage==1){
    xaxis=17000;yaxis=26800;button=(t%42)<4?256:0;
    if(x>19.f){stage=2;heading=0.56f;prev_x=x;prev_z=z;old_stick=atan2f(yaxis,xaxis);}
 }else{
    static unsigned reached;
    if(!reached && x>26.5f && y>2.8f)reached=t;
    if(!reached){
        uint32_t dev=MEM32(0x3d83c8);
        float dx=29.0f-x,dz=-4.8f-z;
        if(dev){float sx=MEMF(dev+0xc60)*dx+MEMF(dev+0xc60+32)*dz,sy=MEMF(dev+0xc60+8)*dx+MEMF(dev+0xc60+40)*dz;
          float len=hypotf(sx,sy);if(len>0.2f){xaxis=30000*sx/len;yaxis=30000*sy/len;}}
        unsigned combo=t%16;
        if(combo==0 || combo==1 || combo==8 || combo==9)button=256;
        else if(combo>=4 && combo<7)button=1024|256;
        else if(combo==12 || combo==13)button=512;
    }else{
        xaxis=0;yaxis=0;
        unsigned phase=(t-reached)%36;
        if(phase<4)button=512;else if(phase>=8 && phase<13)button=1024;else if(phase>=18 && phase<22)button=2048;
    }
 }
 ngb_ohci_pad_sample(button,xaxis,yaxis,0,0);
 if(t%24==1)fprintf(stderr,"[FIGHT] %u stage=%u pos=%.2f,%.2f,%.2f target=%u at=%.1f,%.1f,%.1f hp=%u pad=%d,%d,%u hits=%u\n",t,stage,x,y,z,enemy,tx,ty,tz,hp,xaxis,yaxis,button,damage_hits);
 if((damage_hits||enemy_hits) && ++certified>=240)ngb_stop(damage_hits?"verified first chapter combat with player damage dealt":"verified first chapter opponent damaged player",t);
}

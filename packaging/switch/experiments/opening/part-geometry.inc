struct geo_tri {uint8_t xyz[36],mat[64],out[48];unsigned slot;};
struct geo_set {unsigned actor,n;uint8_t input[16],raw[64][64],types[128],field1[64],field2[64];unsigned filled;struct geo_tri tri[64];};
static struct geo_set first_geo[32],current_geo;
static struct {unsigned calls[2],tri[2],matched_actor,same_geometry,same_transform_set,geom_slots,mat_slots,both_slots,any_geom,any_both,outputs,bad;} gs;
static unsigned nfirst,geo_open,sel_all,sel_input,sel_raw,sel_type,sel_aux,sel_id;
static void geo_event_c(unsigned k,unsigned slot_addr,unsigned sp) {
 if(!tf||(tk!=GEO_A && tk!=GEO_B))return;
 unsigned route=tk-GEO_A;
 if(k==0){if(geo_open)abort();geo_open=1;current_geo.actor=*(uint32_t*)ngb_guest_pointer(0x4b2450,4);current_geo.n=0;current_geo.filled=0;++gs.calls[route];return;}
 if(!geo_open)abort();
 struct geo_set *c=&current_geo;
 if(k==4){unsigned addr=*(uint32_t*)ngb_guest_pointer(sp+4,4);memcpy(c->input,(void*)ngb_guest_pointer(addr,16),16);return;}
 if(k==5){unsigned n=*(uint32_t*)ngb_guest_pointer(0x496060,4);if(n>64)abort();c->filled=1;
 if(n){memcpy(c->raw,(void*)ngb_guest_pointer(0x494be0,n*64),n*64);memcpy(c->types,(void*)ngb_guest_pointer(0x494ab0,n*2),n*2);memcpy(c->field1,(void*)ngb_guest_pointer(0x495fe0,n),n);memcpy(c->field2,(void*)ngb_guest_pointer(0x496020,n),n);}return;}
 if(k==1||k==2){unsigned i=(slot_addr-0x494be0u)/64;
 if(i>=64||slot_addr!=0x494be0u+64*i||i!=c->n-(k==2))abort();
 struct geo_tri *t=c->tri+i;
 if(k==1){c->n++;gs.tri[route]++;t->slot=i;for(unsigned j=0;j<3;j++)memcpy(t->xyz+12*j,(void*)ngb_guest_pointer(slot_addr+16*j,12),12);
 memcpy(t->mat,(void*)ngb_guest_pointer(0x950180,64),64);}
 else memcpy(t->out,(void*)ngb_guest_pointer(slot_addr,48),48);
 return;}
 if(!route){if(nfirst==32)abort();first_geo[nfirst++]=*c;}
 else{struct geo_set *p=NULL;for(unsigned j=0;j<nfirst;j++)if(first_geo[j].actor==c->actor){if(p)abort();p=first_geo+j;}
 if(p){if(c->filled&&p->filled){unsigned n=c->n,v=n==p->n;
 unsigned r=v&&!memcmp(c->raw,p->raw,n*64),t=v&&!memcmp(c->types,p->types,n*2),x=v&&!memcmp(c->field1,p->field1,n)&&!memcmp(c->field2,p->field2,n);
 sel_all++;sel_input+=!memcmp(c->input,p->input,16);sel_raw+=r;sel_type+=t;sel_aux+=x;sel_id+=r&&t&&x;}
 gs.matched_actor++;int ge=p->n==c->n,mt=ge;
 for(unsigned i=0;i<c->n;i++){struct geo_tri *t=c->tri+i;unsigned g=0,b=0;
 for(unsigned j=0;j<p->n;j++){struct geo_tri *v=p->tri+j;unsigned gv=!memcmp(t->xyz,v->xyz,36),mv=!memcmp(t->mat,v->mat,64);g|=gv;b|=gv&&mv;
 if(i==j){gs.geom_slots+=gv;gs.mat_slots+=mv;gs.both_slots+=gv&&mv;ge&=gv;mt&=mv;}
 if(gv&&mv){gs.outputs++;gs.bad+=memcmp(v->out,t->out,48)!=0;}}
 gs.any_geom+=g;gs.any_both+=b;}
 gs.same_geometry+=ge&&c->n;gs.same_transform_set+=ge&&mt&&c->n;}}
 geo_open=0;
}
void geo_event(unsigned k,unsigned si,unsigned sp){geo_event_c(k,si,sp);}
static void geo_frame(unsigned f){if(geo_open)abort();nfirst=0;if(f==30||f==120){if(sel_all)fprintf(stderr,"[SELECTION] %u paired=%u input=%u raw=%u types=%u aux=%u complete=%u\n",f,sel_all,sel_input,sel_raw,sel_type,sel_aux,sel_id);sel_all=sel_input=sel_raw=sel_type=sel_aux=sel_id=0;fprintf(stderr,"[GEOMETRY] %u calls=%u:%u tris=%u:%u actor=%u sets=%u sets_with_matrix=%u slot_geom=%u slot_mat=%u slot_both=%u any_geom=%u any_both=%u out_pairs=%u bad_outputs=%u\n",f,gs.calls[0],gs.calls[1],gs.tri[0],gs.tri[1],gs.matched_actor,gs.same_geometry,gs.same_transform_set,gs.geom_slots,gs.mat_slots,gs.both_slots,gs.any_geom,gs.any_both,gs.outputs,gs.bad);memset(&gs,0,sizeof gs);}}

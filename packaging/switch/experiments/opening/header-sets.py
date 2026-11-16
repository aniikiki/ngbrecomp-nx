"""Count exact cache-key misses for live and shadow layouts on the producer thread."""
def transform(t):
    k='        if (r.key != header) r = {header, &sent_headers_[header]};';assert t.count(k)==1
    t=t.replace(k,'        hs_probe(header,r.key != header,0);\n'+k)
    k='        recent_[(header >> 4) & 63] = {};';assert t.count(k)==1
    return 'extern "C" void hs_probe(unsigned,unsigned,unsigned);\n'+t.replace(k,'        hs_probe(header,0,1);\n'+k)
counters=r"""
static _Thread_local unsigned hs_phase,hs_live,hs_calls,hs_up,hs_misses[4],hs_keys[4][256];
void hs_probe(unsigned h,unsigned miss,unsigned up){
 for(unsigned k=0;k<4;k++){
 unsigned key=h>>4;if(k&1)key^=h>>12;
 unsigned slot=key&((k&2)?255:63);
 if(hs_phase&&!up)hs_misses[k]+=hs_keys[k][slot]!=h;
 hs_keys[k][slot]=up?0:h;
 }
 if(hs_phase){if(up){hs_up++;}else{hs_calls++;hs_live+=miss;}}
}
void phase_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[HEADER_SETS] %u %u %u %u %u %u %u %u\n",f,hs_calls,hs_up,hs_live,hs_misses[0],hs_misses[1],hs_misses[2],hs_misses[3]);
 if(!f||f==30){hs_calls=hs_up=hs_live=0;memset(hs_misses,0,sizeof hs_misses);}
 hs_phase=f<120;
}
"""

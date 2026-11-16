/* REP STOSD has no intermediate service point in the lift. Accept only
 * complete ordinary spans. Backwards writes have the same final value. */
static inline int ngb_stos_fast(uint32_t dst,uint32_t count,uint32_t word,int backward){
 if(!count)return 1;
 if(count>16384)return 0;
 uint32_t bytes=count*4,first=backward?dst-(bytes-4):dst;
 if((backward && first>dst) || first+bytes<first)return 0;
 uint32_t end=first+bytes-1;
 for(uint32_t pg=first>>12;pg<=(end>>12);pg++){
    unsigned need=pg==(end>>12)?(end&4095)+1:4096;
    if(ngb_fast_page_bytes[pg]<need)return 0;
 }
 unsigned char *out=ngb_fast_ram+(first&0x7fffffff);
 if((word&255)*UINT32_C(0x01010101)==word)__builtin_memset(out,(unsigned char)word,bytes);
 else for(uint32_t i=0;i<count;i++)__builtin_memcpy(out+4*i,&word,4);
 return 1;
}

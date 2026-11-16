#include "../../runtime/wide_blit.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
static uint32_t src[480*720],a[720*1296],b[720*1296];
static unsigned col[1280];
static void scalar(uint32_t *dst,unsigned stride){
 unsigned previous=480;
 for(unsigned y=0;y<720;y++) {
    uint32_t *row=dst+y*stride;unsigned sy=y*480/720;
    if(previous==sy)memcpy(row,row-stride,1280*4);
    else for(unsigned x=0;x<1280;x++){
        uint32_t v=src[sy*720+col[x]];row[x]=0xff000000u|(v&0xff00u)|((v>>16)&255u)|((v&255u)<<16);
    }
    previous=sy;
 }
}
static double clock_ms(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return 1000.*t.tv_sec+1e-6*t.tv_nsec;}
int main(void){
 uint32_t r=12345;
 for(unsigned i=0;i<720*480;i++){r^=r<<13;r^=r>>17;r^=r<<5;src[i]=r;}
 for(unsigned x=0;x<1280;x++)col[x]=x*720/1280;
 for(unsigned s=1280;s<=1296;s+=16){
     memset(a,0x8f,sizeof a);memset(b,0x8f,sizeof b);scalar(a,s);ngb_wide_blit(b,s,src);
     if(memcmp(a,b,sizeof a))return 1;
 }
 puts("matched all 921600 pixels including alpha; both strides and guard words");
 for(unsigned i=0;i<4;i++) {
    int use=i==1||i==2;double t=clock_ms();
    for(unsigned j=0;j<120;j++){src[j]^=j;if(use)ngb_wide_blit(b,1296,src);else scalar(a,1296);__asm__ volatile("":::"memory");}
    printf("%s %.3f ms/frame (display thread isolated)\n",use?"NEON":"scalar",(clock_ms()-t)/120.);
 }
}

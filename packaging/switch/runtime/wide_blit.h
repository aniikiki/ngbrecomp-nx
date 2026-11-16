#pragma once
#include <arm_neon.h>
#include <stdint.h>
/* 720x480 -> 1280x720; each 9 source pixels produce 16 pixels. Two
 * adjacent lines share source row 2*y; never read back the display surface.
 * Preserve the scalar path's channel swizzle and opaque alpha exactly. */
static inline void ngb_wide_rows(uint32_t *row,uint32_t *repeat,const uint32_t *src)
{
    static const unsigned char lut[4][16]={
#define PX(i) (4*(i)+2),(4*(i)+1),(4*(i)),(4*(i)+3)
        {PX(0),PX(0),PX(1),PX(1)}, {PX(2),PX(2),PX(3),PX(3)},
        {PX(4),PX(5),PX(5),PX(6)}, {PX(6),PX(7),PX(7),PX(8)}
#undef PX
    };
    uint8x16_t ix[4];for(unsigned k=0;k<4;k++)ix[k]=vld1q_u8(lut[k]);
    for(unsigned b=0;b<80;b++,src+=9,row+=16) {
        uint8x16x3_t bank={{vreinterpretq_u8_u32(vld1q_u32(src)),vreinterpretq_u8_u32(vld1q_u32(src+4)),
                            vreinterpretq_u8_u32(vld1q_dup_u32(src+8))}};
        for(unsigned k=0;k<4;k++) {
            uint32x4_t out=vorrq_u32(vreinterpretq_u32_u8(vqtbl3q_u8(bank,ix[k])),vdupq_n_u32(0xff000000u));
            vst1q_u32(row+4*k,out);
            if(repeat)vst1q_u32(repeat+16*b+4*k,out);
        }
    }
}
static inline void ngb_wide_blit(uint32_t *dst,unsigned stride,const uint32_t *src)
{
    for(unsigned i=0;i<240;i++,src+=1440,dst+=3*stride) {
        ngb_wide_rows(dst,dst+stride,src);
        ngb_wide_rows(dst+2*stride,0,src+720);
    }
}

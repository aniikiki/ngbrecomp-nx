/* Host shadow only: predicts a miss, then executes the entire original.
 * Limit magnitudes, conditioning, and affine inputs; no speculative guest writes. */
struct boxmemo {unsigned key[3];unsigned char input[168];double center[3],slope[3],span[3];unsigned serial;};
static struct boxmemo boxbank[16][4];static unsigned boxclock;
static int predict_box(unsigned descriptor,unsigned query) {
 if(descriptor<0x7a79c6 || descriptor>0x7a9000)return 0;
 unsigned actor=0x4b4e50+MEM8(descriptor)*0x2800u,boneid=MEM16(descriptor-2);
 if(boneid>=31 || actor>=0x7a0000)return 0;
 unsigned bone=actor+(3+boneid)*64,box=MEM32(descriptor-6),ball=MEM32(query);
 if(box>0xffffffd0u)return 0;
 const void *p=ngb_ram_span(ball,16),*b=ngb_ram_span(box+16,28);
 if(!p||!b)return 0;
 float xyz[4],pad=MEMF(0x4149c4);memcpy(xyz,p,16);
 for(int i=0;i<4;i++)if(!(fabsf(xyz[i])<4096))return 0;
 if(!(pad>=0 && pad<=1 && xyz[3]>=0 && xyz[3]<64))return 0;
 unsigned key[3]={actor,bone,box};
 unsigned char bytes[168];memcpy(bytes,ngb_fast_ram+actor,64);memcpy(bytes+64,ngb_fast_ram+actor+0x8c0,12);memcpy(bytes+76,ngb_fast_ram+bone,64);memcpy(bytes+140,b,28);
 struct boxmemo *bucket=boxbank[((box>>5)^(bone>>6)^(actor>>10))&15],*item=bucket;
 for(unsigned i=0;i<4;i++){
    if(bucket[i].serial&&!memcmp(key,bucket[i].key,12)){item=bucket+i;break;}
    if(bucket[i].serial<item->serial)item=bucket+i;
 }
 if(!item->serial||memcmp(item->key,key,12)||memcmp(item->input,bytes,168)){
   float a[16],l[16],m[4][4],bounds[7];memcpy(a,bytes,64);memcpy(a+12,bytes+64,12);a[15]=MEMF(0x4148c8);memcpy(l,bytes+76,64);memcpy(bounds,bytes+140,28);
   if(a[15]!=1)return 0;
   for(int i=0;i<16;i++)if(!(fabsf(a[i])<4096 && fabsf(l[i])<4096))return 0;
   for(int i=0;i<7;i++)if(!(fabsf(bounds[i])<4096) || (i>=4 && bounds[i]<0))return 0;
   for(int i=0;i<4;i++)for(int j=0;j<4;j++)m[i][j]=((l[4*i]*a[j]+l[4*i+1]*a[j+4])+l[4*i+2]*a[j+8])+l[4*i+3]*a[j+12];
   double mat[3][3];for(int i=0;i<3;i++)for(int j=0;j<3;j++){
       mat[i][j]=m[i][j];if(!(fabs(mat[i][j])<=2 && fabsf(m[3][i])<4096))return 0;}
   double det=mat[0][0]*(mat[1][1]*mat[2][2]-mat[1][2]*mat[2][1])-mat[0][1]*(mat[1][0]*mat[2][2]-mat[1][2]*mat[2][0])+mat[0][2]*(mat[1][0]*mat[2][1]-mat[1][1]*mat[2][0]);
   if(!(fabs(det)>.125))return 0;
   double c[3],h[3],s[3];
   for(int i=0;i<3;i++){c[i]=m[3][i];h[i]=s[i]=0;
    for(int j=0;j<3;j++){
      double v=(mat[(j+1)%3][(i+1)%3]*mat[(j+2)%3][(i+2)%3]-mat[(j+1)%3][(i+2)%3]*mat[(j+2)%3][(i+1)%3])/det;
      c[i]+=v*((double)bounds[j]+bounds[4+j]*.5);h[i]+=fabs(v)*bounds[4+j]*.5;s[i]+=fabs(v);
    }
   }
   memcpy(item->key,key,12);memcpy(item->input,bytes,168);memcpy(item->center,c,24);memcpy(item->span,h,24);memcpy(item->slope,s,24);
 }
 item->serial=++boxclock;
 // Expand in local coordinates before inverse transform, allowing for the
 // original sequence of float operations. This is still checked in shadow.
 for(int i=0;i<3;i++)if(fabs(xyz[i]-item->center[i])>item->span[i]+item->slope[i]*(xyz[3]+pad+.25)+.01)return 1;
 return 0;
}

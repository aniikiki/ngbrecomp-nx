/* Same ordered floating-point operations as leaf.h. Reuse only pose-derived
 * values, keyed by content (including fourth lanes and template data).
 * The test and its architectural side effects still run for EVERY sphere. */
struct contact_pose {
    unsigned char input[160];
    unsigned key;
    V4 mm[4],inv[4];
    float neg[3];
};
static struct contact_pose contact_poses[128];
struct contact_pose *cache=&contact_poses[((bone_addr>>6)^(actor>>10))&127];
unsigned char keybytes[160];memcpy(keybytes,a,64);memcpy(keybytes+64,l,64);
for(unsigned i=0;i<3;i++)memcpy(keybytes+128+i*4,(const char*)&init[i]+12,4);
memcpy(keybytes+140,&one,4);memset(keybytes+144,0,16);
if(cache->key==bone_addr && !memcmp(cache->input,keybytes,144)){
  memcpy(mm,cache->mm,sizeof mm);memcpy(inv,cache->inv,sizeof inv);memcpy(neg,cache->neg,sizeof neg);
}else{
  for(int i=0;i<4;i++)mm[i]=((l[i][0]*a[0]+l[i][1]*a[1])+l[i][2]*a[2])+l[i][3]*a[3];
  for(unsigned i=0;i<3;i++){inv[i]=init[i];for(unsigned j=0;j<3;j++)inv[i][j]=mm[j][i];}
  for(unsigned i=0;i<3;i++)neg[i]=0.f-mm[3][i];
  inv[3]=(neg[0]*inv[0]+neg[1]*inv[1])+neg[2]*inv[2];inv[3][3]=one;
  cache->key=bone_addr;memcpy(cache->input,keybytes,144);memcpy(cache->mm,mm,sizeof mm);
  memcpy(cache->inv,inv,sizeof inv);memcpy(cache->neg,neg,sizeof neg);
}

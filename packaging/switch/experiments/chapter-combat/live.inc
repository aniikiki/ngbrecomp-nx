 /* Private, offline controller only. Reload the route while play continues. */
 static int mode,stick1,stick2,period,hold,mask;
 static unsigned epoch;
 const char *path=getenv("NGB_ROUTE_FILE");
 if(stage>=2 && path && t%6==1){
     FILE *in=fopen(path,"r");int m,a,b,p,h,k;
     if(in){if(fscanf(in,"%d%d%d%d%d%d",&m,&a,&b,&p,&h,&k)==6 && p>0 && h>=0 && h<=p){
         if(mode!=m || stick1!=a || stick2!=b || mask!=k || period!=p || hold!=h)epoch=t;
         mode=m;stick1=a;stick2=b;period=p;hold=h;mask=k;
     }fclose(in);}
 }
 if(stage>=2 && mode){
     float sx=stick1,sy=stick2;
     if(mode==2){
         uint32_t dev=MEM32(0x3d83c8);float dx=stick1*0.01f-x,dz=stick2*0.01f-z;
         sx=MEMF(dev+0xc60)*dx+MEMF(dev+0xc80)*dz;
         sy=MEMF(dev+0xc68)*dx+MEMF(dev+0xc88)*dz;
         float len=hypotf(sx,sy);if(len>0.1f){sx*=31000/len;sy*=31000/len;}else sx=sy=0;
     }
     xaxis=sx;yaxis=sy;button=((t-epoch)%period<(unsigned)hold)?mask:0;
 }
 ngb_ohci_pad_sample(button,xaxis,yaxis,0,0);
 if(path && stage>=2 && t%36==1){
     static uint32_t surface[240][360];static unsigned char rgb[240][360][3];
     ngb_scanout_blit(&surface[0][0],360,360,240);
     for(unsigned j=0;j<240;j++)for(unsigned i=0;i<360;i++)for(unsigned k=0;k<3;k++)rgb[j][i][k]=surface[j][i]>>(8*k);
     char temp[512],dest[512];snprintf(dest,sizeof dest,"%s.ppm",path);snprintf(temp,sizeof temp,"%s.tmp",path);
     FILE *fp=fopen(temp,"wb");if(fp){fprintf(fp,"P6 360 240 255\n");fwrite(rgb,sizeof rgb,1,fp);fclose(fp);rename(temp,dest);}
 }

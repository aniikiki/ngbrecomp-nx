unsigned bias_draw_serial;
static unsigned bias_on,bias_prev,bias_serial,bias_value,bias_a,bias_b,bias_pairs,bias_equal,bias_drawn,bias_other;
static void bias_visit(unsigned pc,unsigned value){
 if(pc==0x1d6f8c)++bias_a;
 else if(pc==0x1d77fb)++bias_b;
 else ++bias_other;
 if(pc==0x1d77fb && bias_prev==0x1d6f8c){
  ++bias_pairs;bias_equal+=value==bias_value;bias_drawn+=bias_draw_serial!=bias_serial;
 }
 bias_prev=pc;bias_value=value;bias_serial=bias_draw_serial;
}
static void bias_flip(unsigned f){
 if(f==30||f==120)fprintf(stderr,"[BIAS_PAIR] %u set=%u restore=%u pairs=%u equal=%u with_draw=%u other=%u\n",f,bias_a,bias_b,bias_pairs,bias_equal,bias_drawn,bias_other);
 if(!f||f==30)bias_a=bias_b=bias_pairs=bias_equal=bias_drawn=bias_other=0;
 bias_on=f<120;bias_prev=0;
}

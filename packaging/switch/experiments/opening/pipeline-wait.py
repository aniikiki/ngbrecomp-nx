"""Capture bounded monotonic intervals for pipeline creation and title waits."""
def backend(s):
 k='        if (d_.vkCreateGraphicsPipelines(dev_, pcache_, 1, &ci, nullptr, &pipe) != VK_SUCCESS) pipe = VK_NULL_HANDLE;'
 assert s.count(k)==1
 return 'extern "C" unsigned long long pw_now(void); extern "C" void pw_done(unsigned,unsigned long long);\n'+s.replace(k,'        auto pw_start=pw_now();\n'+k+'\n        pw_done(1,pw_start);')
def wait(t):
 k='        ngb_direct_render_event(false, true);';end='            ngb_direct_render_event(false, false);';assert t.count(k)==t.count(end)==1
 return 'extern "C" unsigned long long pw_now(void); extern "C" void pw_done(unsigned,unsigned long long);\n'+t.replace(k,'        auto pw_start=pw_now();\n'+k).replace(end,end+'\n            pw_done(0,pw_start);')
counters=r"""
#include <pthread.h>
static pthread_mutex_t pw_m=PTHREAD_MUTEX_INITIALIZER;
static struct {unsigned kind;unsigned long long a,b;} pw_rows[8192];
static unsigned pw_n,pw_over;
unsigned long long pw_now(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))abort();return t.tv_sec*1000000000ull+t.tv_nsec;}
void pw_done(unsigned k,unsigned long long a){unsigned long long b=pw_now();pthread_mutex_lock(&pw_m);
 if(pw_n<8192){pw_rows[pw_n].kind=k;pw_rows[pw_n].a=a;pw_rows[pw_n++].b=b;}else pw_over++;
 pthread_mutex_unlock(&pw_m);}
void phase_flip(unsigned f){unsigned long long b=pw_now();static unsigned long long flip[121];
 if(f>120)return;
 flip[f]=b;
 if(f==120){pthread_mutex_lock(&pw_m);
 for(unsigned i=0;i<=120;i++)fprintf(stderr,"[PW_FLIP] %u %llu\n",i,flip[i]);
 for(unsigned i=0;i<pw_n;i++)fprintf(stderr,"[PW_EVENT] %u %llu %llu\n",pw_rows[i].kind,pw_rows[i].a,pw_rows[i].b);
 fprintf(stderr,"[PW_LOST] %u\n",pw_over);pthread_mutex_unlock(&pw_m);}
}
"""

char __executable_start;
#include "provenance.c"
#include <assert.h>
int main(void){
  uint8_t *ram=calloc(RAM,1);assert(ram);
  dep_bind(ram);dep_flip(1801,tasks[1]);__tsan_write4(ram);ram[0]=1;ram[1]=2;
  dep_key(tasks[2]);__tsan_read4(ram);
  assert(edges[0][1][2]==2);
  __tsan_write4(ram+1);ram[1]=3;ram[2]=4;dep_key(tasks[3]);
  assert(edges[2][1][2]==1);
  __tsan_read4(ram);assert(edges[0][1][3]==1 && edges[0][2][3]==2);
  dep_key(tasks[1]);__tsan_write_range(ram,32);memset(ram,9,32);
  dep_key(tasks[4]);__tsan_read_range(ram,32);assert(edges[0][1][4]==32);
  assert(edges[1][2][1]==2 && edges[1][3][1]==4);
  printf("Byte provenance: changed values, overwritten producers, reader ordering, overlap and bulk hooks verified\n");
}

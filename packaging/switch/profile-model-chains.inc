/* Offline observer only. Fingerprint list topology, never cache guest values. */

#include <stdio.h>
#include <string.h>
static struct { uint32_t address; uint64_t desc; unsigned used; } plans[4096];
static unsigned chain_calls, nulls, valid, matched, nodes, custom, incomplete;
static void observe_chain(uint32_t address) {
 ++chain_calls;
 if (!address) { ++nulls; return; }
 uint32_t p = address;
 uint64_t h = 1469598103934665603ull;
 unsigned n = 0, c = 0;
 for (; p && n < 32; ++n) {
   const unsigned char *data = ngb_ram_span(p,16); if (!data) break;
   uint32_t next; memcpy(&next,data+12,4);
   h=(h^p)*1099511628211ull;
   h=(h^data[0])*1099511628211ull;
   h=(h^data[1])*1099511628211ull;
   if (data[0]==254 && (data[1]==10||data[1]==11)) {
     uint32_t target; memcpy(&target,data+4,4);
     h=(h^target)*1099511628211ull; ++c;
   }
   p=next;
 }
 if (p) { ++incomplete; return; }
 ++valid; nodes+=n; custom+=c;
 unsigned i=((address>>4)*2654435761u)>>20;
 if (plans[i].used && plans[i].address==address && plans[i].desc==h) ++matched;
 plans[i].used=1; plans[i].address=address; plans[i].desc=h;
}
void dump_model(unsigned f) {
 fprintf(stderr,"[CHAIN] end=%u calls=%u null=%u valid=%u repeat=%u nodes=%u fe_callbacks=%u incomplete=%u\n",
   f,chain_calls,nulls,valid,matched,nodes,custom,incomplete);
 chain_calls=nulls=valid=matched=nodes=custom=incomplete=0;
}

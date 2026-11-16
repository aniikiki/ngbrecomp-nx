"""Measure scalar widths, alignment and locality of ordinary nonliteral
translations. Per unit, history excludes literal/slow accesses and is reset
each frame; intervening work from other units is not observed."""
from pathlib import Path
p=Path(__file__).resolve().parent
src=(p/'memory-census.py').read_text().replace('opening-memory-census','opening-page-shape')
a=src.index('    extern unsigned census_active;');b=src.index("'''+k)",a)
src=src[:a]+'''    extern unsigned shape_active,shape_page[4];
    extern uint64_t shape_counts[4][16];
    if(shape_active){
      uint64_t *row=shape_counts[CENSUS_UNIT]; unsigned page=address>>12;
      unsigned w=bytes==1?0:bytes==2?1:bytes==4?2:bytes==8?3:4;
      if(ngb_static_image_span(address,bytes) && ngb_fast_ram)row[0]++;
      else if((address&4095u)+bytes>ngb_fast_page_bytes[page])row[1]++;
      else {row[2+w]++;
        if((address&(bytes-1))==0)row[7+w]++;
        if(shape_page[CENSUS_UNIT]==page)row[12]++;
        if(page==(g_esp>>12))row[13]++;
        if(bytes>1 && (address&4095u)<=4080u)row[14]++;
        shape_page[CENSUS_UNIT]=page;
      }
      row[15]++;
    }
'''+src[b:]
exec(compile(src,'page-shape-build','exec'))

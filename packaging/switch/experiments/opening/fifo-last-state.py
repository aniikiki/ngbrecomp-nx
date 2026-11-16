"""Publish the final retired method once: no callback or observation inside the group."""
def transform(s):
 a=s.index('static unsigned retire_state_packets(');b=s.index('\n}',a)+2;body=s[a:b]
 old='        *state = ((header & NV_PFIFO_CACHE1_DMA_STATE_METHOD) + 4 * (words - 1)) & NV_PFIFO_CACHE1_DMA_STATE_METHOD;'
 k='    packet_count += packets;'
 assert body.count(old)==body.count(k)==1 and body.count('*state')==2
 body=body.replace('uint32_t header = first;', 'uint32_t header = first, last_header; unsigned last_words;').replace(old,'        last_header = header; last_words = words;').replace(k,'    *state = ((last_header & NV_PFIFO_CACHE1_DMA_STATE_METHOD) + 4 * (last_words - 1)) & NV_PFIFO_CACHE1_DMA_STATE_METHOD;\n'+k)
 return s[:a]+body+s[b:]

"""Use the terminal header already read by the ordinary-page retirement loop."""
def transform(s):
 def rep(a,b):
    nonlocal s
    assert s.count(a)==1,a
    s=s.replace(a,b)
 rep('uint32_t limit, uint32_t *state)\n{\n    unsigned words', 'uint32_t limit, uint32_t *state, uint32_t *next, unsigned *ready)\n{\n    unsigned words')
 k='    } while (words && words <= available - used);'
 rep(k,k+'''
    // used < available means the complete following word was read from
    // this mapping, even when its own packet is incomplete. Parse normally.
    if(used<available){*next=header;*ready=1;}
''')
 rep('        unsigned retired = retire_state_packets(word, base, *get, put, desc[1], state);','        uint32_t next=0; unsigned ready=0;\n        unsigned retired = retire_state_packets(word, base, *get, put, desc[1], state,&next,&ready);')
 rep('            *get += retired;\n            continue;', '            *get += retired;\n            if(!ready)continue;\n            word=next;')
 return s

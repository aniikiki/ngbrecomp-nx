"""Check the new magnitude predicate on every exponent, both signs and mantissa endpoints."""
import struct
for sign in (0,1):
 for e in range(256):
  for m in (0,1,2,0x123456,0x7ffffe,0x7fffff):
   v=(sign<<31)|(e<<23)|m;mag=v&0x7fffffff
   ref=mag==0 or (97<<23)<=mag<=(157<<23)
   assert ref==(mag==0 or ((mag-(97<<23))&0xffffffff)<=(60<<23))
print("3072 binary32 patterns agree; subtraction wraps below lower bound.")

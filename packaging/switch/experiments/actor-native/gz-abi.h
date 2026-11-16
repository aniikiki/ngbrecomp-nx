#pragma once
/* Stable zlib file API. The offline ARM runner ships libz.so.1 without
 * development headers. No z_stream struct or internal zlib ABI is used. */
typedef struct gzFile_s *gzFile;
extern gzFile gzopen(const char *,const char *);
extern int gzwrite(gzFile,const void *,unsigned);
extern int gzread(gzFile,void *,unsigned);
extern int gzgetc(gzFile);
extern int gzclose(gzFile);
#define Z_OK 0

#define _POSIX_C_SOURCE 200809L
#define _DARWIN_C_SOURCE
#include "files.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); exit(1); } } while (0)
static uint32_t u32(const void *p) { uint32_t n; memcpy(&n, p, 4); return n; }
static uint64_t u64(const void *p) { uint64_t n; memcpy(&n, p, 8); return n; }
int main(void)
{
    char temp[] = "/tmp/ngb-files-XXXXXX", disc[1024], data[1024], path[1200];
    CHECK(mkdtemp(temp));
    snprintf(disc, sizeof(disc), "%s/disc", temp);
    snprintf(data, sizeof(data), "%s/data", temp);
    CHECK(mkdir(disc, 0700) == 0);
    snprintf(path, sizeof(path), "%s/Mixed.bin", disc);
    FILE *f = fopen(path, "wb"); CHECK(f);
    CHECK(fwrite("0123456789", 1, 10, f) == 10 && fclose(f) == 0);
    CHECK(ngb_files_init(disc, data) == 0);
    uint32_t dir, file, info, count;
    unsigned char buffer[64];
    CHECK(ngb_file_open("\\Device\\Harddisk0\\partition1\\", 0, 0x100001, 3, 1, 0x800021, &dir, &info) == 0);
    CHECK(info == 1);
    memset(buffer, 0xa5, sizeof(buffer));
    CHECK(ngb_file_volume(dir, 3, buffer, 23, &count) == 0xc0000023u && count == 0 && buffer[0] == 0xa5);
    CHECK(ngb_file_volume(dir, 3, buffer, 24, &count) == 0 && count == 24 && buffer[24] == 0xa5);
    CHECK(u32(buffer + 16) * u32(buffer + 20) == 16384);
    CHECK(u64(buffer) * 16384 <= NGB_DATA_MAX_BYTES && u64(buffer + 8) <= u64(buffer));
    CHECK(ngb_file_open("TDATA", dir, 0x120117, 3, 3, 0x4021, &file, &info) == 0 && info == 2);
    CHECK(ngb_file_close(file) == 0);
    CHECK(ngb_file_link("\\??\\T:", "\\Device\\Harddisk0\\partition1\\TDATA") == 0);
    CHECK(ngb_file_open("t:\\", 0, 0x100001, 3, 1, 0x21, &file, &info) == 0);
    CHECK(ngb_file_close(file) == 0);
    CHECK(ngb_file_close(dir) == 0 && ngb_file_close(dir) == NGB_FS_INVALID_HANDLE);
    CHECK(ngb_file_open("D:\\mixed.BIN", 0, 0x80000000, 0, 1, 0x60, &file, &info) == 0);
    uint32_t duplicate;
    CHECK(ngb_file_open("D:\\Mixed.bin", 0, 1, 1, 1, 0x60, &duplicate, &info) == 0xc0000043u);
    CHECK(ngb_file_read(file, buffer, 3, 2, &count) == 0 && count == 3 && !memcmp(buffer, "234", 3));
    CHECK(ngb_file_read(file, buffer, 2, -2, &count) == 0 && count == 2 && !memcmp(buffer, "56", 2));
    CHECK(ngb_file_position(file, 8) == 0);
    CHECK(ngb_file_read(file, buffer, 4, -2, &count) == 0 && count == 2 && !memcmp(buffer, "89", 2));
    CHECK(ngb_file_read(file, buffer, 4, -2, &count) == 0xc0000011u && count == 0);
    CHECK(ngb_file_read(file, buffer, 0, -2, &count) == 0);
    CHECK(ngb_file_query(file, 5, buffer, 24, &count) == 0 && count == 24 && u64(buffer + 8) == 10);
    uint32_t stale = file;
    CHECK(ngb_file_close(file) == 0);
    CHECK(ngb_file_open("D:\\Mixed.bin", 0, 1, 3, 1, 0x60, &file, &info) == 0 && file != stale);
    CHECK(ngb_file_read(stale, buffer, 1, 0, &count) == NGB_FS_INVALID_HANDLE);
    CHECK(ngb_file_close(file) == 0);
    CHECK(ngb_file_open("D:\\", 0, 1, 3, 1, 0x21, &dir, &info) == 0);
    CHECK(ngb_file_open("mixed.bin", dir, 1, 3, 1, 0x60, &file, &info) == 0);
    CHECK(ngb_file_close(file) == 0);
    CHECK(ngb_file_open("..\\secret", dir, 1, 3, 1, 0x60, &file, &info) == 0xc0000022u);
    CHECK(ngb_file_open("D:\\Mixed.bin", 0, 0x40000000, 3, 1, 0x60, &file, &info) == 0xc0000022u);
    /* Xbox XAPI removes a stale level archive with a DELETE-only handle. */
    uint32_t cache, reader, remove_handle, other;
    CHECK(ngb_file_open("D:\\Mixed.bin",0,0x10000,7,1,0x4040,&other,&info)==0xc0000022u);
    CHECK(!ngb_file_open("E:\\evict.afs",0,0xc0000000,7,3,0x60,&cache,&info));
    CHECK(!ngb_file_write(cache,"old",3,0,&count) && count==3);
    CHECK(!ngb_file_close(cache));
    CHECK(!ngb_file_open("E:\\evict.afs",0,1,7,1,0x60,&reader,&info));
    CHECK(!ngb_file_open("E:\\evict.afs",0,0x10000,7,1,0x4040,&remove_handle,&info));
    CHECK(ngb_file_disposition(reader,1)==0xc0000022u);
    CHECK(!ngb_file_disposition(remove_handle,1));
    CHECK(ngb_file_open("E:\\evict.afs",0,1,7,1,0x60,&other,&info)==0xc0000056u);
    CHECK(!ngb_file_disposition(remove_handle,0));
    CHECK(!ngb_file_open("E:\\evict.afs",0,1,7,1,0x60,&other,&info));
    CHECK(!ngb_file_close(other));
    CHECK(!ngb_file_disposition(remove_handle,1) && !ngb_file_close(remove_handle));
    CHECK(!ngb_file_read(reader,buffer,3,0,&count) && count==3 && !memcmp(buffer,"old",3));
    CHECK(!ngb_file_close(reader));
    CHECK(ngb_file_open("E:\\evict.afs",0,1,7,1,0x60,&other,&info)==0xc0000034u);
    CHECK(ngb_file_open("E:\\new.bin", 0, 0xc0000000, 3, 3, 0x60, &file, &info) == 0);
    CHECK(ngb_file_write(file, "abc", 3, 0, &count) == 0 && count == 3);
    CHECK(ngb_file_write(file, "!", 1, -1, &count) == 0 && count == 1);
    CHECK(ngb_file_read(file, buffer, 4, 0, &count) == 0 && !memcmp(buffer, "abc!", 4));
    CHECK(ngb_file_query(file, 34, buffer, 56, &count) == 0 && count == 56 && u64(buffer + 40) == 4);
    CHECK(ngb_file_open("E:\\new.bin", 0, 0x40000000, 0, 5, 0x60, &duplicate, &info) == 0xc0000043u);
    CHECK(ngb_file_open("D:\\Mixed.bin", 0, 1, 3, 5, 0x60, &duplicate, &info) == 0xc0000022u);
    CHECK(ngb_file_open("E:\\cache.bin", 0, 0xc0000000, 3, 5, 0x60, &duplicate, &info) == 0 && info == 2);
    CHECK(ngb_file_write(duplicate, "cache", 5, 0, &count) == 0 && count == 5);
    CHECK(ngb_file_close(duplicate) == 0);
    CHECK(ngb_file_open("E:\\cache.bin", 0, 0xc0000000, 3, 5, 0x60, &duplicate, &info) == 0 && info == 3);
    CHECK(ngb_file_query(duplicate, 5, buffer, 24, &count) == 0 && u64(buffer + 8) == 0);
    CHECK(ngb_file_close(duplicate) == 0);
    CHECK(ngb_file_resize(file, 32, 0) == 0);
    CHECK(ngb_file_query(file, 14, buffer, 8, &count) == 0 && u64(buffer) == 4);
    CHECK(ngb_file_read(file, buffer, 28, -2, &count) == 0 && count == 28);
    for (unsigned i = 0; i < 28; ++i) CHECK(!buffer[i]);
    CHECK(ngb_file_resize(file, 16384, 1) == 0);
    CHECK(ngb_file_query(file, 5, buffer, 24, &count) == 0 && u64(buffer+8) == 32);
    CHECK(ngb_file_resize(file, NGB_FILE_MAX_BYTES+1, 0) == 0xc000007fu);
    CHECK(ngb_file_resize(file, 4, 0) == 0);
    CHECK(ngb_file_read(file, buffer, 4, 0, &count) == 0 && !memcmp(buffer, "abc!", 4));
    /* Information queries belong to the open object even when its path is
     * unavailable. Host POSIX rename lets us exercise that distinction. */
    char moved[1200];
    snprintf(path, sizeof(path), "%s/hdd/partition1/new.bin", data);
    snprintf(moved, sizeof(moved), "%s/hdd/partition1/held.bin", data);
    CHECK(rename(path, moved) == 0);
    CHECK(ngb_file_query(file, 34, buffer, 56, &count) == 0 && count == 56 && u64(buffer + 40) == 4);
    CHECK(rename(moved, path) == 0);
    CHECK(ngb_file_write(file, "x", 1, NGB_FILE_MAX_BYTES, &count) == 0xc000007fu && count == 0);
    CHECK(ngb_file_write(file, "", 0, NGB_FILE_MAX_BYTES + 1, &count) == 0 && count == 0);
    CHECK(ngb_file_close(file) == 0);
    CHECK(ngb_file_open("\\Device\\Harddisk0\\partition0", 0, 0xc0100000, 3, 1, 0x10, &file, &info) == 0);
    unsigned char sector[513]; memset(sector, 0xa5, sizeof(sector));
    CHECK(ngb_file_read(file, sector, 512, 0x800, &count) == 0 && count == 512 && sector[512] == 0xa5);
    CHECK(!memcmp(sector, "****PARTINFO****", 16));
    CHECK(u32(sector + 48 + 16) == 0x80000000 && u32(sector + 48 + 20) == 0x400);
    CHECK(ngb_file_read(file, sector, 1, 4096, &count) == NGB_FS_UNSUPPORTED && count == 0);
    CHECK(ngb_file_write(file, sector, 512, 4096, &count) == NGB_FS_UNSUPPORTED && count == 0);
    CHECK(ngb_file_write(file, "test", 4, 2048, &count) == 0 && count == 4);
    CHECK(ngb_file_read(file, buffer, 4, 2048, &count) == 0 && !memcmp(buffer, "test", 4));
    memset(buffer, 0xa5, sizeof(buffer));
    CHECK(ngb_file_ioctl(file, 0x70000, buffer, 23, &count) == 0xc0000023u && buffer[0] == 0xa5);
    CHECK(ngb_file_ioctl(file, 0x70000, buffer, 24, &count) == 0 && count == 24 && buffer[24] == 0xa5);
    CHECK(u64(buffer) == 1216 && u32(buffer + 20) == 512);
    CHECK(ngb_file_close(file) == 0);
    CHECK(ngb_files_init(disc, data) == 0);
    CHECK(ngb_file_open("\\Device\\Harddisk0\\partition0", 0, 1, 3, 1, 0x10, &file, &info) == 0);
    CHECK(ngb_file_read(file, buffer, 4, 2048, &count) == 0 && !memcmp(buffer, "test", 4));
    CHECK(ngb_file_write(file, "x", 1, 2048, &count) == 0xc0000022u && count == 0);
    CHECK(ngb_file_close(file) == 0);
    CHECK(ngb_file_open("\\Device\\Harddisk0\\Partition5\\", 0, 1, 3, 1, 0x21, &dir, &info) == 0xc000014fu);
    CHECK(ngb_file_open("\\Device\\Harddisk0\\Partition5", 0, 3, 0, 1, 0x18, &file, &info) == 0);
    CHECK(ngb_file_open("\\Device\\Harddisk0\\Partition5", 0, 3, 0, 1, 0x18, &duplicate, &info) == 0xc0000043u);
    CHECK(ngb_file_ioctl(file, 0x74004, buffer, 31, &count) == 0xc0000023u && count == 0);
    CHECK(ngb_file_ioctl(file, 0x74004, buffer, 32, &count) == 0 && count == 32 && u64(buffer+8) == 786432000);
    memset(buffer, 0xa5, sizeof(buffer));
    CHECK(ngb_file_read(file, buffer, 8, 0, &count) == 0 && count == 8 && u64(buffer) == 0 && buffer[8] == 0xa5);
    CHECK(ngb_file_write(file, "ABCD", 4, -2, &count) == 0 && count == 4);
    CHECK(ngb_file_read(file, buffer, 12, 0, &count) == 0 && u64(buffer) == 0 && !memcmp(buffer+8,"ABCD",4));
    CHECK(ngb_file_read(file, buffer, 1, NGB_FILE_MAX_BYTES, &count) == NGB_FS_UNSUPPORTED && count == 0);
    CHECK(ngb_file_write(file, "x", 1, NGB_FILE_MAX_BYTES, &count) == 0xc000007fu && count == 0);
    CHECK(ngb_file_dismount(file, 0x1234) == NGB_FS_UNSUPPORTED);
    CHECK(ngb_file_dismount(file, 0x90020) == 0);
    CHECK(ngb_file_read(file, buffer, 1, 0, &count) == 0xc00000a3u);
    CHECK(ngb_file_write(file, "x", 1, 0, &count) == 0xc00000a3u);
    CHECK(ngb_file_close(file) == 0);
    CHECK(ngb_files_init(disc, data) == 0);
    CHECK(ngb_file_open("\\Device\\Harddisk0\\Partition5", 0, 1, 3, 1, 0x18, &file, &info) == 0);
    CHECK(ngb_file_read(file, buffer, 4, 8, &count) == 0 && !memcmp(buffer, "ABCD", 4));
    CHECK(ngb_file_close(file) == 0);
    CHECK(ngb_file_open("D:\\missing.bin", 0, 1, 3, 1, 0x60, &file, &info) == 0xc0000034u);
    snprintf(path, sizeof(path), "%s/link", disc);
    CHECK(symlink("Mixed.bin", path) == 0);
    CHECK(ngb_file_open("D:\\link", 0, 1, 3, 1, 0x60, &file, &info) == 0xc0000022u);
    ngb_files_close_all();
    /* Reopen with a cache larger than the entire save quota. The title
     * still has its free blocks and can write/read its existing save. */
    snprintf(path,sizeof(path),"%s/hdd/partition5",data);
    CHECK(mkdir(path,0700)==0);
    snprintf(path,sizeof(path),"%s/hdd/partition5/level.afs",data);
    f=fopen(path,"wb"); CHECK(f && !ftruncate(fileno(f),40*1024*1024) && !fclose(f));
    CHECK(!ngb_files_init(disc,data));
    CHECK(!ngb_file_open("E:\\",0,0x100001,3,1,0x800021,&dir,&info));
    CHECK(!ngb_file_volume(dir,3,buffer,24,&count) && u64(buffer+8)>1024);
    CHECK(!ngb_file_open("E:\\new.bin",0,0xc0000000,3,1,0x60,&file,&info));
    CHECK(!ngb_file_write(file,"OK",2,0,&count) && count==2);
    CHECK(!ngb_file_read(file,buffer,2,0,&count) && count==2 && !memcmp(buffer,"OK",2));
    ngb_files_close_all(); CHECK(!unlink(path));
    snprintf(path,sizeof(path),"%s/hdd/partition5",data); CHECK(!rmdir(path));
    /* Existing data is charged again on restart, rather than resetting the
     * quota counter and permitting unlimited growth over repeated runs. */
    snprintf(path, sizeof(path), "%s/hdd/partition1/quota.bin", data);
    f = fopen(path, "wb"); CHECK(f);
    CHECK(ftruncate(fileno(f), NGB_DATA_MAX_BYTES - 4 - 4096 - 12) == 0 && fclose(f) == 0);
    CHECK(ngb_files_init(disc, data) == 0);
    CHECK(ngb_file_open("E:\\new.bin", 0, 0x40000000, 3, 1, 0x60, &file, &info) == 0);
    CHECK(ngb_file_write(file, "x", 1, 4, &count) == 0xc000007fu && count == 0);
    CHECK(ngb_file_write(file, "x", 1, 0, &count) == 0 && count == 1);
    ngb_files_close_all();
    CHECK(unlink(path) == 0);
    /* Header creation consumes the shared quota too; an interrupted/truncated
     * header is rejected on restart instead of silently resetting it. */
    snprintf(path, sizeof(path), "%s/hdd/partition0-header.bin", data); CHECK(unlink(path) == 0);
    snprintf(path, sizeof(path), "%s/hdd/partition1/quota.bin", data);
    f = fopen(path, "wb"); CHECK(f);
    CHECK(ftruncate(fileno(f), NGB_DATA_MAX_BYTES - 4 - 12) == 0 && fclose(f) == 0);
    CHECK(ngb_files_init(disc, data) == 0);
    CHECK(ngb_file_open("\\Device\\Harddisk0\\partition0", 0, 3, 3, 1, 0x10, &file, &info) == 0);
    CHECK(ngb_file_write(file, "x", 1, 2048, &count) == 0xc000007fu && count == 0);
    ngb_files_close_all(); CHECK(unlink(path) == 0);
    snprintf(path, sizeof(path), "%s/hdd/partition0-header.bin", data);
    f = fopen(path, "wb"); CHECK(f); CHECK(fputs("short", f) >= 0 && fclose(f) == 0);
    CHECK(ngb_files_init(disc, data) != 0); CHECK(unlink(path) == 0);
    snprintf(path, sizeof(path), "%s/hdd/cache-partition5.bin", data); CHECK(unlink(path) == 0);
    snprintf(path, sizeof(path), "%s/hdd/partition1/cache.bin", data); CHECK(unlink(path) == 0);
    snprintf(path, sizeof(path), "%s/hdd/partition1/new.bin", data); CHECK(unlink(path) == 0);
    snprintf(path, sizeof(path), "%s/link", disc);
    CHECK(unlink(path) == 0);
    snprintf(path, sizeof(path), "%s/Mixed.bin", disc); CHECK(unlink(path) == 0);
    CHECK(rmdir(disc) == 0);
    snprintf(path, sizeof(path), "%s/hdd/partition1/TDATA", data); CHECK(rmdir(path) == 0);
    snprintf(path, sizeof(path), "%s/hdd/partition1", data); CHECK(rmdir(path) == 0);
    snprintf(path, sizeof(path), "%s/hdd", data); CHECK(rmdir(path) == 0);
    CHECK(rmdir(data) == 0 && rmdir(temp) == 0);
    puts("Guest files: FATX geometry, paths, real reads, EOF, sharing, stale handles and isolation passed");
}

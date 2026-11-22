#pragma once
#include <stddef.h>
#include <stdio.h>
#include <stdint.h>
#define NGB_FS_UNSUPPORTED 0xc0000002u
#define NGB_FS_INVALID_HANDLE 0xc0000008u
#define NGB_FS_PENDING 0x103u
#define NGB_FS_TIMEOUT 0x102u
#define NGB_FILE_MAX_BYTES (1024u * 1024u)
#define NGB_DATA_MAX_BYTES (32u * 1024u * 1024u)
int ngb_files_init(const char *disc_root, const char *data_root);
int ngb_files_init_indexed(const char *disc_root, const char *data_root, const char *cache_dir);
/* The retail loader can read its AFS archives in place on an extracted disc. */
extern int ngb_disc_archives_direct;
int ngb_files_close_all(void);
int ngb_queue_menu_profile(const void *bytes, unsigned size);
uint32_t ngb_file_open(const char *path, uint32_t root, uint32_t access,
                       uint32_t share, uint32_t disposition, uint32_t options,
                       uint32_t *handle, uint32_t *information);
uint32_t ngb_file_disposition(uint32_t handle, int pending);
uint32_t ngb_file_set_basic(uint32_t handle, const void *buffer, uint32_t length);
uint32_t ngb_file_wait_status(uint32_t handle);
uint32_t ngb_file_flush(uint32_t handle);
uint32_t ngb_file_close(uint32_t handle);
const char *ngb_file_basename(uint32_t handle);
const char *ngb_file_async_disc_path(uint32_t handle);
void ngb_file_disc_submitted(uint32_t handle);
void ngb_file_disc_completed(uint32_t handle, int64_t offset, uint32_t received, uint32_t status);
uint32_t ngb_disc_stream_read(FILE *file, void *buffer, uint32_t length,
                              int64_t offset, uint32_t *received);
void ngb_file_disc_textures(const char *name, uint64_t offset, const void *buffer, uint32_t length);
#ifdef NGB_NATIVE_DIAG
int ngb_file_is_cache_archive(uint32_t handle);
#endif
uint32_t ngb_file_read(uint32_t handle, void *buffer, uint32_t length,
                       int64_t offset, uint32_t *received);
uint32_t ngb_file_write(uint32_t handle, const void *buffer, uint32_t length,
                        int64_t offset, uint32_t *written);
uint32_t ngb_file_query(uint32_t handle, uint32_t kind, void *buffer,
                        uint32_t length, uint32_t *received);
uint32_t ngb_file_resize(uint32_t handle, int64_t size, int allocation);
uint32_t ngb_file_position(uint32_t handle, int64_t position);
uint32_t ngb_file_volume(uint32_t handle, uint32_t kind, void *buffer,
                         uint32_t length, uint32_t *received);
uint32_t ngb_file_link(const char *name, const char *target);
uint32_t ngb_file_ioctl(uint32_t handle, uint32_t code, void *out,
                        uint32_t length, uint32_t *received);
uint32_t ngb_file_dismount(uint32_t handle, uint32_t code);

uint32_t ngb_link_open(const char *name, int ignore_case, uint32_t *handle);
uint32_t ngb_link_target(uint32_t handle, char target[1024]);

uint32_t ngb_file_directory(uint32_t handle, const char *pattern, int restart, void *buffer, uint32_t length, uint32_t *done);
FILE *ngb_open_disc_movie(const char *leaf);

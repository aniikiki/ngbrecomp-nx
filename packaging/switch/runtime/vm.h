#pragma once
#include <stddef.h>
#include <stdint.h>

/* Guest virtual allocation area; image/TLS and bootstrap stacks are outside. */
#define NGB_VM_BEGIN 0x01000000u
#define NGB_VM_END   0x03e00000u
void ngb_vm_init(unsigned char *guest_ram);
uint32_t ngb_vm_allocate(uint32_t *base, uint32_t *size, uint32_t zero_bits,
                         uint32_t flags, uint32_t protection);
uint32_t ngb_vm_free(uint32_t *base, uint32_t *size, uint32_t flags);
uint32_t ngb_vm_query(uint32_t address, uint32_t info[7]);
int ngb_vm_access(uint32_t address, size_t bytes);

int ngb_vm_pin(uint32_t address, uint32_t bytes, int unlock);

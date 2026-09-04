
#ifndef CHECKSUM_H
#define CHECKSUM_H
#include <stddef.h>
#include <stdint.h>

/* Implementada en Ensamblador (src/checksum.asm) */
uint64_t pawos_checksum(const unsigned char *datos, size_t len);

#endif

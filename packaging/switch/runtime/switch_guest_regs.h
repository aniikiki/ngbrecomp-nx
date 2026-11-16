#pragma once
/* The libnx guest runner executes all Xbox threads as cooperative fibers on
 * one host thread. The scheduler saves the register file at each hand-off.
 * Select ordinary storage for that file only. The generated and kernel
 * headers still define RECOMP_TLS normally for other thread-local objects. */
#define RECOMP_TLS
#pragma GCC visibility push(hidden)
#include "recomp_regs.h"
#pragma GCC visibility pop
#undef RECOMP_TLS

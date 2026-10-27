#ifndef _PSTAT_H_
#define _PSTAT_H_

#include "param.h"

struct pstat {
  int inuse[NPROC];   // 1 if this slot is in use, 0 otherwise
  int pid[NPROC];     // process ID
  int tickets[NPROC]; // tickets held
  int ticks[NPROC];   // time slices received (numTicks)
  int stride[NPROC];  // STRIDE_BIG / tickets
  int pass[NPROC];    // stride progress
  int size[NPROC];    // memory size in bytes
};

#endif // _PSTAT_H_

#include "types.h"
#include "stat.h"
#include "user.h"
#include "pstat.h"

int
main(void)
{
  struct pstat st;
  int i;

  if(getpinfo(&st) < 0){
    printf(2, "getpinfo failed\n");
    exit();
  }

  printf(1, "PID\tTickets\tStride\tPass\tTicks\n");
  for(i = 0; i < NPROC; i++){
    if(st.inuse[i])
      printf(1, "%d\t%d\t%d\t%d\t%d\n",
             st.pid[i], st.tickets[i], st.stride[i], st.pass[i], st.ticks[i]);
  }
  exit();
}

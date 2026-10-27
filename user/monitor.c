#include "types.h"
#include "stat.h"
#include "user.h"
#include "param.h"
#include "pstat.h"

int
main(int argc, char *argv[])
{
  struct pstat st;
  int interval, samples, sample, i;

  if(argc != 3){
    printf(1, "usage: monitor <interval-ticks> <samples>\n");
    exit();
  }

  interval = atoi(argv[1]);
  samples = atoi(argv[2]);

  printf(1, "time,pid,tickets,ticks\n");

  for(sample = 0; sample < samples; sample++){
    sleep(interval);
    if(getpinfo(&st) < 0){
      printf(1, "getpinfo failed\n");
      exit();
    }
    for(i = 0; i < NPROC; i++)
      if(st.inuse[i])
        printf(1, "%d,%d,%d,%d\n", uptime(), st.pid[i], st.tickets[i], st.ticks[i]);
  }
  exit();
}
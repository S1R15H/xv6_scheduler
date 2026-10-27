#include "types.h"
#include "stat.h"
#include "user.h"

int
main(int argc, char *argv[])
{
  int i, tickets, pid;

  if(argc < 2){
    printf(1, "Usage: schedtest t1 [t2 ...]\n");
    exit();
  }

  printf(1, "schedtest parent pid %d\n", getpid());

  for(i = 1; i < argc; i++){
    tickets = atoi(argv[i]);
    pid = fork();
    if(pid < 0){
      printf(1, "fork failed\n");
      exit();
    }
    if(pid == 0){
      if(settickets(tickets) < 0){
        printf(1, "settickets(%d) failed\n", tickets);
        exit();
      }
      printf(1, "child pid %d tickets %d\n", getpid(), tickets);
      for(;;)
        ;
    }
  }
  exit();
}
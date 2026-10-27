#include "types.h"
#include "stat.h"
#include "user.h"

int
main(void)
{
  int pid1, pid2;
  int i;

  pid1 = fork();
  if(pid1 == 0){
    for(i = 0; i < 20000000; i++)
      ;
    exit();
  }

  pid2 = fork();
  if(pid2 == 0){
    for(i = 0; i < 20000000; i++)
      ;
    exit();
  }

  wait();
  wait();
  ps();
  exit();
}

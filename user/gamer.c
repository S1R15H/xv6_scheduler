#include "types.h"
#include "stat.h"
#include "user.h"

int
main(void)
{
  int i, pid, start;

  for(i = 0; i < 30; i++){
    pid = fork();
    if(pid < 0){
      printf(1, "fork failed\n");
      break;
    }
    if(pid == 0){
      start = uptime();
      while(uptime() - start < 100)
        ;
      exit();
    }
    sleep(20);
  }

  while(wait() >= 0)
    ;
  exit();
}
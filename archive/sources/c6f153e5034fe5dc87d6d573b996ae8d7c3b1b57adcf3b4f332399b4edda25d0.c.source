/* Linux namespace test workload only. Never linked into the scanner. */
#define _GNU_SOURCE 1
#include <pthread.h>
#include <sched.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdatomic.h>
static atomic_int ready;
static atomic_int retire_rep,rep_done,survivor_ready;
static const char *protected;
static int protect_after_exit;
static void *survivor(void *arg){
    (void)arg;atomic_fetch_add(&ready,1);
    while(!atomic_load(&retire_rep))usleep(1000);
    if(protect_after_exit&&open(protected,O_RDONLY)<0)_exit(67);
    atomic_store(&survivor_ready,1);
    for(;;)pause();
    return NULL;
}
static void *representative(void *arg){
    (void)arg;if(unshare(CLONE_FILES))_exit(68);
    pthread_t t;if(pthread_create(&t,NULL,survivor,NULL))_exit(69);
    atomic_fetch_add(&ready,1);
    while(!atomic_load(&retire_rep))usleep(1000);
    atomic_store(&rep_done,1);return NULL;
}
static void *worker(void *arg){
    long kind=(long)arg;
    if(kind==1){if(unshare(CLONE_FILES))_exit(61);if(open(protected,O_RDONLY)<0)_exit(62);}
    atomic_fetch_add(&ready,1);
    for(;;)pause();
    return NULL;
}
int main(int argc,char **argv){
    if(argc!=4)return 60;
    unsigned n=(unsigned)strtoul(argv[1],NULL,10);protected=argv[3];
    if(n<1||n>2048)return 60;
    pthread_attr_t attr;if(pthread_attr_init(&attr)||pthread_attr_setstacksize(&attr,262144))return 63;
    int pair=argv[2][0]=='r'||argv[2][0]=='R';protect_after_exit=argv[2][0]=='R';
    if(pair){pthread_t t;if(pthread_create(&t,&attr,representative,NULL))return 64;}
    else for(unsigned i=1;i<n;i++){pthread_t t;if(pthread_create(&t,&attr,worker,(void*)(long)(argv[2][0]=='u'&&i==1)))return 64;}
    while((unsigned)atomic_load(&ready)!=n-1)usleep(1000);
    if(argv[2][0]=='s')for(unsigned i=0;i<125;i++)if(open("/dev/null",O_RDONLY)<0)return 74;
    if(argv[2][0]=='p'&&open(protected,O_RDONLY)<0)return 65;
    if(argv[2][0]=='q'&&chroot(protected))return 73;
    int replacefd=-1;if(argv[2][0]=='f'){replacefd=open("/dev/null",O_RDONLY);if(replacefd<0)return 70;}
    printf("READY %ld %u\n",(long)getpid(),n);fflush(stdout);
    char cmd;
    while(read(STDIN_FILENO,&cmd,1)==1){
        if(cmd=='x')return 0;
        if(cmd=='l')pthread_exit(NULL);
        if(cmd=='r'){
            atomic_store(&retire_rep,1);
            while(!atomic_load(&rep_done)||!atomic_load(&survivor_ready))usleep(1000);
            usleep(1000);puts("ACK");fflush(stdout);
        }
        if(cmd=='p'||cmd=='z'||cmd=='n'||cmd=='d'){
            if(replacefd<0||close(replacefd))return 71;
            if(cmd!='d'){int fd=open(cmd=='p'?protected:cmd=='n'?"/dev/null":"/dev/zero",O_RDONLY);if(fd!=replacefd)return 72;}
            puts("ACK");fflush(stdout);
        }
        if(cmd=='c'){for(unsigned i=0;i<200;i++){int f[2];if(pipe(f))return 66;usleep(50);close(f[0]);close(f[1]);}}
    }
    return 0;
}

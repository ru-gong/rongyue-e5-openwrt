/* Public reference export. Default build never accesses a device. */
#ifndef E5_PUBLIC_FIXTURE
#include <stdio.h>
int main(void){fputs("Reference-only export: device execution is disabled.\n",stderr);return 64;}
#else
#ifndef E5_UI_STREAM_TEST
#error "Public fixture build also requires E5_UI_STREAM_TEST"
#endif
#define _GNU_SOURCE
/* Read-only fixed-path NDJSON observer. It never starts or cancels a switch. */
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <math.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/vfs.h>
#endif
#ifndef O_CLOEXEC
#define O_CLOEXEC 0
#endif
#ifndef E5_UI_STREAM_TEST
#define BASE "/dev/e5-switch-ui"
#define DEV "/dev"
#define PROC "/proc"
#else
/* Test builds require compile-time paths, never runtime environment overrides. */
#ifndef BASE
#error Test BASE is required
#endif
#ifndef DEV
#error Test DEV is required
#endif
#ifndef PROC
#error Test PROC is required
#endif
#endif

static const char *boot, *started_text;
static double started;
static int phase, terminal, dfd=-1, lfd=-1, kfd=-1;
static const char *names[]={"STARTING","IDENTITY","ANDROID_VERIFY","BOOT_VERIFY",
    "TF_READONLY","CONTROL_BACKUP","TF_REQUEST","TF_READBACK","ARM","REBOOT"};
static double uptime_now(void) {
    struct timespec ts;
#ifdef __linux__
    if(clock_gettime(CLOCK_BOOTTIME,&ts)) return -1;
#else
    if(clock_gettime(CLOCK_MONOTONIC,&ts)) return -1;
#endif
    return (double)ts.tv_sec+(double)ts.tv_nsec/1e9;
}
static int emit(const char *state,const char *p,const char *message,int code) {
    double now=uptime_now();
    if(now<started || now-started>INT_MAX) return -1;
    char output[1024],c[16];
    if(code<0) strcpy(c,"null"); else snprintf(c,sizeof(c),"%d",code);
    int n=snprintf(output,sizeof(output),"{\"schema\":\"e5-switch-ui-v1\",\"boot_id\":\"%s\",\"run_id\":\"%s-1\",\"state\":\"%s\",\"phase\":\"%s\",\"message\":\"%s\",\"elapsed_seconds\":%d,\"exit_code\":%s}\n",boot,boot,state,p,message,(int)(now-started),c);
    if(n<0 || (size_t)n>=sizeof(output)) return -1;
    size_t pos=0;
    while(pos<(size_t)n){ssize_t k=write(STDOUT_FILENO,output+pos,(size_t)n-pos);if(k<0&&errno==EINTR)continue;if(k<=0)return -1;pos+=(size_t)k;}
    return 0;
}
static int unknown(void) {
    (void)emit("UNKNOWN","UNKNOWN","状态无法完整确认，请保持开机并联系维护。",-1);
    return 1;
}
static int numeric(const char *s,int decimal) {
    int dots=0,digits=0;
    if(!s || !*s)return 0;
    for(;*s;s++){if(*s=='.'&&decimal){if(++dots>1)return 0;}else if(*s<'0'||*s>'9')return 0;else digits++;}
    return digits>0;
}
static int uuid(const char *s) {
    if(strlen(s)!=36)return 0;
    for(int i=0;i<36;i++){if(i==8||i==13||i==18||i==23){if(s[i]!='-')return 0;}else if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return 0;}
    return 1;
}
static int owned(const struct stat *st,mode_t mode,int directory) {
#ifndef E5_UI_STREAM_TEST
    if(st->st_uid!=0||st->st_gid!=0)return 0;
#else
    if(st->st_uid!=geteuid()||st->st_gid!=getegid())return 0;
#endif
    return (st->st_mode&07777)==mode && (directory?S_ISDIR(st->st_mode):(S_ISREG(st->st_mode)&&st->st_nlink==1));
}
static int open_private(const char *name) {
    struct stat st;
    int fd=openat(dfd,name,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0)return -1;
    if(fstat(fd,&st)||!owned(&st,0600,0)){close(fd);return -1;}
    return fd;
}
static int read_text(int fd,char *buf,size_t cap) {
    struct stat st;
    if(fstat(fd,&st)||st.st_size<0||(uint64_t)st.st_size>=cap)return -1;
    size_t n=0;
    while(n+1<cap){ssize_t r=read(fd,buf+n,cap-1-n);if(r<0&&errno==EINTR)continue;if(r<0)return -1;if(!r){buf[n]=0;return (int)n;}n+=(size_t)r;}
    return -1;
}
static int same_boot(void) {
    char value[64];int fd=open(PROC "/sys/kernel/random/boot_id",O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0)return 0;
    ssize_t n=read(fd,value,sizeof(value));close(fd);
    return n==37&&!memcmp(value,boot,36)&&value[36]=='\n';
}
static int task_identity(void) {
    char meta[256];int fd=open_private("meta");if(fd<0)return 0;
    int n=read_text(fd,meta,sizeof(meta));close(fd);if(n<0)return 0;
    char *save=0,*b=strtok_r(meta," \n",&save),*pid=strtok_r(NULL," \n",&save),*ticks=strtok_r(NULL," \n",&save),*begin=strtok_r(NULL," \n",&save);
    if(!b||!pid||!ticks||!begin||strtok_r(NULL," \n",&save)||strcmp(b,boot)||strcmp(begin,started_text)||!numeric(pid,0)||!numeric(ticks,0))return 0;
    if(!strcmp(pid,"0")&&!strcmp(ticks,"0"))return 1; /* launch handoff, lock is held */
    errno=0;unsigned long p=strtoul(pid,NULL,10);if(errno||p==0||p>INT_MAX)return 0;
    char path[PATH_MAX],statline[4096];snprintf(path,sizeof(path),PROC "/%lu/stat",p);
    fd=open(path,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);if(fd<0)return 0;
    ssize_t size=read(fd,statline,sizeof(statline)-1);close(fd);if(size<=0||size==(ssize_t)sizeof(statline)-1)return 0;statline[size]=0;
    char *tail=strrchr(statline,')');if(!tail||tail[1]!=' ')return 0;tail+=2;
    char *sp=0,*token=strtok_r(tail," \n",&sp);
    if(!token||!strcmp(token,"Z"))return 0;
    for(int field=1;field<20;field++){token=strtok_r(NULL," \n",&sp);if(!token)return 0;}
    return !strcmp(token,ticks);
}
static int on_line(char *s) {
    if(strlen(s)>=6&&s[0]=='['&&s[1]>='1'&&s[1]<='9'&&!strncmp(s+2,"/9] ",4)){
        int n=s[1]-'0';if(n<=phase)return 0;phase=n;
        return emit(n==9?"REBOOTING":"RUNNING",names[n],"阶段已更新，请继续等待。",-1);
    }
    const char prefix[]="E5_UI_TERMINAL ";
    if(!strncmp(s,prefix,sizeof(prefix)-1)){
        const char *c=s+sizeof(prefix)-1;if(!numeric(c,0)||strlen(c)>3)return -1;
        int code=atoi(c);if(code>255)return -1;
        terminal=1;
        return emit(code==0?"UNKNOWN":(phase<8?"REFUSED":"FAILED"),"FINISHED","切换未完成，请保持开机并提供阶段与退出码；不会自动重试。",code);
    }
    return 0;
}
static int drain(void) {
    static char line[4096];static size_t used;
    struct stat st;if(fstat(lfd,&st)||st.st_size<0||st.st_size>1048576)return -1;
    char buf[4096];ssize_t n;
    while((n=read(lfd,buf,sizeof(buf)))>0){
        for(ssize_t i=0;i<n;i++){
            if(buf[i]=='\n'){line[used]=0;if(on_line(line))return -1;used=0;if(terminal)return 0;}
            else {if(!buf[i]||used+1>=sizeof(line))return -1;line[used++]=buf[i];}
        }
    }
    return n<0?-1:0;
}
int main(int argc,char **argv) {
    if(argc!=4||!uuid(argv[1])||!numeric(argv[2],1)||!numeric(argv[3],0))return 64;
    boot=argv[1];started_text=argv[2];started=strtod(argv[2],NULL);
    if(!isfinite(started)||started<0||strlen(argv[3])!=1)return 64;
    phase=argv[3][0]-'0';if(phase<0||phase>9)return 64;
#ifndef E5_UI_STREAM_TEST
    if(geteuid()!=0)return 77;
#endif
    signal(SIGPIPE,SIG_IGN);
    struct stat ds,bs;int devfd=open(DEV,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    dfd=open(BASE,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(devfd<0||dfd<0||fstat(devfd,&ds)||fstat(dfd,&bs)||!owned(&bs,0700,1)||ds.st_dev!=bs.st_dev||!same_boot())return unknown();
#if defined(__linux__) && !defined(E5_UI_STREAM_TEST)
    struct statfs fs;if(ds.st_uid!=0||ds.st_gid!=0||(ds.st_mode&0022)||fstatfs(dfd,&fs)||fs.f_type!=0x01021994)return unknown();
#endif
    close(devfd);lfd=open_private("worker.log");kfd=open_private("lock");
    if(lfd<0||kfd<0)return unknown();
    double heartbeat=uptime_now();
    for(;;){
        if(drain())return errno==EPIPE?0:unknown();
        if(terminal)return 0;
        if(flock(kfd,LOCK_EX|LOCK_NB)==0){
            int r=drain();(void)flock(kfd,LOCK_UN);
            if(!r&&terminal)return 0;
            return unknown();
        }
        if(errno!=EAGAIN&&errno!=EWOULDBLOCK)return unknown();
        if(!task_identity())return unknown();
        /* Native heartbeat only: no shell/su, /data write or fake progress. */
        if(uptime_now()-heartbeat>=2){
            if(emit(phase==9?"REBOOTING":"RUNNING",names[phase],"检查进行中；通过后自动重启，请勿手动重启。",-1))return errno==EPIPE?0:unknown();
            heartbeat=uptime_now();
        }
        struct pollfd out={STDOUT_FILENO,0,0};
        int r=poll(&out,1,1000);
        if(r<0&&errno==EINTR)continue;
        if(r<0)return 1;
        if(out.revents&(POLLERR|POLLHUP|POLLNVAL))return 0;
    }
}

#endif /* E5_PUBLIC_FIXTURE */

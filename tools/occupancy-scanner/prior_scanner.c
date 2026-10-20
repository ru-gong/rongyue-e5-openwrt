/* Native, read-only occupancy check. scan does not fork, execute commands or mutate files.
 * capability separately clone/forks two private in-memory children, then kills/reaps only them.
 * Production is deliberately disabled. HOST_TEST reads only a canonical
 * dedicated /tmp/e5-native-test-* sandbox fixture; never real /data.
 * CLI: scan|capability TXID BOOT_UUID OPID32 DEADLINE_BOOTTIME_MS
 */
#define _GNU_SOURCE 1
#define _DARWIN_C_SOURCE 1
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/resource.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <inttypes.h>
#include <limits.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/wait.h>
#if defined(__linux__)
#include <sys/syscall.h>
#include <linux/kcmp.h>
#include <sched.h>
#include <sys/vfs.h>
#endif

static const int DEVICE_EXECUTION_ENABLED=0;
#define MAX_PIDS 4096
#define MAX_FDS 131072
#define MAX_KCMP 131072
#define MAX_NS 256
#define MAX_TREE 1024
#define MAX_READ (32U*1024U*1024U)
#define MAX_LIFECYCLE_ROUNDS 3
#define HANDLE_LIMIT (2U*MAX_PIDS+64U)
#define E5_PIPEFS_MAGIC 0x50495045UL
#define E5_SOCKFS_MAGIC 0x534f434bUL
#define MAX_DIFF_TABLES 4
#define MAX_DIFF_RECORDS 8
#define MOUNT_BYTES (1024U*1024U)
#define PF_KTHREAD_E5 0x00200000UL
static volatile sig_atomic_t cancelled;
static const char *phase="arguments",*subphase="arguments",*detail="",*tx="",*boot="",*op="";
static char base[PATH_MAX],names[4][96];
static uintmax_t deadline_ms,self_start;
static unsigned current_pid,current_fd,pids_seen,fds_seen,ns_seen,loops_seen,tree_seen,gone_seen;
static size_t read_bytes;
static unsigned fd_tables_seen,kcmp_calls,shared_tasks,capability_shared,capability_distinct;
static int final_relations;
static unsigned ident_count,lifecycle_round,retired_tasks,added_tasks,enum_gaps;
static unsigned snapshot_attempts,snapshots_complete,snapshots_discarded;
static int last_acquire_errno;
static unsigned stream_observations,diff_tables_seen,diff_tables_recorded,diff_records_count,diff_records_omitted;
struct diff_record { unsigned pid,fd,pass,old_kind,new_kind;uintmax_t old_dev,old_ino,new_dev,new_ino; };
static struct diff_record differences[MAX_DIFF_RECORDS];
static uintmax_t nofile_before,nofile_after,nofile_hard;
/* Only the direct final stat check owns these diagnostics. Unparsed values
 * remain null, rather than implying a starttime or state was observed. */
static int final_stat_expected_known,final_stat_observed_known;
static uintmax_t final_stat_expected,final_stat_observed;
static char final_stat_state;
static pid_t cap_shared_pid,cap_distinct_pid;
static unsigned cap_children_reaped;
struct ident { unsigned pid,tgid,representative; uintmax_t start; char ns[80]; int kernel,missing_kernel_fs;
    int dirfd,statfd,known,retired,scanned,fd_scanned; dev_t procdev; ino_t procino; };
static struct ident ids[MAX_PIDS];
static struct { dev_t dev; ino_t ino; } tree[MAX_TREE];
static char namespaces[MAX_NS][80];
static struct ident *latest(unsigned pid){for(unsigned i=ident_count;i;i--)if(ids[i-1].pid==pid&&!ids[i-1].retired)return &ids[i-1];return NULL;}
/* Every generated /proc/TID path is routed through its retained directory.
 * Numeric reuse therefore never redirects a read of an existing identity. */
static int anchored(const char *p,int *fd,const char **tail){
    char prefix[PATH_MAX];int n=snprintf(prefix,sizeof prefix,"%s/proc/",base);
    if(n<0||(size_t)n>=sizeof prefix||strncmp(p,prefix,(size_t)n))return 0;
    const char *s=p+n,*end=s;unsigned long pid=0;
    while(*end>='0'&&*end<='9'){pid=pid*10+(unsigned)(*end-'0');if(pid>INT_MAX)return 0;end++;}
    if(end==s||*end!='/')return 0;
    struct ident *id=latest((unsigned)pid);if(!id||id->dirfd<0)return 0;
    *fd=id->dirfd;*tail=end+1;return 1;
}
static int target_open(const char *p,int flags){int fd;const char *tail;return anchored(p,&fd,&tail)?openat(fd,tail,flags):open(p,flags);}
#if !defined(E5_SCANNER_HOST_TEST) || defined(E5_SCANNER_LINUX_INTEGRATION)
static int target_stat(const char *p,struct stat *s){int fd;const char *tail;return anchored(p,&fd,&tail)?fstatat(fd,tail,s,0):stat(p,s);}
#endif
static DIR *target_dir(const char *p){int fd=target_open(p,O_RDONLY|O_CLOEXEC|O_DIRECTORY);if(fd<0)return NULL;DIR *d=fdopendir(fd);if(!d){int e=errno;close(fd);errno=e;}return d;}
static void on_signal(int sig){cancelled=sig;}
static int decimal(const char *s,uintmax_t *v){
    if(!s||!*s||(*s=='0'&&s[1]))return -1;
    for(const char *p=s;*p;p++)if(*p<'0'||*p>'9')return -1;
    errno=0;char *end;*v=strtoumax(s,&end,10);return errno||*end?-1:0;
}
static int hexid(const char *s,size_t n){return strlen(s)==n&&strspn(s,"0123456789abcdef")==n;}
static int uuid_ok(const char *s){
    if(strlen(s)!=36)return 0;
    for(int i=0;i<36;i++)if(i==8||i==13||i==18||i==23){if(s[i]!='-')return 0;}else if(!strchr("0123456789abcdef",s[i]))return 0;
    return 1;
}
static int clock_ms(uintmax_t *out){
    struct timespec t;
#if defined(__linux__)
    if(clock_gettime(CLOCK_BOOTTIME,&t))return -1;
#elif defined(E5_SCANNER_HOST_TEST) && defined(__APPLE__)
    if(clock_gettime(CLOCK_MONOTONIC,&t))return -1;
#else
    errno=ENOSYS;return -1;
#endif
    if(t.tv_sec<0||(uintmax_t)t.tv_sec>UINTMAX_MAX/1000U){errno=EOVERFLOW;return -1;}
    *out=(uintmax_t)t.tv_sec*1000U+(uintmax_t)t.tv_nsec/1000000U;return 0;
}
static int control(void){uintmax_t n;if(cancelled){errno=ECANCELED;return -1;}if(clock_ms(&n))return -1;if(n>=deadline_ms){errno=ETIMEDOUT;return -1;}return 0;}
static int emit(const char *event,int complete,const char *why){
    int saved=errno;
    char expected[32]="null",observed[32]="null",observed_state[8]="null";
    if(final_stat_expected_known)snprintf(expected,sizeof expected,"%ju",final_stat_expected);
    if(final_stat_observed_known){snprintf(observed,sizeof observed,"%ju",final_stat_observed);observed_state[0]='\"';observed_state[1]=final_stat_state;observed_state[2]='\"';observed_state[3]=0;}
    int n=printf("{\"schema\":\"e5-native-occupancy-v1\",\"event\":\"%s\",\"phase\":\"%s\",\"subphase\":\"%s\",\"detail\":\"%s\",\"txid\":\"%s\",\"opid\":\"%s\",\"boot_id\":\"%s\",\"self_pid\":%ld,\"self_starttime\":%ju,\"deadline_ms\":%ju,\"complete\":%s,\"reason\":\"%s\",\"errno\":%d,\"cancel_signal\":%d,\"pid\":%u,\"fd\":%u,\"processes\":%u,\"fds\":%u,\"namespaces\":%u,\"loops\":%u,\"tree_entries\":%u,\"read_bytes\":%zu,\"gone_observed\":%u,\"unknown\":%s,\"atomic_snapshot\":false,\"fd_tables\":%u,\"kcmp_calls\":%u,\"shared_tasks\":%u,\"capability_shared\":%s,\"capability_distinct\":%s,\"capability_shared_pid\":%ld,\"capability_distinct_pid\":%ld,\"capability_children_reaped\":%s,\"final_stat_expected_starttime\":%s,\"final_stat_observed_starttime\":%s,\"final_stat_observed_state\":%s,\"lifecycle_round\":%u,\"retired_tasks\":%u,\"observed_identities\":%u,\"enum_gaps\":%u,\"nofile_before\":%ju,\"nofile_after\":%ju,\"nofile_hard\":%ju,",event,phase,subphase,detail,tx,op,boot,(long)getpid(),self_start,deadline_ms,complete?"true":"false",why,saved,(int)cancelled,current_pid,current_fd,pids_seen,fds_seen,ns_seen,loops_seen,tree_seen,read_bytes,gone_seen,complete?"[]":"[\"scan-not-complete\"]",fd_tables_seen,kcmp_calls,shared_tasks,capability_shared?"true":"false",capability_distinct?"true":"false",(long)cap_shared_pid,(long)cap_distinct_pid,cap_children_reaped?"true":"false",expected,observed,observed_state,lifecycle_round,retired_tasks,ident_count,enum_gaps,nofile_before,nofile_after,nofile_hard);
    if(n>=0)n=printf("\"fd_snapshot_attempts\":%u,\"fd_snapshots_complete\":%u,\"fd_snapshots_discarded\":%u,\"fd_last_acquire_errno\":%d,\"fd_stream_observations\":%u,\"fd_diff_pairs_seen\":%u,\"fd_diff_pairs_recorded\":%u,\"fd_diff_records_omitted\":%u,\"fd_differences\":[",snapshot_attempts,snapshots_complete,snapshots_discarded,last_acquire_errno,stream_observations,diff_tables_seen,diff_tables_recorded,diff_records_omitted);
    for(unsigned i=0;n>=0&&i<diff_records_count;i++){
        const struct diff_record *d=&differences[i];
        n=printf("%s{\"pid\":%u,\"fd\":%u,\"pass\":%u,\"old_kind\":%u,\"new_kind\":%u,\"old_dev\":%ju,\"old_ino\":%ju,\"new_dev\":%ju,\"new_ino\":%ju}",i?",":"",d->pid,d->fd,d->pass,d->old_kind,d->new_kind,d->old_dev,d->old_ino,d->new_dev,d->new_ino);
    }
    if(n>=0)n=printf("]}\n");
    if(n<0||fflush(stdout)){cancelled=SIGPIPE;errno=EPIPE;return -1;}errno=saved;return 0;
}
static int fail(const char *why){emit("RESULT",0,why);return 70;}
static int set_phase(const char *p){
    phase=p;subphase=p;detail="";if(control()||emit("PHASE",0,""))return -1;
#ifdef E5_SCANNER_HOST_TEST
    const char *sync=getenv("E5_SCANNER_TEST_SYNC");
    if(sync&&!strcmp(sync,p)){
        for(;;){if(control())return -1;struct pollfd f={STDIN_FILENO,POLLIN,0};int r=poll(&f,1,1);if(r<0&&errno!=EINTR)return -1;if(r>0){char c;if(read(STDIN_FILENO,&c,1)!=1||c!='.'){errno=EPROTO;return -1;}break;}}
    }
    const char *fault=getenv("E5_SCANNER_TEST_FAULT");
    if(fault&&!strcmp(fault,"pause-before-scan")&&!strcmp(p,"protected-tree"))
        while(!control()){struct timespec t={0,1000000};nanosleep(&t,NULL);}
#endif
    return control();
}
static int path(char *out,size_t size,const char *suffix){int n=snprintf(out,size,"%s%s",base,suffix);if(n<0||(size_t)n>=size){errno=ENAMETOOLONG;return -1;}return 0;}
static int join(char *out,size_t cap,const char *parent,const char *leaf){
    size_t a=strlen(parent),b=strlen(leaf);if(a>=cap||b>=cap-a||a+b+2>cap){errno=ENAMETOOLONG;return -1;}
    memcpy(out,parent,a);out[a]='/';memcpy(out+a+1,leaf,b+1);return 0;
}
static int confined(const char *p,int parent_only){
#ifdef E5_SCANNER_HOST_TEST
    int pinned;const char *relative;if(anchored(p,&pinned,&relative))return 0;
    char input[PATH_MAX],real[PATH_MAX];
    if(strlen(p)>=sizeof input){errno=ENAMETOOLONG;return -1;}strcpy(input,p);
    if(parent_only){char *s=strrchr(input,'/');if(!s){errno=EPERM;return -1;}*s=0;}
    if(!realpath(input,real))return -1;
    size_t n=strlen(base);if(strncmp(real,base,n)||(real[n]&&real[n]!='/')){errno=EPERM;return -1;}
#else
    (void)p;(void)parent_only;
#endif
    return 0;
}
static int read_file(const char *file,char *out,size_t cap,size_t *length){
    if(control()||confined(file,1))return -1;
    int fd=target_open(file,O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);if(fd<0)return -1;
    size_t total=0;int rc=0,saved=0;
    while(total<cap){
        if(control()){rc=-1;saved=errno;break;}
        ssize_t n=read(fd,out+total,cap-total);
        if(n<0){rc=-1;saved=errno;break;}if(!n)break;
        total+=(size_t)n;read_bytes+=(size_t)n;
        if(read_bytes>MAX_READ){rc=-1;saved=E2BIG;break;}
    }
    if(!rc&&total==cap){rc=-1;saved=E2BIG;}
    if(close(fd)&&!rc){rc=-1;saved=errno;}
    if(!rc&&control()){rc=-1;saved=errno;}
    if(rc){errno=saved;return -1;}out[total]=0;*length=total;return 0;
}
static int boot_check(void){char p[PATH_MAX],b[80];size_t n;if(path(p,sizeof p,"/proc/sys/kernel/random/boot_id")||read_file(p,b,sizeof b-1,&n))return -1;while(n&&b[n-1]=='\n')b[--n]=0;if(strcmp(b,boot)){errno=ESTALE;return -1;}return 0;}
static int proc_path(char *out,size_t cap,unsigned pid,const char *suffix){char rel[128];int n=snprintf(rel,sizeof rel,"/proc/%u/%s",pid,suffix);if(n<0||(size_t)n>=sizeof rel){errno=ENAMETOOLONG;return -1;}return path(out,cap,rel);}
static int kept_stat_read;
static int read_kept_stat(struct ident *id,char *b,size_t cap,size_t *length){
    kept_stat_read=1;
    if(control()||lseek(id->statfd,0,SEEK_SET)<0)return -1;
    size_t n=0;
    while(n<cap){
        if(control())return -1;
        ssize_t got=read(id->statfd,b+n,cap-n);if(got<0)return -1;if(!got)break;
        n+=(size_t)got;read_bytes+=(size_t)got;if(read_bytes>MAX_READ){errno=E2BIG;return -1;}
    }
    if(n==cap){errno=E2BIG;return -1;}b[n]=0;*length=n;return control();
}
static int stat_record(unsigned pid,uintmax_t *start,unsigned long *flags,char *state){
    char p[PATH_MAX],b[8193];size_t n;detail="stat-read";kept_stat_read=0;
    if(proc_path(p,sizeof p,pid,"stat"))return -1;
#ifdef E5_SCANNER_HOST_TEST
    /* Static alternate records exercise reread drift without changing production
     * behavior or writing even the synthetic filesystem from the scanner. */
    static unsigned pid1_reads;const char *fault=getenv("E5_SCANNER_TEST_FAULT");
    if(pid==1){pid1_reads++;if(fault&&((!strcmp(fault,"pid1-second-stat")&&pid1_reads==2)||
       (!strcmp(fault,"pid1-final-stat")&&final_relations)))
        if(proc_path(p,sizeof p,pid,final_relations?"stat.final":"stat.second"))return -1;}
#endif
#ifdef E5_SCANNER_HOST_TEST
    if(fault&&!strcmp(fault,"kcmp-final-reused")&&final_relations&&pid==100)
        if(proc_path(p,sizeof p,pid,"stat.final"))return -1;
    /* Faults are confined to the direct final check in HOST_TEST. Production
     * has no environment-controlled fault or alternate-path handling. */
    if(fault&&final_relations&&pid==100&&!strcmp(subphase,"pid-final-stat")){
        if(!strcmp(fault,"final-stat-enoent")){errno=ENOENT;return -1;}
        if(!strcmp(fault,"final-stat-esrch")){errno=ESRCH;return -1;}
        if(!strcmp(fault,"final-stat-eacces")){errno=EACCES;return -1;}
        if(!strcmp(fault,"final-stat-eio")){errno=EIO;return -1;}
        if(!strcmp(fault,"final-stat-expired"))deadline_ms=0;
        if(!strcmp(fault,"final-stat-cancelled"))raise(SIGTERM);
        if(!strcmp(fault,"final-stat-record"))
            if(proc_path(p,sizeof p,pid,"stat.final-diagnostic"))return -1;
    }
#endif
    struct ident *held=latest(pid);
#ifdef E5_SCANNER_HOST_TEST
    /* Existing alternate-record fixtures deliberately bypass the kept read. */
    if(strstr(p,"stat.final")||strstr(p,"stat.second"))held=NULL;
#endif
    if(held?read_kept_stat(held,b,sizeof b-1,&n):read_file(p,b,sizeof b-1,&n))return -1;
    detail="stat-format";char *end=strrchr(b,')'),*left=strchr(b,' ');
    if(!left||left[1]!='('||!end||end<=left+1||end[1]!=' '){errno=EPROTO;return -1;}
    *left=0;uintmax_t got;detail="stat-pid";
    if(decimal(b,&got)||got!=pid){errno=ESTALE;return -1;}
    char *save=NULL,*s=strtok_r(end+2," \n",&save);unsigned field=3;
    int have_state=0,have_flags=0,have_start=0;*start=0;*flags=0;*state=0;
    for(;s;s=strtok_r(NULL," \n",&save),field++){
        if(field==3){detail="stat-state";if(strlen(s)!=1||!strchr("RSDTtXZPIKW",*s)){errno=EPROTO;return -1;}*state=*s;have_state=1;}
        if(field==9){detail="stat-flags";uintmax_t v;if(decimal(s,&v)||v>ULONG_MAX){errno=EPROTO;return -1;}*flags=(unsigned long)v;have_flags=1;}
        if(field==22){detail="stat-starttime";if(decimal(s,start)){errno=EPROTO;return -1;}have_start=1;}
    }
    detail="stat-required-fields";
    if(field<=22||!have_start||!have_flags||!have_state){errno=EPROTO;return -1;}
    /* A successfully parsed target starttime of zero is legal. Do not skip its
     * namespace/FD scan or any of the later identity comparisons. */
    detail="";return 0;
}
static int numeric_name(const char *s,unsigned *v){uintmax_t n;if(decimal(s,&n)||!n||n>INT_MAX)return 0;*v=(unsigned)n;return 1;}
static int compare_pid(const void *a,const void *b){unsigned x=*(const unsigned*)a,y=*(const unsigned*)b;return x>y?1:x<y?-1:0;}
static int enumerate(unsigned *out,size_t *count){
    char p[PATH_MAX];if(path(p,sizeof p,"/proc")||control()||confined(p,0))return -1;
    DIR *d=opendir(p);if(!d)return -1;size_t n=0;int rc=0,saved=0;
    for(;;){
        if(control()){rc=-1;saved=errno;break;}errno=0;struct dirent *de=readdir(d);if(!de){if(errno){rc=-1;saved=errno;}break;}
        unsigned pid;if(!numeric_name(de->d_name,&pid))continue;
        char task[PATH_MAX];if(proc_path(task,sizeof task,pid,"task")||confined(task,0)){rc=-1;saved=errno;break;}
        DIR *td=target_dir(task);if(!td){if(errno==ENOENT||errno==ESRCH){enum_gaps++;continue;}rc=-1;saved=errno;break;}int leader=0;
        for(;;){
            if(control()){rc=-1;saved=errno;break;}errno=0;struct dirent *te=readdir(td);if(!te){if(errno){rc=-1;saved=errno;}break;}
            if(!strcmp(te->d_name,".")||!strcmp(te->d_name,".."))continue;
            unsigned tid;if(!numeric_name(te->d_name,&tid)){rc=-1;saved=EPROTO;break;}if(tid==pid)leader=1;
            int found=0;for(size_t j=0;j<n;j++)if(out[j]==tid){found=1;break;}if(found)continue;
            if(n==MAX_PIDS){rc=-1;saved=E2BIG;break;}out[n++]=tid;
        }
        if(closedir(td)&&!rc){rc=-1;saved=errno;}if(!rc&&!leader){rc=-1;saved=ESTALE;}if(rc)break;
    }
    if(closedir(d)&&!rc){rc=-1;saved=errno;}if(rc){errno=saved;return -1;}qsort(out,n,sizeof *out,compare_pid);*count=n;return 0;
}
static int unescape(const char *in,char *out,size_t cap){
    size_t w=0;
    for(size_t i=0;in[i];i++){
        unsigned char ch=(unsigned char)in[i];
        if(ch=='\\'){
            if(strlen(in+i)<4){errno=EPROTO;return -1;}
            if(!strncmp(in+i,"\\040",4))ch=' ';else if(!strncmp(in+i,"\\011",4))ch='\t';else if(!strncmp(in+i,"\\012",4))ch='\n';else if(!strncmp(in+i,"\\134",4))ch='\\';else{errno=EPROTO;return -1;}i+=3;
        }
        if(w+1>=cap){errno=E2BIG;return -1;}out[w++]=(char)ch;
    }out[w]=0;return 0;
}
static int protected_path(const char *p){
#ifdef E5_SCANNER_LINUX_INTEGRATION
    if(*base&&!strncmp(p,base,strlen(base))&&p[strlen(base)]=='/')p+=strlen(base);
#endif
    for(int i=0;i<4;i++){
        char full[128];snprintf(full,sizeof full,"/data/%.95s",names[i]);size_t n=strlen(full);
        if(!strncmp(p,full,n)&&(!p[n]||p[n]=='/'||!strcmp(p+n," (deleted)")))return 1;
        snprintf(full,sizeof full,"/%.95s",names[i]);n=strlen(full);
        if(!strncmp(p,full,n)&&(!p[n]||p[n]=='/'||!strcmp(p+n," (deleted)")))return 1;
    }return 0;
}
static int protected_inode(const struct stat *s){for(unsigned i=0;i<tree_seen;i++)if(tree[i].dev==s->st_dev&&tree[i].ino==s->st_ino)return 1;return 0;}
static int tree_walk(const char *p,dev_t device,unsigned depth){
    if(control()||confined(p,1))return -1;
    if(depth>16||tree_seen==MAX_TREE){errno=E2BIG;return -1;}
    struct stat s;if(lstat(p,&s))return -1;
    if(s.st_dev!=device||!(S_ISREG(s.st_mode)||S_ISDIR(s.st_mode))||(S_ISREG(s.st_mode)&&s.st_nlink!=1)){errno=EPERM;return -1;}
    tree[tree_seen].dev=s.st_dev;tree[tree_seen++].ino=s.st_ino;
    if(!S_ISDIR(s.st_mode))return 0;
    DIR *d=opendir(p);if(!d)return -1;int rc=0,saved=0;
    for(;;){if(control()){rc=-1;saved=errno;break;}errno=0;struct dirent *de=readdir(d);if(!de){if(errno){rc=-1;saved=errno;}break;}if(!strcmp(de->d_name,".")||!strcmp(de->d_name,".."))continue;char q[PATH_MAX];int n=snprintf(q,sizeof q,"%s/%s",p,de->d_name);if(n<0||(size_t)n>=sizeof q||tree_walk(q,device,depth+1)){rc=-1;saved=errno?errno:E2BIG;break;}}
    if(closedir(d)&&!rc){rc=-1;saved=errno;}if(rc)errno=saved;return rc;
}
static int load_tree(void){
    char p[PATH_MAX];if(path(p,sizeof p,"/data"))return -1;struct stat s;if(lstat(p,&s)||!S_ISDIR(s.st_mode)){errno=EPERM;return -1;}
    for(int i=0;i<4;i++){char rel[128];snprintf(rel,sizeof rel,"/data/%.95s",names[i]);if(path(p,sizeof p,rel)||confined(p,1))return -1;struct stat x;if(lstat(p,&x)){if(errno==ENOENT)continue;return -1;}if(!S_ISDIR(x.st_mode)){errno=EPERM;return -1;}if(tree_walk(p,s.st_dev,0))return -1;}
    return 0;
}
static int read_link(const char *p,char *out,size_t size){
#ifdef E5_SCANNER_HOST_TEST
    static unsigned pid1_ns_reads;char alternate[PATH_MAX];const char *fault=getenv("E5_SCANNER_TEST_FAULT");
    char first[PATH_MAX];if(proc_path(first,sizeof first,1,"ns/mnt"))return -1;
    if(!strcmp(p,first)){pid1_ns_reads++;if(fault&&((!strcmp(fault,"pid1-second-namespace")&&pid1_ns_reads==2)||
       (!strcmp(fault,"pid1-final-namespace")&&pid1_ns_reads==3))){
        if(proc_path(alternate,sizeof alternate,1,pid1_ns_reads==2?"ns/mnt.second":"ns/mnt.final"))return -1;
        p=alternate;}}
#endif
    if(control()||confined(p,1))return -1;
    int anchorfd;const char *tail;ssize_t n=anchored(p,&anchorfd,&tail)?readlinkat(anchorfd,tail,out,size-1):readlink(p,out,size-1);if(n<0)return -1;if((size_t)n==size-1){errno=E2BIG;return -1;}out[n]=0;return control();}
static int check_link_record(const char *p,int kernel_optional,struct stat *record,char *link_record){
    char b[PATH_MAX];if(read_link(p,b,sizeof b)){if(kernel_optional&&errno==ENOENT)return 1;return -1;}
    if(protected_path(b)){errno=EBUSY;return -1;}
    if(link_record)snprintf(link_record,PATH_MAX,"%s",b);
    struct stat s;memset(&s,0,sizeof s);
#if defined(E5_SCANNER_HOST_TEST) && !defined(E5_SCANNER_LINUX_INTEGRATION)
    /* Fixture links are strings, never permission to inspect host /data. */
    char mapped[PATH_MAX];
    if(!strncmp(b,"/data/",6)){if(path(mapped,sizeof mapped,b)||confined(mapped,0)||stat(mapped,&s))return -1;}
    else if(!strncmp(b,base,strlen(base))&&b[strlen(base)]=='/'){if(confined(b,0)||stat(b,&s))return -1;}
    else {if(record)*record=s;return 0;}
#else
    if(target_stat(p,&s))return -1;
#endif
    if(protected_inode(&s)){errno=EBUSY;return -1;}if(record)*record=s;return 0;
}
static int check_link(const char *p,int kernel_optional){return check_link_record(p,kernel_optional,NULL,NULL);}
static int mount_check(unsigned pid,const char *ns){
    for(unsigned i=0;i<ns_seen;i++)if(!strcmp(ns,namespaces[i]))return 0;
    subphase="pid-mountinfo";detail="mountinfo-read";
    if(ns_seen==MAX_NS){errno=E2BIG;return -1;}char p[PATH_MAX];if(proc_path(p,sizeof p,pid,"mountinfo"))return -1;
    char *buf=malloc(MOUNT_BYTES+1);if(!buf){errno=ENOMEM;return -1;}size_t n;int rc=read_file(p,buf,MOUNT_BYTES,&n);if(rc){free(buf);return -1;}if(!n||buf[n-1]!='\n'){free(buf);errno=EPROTO;return -1;}
    detail="mountinfo-format";char *line_save=NULL;for(char *line=strtok_r(buf,"\n",&line_save);line;line=strtok_r(NULL,"\n",&line_save)){
        if(control()){rc=-1;break;}char *tok_save=NULL,*root=NULL,*mount=NULL;unsigned field=0;int separator=0;
        for(char *t=strtok_r(line," ",&tok_save);t;t=strtok_r(NULL," ",&tok_save)){field++;if(field==4)root=t;if(field==5)mount=t;if(field>=7&&!strcmp(t,"-"))separator=1;}
        char a[PATH_MAX],b[PATH_MAX];if(field<10||!separator||!root||!mount||unescape(root,a,sizeof a)||unescape(mount,b,sizeof b)||a[0]!='/'||b[0]!='/'){errno=EPROTO;rc=-1;break;}
        if(protected_path(a)||protected_path(b)){detail="mountinfo-protected";errno=EBUSY;rc=-1;break;}
    }
    free(buf);if(rc)return -1;snprintf(namespaces[ns_seen++],80,"%s",ns);detail="";return 0;
}
static int task_group(unsigned pid,unsigned *tgid){
    char p[PATH_MAX],b[16385];size_t n;detail="status-tgid";
    if(proc_path(p,sizeof p,pid,"status")||read_file(p,b,sizeof b-1,&n))return -1;
    unsigned found=0;char *save=NULL;
    for(char *line=strtok_r(b,"\n",&save);line;line=strtok_r(NULL,"\n",&save)){
        if(strncmp(line,"Tgid:",5))continue;
        if(found++){errno=EPROTO;return -1;}char *v=line+5;while(*v==' '||*v=='\t')v++;
        size_t len=strlen(v);while(len&&(v[len-1]==' '||v[len-1]=='\t'))v[--len]=0;
        if(!numeric_name(v,tgid)){errno=EPROTO;return -1;}
    }
    if(found!=1){errno=EPROTO;return -1;}return 0;
}
/* ESRCH from this already-open proc stat is the kernel's no-task result.
 * Failed pathname opens, child links, permissions and parse errors are NOT
 * exit evidence. Z/X is accepted only after parsing this same pinned identity;
 * Linux do_exit releases files/fs/namespaces before setting those exit states. */
static int retire_if_exited(struct ident *id){
    uintmax_t start;unsigned long flags;char state;
    int rc=stat_record(id->pid,&start,&flags,&state),e=errno;
    if(rc){if(!(kept_stat_read&&e==ESRCH)){errno=e;return -1;}}
    else {
        if(id->known&&start!=id->start){errno=ESTALE;return -1;}
        if(state!='Z'&&state!='X')return 0;
    }
    id->retired=1;retired_tasks++;gone_seen++;return 1;
}
static int exit_or_fail(struct ident *id){
    int e=errno;if(e!=ENOENT&&e!=ESRCH)return -1;
    int retired=retire_if_exited(id);if(retired==1)return 0;
    if(!retired)errno=e;
    return -1;
}
static int handle_budget(void){
    struct rlimit limit;if(getrlimit(RLIMIT_NOFILE,&limit))return -1;
    nofile_before=limit.rlim_cur;nofile_hard=limit.rlim_max;
    if(limit.rlim_cur<HANDLE_LIMIT){
        if(limit.rlim_max<HANDLE_LIMIT){detail="hard-nofile-insufficient";errno=EMFILE;return -1;}
        limit.rlim_cur=HANDLE_LIMIT;if(setrlimit(RLIMIT_NOFILE,&limit))return -1;
    }
    nofile_after=limit.rlim_cur;return 0;
}
static int pin_task(unsigned pid,int *added){
    *added=0;char p[PATH_MAX],suffix[80];snprintf(suffix,sizeof suffix,"/proc/%u",pid);
    if(path(p,sizeof p,suffix)||control()||confined(p,1))return -1;
    int fd=open(p,O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0){if(errno==ENOENT||errno==ESRCH){enum_gaps++;return 0;}return -1;}
    struct stat st;if(fstat(fd,&st)){int e=errno;close(fd);errno=e;return -1;}
#if defined(__linux__) && (!defined(E5_SCANNER_HOST_TEST) || defined(E5_SCANNER_LINUX_INTEGRATION))
    struct statfs fs;if(fstatfs(fd,&fs)||fs.f_type!=0x9fa0){int e=errno?errno:EPROTO;close(fd);errno=e;return -1;}
#endif
    for(unsigned i=0;i<ident_count;i++)if(ids[i].pid==pid&&ids[i].procdev==st.st_dev&&ids[i].procino==st.st_ino){close(fd);return 0;}
    struct ident *old=latest(pid);
    if(old&&old->procdev==st.st_dev&&old->procino==st.st_ino){close(fd);return 0;}
    if(old){int r=retire_if_exited(old);if(r!=1){int e=r<0?errno:ESTALE;close(fd);errno=e;return -1;}}
    if(ident_count==MAX_PIDS){close(fd);errno=E2BIG;return -1;}
    int statfd=openat(fd,"stat",O_RDONLY|O_CLOEXEC|O_NOFOLLOW|O_NONBLOCK);
    if(statfd<0){int e=errno;close(fd);if(e==ENOENT||e==ESRCH){enum_gaps++;return 0;}errno=e;return -1;}
    struct ident *id=&ids[ident_count];memset(id,0,sizeof *id);
    id->pid=pid;id->dirfd=fd;id->statfd=statfd;id->procdev=st.st_dev;id->procino=st.st_ino;id->representative=ident_count;
    ident_count++;pids_seen=ident_count;added_tasks++;*added=1;
    /* A new pair of our own handles changes our table. Never exempt inherited
     * self FDs, cwd or root; only invalidate and recheck the self table. */
    struct ident *self=latest((unsigned)getpid());if(self)self->fd_scanned=0;
    return 0;
}
static int reconcile_tasks(unsigned *list,size_t count,unsigned *changed){
    *changed=0;
    for(size_t i=0;i<count;i++){current_pid=list[i];int added;if(pin_task(list[i],&added))return -1;*changed+=(unsigned)added;}
    for(unsigned i=0;i<ident_count;i++)if(!ids[i].retired){
        int present=0;for(size_t j=0;j<count;j++)if(list[j]==ids[i].pid){present=1;break;}
        if(!present){current_pid=ids[i].pid;int r=retire_if_exited(&ids[i]);if(r!=1){if(!r)errno=ESTALE;return -1;}(*changed)++;}
    }
    return 0;
}
static int identity_matches(const struct ident *id){
    uintmax_t start;unsigned long flags;char state;unsigned tgid;
    if(stat_record(id->pid,&start,&flags,&state)||task_group(id->pid,&tgid))return -1;
    if(start!=id->start||tgid!=id->tgid||!!(flags&PF_KTHREAD_E5)!=id->kernel){errno=ESTALE;return -1;}if(state=='Z'||state=='X'){errno=ESRCH;return -1;}return 0;
}
static int compare_files(unsigned a,unsigned b,int *same){
    if(control())return -1;
    if(++kcmp_calls>MAX_KCMP){errno=E2BIG;return -1;}
    long result;
#if defined(E5_SCANNER_HOST_TEST) && !defined(E5_SCANNER_LINUX_INTEGRATION)
    char pathbuf[PATH_MAX],value[80];size_t length;uintmax_t av,bv;
    const char *fault=getenv("E5_SCANNER_TEST_FAULT");
    if(fault&&!strcmp(fault,"kcmp-eperm")){errno=EPERM;return -1;}
    if(fault&&!strcmp(fault,"kcmp-enosys")){errno=ENOSYS;return -1;}
    if(fault&&!strcmp(fault,"kcmp-eacces")){errno=EACCES;return -1;}
    if(fault&&!strcmp(fault,"kcmp-einval")){errno=EINVAL;return -1;}
    if(fault&&!strcmp(fault,"kcmp-sigsys")){raise(SIGSYS);return control();}
    if(proc_path(pathbuf,sizeof pathbuf,a,"files-table")||read_file(pathbuf,value,sizeof value-1,&length))return -1;
    while(length&&value[length-1]=='\n')value[--length]=0;
    if(decimal(value,&av)){errno=EPROTO;return -1;}
    if(proc_path(pathbuf,sizeof pathbuf,b,"files-table")||read_file(pathbuf,value,sizeof value-1,&length))return -1;
    while(length&&value[length-1]=='\n')value[--length]=0;
    if(decimal(value,&bv)){errno=EPROTO;return -1;}
    result=av==bv?0:1;
    if(fault&&!strcmp(fault,"kcmp-distinct-2")&&av!=bv)result=2;
    if(fault&&!strcmp(fault,"kcmp-distinct-3")&&av!=bv)result=3;
    if(fault&&!strcmp(fault,"kcmp-invalid-result"))result=4;
    if(fault&&!strcmp(fault,"kcmp-final-split")&&final_relations)result=1;
    if(fault&&!strcmp(fault,"kcmp-final-esrch")&&final_relations){errno=ESRCH;return -1;}
    if(fault&&!strcmp(fault,"kcmp-final-expired")&&final_relations)deadline_ms=0;
#else
#if defined(__linux__) && defined(SYS_kcmp)
    result=syscall(SYS_kcmp,(pid_t)a,(pid_t)b,KCMP_FILES,0UL,0UL);
#else
    (void)a;(void)b;errno=ENOSYS;return -1;
#endif
#endif
    if(control())return -1;
    if(result<0)return -1;
    if(result>3){errno=EPROTO;return -1;}*same=result==0;return 0;
}
static int compare_stable(const struct ident *a,const struct ident *b,int *same){
    if(identity_matches(a)||identity_matches(b))return -1;
    if(compare_files(a->pid,b->pid,same))return -1;
    return identity_matches(a)||identity_matches(b)?-1:0;
}
static int classify_files(struct ident *id){
    id->representative=(unsigned)(id-ids);
    /* TGID only bounds the candidate search. Only KCMP_FILES equality merges.
     * Kernel tasks are scanned independently, including their empty FD dirs. */
    if(id->kernel)return 0;
    for(unsigned i=0;i<ident_count;i++){
        if(&ids[i]==id||ids[i].retired||!ids[i].scanned||ids[i].kernel||ids[i].representative!=i||ids[i].tgid!=id->tgid)continue;
        int same;subphase="pid-files-classification";detail="kcmp-files";
        if(compare_stable(id,&ids[i],&same)){int e=errno;if((e==ENOENT||e==ESRCH)&&retire_if_exited(&ids[i])==1)continue;errno=e;return -1;}
        if(same){id->representative=i;ids[i].fd_scanned=0;shared_tasks++;return 0;}
    }
    return 0;
}
/* 0=ordinary/unclassified (strict), 1=kernel anonymous pipe, 2=kernel socket.
 * This is direct held-path classification, not a claim about hidden references. */
static unsigned stream_kind(const struct stat *st,uintmax_t fs){
    if(S_ISFIFO(st->st_mode)&&fs==E5_PIPEFS_MAGIC)return 1;
    if(S_ISSOCK(st->st_mode)&&fs==E5_SOCKFS_MAGIC)return 2;
    return 0;
}
#if defined(__linux__) && (!defined(E5_SCANNER_HOST_TEST) || defined(E5_SCANNER_LINUX_INTEGRATION))
static int object_equal(const struct stat *a,const struct stat *b){
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode;
}
#endif
#if defined(E5_SCANNER_HOST_TEST) && defined(E5_SCANNER_LINUX_INTEGRATION)
/* Real-object interleaving fixture; absent from every production build. */
static int object_test_barrier(const char *stage){
    const char *v=getenv("E5_SCANNER_TEST_OBJECT_SYNC");unsigned pid,fd;char at[32],extra;static int used;
    if(!v||used||sscanf(v,"%u:%u:%31s %c",&pid,&fd,at,&extra)!=3||pid!=current_pid||fd!=current_fd||strcmp(at,stage))return 0;
    used=1;const char *old=subphase;subphase="fd-object-test-barrier";detail=stage;
    if(emit("PHASE",0,""))return -1;
    for(;;){if(control())return -1;struct pollfd f={STDIN_FILENO,POLLIN,0};int r=poll(&f,1,1);if(r<0&&errno!=EINTR)return -1;if(r>0){char c;if(read(STDIN_FILENO,&c,1)!=1||c!='.'){errno=EPROTO;return -1;}break;}}
    subphase=old;return 0;
}
#endif
static int fd_object(const char *p,struct stat *out,char *link,uintmax_t *fs){
    *fs=0;
#if defined(E5_SCANNER_HOST_TEST) && !defined(E5_SCANNER_LINUX_INTEGRATION)
    /* Original fixtures stay strict. Only explicit test metadata models an
     * acquired object; this branch is absent in the real-proc integration. */
    if(check_link_record(p,0,out,link))return -1;
    char q[PATH_MAX],meta[160];size_t n;
    if(proc_path(q,sizeof q,current_pid,"fd-object-meta"))return -1;
    struct stat exists;if(lstat(q,&exists)){if(errno==ENOENT)return 0;return -1;}
    char name[32],full[PATH_MAX];snprintf(name,sizeof name,"%u",current_fd);
    if(join(full,sizeof full,q,name)||read_file(full,meta,sizeof meta-1,&n))return -1;
    unsigned long mode;uintmax_t dev,ino,magic;char extra;
    if(sscanf(meta,"%lo %ju %ju %jx %c",&mode,&dev,&ino,&magic,&extra)!=4){errno=EPROTO;return -1;}
    out->st_mode=(mode_t)mode;out->st_dev=(dev_t)dev;out->st_ino=(ino_t)ino;*fs=magic;
    if(protected_inode(out)){errno=EBUSY;return -1;}
    const char *fault=getenv("E5_SCANNER_TEST_FAULT");
    if(fault&&!strcmp(fault,"fd-object-identity-drift")){detail="fd-object-identity-drift";errno=ESTALE;return -1;}
    if(fault&&!strcmp(fault,"fd-object-open-eacces")){detail="fd-object-open";errno=EACCES;return -1;}
    return 0;
#elif defined(__linux__)
    struct stat initial,held,final;struct statfs info;char initial_link[PATH_MAX],held_link[PATH_MAX],final_link[PATH_MAX],selfpath[PATH_MAX],suffix[80];
    detail="fd-object-initial";
    if(check_link_record(p,0,&initial,initial_link))return -1;
#if defined(E5_SCANNER_HOST_TEST) && defined(E5_SCANNER_LINUX_INTEGRATION)
    if(object_test_barrier("initial"))return -1;
#endif
    if(control())return -1;
    detail="fd-object-open";
#if defined(E5_SCANNER_HOST_TEST) && defined(E5_SCANNER_LINUX_INTEGRATION)
    const char *of=getenv("E5_SCANNER_TEST_OPEN_FAULT");unsigned opid,ofd;int oe;char ox;
    if(of&&sscanf(of,"%u:%u:%d %c",&opid,&ofd,&oe,&ox)==3&&opid==current_pid&&ofd==current_fd){errno=oe;return -1;}
#endif
    /* Follow only the generated proc magiclink. O_NOFOLLOW here would pin the
     * symlink, not the object, and is therefore deliberately not used. */
    int fd=target_open(p,O_PATH|O_CLOEXEC);if(fd<0)return -1;
    int rc=-1,saved=0;
    detail="fd-object-held";
    if(fstat(fd,&held)||fstatfs(fd,&info)){saved=errno;goto done;}
    snprintf(suffix,sizeof suffix,"/proc/self/fd/%d",fd);
    if(path(selfpath,sizeof selfpath,suffix)||read_link(selfpath,held_link,sizeof held_link)){saved=errno;goto done;}
    if(protected_path(held_link)||protected_inode(&held)){saved=EBUSY;goto done;}
    /* Neither a safe initial string nor a later stream class can erase an
     * intervening different object. Compare each independent observation. */
    if(!object_equal(&initial,&held)||strcmp(initial_link,held_link)){detail="fd-object-identity-drift";saved=ESTALE;goto done;}
    #if defined(E5_SCANNER_HOST_TEST) && defined(E5_SCANNER_LINUX_INTEGRATION)
    if(object_test_barrier("held")){saved=errno;goto done;}
#endif
    detail="fd-object-final";
    if(check_link_record(p,0,&final,final_link)){saved=errno;goto done;}
    if(!object_equal(&held,&final)||strcmp(held_link,final_link)){detail="fd-object-identity-drift";saved=ESTALE;goto done;}
    if(control()){saved=errno;goto done;}
    *out=held;*fs=(uintmax_t)(unsigned long)info.f_type;snprintf(link,PATH_MAX,"%s",held_link);rc=0;
 done:
    if(close(fd)&&!rc){rc=-1;saved=errno;}
    if(rc)errno=saved;
    return rc;
#else
    (void)p;(void)out;(void)link;errno=ENOSYS;return -1;
#endif
}
struct fd_record { unsigned number;dev_t dev;ino_t ino;mode_t mode;char *link;uintmax_t fs;unsigned kind; };
struct fd_snapshot { struct fd_record *items;size_t count,cap,bytes; };
static void free_snapshot(struct fd_snapshot *s){for(size_t i=0;i<s->count;i++)free(s->items[i].link);free(s->items);memset(s,0,sizeof *s);}
static int fd_order(const void *a,const void *b){unsigned x=((const struct fd_record*)a)->number,y=((const struct fd_record*)b)->number;return x>y?1:x<y?-1:0;}
static int same_record(const struct fd_record *x,const struct fd_record *y){
    return x->number==y->number&&x->dev==y->dev&&x->ino==y->ino&&x->mode==y->mode&&x->fs==y->fs&&x->kind==y->kind&&!strcmp(x->link,y->link);
}
static int same_snapshot(const struct fd_snapshot *a,const struct fd_snapshot *b){
    size_t i=0,j=0;
    for(;;){
        while(i<a->count&&a->items[i].kind)i++;
        while(j<b->count&&b->items[j].kind)j++;
        if(i==a->count||j==b->count)return i==a->count&&j==b->count;
        if(!same_record(&a->items[i++],&b->items[j++]))return 0;
    }
}
static void diff_snapshot(const struct fd_snapshot *a,const struct fd_snapshot *b,unsigned pass){
    size_t i=0,j=0;int found=0,record_table=0;
    while(i<a->count||j<b->count){
        const struct fd_record *x=i<a->count?&a->items[i]:NULL,*y=j<b->count?&b->items[j]:NULL;
        if(x&&y&&x->number==y->number&&same_record(x,y)){i++;j++;continue;}
        if(!found){found=1;diff_tables_seen++;if(diff_tables_recorded<MAX_DIFF_TABLES){diff_tables_recorded++;record_table=1;}}
        if(x&&y&&x->number<y->number)y=NULL;else if(x&&y&&x->number>y->number)x=NULL;
        if(record_table&&diff_records_count<MAX_DIFF_RECORDS){
            struct diff_record *d=&differences[diff_records_count++];
            *d=(struct diff_record){current_pid,x?x->number:y->number,pass,x?x->kind:3,y?y->kind:3,x?(uintmax_t)x->dev:0,x?(uintmax_t)x->ino:0,y?(uintmax_t)y->dev:0,y?(uintmax_t)y->ino:0};
        }else diff_records_omitted++;
        if(x)i++;
        if(y)j++;
    }
}
static int fd_snapshot(struct ident *id,struct fd_snapshot *snapshot){
    char p[PATH_MAX];if(proc_path(p,sizeof p,id->pid,"fd")||confined(p,0))return -1;
    DIR *d=target_dir(p);if(!d)return -1;int rc=0,saved=0;
    struct stat own;if(fstat(dirfd(d),&own)){saved=errno;closedir(d);errno=saved;return -1;}
    for(;;){
        if(control()){rc=-1;saved=errno;break;}errno=0;struct dirent *de=readdir(d);if(!de){if(errno){rc=-1;saved=errno;}break;}
        if(!strcmp(de->d_name,".")||!strcmp(de->d_name,".."))continue;
        uintmax_t fdn;if(decimal(de->d_name,&fdn)||fdn>INT_MAX){rc=-1;saved=EPROTO;break;}
        current_fd=(unsigned)fdn;detail="fd-entry-limit";if(++fds_seen>MAX_FDS){rc=-1;saved=E2BIG;break;}
        char q[PATH_MAX],link[PATH_MAX];struct stat st;uintmax_t fs;int n=snprintf(q,sizeof q,"%s/%s",p,de->d_name);
        detail="fd-link-check";if(n<0||(size_t)n>=sizeof q||fd_object(q,&st,link,&fs)){rc=-1;saved=errno?errno:E2BIG;break;}
        /* Only our exact, newly opened enumeration descriptor is omitted from
         * stability comparison. It was checked above, and inherited self FDs
         * remain in the snapshot. No other task's FD gets this exception. */
        if(id->pid==(unsigned)getpid()&&fdn==(unsigned)dirfd(d)&&st.st_dev==own.st_dev&&st.st_ino==own.st_ino)continue;
        size_t size=strlen(link)+1;if(snapshot->bytes+size>16U*1024U*1024U){rc=-1;saved=E2BIG;break;}
        if(snapshot->count==snapshot->cap){size_t cap=snapshot->cap?snapshot->cap*2:32;if(cap>MAX_FDS)cap=MAX_FDS;void *next=realloc(snapshot->items,cap*sizeof *snapshot->items);if(!next){rc=-1;saved=ENOMEM;break;}snapshot->items=next;snapshot->cap=cap;}
        char *copy=strdup(link);if(!copy){rc=-1;saved=ENOMEM;break;}
        snapshot->items[snapshot->count++]=(struct fd_record){(unsigned)fdn,st.st_dev,st.st_ino,st.st_mode,copy,fs,stream_kind(&st,fs)};snapshot->bytes+=size;
        if(stream_kind(&st,fs))stream_observations++;
    }
    if(closedir(d)&&!rc){rc=-1;saved=errno;}if(rc){errno=saved;return -1;}
    qsort(snapshot->items,snapshot->count,sizeof *snapshot->items,fd_order);
#ifdef E5_SCANNER_HOST_TEST
    const char *sync=getenv("E5_SCANNER_TEST_FD_SYNC");
    if(sync&&(!strcmp(sync,"*")||(unsigned)strtoul(sync,NULL,10)==id->pid)){
        subphase="fd-snapshot-test-barrier";if(emit("PHASE",0,""))return -1;
        for(;;){if(control())return -1;struct pollfd f={STDIN_FILENO,POLLIN,0};int r=poll(&f,1,1);if(r<0&&errno!=EINTR)return -1;if(r>0){char c;if(read(STDIN_FILENO,&c,1)!=1||c!='.'){errno=EPROTO;return -1;}break;}}
        subphase="pid-fds";
    }
#endif
    return 0;
}
static int scan_fds(struct ident *id){
    current_pid=id->pid;current_fd=0;subphase="pid-fds";detail="identity-before-fds";
    if(identity_matches(id))return -1;
    struct fd_snapshot previous={0};int have_previous=0;fd_tables_seen++;
    for(unsigned pass=0;pass<MAX_LIFECYCLE_ROUNDS;pass++){
        struct fd_snapshot current={0};snapshot_attempts++;
        if(fd_snapshot(id,&current)){
            int e=errno;snapshots_discarded++;last_acquire_errno=e;free_snapshot(&current);free_snapshot(&previous);have_previous=0;
            /* A closed FD of a live task is not ignored: discard the entire
             * table and require two complete matching scans within this cap. */
            if(e==ENOENT||e==ESRCH){if(identity_matches(id))return -1;continue;}
            errno=e;return -1;
        }
        snapshots_complete++;
        if(id->missing_kernel_fs&&current.count){free_snapshot(&current);free_snapshot(&previous);detail="kernel-missing-fs-with-fds";errno=EPROTO;return -1;}
        if(have_previous)diff_snapshot(&previous,&current,pass+1);
        int stable=have_previous&&same_snapshot(&previous,&current);free_snapshot(&previous);previous=current;have_previous=1;
        if(identity_matches(id)){int e=errno;free_snapshot(&previous);errno=e;return -1;}
        if(stable){free_snapshot(&previous);id->fd_scanned=1;return 0;}
    }
    free_snapshot(&previous);detail="fd-table-not-converged";errno=ESTALE;return -1;
}
static int scan_pid(struct ident *id){
    current_pid=id->pid;current_fd=0;subphase="pid-initial-stat";detail="";uintmax_t start,after;unsigned long flags,after_flags;char state,after_state;
    if(stat_record(id->pid,&start,&flags,&state))goto unknown;
    if(state=='Z'||state=='X'){detail="pid-not-live";errno=ESRCH;goto unknown;}
    if(id->known&&id->start!=start){detail="pinned-start-drift";errno=ESTALE;goto unknown;}
    id->start=start;id->known=1;int kernel=(flags&PF_KTHREAD_E5)!=0,missing_kernel_fs=0;char p[PATH_MAX],ns[80],again[80];
    id->kernel=kernel;subphase="pid-tgid";if(task_group(id->pid,&id->tgid))goto unknown;
    subphase="pid-initial-namespace";detail="namespace-read";if(proc_path(p,sizeof p,id->pid,"ns/mnt"))return -1;
    if(read_link(p,ns,sizeof ns)){if(kernel&&errno==ENOENT){ns[0]=0;missing_kernel_fs=1;}else goto unknown;}
    if(*ns){detail="namespace-format";size_t n=strlen(ns);if(n<7||strncmp(ns,"mnt:[",5)||ns[n-1]!=']'||strspn(ns+5,"0123456789")!=n-6){errno=EPROTO;goto unknown;}if(mount_check(id->pid,ns))goto unknown;}
    for(int i=0;i<2;i++){subphase=i?"pid-root":"pid-cwd";detail="link-check";if(proc_path(p,sizeof p,id->pid,i?"root":"cwd"))goto unknown;int r=check_link(p,kernel);if(r<0)goto unknown;if(r>0)missing_kernel_fs=1;}
    id->missing_kernel_fs=missing_kernel_fs;
    if(classify_files(id))goto unknown;
    subphase="pid-post-stat";detail="";if(stat_record(id->pid,&after,&after_flags,&after_state))goto unknown;
    if(start!=after||((flags^after_flags)&PF_KTHREAD_E5)){detail="pid-identity-drift";errno=ESTALE;goto unknown;}
    if(after_state=='Z'||after_state=='X'){detail="pid-post-confirmable-exit";errno=ESRCH;goto unknown;}
    subphase="pid-post-namespace";detail="namespace-read";if(proc_path(p,sizeof p,id->pid,"ns/mnt"))return -1;
    if(read_link(p,again,sizeof again)){if(kernel&&errno==ENOENT)again[0]=0;else goto unknown;}
    if(strcmp(ns,again)){detail="namespace-drift";errno=ESTALE;goto unknown;}snprintf(id->ns,sizeof id->ns,"%s",ns);id->scanned=1;detail="";return 0;
unknown:
    return -1;
}
static int loops(void){
    char p[PATH_MAX];if(path(p,sizeof p,"/sys/block")||confined(p,0))return -1;DIR *d=opendir(p);if(!d)return -1;int rc=0,saved=0;
    for(;;){if(control()){rc=-1;saved=errno;break;}errno=0;struct dirent *de=readdir(d);if(!de){if(errno){rc=-1;saved=errno;}break;}if(strncmp(de->d_name,"loop",4))continue;uintmax_t loop;if(decimal(de->d_name+4,&loop)||loop>UINT_MAX){rc=-1;saved=EPROTO;break;}if(++loops_seen>128){rc=-1;saved=E2BIG;break;}char q[PATH_MAX],b[PATH_MAX],decoded[PATH_MAX];int n=snprintf(q,sizeof q,"%s/%s/loop/backing_file",p,de->d_name);size_t len;if(n<0||(size_t)n>=sizeof q){rc=-1;saved=E2BIG;break;}
        if(read_file(q,b,sizeof b-1,&len)){
            /* Absence is accepted only for an existing loop node whose entire
             * loop attribute directory is absent (unbound). Other gaps fail. */
            if(errno==ENOENT){char node[PATH_MAX],attr[PATH_MAX];struct stat a,z;if(join(node,sizeof node,p,de->d_name)||join(attr,sizeof attr,node,"loop")){rc=-1;saved=errno;break;}if(!confined(node,0)&&!stat(node,&a)&&stat(attr,&z)&&errno==ENOENT)continue;}
            rc=-1;saved=errno;break;
        }
        while(len&&b[len-1]=='\n')b[--len]=0;
        if(unescape(b,decoded,sizeof decoded)){rc=-1;saved=errno;break;}
        if(protected_path(decoded)){rc=-1;saved=EBUSY;break;}
        if(*decoded){
            struct stat backing;char target[PATH_MAX];
            if(decoded[0]!='/'){rc=-1;saved=EPROTO;break;}
#ifdef E5_SCANNER_HOST_TEST
            if(path(target,sizeof target,decoded)||confined(target,0)){rc=-1;saved=errno;break;}
#else
            snprintf(target,sizeof target,"%s",decoded);
#endif
            if(stat(target,&backing)){rc=-1;saved=errno;break;}
            if(protected_inode(&backing)){rc=-1;saved=EBUSY;break;}
        }
    }
    if(closedir(d)&&!rc){rc=-1;saved=errno;}if(rc)errno=saved;return rc;
}
#if defined(__linux__)
static int capability_child(void *arg){
    (void)arg;cancelled=0;
    while(!control()){struct timespec t={0,1000000};nanosleep(&t,NULL);}
    return 0;
}
static int reap_owned(pid_t child){
    if(child<=0)return 0;
    /* Only our two known private children. Never signal observed Android tasks. */
    if(kill(child,SIGKILL)&&errno!=ESRCH)return -1;
    uintmax_t begin,n;int status;if(clock_ms(&begin))return -1;
    for(;;){pid_t r=waitpid(child,&status,WNOHANG);if(r==child)return 0;if(r<0&&errno!=EINTR)return -1;
        if(clock_ms(&n)||n-begin>=250){errno=ETIMEDOUT;return -1;}
        struct timespec t={0,1000000};nanosleep(&t,NULL);
    }
}
static int real_capability(void){
    char *stack=NULL;pid_t shared=-1,separate=-1;int rc=-1,saved=0;long value;
    if(control())return -1;
    stack=malloc(65536);if(!stack)return -1;
    shared=clone(capability_child,stack+65536,CLONE_FILES|SIGCHLD,NULL);
    if(shared<0){saved=errno;goto done;}cap_shared_pid=shared;
    if(control()){saved=errno;goto done;}
    separate=fork();if(separate<0){saved=errno;goto done;}
    if(!separate)_exit(capability_child(NULL));
    cap_distinct_pid=separate;
#ifdef E5_SCANNER_HOST_TEST
    const char *capfault=getenv("E5_SCANNER_TEST_FAULT");
    if(capfault&&!strcmp(capfault,"capability-cancel-after-clone"))raise(SIGTERM);
    if(capfault&&!strcmp(capfault,"capability-expire-after-clone"))deadline_ms=0;
    if(capfault&&!strcmp(capfault,"capability-sigsys-after-clone"))raise(SIGSYS);
#endif
    if(control()){saved=errno;goto done;}
    detail="kcmp-owned-shared";kcmp_calls++;
#ifdef SYS_kcmp
    value=syscall(SYS_kcmp,getpid(),shared,KCMP_FILES,0UL,0UL);
#else
    value=-1;errno=ENOSYS;
#endif
    if(value!=0){saved=value<0?errno:EPROTO;goto done;}capability_shared=1;
    if(control()){saved=errno;goto done;}
    detail="kcmp-owned-distinct";kcmp_calls++;
#ifdef SYS_kcmp
    value=syscall(SYS_kcmp,getpid(),separate,KCMP_FILES,0UL,0UL);
#else
    value=-1;errno=ENOSYS;
#endif
    if(value<1||value>3){saved=value<0?errno:EPROTO;goto done;}capability_distinct=1;
    if(control()){saved=errno;goto done;}rc=0;
done:
    int separate_ok=reap_owned(separate)==0;
    if(!separate_ok){rc=-1;saved=errno;}
    int shared_ok=reap_owned(shared)==0;
    if(!shared_ok){rc=-1;saved=errno;}
    cap_children_reaped=separate_ok&&shared_ok;
    free(stack);if(rc)errno=saved?saved:EIO;return rc;
}
#endif
static int capability(void){
    if(set_phase("capability-owned-children"))return -1;
#ifdef E5_SCANNER_HOST_TEST
    const char *real=getenv("E5_SCANNER_TEST_REAL_KCMP");
    if(!real||strcmp(real,"1")){
        const char *fault=getenv("E5_SCANNER_TEST_FAULT");
        if(fault&&!strcmp(fault,"capability-eperm")){errno=EPERM;return -1;}
        if(fault&&!strcmp(fault,"capability-sigsys")){raise(SIGSYS);return control();}
        capability_shared=1;capability_distinct=1;cap_children_reaped=1;kcmp_calls=2;return control();
    }
#endif
#if defined(__linux__)
    return real_capability();
#else
    errno=ENOSYS;return -1;
#endif
}
#ifdef E5_SCANNER_HOST_TEST
static int test_base(const char *s){const char *p=NULL;if(!strncmp(s,"/tmp/e5-native-test-",20))p=s+20;if(!strncmp(s,"/private/tmp/e5-native-test-",28))p=s+28;if(!p||!*p)return 0;while(*p&&*p!='/'){if(!strchr("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",*p))return 0;p++;}return !strcmp(p,"/sandbox");}
#endif
int main(int argc,char **argv){
#ifdef E5_SCANNER_HOST_TEST
    (void)DEVICE_EXECUTION_ENABLED;
    if(argc<4||strcmp(argv[1],"--test-root"))return fail("host-test-root-required");
    char real[PATH_MAX];if(!test_base(argv[2])||!realpath(argv[2],real)||strcmp(real,argv[2])||!test_base(real))return fail("host-test-root-refused");snprintf(base,sizeof base,"%s",real);argc-=2;argv+=2;
#else
    if(!DEVICE_EXECUTION_ENABLED){errno=EPERM;return fail("production-device-execution-disabled");}
    if(geteuid()!=0){errno=EPERM;return fail("root-required");}
#endif
    if(argc!=6||(strcmp(argv[1],"scan")&&strcmp(argv[1],"capability"))||!hexid(argv[2],16)||!uuid_ok(argv[3])||!hexid(argv[4],32)||decimal(argv[5],&deadline_ms))return fail("invalid-arguments");
    tx=argv[2];boot=argv[3];op=argv[4];uintmax_t now;
    if(clock_ms(&now)||deadline_ms<=now||deadline_ms-now>7000){errno=ETIMEDOUT;return fail("invalid-short-deadline");}
    struct sigaction sa;memset(&sa,0,sizeof sa);sa.sa_handler=on_signal;sigemptyset(&sa.sa_mask);if(sigaction(SIGTERM,&sa,NULL)||sigaction(SIGINT,&sa,NULL)||sigaction(SIGHUP,&sa,NULL)||sigaction(SIGPIPE,&sa,NULL)||sigaction(SIGSYS,&sa,NULL))return fail("signal-setup-failed");
#if defined(E5_SCANNER_HOST_TEST) && !defined(E5_SCANNER_LINUX_INTEGRATION)
    self_start=1;const char *fault=getenv("E5_SCANNER_TEST_FAULT");if(fault&&!strcmp(fault,"self-start-zero"))self_start=0;if(fault&&!strcmp(fault,"cancel-before-scan"))raise(SIGTERM);if(fault&&!strcmp(fault,"expire-before-scan"))deadline_ms=now;
#else
    subphase="self-stat";unsigned long flags;char state;if(stat_record((unsigned)getpid(),&self_start,&flags,&state))return fail("self-starttime-unreadable");
#endif
    /* Unlike early target tasks, this newly launched scanner must have a positive tick identity. */
    if(!self_start){subphase="self-stat";detail="self-starttime-nonpositive";errno=EPROTO;return fail("self-starttime-nonpositive");}
    subphase="initial-boot";detail="";if(control()||boot_check()||emit("BEGIN",0,""))return fail("initial-control-or-boot-failed");
    if(!strcmp(argv[1],"capability")){
        if(capability()||boot_check()||control())return fail("kcmp-capability-unproven");
        phase="complete";subphase="capability-complete";detail="owned-children-only-not-cross-domain-permission";errno=0;return emit("RESULT",1,"")?70:0;
    }
    const char *roles[]={"active","stage","archive","failed"};snprintf(names[0],sizeof names[0],"e5linux");for(int i=1;i<4;i++)snprintf(names[i],sizeof names[i],"e5linux.%s.%s",roles[i],tx);
    if(set_phase("protected-tree")||load_tree())return fail("protected-tree-unknown");
    if(set_phase("global-loops")||loops())return fail("loop-busy-or-unknown");
    if(handle_budget())return fail("process-local-handle-budget-unavailable");
    unsigned list[MAX_PIDS];size_t count;unsigned changed;
    if(set_phase("enumerate-processes")||enumerate(list,&count)||!count)return fail("process-enumeration-unknown");
    if(set_phase("pin-process-identities")||reconcile_tasks(list,count,&changed))return fail("process-pinning-unknown");
    int converged=0;
    for(lifecycle_round=1;lifecycle_round<=MAX_LIFECYCLE_ROUNDS;lifecycle_round++){
        if(set_phase("processes"))return fail("cancel-or-deadline");
        final_relations=0;
        for(unsigned i=0;i<ident_count;i++)if(!ids[i].retired&&!ids[i].scanned){
            if(scan_pid(&ids[i])&&exit_or_fail(&ids[i]))return fail(errno==EBUSY?"process-uses-protected-tree":"process-scan-unknown");
        }
        /* Only a retired representative invalidates existing class coverage.
         * Each surviving member is compared again; the replacement table gets
         * a full scan. A live KCMP relationship change remains UNKNOWN. */
        for(unsigned i=0;i<ident_count;i++)if(!ids[i].retired&&ids[ids[i].representative].retired){
            ids[i].fd_scanned=0;
            if(classify_files(&ids[i])&&exit_or_fail(&ids[i]))return fail("retired-representative-reclassification-unknown");
        }
        if(set_phase("fd-tables"))return fail("fd-phase-control");
        for(unsigned i=0;i<ident_count;i++)if(!ids[i].retired&&ids[i].representative==i&&!ids[i].fd_scanned){
            if(scan_fds(&ids[i])&&exit_or_fail(&ids[i]))return fail(errno==EBUSY?"process-uses-protected-tree":"fd-table-scan-unknown");
        }
        final_relations=1;
        if(set_phase("final-process-identities"))return fail("final-control-unknown");
        for(unsigned i=0;i<ident_count;i++)if(!ids[i].retired){
            struct ident *id=&ids[i];uintmax_t start;unsigned long flags;char state;
            current_pid=id->pid;subphase="pid-final-stat";detail="";
            final_stat_expected_known=1;final_stat_expected=id->start;final_stat_observed_known=0;
            if(stat_record(id->pid,&start,&flags,&state)){
                int e=errno;
                if(kept_stat_read&&e==ESRCH&&retire_if_exited(id)==1){final_stat_expected_known=0;continue;}
                errno=e;
                if(e==ENOENT||e==ESRCH)return fail("final-pid-gone-unconfirmed");
                if(e==ETIMEDOUT)return fail("final-pid-stat-deadline-unknown");
                if(e==ECANCELED)return fail("final-pid-stat-cancelled-unknown");
                return fail(!strcmp(detail,"stat-read")?"final-pid-stat-read-error-unknown":"final-pid-stat-parse-error-unknown");
            }
            final_stat_observed_known=1;final_stat_observed=start;final_stat_state=state;
            if(start!=id->start){detail="stat-starttime-drift";errno=ESTALE;return fail("final-pid-starttime-changed-unknown");}
            if(state=='Z'||state=='X'){if(retire_if_exited(id)!=1)return fail("final-exit-not-confirmed");final_stat_expected_known=0;final_stat_observed_known=0;continue;}
            final_stat_expected_known=0;final_stat_observed_known=0;
            subphase="pid-final-namespace";detail="namespace-read";char p[PATH_MAX],ns[80];
            if(proc_path(p,sizeof p,id->pid,"ns/mnt"))return fail("final-namespace-unknown");
            if(read_link(p,ns,sizeof ns)){if((flags&PF_KTHREAD_E5)&&errno==ENOENT)ns[0]=0;else {if(!exit_or_fail(id))continue;return fail("final-namespace-unknown");}}
            if(strcmp(ns,id->ns)){errno=ESTALE;return fail("final-namespace-changed-unknown");}
            if(identity_matches(id)){if(!exit_or_fail(id))continue;return fail("final-task-identity-changed-unknown");}
            if(id->representative!=i&&!ids[id->representative].retired){
                int same;subphase="final-files-relation";detail="kcmp-files";
                if(compare_stable(id,&ids[id->representative],&same)){
                    int e=errno;
                    if(e==ENOENT||e==ESRCH){if(retire_if_exited(id)==1)continue;if(retire_if_exited(&ids[id->representative])==1)continue;}
                    errno=e;return fail("final-files-relation-changed-unknown");
                }
                if(!same){errno=ESTALE;return fail("final-files-relation-changed-unknown");}
            }
        }
        enum_gaps=0;subphase="closing-task-set";detail="";
        if(enumerate(list,&count)||reconcile_tasks(list,count,&changed))return fail("closing-task-set-unknown");
        unsigned pending=0;
        for(unsigned i=0;i<ident_count;i++)if(!ids[i].retired&&(!ids[i].scanned||ids[ids[i].representative].retired||!ids[ids[i].representative].fd_scanned))pending++;
        if(!enum_gaps&&!pending){converged=1;break;}
    }
    if(!converged){detail="bounded-lifecycle-not-converged";errno=ESTALE;return fail("lifecycle-not-converged-unknown");}
    if(set_phase("final-boot")||boot_check()||control())return fail("final-control-or-boot-failed");
    phase="complete";subphase="complete";detail="";errno=0;if(emit("RESULT",1,""))return 70;return 0;
}

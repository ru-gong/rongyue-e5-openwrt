/* Public reference export. Default build never accesses a device. */
#ifndef E5_PUBLIC_FIXTURE
#include <stdio.h>
int main(void){fputs("Reference-only export: device execution is disabled.\n",stderr);return 64;}
#else
#ifndef E5_IDLE_TEST
#error "Public fixture build also requires E5_IDLE_TEST"
#endif
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/sysmacros.h>
#include <sys/statfs.h>
#include <sys/ioctl.h>
#include <linux/magic.h>
#include <linux/nsfs.h>
#include <sched.h>
#endif
/* Read-only occupancy guard; scans every observable task, including unshared
 * thread file tables, cwd/root and mappings. It never opens a block device.
 * Mount namespaces/holders/swaps are additionally checked by tf-common.sh.
 * This is a bounded observation, not a claim that Android cannot race it. */
static const char *proc="/proc";
static dev_t target,disk;
static int number(const char*s){if(!*s)return 0;while(*s)if(*s<'0'||*s++>'9')return 0;return 1;}
static int path(char*out,size_t cap,const char*a,const char*b){int n=snprintf(out,cap,"%s/%s",a,b);return n<0||(size_t)n>=cap?-1:0;}
static int referenced(const struct stat*s){return s->st_dev==target||s->st_dev==disk||(S_ISBLK(s->st_mode)&&(s->st_rdev==target||s->st_rdev==disk));}
static int check_stat(const char*p){struct stat s;if(stat(p,&s)){if(errno==ENOENT||errno==ESRCH)return 0;return -1;}return referenced(&s)?1:0;}
#if defined(__linux__) && !defined(E5_IDLE_TEST)
static ino_t namespaces[16384];
static size_t namespace_count;
static int kernel_task(const char *p) {
 char name[PATH_MAX],line[256];
 if(path(name,sizeof name,p,"status"))return 0;
 FILE*f=fopen(name,"r");if(!f)return 0;
 int yes=0;while(fgets(line,sizeof line,f))if(!strcmp(line,"Kthread:\t1\n"))yes=1;
 fclose(f);return yes;
}
static int collect_namespaces(void) {
 DIR*ps=opendir(proc);if(!ps)return -1;
 struct dirent*e;int result=0;
 while((e=readdir(ps))){
  if(!number(e->d_name))continue;
  char pp[PATH_MAX],tp[PATH_MAX];
  if(path(pp,sizeof pp,proc,e->d_name)||path(tp,sizeof tp,pp,"task")){result=-1;break;}
  DIR*ts=opendir(tp);if(!ts){if(access(pp,F_OK))continue;result=-1;break;}
  struct dirent*t;
  while((t=readdir(ts))){
   if(!number(t->d_name))continue;
   char p[PATH_MAX],ns[PATH_MAX];struct stat st;
   if(path(p,sizeof p,tp,t->d_name)||path(ns,sizeof ns,p,"ns/mnt")){result=-1;break;}
   if(kernel_task(p))continue;
   if(stat(ns,&st)){if(access(p,F_OK))continue;result=-1;break;}
   size_t i;for(i=0;i<namespace_count;i++)if(namespaces[i]==st.st_ino)break;
   if(i==namespace_count){if(namespace_count==16384){result=-1;break;}namespaces[namespace_count++]=st.st_ino;}
  }
  closedir(ts);if(result)break;
 }
 closedir(ps);return result||!namespace_count?-1:0;
}
static int namespace_fd(const char *p) {
 int fd=open(p,O_PATH|O_CLOEXEC);if(fd<0)return errno==ENOENT||errno==ESRCH?0:-1;
 struct statfs fs;int result=fstatfs(fd,&fs);close(fd);if(result)return -1;
 if((unsigned long)fs.f_type!=NSFS_MAGIC)return 0;
 fd=open(p,O_RDONLY|O_CLOEXEC);if(fd<0)return -1;
 int type=ioctl(fd,NS_GET_NSTYPE);struct stat st;
 if(type<0||fstat(fd,&st)){close(fd);return -1;}close(fd);
 if(type!=CLONE_NEWNS)return 0;
 for(size_t i=0;i<namespace_count;i++)if(namespaces[i]==st.st_ino)return 0;
 return -1; /* Namespace survives only by fd: its mounts are not certified. */
}
#else
static int kernel_task(const char *p){(void)p;return 0;}
static int namespace_fd(const char *p){(void)p;return 0;}
#endif
static int scan_task(const char*p){
 if(kernel_task(p))return 0;
 char name[PATH_MAX];const char*links[]={"cwd","root",NULL};
 for(int i=0;links[i];i++){if(path(name,sizeof name,p,links[i]))return -1;int r=check_stat(name);if(r)return r;}
 if(path(name,sizeof name,p,"maps"))return -1;
 FILE*f=fopen(name,"r");
 if(!f){if((errno==ENOENT||errno==ESRCH)&&access(p,F_OK))return 0;return -1;}
 char *line=NULL;size_t cap=0;int r=0;
 while(getline(&line,&cap,f)>=0){unsigned ma,mi;if(sscanf(line,"%*s %*s %*s %x:%x",&ma,&mi)!=2){r=-1;break;}dev_t d=makedev(ma,mi);if(d==target||d==disk){r=1;break;}}
 if(ferror(f))r=-1;
 free(line);fclose(f);if(r)return r;
 if(path(name,sizeof name,p,"fd"))return -1;
 DIR*d=opendir(name);
 if(!d){if((errno==ENOENT||errno==ESRCH)&&access(p,F_OK))return 0;return -1;}
 struct dirent*e;while((e=readdir(d))){if(!number(e->d_name))continue;char fp[PATH_MAX];if(path(fp,sizeof fp,name,e->d_name)){r=-1;break;}r=check_stat(fp);if(!r)r=namespace_fd(fp);if(r)break;}closedir(d);return r;
}
int main(int argc,char**argv){
#ifdef E5_IDLE_TEST
 if(argc!=4)return 2;
 proc=argv[3];argc=3;
#endif
 unsigned a,b,c,d;char tail;
 if(argc!=3||sscanf(argv[1],"%u:%u%c",&a,&b,&tail)!=2||sscanf(argv[2],"%u:%u%c",&c,&d,&tail)!=2)return 2;
 target=makedev(a,b);disk=makedev(c,d);if(target==disk)return 2;
#if defined(__linux__) && !defined(E5_IDLE_TEST)
 if(collect_namespaces()){fputs("TF namespace inventory unknown; switching refused\n",stderr);return 2;}
#endif
 DIR*ps=opendir(proc);if(!ps)return 2;struct dirent*e;int result=0;unsigned tasks=0;
 while((e=readdir(ps))){if(!number(e->d_name))continue;char pp[PATH_MAX],tp[PATH_MAX];if(path(pp,sizeof pp,proc,e->d_name)||path(tp,sizeof tp,pp,"task")){result=2;break;}
   DIR*ts=opendir(tp);if(!ts){if(errno==ENOENT||errno==ESRCH)continue;result=2;break;}struct dirent*t;
   while((t=readdir(ts))){if(!number(t->d_name))continue;char p[PATH_MAX];if(path(p,sizeof p,tp,t->d_name)){result=2;break;}int r=scan_task(p);tasks++;if(r){result=r>0?1:2;break;}}
   closedir(ts);if(result)break;
 }
 closedir(ps);if(!tasks)result=2;
 if(result)fprintf(stderr,"TF occupancy %s; switching refused\n",result==1?"present":"unknown");
 return result;
}

#endif /* E5_PUBLIC_FIXTURE */

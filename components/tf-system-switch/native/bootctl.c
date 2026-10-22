/* Public reference export. Default build never accesses a device. */
#ifndef E5_PUBLIC_FIXTURE
#include <stdio.h>
int main(void){fputs("Reference-only export: device execution is disabled.\n",stderr);return 64;}
#else
#ifndef E5_BOOTCTL_TEST
#error "Public fixture build also requires E5_BOOTCTL_TEST"
#endif
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>
#ifndef E5_BOOTCTL_TEST
#include <sys/ioctl.h>
#include <sys/sysmacros.h>
#include <linux/fs.h>
#endif
/* Derived from the pinned e5-linux Magisk bootctl (MIT). The only block write
 * remains exactly 32 bytes at offset 2048. No foreign template is imported. */
static uint32_t crc32(const uint8_t *p,size_t n){uint32_t c=~0U;while(n--){c^=*p++;for(int i=0;i<8;i++)c=(c>>1)^(0xedb88320U&-(c&1));}return ~c;}
static uint32_t le32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int valid(const uint8_t*b){return !memcmp(b+4,"BCAB",4)&&b[8]==1&&(b[9]&7)==2&&le32(b+28)==crc32(b,28)&&(b[12]&15)&&(b[12]&128)&&!(b[13]&1)&&!(b[15]&1);}
static int bootable(int b){return (b&15)&&((b&128)||((b>>4&7)>=2));}
int main(int argc,char**argv){
 const char *path="/dev/block/by-name/misc";
#ifdef E5_BOOTCTL_TEST
 if(argc<3)return 2;
 path=argv[--argc];
#else
 if(access(path,F_OK))path="/dev/mmcblk0p3";
#endif
 if(argc<2)return 2;
 int arm=!strcmp(argv[1],"arm"),android=!strcmp(argv[1],"android");
 int next=!strcmp(argv[1],"next"),check=!strcmp(argv[1],"check"),writeop=arm||android;
 if((writeop&&argc!=3&&argc!=4)||(!writeop&&((!next&&!check)||argc!=2)))return 2;
 int fd=open(path,(writeop?O_RDWR:O_RDONLY)|O_CLOEXEC|O_NOFOLLOW);if(fd<0){perror("open misc");return 1;}
#ifdef E5_BOOTCTL_TEST
 struct stat fixture_st;
 if(fstat(fd,&fixture_st)||!S_ISREG(fixture_st.st_mode)||fixture_st.st_uid!=geteuid()||fixture_st.st_nlink!=1){fputs("regular owned fixture required\n",stderr);close(fd);return 64;}
#endif
#ifndef E5_BOOTCTL_TEST
 struct stat st;unsigned long long size=0;
 if(fstat(fd,&st)||!S_ISBLK(st.st_mode)||st.st_rdev!=makedev(179,3)||geteuid()!=0||ioctl(fd,BLKGETSIZE64,&size)||size!=1048576){fputs("misc identity refused\n",stderr);close(fd);return 1;}
#endif
 uint8_t before[32],after[32],verify[32];
 if(flock(fd,writeop?LOCK_EX:LOCK_SH)||pread(fd,before,32,2048)!=32||!valid(before)){fputs("misc CRC/state refused\n",stderr);close(fd);return 1;}
 if(check){puts("Boot control: CRC OK, Android A successful");close(fd);return 0;}
 if(next){puts(bootable(before[14])&&(!bootable(before[12])||(before[14]&15)>(before[12]&15))?"linux":"android");close(fd);return 0;}
 if(argc==4){uint8_t expected[33];int e=open(argv[3],O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
   ssize_t n=e<0?-1:read(e,expected,33);if(e>=0)close(e);
   if(n!=32||memcmp(expected,before,32)){fputs("misc changed since preparation\n",stderr);close(fd);return 1;}}
 int b=open(argv[2],O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
 if(b<0){perror("backup");close(fd);return 1;}
 if(write(b,before,32)!=32||fsync(b)){perror("backup write");close(b);close(fd);return 1;}close(b);
 memcpy(after,before,32);memcpy(after,arm?"_b\0\0":"_a\0\0",4);
 if(arm){after[12]=(before[12]&0xf0)|14;after[14]=0x2f;}
 else {after[12]=(before[12]&0xf0)|15;after[14]=(before[14]&0xf0)|14;}
 uint32_t c=crc32(after,28);for(int i=0;i<4;i++)after[28+i]=c>>(i*8);
 if(pwrite(fd,after,32,2048)!=32||fsync(fd)||pread(fd,verify,32,2048)!=32||memcmp(verify,after,32)){
   fputs("misc write/readback failed; restoring\n",stderr);
   if(pwrite(fd,before,32,2048)!=32||fsync(fd)||pread(fd,verify,32,2048)!=32||memcmp(verify,before,32))fputs("RESTORE UNKNOWN: do not reboot\n",stderr);
   close(fd);return 1;
 }
 close(fd);puts(arm?"Linux trial armed":"Android selected");return 0;
}

#endif /* E5_PUBLIC_FIXTURE */

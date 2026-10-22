#!/system/bin/sh
# PUBLIC_REFERENCE_GUARD_BEGIN
printf "%s\n" "Reference-only export: device execution is disabled." >&2
exit 64
# PUBLIC_REFERENCE_GUARD_END
# All supported entry modes first create a private mount namespace.
# The existing switch/native guards still reject any foreign TF mount.
set -eu
# Magisk otherwise saves stderr without showing it in the live console.
exec 2>&1
printf '%s\n' 'E5 系统切换：正在检查。此操作不是普通 Android 重启。'
printf '%s\n' '检查通过后会自动重启，上次约 11 分钟；请保持供电，不要手动重启或重复点击。'
BB=/data/adb/magisk/busybox
fail() { echo "E5-TF ACTION REFUSED: $*" >&2; exit 1; }
case "$#" in 0) mode=reboot ;; 1) mode=$1 ;; *) fail argument-count ;; esac
case "$mode" in check|reboot) ;; *) fail mode ;; esac
MODDIR=$(cd "${0%/*}" && pwd -P)
[ "$MODDIR" = /data/adb/modules/e5_local_system_switch ] || fail module-path
parent_ns=$("$BB" readlink /proc/self/ns/mnt) || fail parent-namespace
printf '%s\n' "$parent_ns" | "$BB" grep -Eq '^mnt:\[[0-9]+\]$' || fail parent-namespace-format
exec "$BB" unshare -m --propagation private "$BB" sh -c '
set -eu
BB=$1
MODDIR=$2
mode=$3
parent_ns=$4
fail() { echo "E5-TF ACTION REFUSED: $*" >&2; exit 1; }
current_ns=$("$BB" readlink /proc/self/ns/mnt) || fail private-namespace
printf "%s\n" "$current_ns" | "$BB" grep -Eq "^mnt:\\[[0-9]+\\]$" || fail private-namespace-format
[ "$current_ns" != "$parent_ns" ] || fail namespace-not-created
"$BB" awk '\''
  { separated=0; for (i=7;i<=NF;i++) {
      if ($i=="-") { separated=1; break }
      if ($i ~ /^(shared|master|propagate_from):/) bad=1
    }
    if (!separated) bad=1
  }
  END { exit (NR==0 || bad) ? 1 : 0 }
'\'' /proc/self/mountinfo || fail propagation-not-private
exec "$BB" sh "$MODDIR/switch.sh" "$mode"
' e5-tf-private "$BB" "$MODDIR" "$mode" "$parent_ns"

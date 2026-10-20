#!/system/bin/sh
# SPDX-License-Identifier: MIT
# Sanitized research reference; private bindings and executable helper omitted.
printf "%s\n" "Reference only: this public snapshot cannot install or switch a device." >&2
exit 64

# Device-specific action only. No boot hooks, boot-chain sync or NV access.
set -eu
umask 077
BB=/data/adb/magisk/busybox
MODDIR=$(cd "${0%/*}" && pwd -P)
BY=/dev/block/by-name
MISC=/dev/block/mmcblk0p3
IMAGE=/data/e5linux/openwrt.ext4
flag=/data/e5linux/openwrt-default-boot
armed=0
tmp=
run=

fail() { echo "切换已停止：$*" >&2; exit 1; }
sha() { "$BB" sha256sum "$1" | "$BB" cut -d ' ' -f1; }
cleanup() {
    rc=$?
    trap - EXIT HUP INT TERM
    if [ "$armed" = 1 ]; then
        # The known reset did not complete. Thaw before touching data-backed logs.
        /system/bin/toybox fsfreeze -u /data 2>/dev/null || true
        if "$BB" cmp -s "$MISC" "$run/before.misc"; then
            echo RESTORED > "$run/result"
        elif "$BB" dd if="$run/before.bc32" of="$MISC" bs=1 seek=2048 count=32 conv=notrunc,fsync 2>/dev/null &&
           "$BB" dd if="$MISC" of="$tmp/restored.misc" bs=1048576 count=1 2>/dev/null &&
           "$BB" cmp -s "$tmp/restored.misc" "$run/before.misc"; then
            echo '切换未完成，原启动控制已恢复并完整核对。' >&2
            echo RESTORED > "$run/result"
        else
            echo '启动控制恢复未获完整确认，请保持开机并联系维护。' >&2
            echo UNKNOWN > "$run/result"
        fi
        if [ -f "$run/default-boot.before" ]; then
            "$BB" cp "$run/default-boot.before" "$flag"
        elif [ -f "$run/default-boot.absent" ]; then
            "$BB" rm -f "$flag"
        fi
        "$BB" sync
        rc=1
    fi
    if [ -n "$tmp" ]; then
        "$BB" umount "$tmp/root" 2>/dev/null || true
        # This private RAM directory holds no user files. Leave unknown contents.
        for file in before.misc after.misc expected.misc restored.misc after.bc32; do
            "$BB" rm -f "$tmp/$file"
        done
        "$BB" rmdir "$tmp/root" "$tmp" 2>/dev/null || true
    fi
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

case "${1:-check}" in check|reboot) mode=${1:-check} ;; *) fail '仅支持 check 或 reboot' ;; esac
[ "$#" -le 1 ] || fail '参数无效'
[ "$MODDIR" = /data/adb/modules/e5_local_system_switch ] || fail '模块路径不正确'
[ "$(id -u)" = 0 ] || fail '需要 root'
[ "$(getprop ro.serialno)" = UNSET_DEVICE_SERIAL ] || fail '设备身份不匹配'
[ "$(getprop ro.boot.slot_suffix)" = _a ] || fail '当前不是 Android A'
[ "$(getprop ro.boot.verifiedbootstate)" = orange ] || fail '启动锁状态不匹配'
[ "$(getprop sys.boot_completed)" = 1 ] || fail '请等 Android 完全开机后再操作'
exec 9>"$MODDIR/.operation.lock"
"$BB" flock -n 9 || fail '另一项切换正在执行'
[ "$(cat /sys/class/block/mmcblk0/device/cid)" = UNSET_DEVICE_CID ] || fail '存储设备不匹配'
for entry in '3 135168 2048' '37 1566720 131072' '70 15241216 45834240'; do
    set -- $entry
    [ "$(cat /sys/class/block/mmcblk0p$1/start)" = "$2" ] &&
    [ "$(cat /sys/class/block/mmcblk0p$1/size)" = "$3" ] || fail '分区几何发生变化'
done
[ "$("$BB" readlink -f "$BY/misc")" = "$MISC" ] && [ -b "$MISC" ] || fail 'misc 别名异常'
[ "$("$BB" stat -c '%t:%T' "$MISC")" = b3:3 ] || fail 'misc 设备号不匹配'
[ "$("$BB" blockdev --getsize64 "$MISC")" = 1048576 ] || fail 'misc 长度异常'
[ "$("$BB" readlink -f "$BY/boot_b")" = /dev/block/mmcblk0p37 ] || fail 'B 槽别名异常'
gpt=$("$BB" dd if=/dev/block/mmcblk0 bs=4096 count=8 2>/dev/null | "$BB" sha256sum | "$BB" cut -d ' ' -f1)
[ "$gpt" = UNSET_VERIFIED_SHA256 ] || fail '分区表不匹配'
[ "$(sha "$MODDIR/e5-bootctl")" = UNSET_VERIFIED_SHA256 ] || fail '启动控制程序校验失败'
"$MODDIR/e5-bootctl" check || fail '启动控制格式、CRC 或回退状态异常'
set -- $("$BB" dd if="$MISC" bs=1 skip=2060 count=4 2>/dev/null | "$BB" od -An -tu1)
[ "$#" = 4 ] && [ $(($3 & 15)) -le $(($1 & 15)) ] || fail '已有待完成的 B 槽启动或 OTA'
"$BB" sha256sum -c "$MODDIR/protected.sha256" >/dev/null || fail '启动链与已验收版本不同；不会自动同步或刷写'
prefix=$("$BB" dd if="$BY/boot_b" bs=1048576 count=56 2>/dev/null | "$BB" sha256sum | "$BB" cut -d ' ' -f1)
suffix=$("$BB" dd if="$BY/boot_b" bs=1048576 skip=60 count=4 2>/dev/null | "$BB" sha256sum | "$BB" cut -d ' ' -f1)
[ "$prefix" = UNSET_VERIFIED_SHA256 ] &&
[ "$suffix" = UNSET_VERIFIED_SHA256 ] || fail 'B 槽不是已验收的 OpenWrt'
[ -f "$IMAGE" ] && [ ! -L "$IMAGE" ] && [ "$("$BB" stat -c %s "$IMAGE")" = 2147483648 ] &&
[ "$("$BB" stat -c %i "$IMAGE")" = UNSET_IMAGE_INODE ] || fail 'OpenWrt 镜像身份或长度异常'
[ "$(cat /data/e5linux/boot-os)" = openwrt ] || fail '现有启动目标不是 OpenWrt'
[ ! -L "$flag" ] && { [ ! -e "$flag" ] || [ -f "$flag" ]; } || fail '默认启动标记异常'
if /system/bin/dmesg | "$BB" grep -Eiq 'F2FS-fs.*(error|corrupt|inconsistent)|I/O error|Kernel panic'; then
    fail '本次 Android 内核记录了文件系统或 I/O 异常'
fi

tmp=$("$BB" mktemp -d /dev/e5-system-switch.XXXXXX)
"$BB" mkdir "$tmp/root"
"$BB" mount -t ext4 -o loop,ro,noload "$IMAGE" "$tmp/root" || fail '无法只读检查 OpenWrt 根镜像'
"$BB" grep -q "DISTRIB_ID='OpenWrt'" "$tmp/root/etc/openwrt_release" && [ -x "$tmp/root/sbin/init" ] || fail '未找到 OpenWrt 系统'
"$BB" umount "$tmp/root" || fail '检查挂载点无法卸载'
echo '校验通过：Android A 保留，已安装的 OpenWrt 可以启动。'
[ "$mode" = reboot ] || exit 0

"$BB" mkdir -p /data/adb/e5-system-switch
"$BB" chmod 0700 /data/adb/e5-system-switch
run=$("$BB" mktemp -d /data/adb/e5-system-switch/switch.XXXXXX)
cat /proc/sys/kernel/random/boot_id > "$run/android-boot-id"
"$BB" dd if="$MISC" of="$run/before.misc" bs=1048576 count=1 conv=fsync 2>/dev/null
[ "$("$BB" stat -c %s "$run/before.misc")" = 1048576 ] || fail '完整启动控制备份失败'
[ "$(sha "$run/before.misc")" = "$(sha "$MISC")" ] || fail '启动控制备份核对失败'
"$BB" dd if="$run/before.misc" of="$run/before.bc32" bs=1 skip=2048 count=32 conv=fsync 2>/dev/null
if [ -f "$flag" ]; then
    "$BB" cp "$flag" "$run/default-boot.before"
else
    : > "$run/default-boot.absent"
fi
echo IN_FLIGHT > "$run/result"
"$BB" sync
# Every possible native write stays inside misc@2048+32, including native rollback.
armed=1
# Existing author S99 hook consumes this only once userspace is up, then
# re-arms Linux on subsequent boots. The user's chosen default is OpenWrt.
printf 'linux\n' > "$flag"
"$BB" sync
"$MODDIR/e5-bootctl" arm "$run/native-before.bc32" || fail '切换写入未获完整确认'
"$BB" cmp -s "$run/native-before.bc32" "$run/before.bc32" || fail '写入前状态发生变化'
"$BB" dd if="$MISC" of="$tmp/after.misc" bs=1048576 count=1 2>/dev/null
"$BB" dd if="$MISC" of="$tmp/after.bc32" bs=1 skip=2048 count=32 2>/dev/null
"$BB" cp "$run/before.misc" "$tmp/expected.misc"
"$BB" dd if="$tmp/after.bc32" of="$tmp/expected.misc" bs=1 seek=2048 count=32 conv=notrunc 2>/dev/null
"$BB" cmp -s "$tmp/after.misc" "$tmp/expected.misc" || fail '指定32字节以外的启动控制状态发生变化'
"$BB" cp "$tmp/after.bc32" "$run/armed.bc32"
echo ARMED_AND_READBACK_VERIFIED > "$run/result"
"$BB" sync
echo '正在进入 OpenWrt，请保持设备供电。'
# A clean Android init reboot would overwrite BCB. Use the proven author reset,
# only after successful sync and F2FS freeze; no writes to data after freezing.
/system/bin/toybox timeout -s TERM 20 /system/bin/sh -c '
    set -eu
    echo 1 > /proc/sys/kernel/sysrq
    /system/bin/toybox sync
    /system/bin/toybox fsfreeze -f /data
    echo b > /proc/sysrq-trigger
'
fail '重启未完成'

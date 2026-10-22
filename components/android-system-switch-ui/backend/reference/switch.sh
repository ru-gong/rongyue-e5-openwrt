#!/system/bin/sh
# PUBLIC_REFERENCE_GUARD_BEGIN
printf "%s\n" "Reference-only export: device execution is disabled." >&2
exit 64
# PUBLIC_REFERENCE_GUARD_END
# Explicit action only. No boot service, boot-chain syncing or physical NV write.
set -eu
umask 077
BB=/data/adb/magisk/busybox
MODDIR=$(cd "${0%/*}" && pwd -P)
TF_BINDING=$MODDIR/tf-binding.conf
TF_DEV_PREFIX=/dev/block
TF_IDLE_BIN=$MODDIR/e5-tf-idle
. "$MODDIR/tf-common.sh"
tf_load
BY=/dev/block/by-name
MISC=/dev/block/mmcblk0p3
armed=0
mounted=0
tmp=
run=
fail() { echo "切换已停止：$*" >&2; exit 1; }
sha() { tf_sha "$1"; }
cleanup() {
    rc=$?
    trap - EXIT HUP INT TERM
    if [ "$armed" = 1 ]; then
        /system/bin/toybox fsfreeze -u /data 2>/dev/null || true
        if "$BB" cmp -s "$MISC" "$run/before.misc"; then
            echo RESTORED > "$run/result"
        elif [ -f "$run/native-before.bc32" ] &&
             "$BB" cmp -s "$run/native-before.bc32" "$run/before.bc32" &&
             "$BB" dd if="$run/before.bc32" of="$MISC" bs=1 seek=2048 count=32 conv=notrunc,fsync 2>/dev/null &&
             "$BB" dd if="$MISC" of="$tmp/restored.misc" bs=1048576 count=1 2>/dev/null &&
             "$BB" cmp -s "$tmp/restored.misc" "$run/before.misc"; then
            echo RESTORED > "$run/result"
        else
            echo '启动控制恢复未完整确认，请保持开机并联系维护。' >&2
            echo UNKNOWN > "$run/result"
        fi
        "$BB" sync
        rc=1
    fi
    if [ "$mounted" = 1 ]; then
        "$BB" sync
        "$BB" umount "$tmp/root" || echo 'TF 卸载未确认；不要拔卡。' >&2
    fi
    # If a later reset/arm fails the valid TF request remains intentionally.
    # It has no Android boot hook and cannot itself alter misc. A later fully
    # validated TF boot may fulfill the user's already-requested return.
    [ -z "$tmp" ] || echo "本次内存诊断目录：$tmp" >&2
    exit "$rc"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
case "${1:-check}" in check|reboot) mode=${1:-check} ;; *) fail '仅支持 check 或 reboot' ;; esac
[ "$#" -le 1 ] || fail '参数无效'
[ "$MODDIR" = /data/adb/modules/e5_local_system_switch ] || fail '模块路径不正确'
[ "$(id -u)" = 0 ] || fail '需要 root'
[ "$(getprop ro.serialno)" = "$TF_ANDROID_SERIAL" ] || fail '设备身份不匹配'
[ "$(getprop ro.boot.slot_suffix)" = _a ] || fail '当前不是 Android A'
[ "$(getprop ro.boot.verifiedbootstate)" = orange ] || fail '启动锁状态不匹配'
[ "$(getprop sys.boot_completed)" = 1 ] || fail '请等 Android 完全开机后再操作'
exec 9>"$MODDIR/.operation.lock"
"$BB" flock -n 9 || fail '另一项切换正在执行'
echo '[1/9] 核对设备、TF 卡和启动控制。'
tf_internal && tf_card || fail '内部存储或 TF 身份不匹配'
[ "$TF_EMMC" = mmcblk0 ] && [ "$TF_MISC" = "$MISC" ] || fail '存储枚举不匹配'
[ "$("$BB" readlink -f "$BY/misc")" = "$MISC" ] || fail 'misc 别名异常'
[ "$("$BB" blockdev --getsize64 "$MISC")" = 1048576 ] || fail 'misc 长度异常'
[ "$("$BB" readlink -f "$BY/boot_b")" = /dev/block/mmcblk0p37 ] || fail 'B 槽别名异常'
[ "$(cat /sys/class/block/mmcblk0p37/start)" = 1566720 ] &&
[ "$(cat /sys/class/block/mmcblk0p37/size)" = 131072 ] || fail 'B 槽几何不匹配'
gpt=$("$BB" dd if=/dev/block/mmcblk0 bs=4096 count=8 2>/dev/null | "$BB" sha256sum | "$BB" cut -d ' ' -f1)
[ "$gpt" = "$TF_GPT_SHA256" ] || fail '分区表不匹配'
[ "$(sha "$MODDIR/e5-tf-bootctl")" = "$TF_BOOTCTL_SHA256" ] &&
[ "$(sha "$TF_IDLE_BIN")" = "$TF_IDLE_SHA256" ] || fail '本地辅助程序校验失败'
"$MODDIR/e5-tf-bootctl" check || fail '启动控制格式、CRC 或 Android 回退状态异常'
set -- $("$BB" dd if="$MISC" bs=1 skip=2060 count=4 2>/dev/null | "$BB" od -An -tu1)
[ "$#" = 4 ] && [ $(($3 & 15)) -le $(($1 & 15)) ] || fail '已有待完成的 B 槽启动或 OTA'
[ "$(sha "$MODDIR/protected.sha256")" = "$TF_PROTECTED_SHA256" ] || fail '保护清单校验失败'
echo '[2/9] 校验 Android 保护分区；本阶段可能需要数分钟。'
"$BB" sha256sum -c "$MODDIR/protected.sha256" >/dev/null || fail 'Android 启动链与已验收版本不同'
echo '[3/9] 校验 OpenWrt 启动镜像。'
prefix=$("$BB" dd if="$BY/boot_b" bs=1048576 count=56 2>/dev/null | "$BB" sha256sum | "$BB" cut -d ' ' -f1)
suffix=$("$BB" dd if="$BY/boot_b" bs=1048576 skip=60 count=4 2>/dev/null | "$BB" sha256sum | "$BB" cut -d ' ' -f1)
[ "$prefix" = "$TF_BOOT_PREFIX_SHA256" ] && [ "$suffix" = "$TF_BOOT_SUFFIX_SHA256" ] || fail 'B 槽不是绑定的 TF OpenWrt'
if /system/bin/dmesg | "$BB" grep -Eiq 'F2FS-fs.*(error|corrupt|inconsistent)|I/O error|Kernel panic'; then
    fail '本次 Android 内核记录了文件系统或 I/O 异常'
fi
echo '[4/9] 检查 TF 占用并只读校验系统文件，请继续等待。'
tmp=$("$BB" mktemp -d /dev/e5-tf-switch.XXXXXX)
"$BB" mkdir "$tmp/root"
cd /
tf_idle || fail 'TF 存在占用或无法完整检查'
"$BB" mount -t ext4 -o ro,noload,noatime "$TF_ROOTDEV" "$tmp/root" || fail 'TF 只读挂载失败'
mounted=1
tf_idle "$tmp/root" && tf_verify_root "$tmp/root" || fail 'TF 校验失败'
"$BB" umount "$tmp/root" || fail 'TF 检查挂载无法卸载'
mounted=0
tf_card && tf_idle || fail 'TF 占用或身份发生变化'
echo '校验通过：Android A 保留，指定 TF OpenWrt 可供切换。'
[ "$mode" = reboot ] || exit 0
echo '[5/9] 只读检查通过，备份启动控制以保留回退能力。'
"$BB" mkdir -p /data/adb/e5-system-switch
"$BB" chmod 0700 /data/adb/e5-system-switch
run=$("$BB" mktemp -d /data/adb/e5-system-switch/tf-switch.XXXXXX)
cat /proc/sys/kernel/random/boot_id > "$run/android-boot-id"
"$BB" dd if="$MISC" of="$run/before.misc" bs=1048576 count=1 conv=fsync 2>/dev/null
[ "$("$BB" stat -c %s "$run/before.misc")" = 1048576 ] &&
[ "$(sha "$run/before.misc")" = "$(sha "$MISC")" ] || fail '完整启动控制备份失败'
"$BB" dd if="$run/before.misc" of="$run/before.bc32" bs=1 skip=2048 count=32 conv=fsync 2>/dev/null
printf 'e5-tf-return-v1\n%s\n%s\n' "$TF_INSTALL_ID" "$TF_KERNEL_RELEASE" > "$tmp/request"
echo PREPARED > "$run/result"
"$BB" sync
echo '[6/9] 重新校验 TF 并准备返回请求；此时尚未选择 OpenWrt 启动。'
tf_card && tf_idle || fail '写入标记前 TF 状态改变'
"$BB" mount -t ext4 -o rw,noatime "$TF_ROOTDEV" "$tmp/root" || fail 'TF 标记挂载失败'
mounted=1
tf_verify_root "$tmp/root" && tf_idle "$tmp/root" || fail '写入前 TF 校验失败'
request=$tmp/root/etc/e5/local-switch/return-to-linux
for p in "$tmp/root/etc/e5" "$tmp/root/etc/e5/local-switch"; do
    [ -d "$p" ] && [ ! -L "$p" ] || fail 'TF 标记目录异常'
done
[ ! -L "$request" ] && { [ ! -e "$request" ] || [ -f "$request" ]; } || fail 'TF 标记类型异常'
if [ -e "$request" ]; then
    "$BB" cmp -s "$request" "$tmp/request" || fail '已有不同返回请求'
else
    request_tmp=$("$BB" mktemp "$tmp/root/etc/e5/local-switch/.request.XXXXXX")
    "$BB" cat "$tmp/request" > "$request_tmp"
    "$BB" chmod 0600 "$request_tmp"
    "$BB" mv "$request_tmp" "$request"
fi
"$BB" sync
"$BB" umount "$tmp/root" || fail 'TF 标记挂载无法卸载'
mounted=0
echo '[7/9] 只读复核返回请求和系统文件，请勿重复点击。'
tf_card && tf_idle || fail 'TF 标记写入后状态改变'
"$BB" mount -t ext4 -o ro,noload,noatime "$TF_ROOTDEV" "$tmp/root" || fail 'TF 标记读回挂载失败'
mounted=1
tf_verify_root "$tmp/root" && "$BB" cmp -s "$tmp/root/etc/e5/local-switch/return-to-linux" "$tmp/request" || fail 'TF 标记读回失败'
"$BB" umount "$tmp/root" || fail 'TF 读回挂载无法卸载'
mounted=0
tf_card && tf_idle || fail '启动控制前 TF 状态改变'
echo '[8/9] 校验完成，设置并读回本次 OpenWrt 启动选择。'
# Only this reviewed native program writes misc; all rollback writes are bounded.
armed=1
"$MODDIR/e5-tf-bootctl" arm "$run/native-before.bc32" "$run/before.bc32" || fail '启动控制写入未确认'
"$BB" cmp -s "$run/native-before.bc32" "$run/before.bc32" || fail '写入前启动控制发生变化'
"$BB" dd if="$MISC" of="$tmp/after.misc" bs=1048576 count=1 2>/dev/null
"$BB" dd if="$MISC" of="$tmp/after.bc32" bs=1 skip=2048 count=32 2>/dev/null
"$BB" cp "$run/before.misc" "$tmp/expected.misc"
"$BB" dd if="$tmp/after.bc32" of="$tmp/expected.misc" bs=1 seek=2048 count=32 conv=notrunc 2>/dev/null
"$BB" cmp -s "$tmp/after.misc" "$tmp/expected.misc" || fail '指定 32 字节外的启动控制发生变化'
tf_card && tf_idle || fail '复位前 TF 状态改变'
echo ARMED_AND_READBACK_VERIFIED > "$run/result"
"$BB" sync
echo '[9/9] 启动选择已读回，正在安全重启；界面和连接随后会断开。'
echo '正在进入 TF OpenWrt，请保持设备供电。'
# Preserve the proven Android reset order. No TF filesystem is mounted here.
# No writes to Android /data after successful freeze.
/system/bin/toybox timeout -s TERM 20 /system/bin/sh -c '
    set -eu
    echo 1 > /proc/sys/kernel/sysrq
    /system/bin/toybox sync
    /system/bin/toybox fsfreeze -f /data
    echo b > /proc/sysrq-trigger
'
fail '重启未完成'

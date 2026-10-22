#!/bin/sh
# PUBLIC_REFERENCE_GUARD_BEGIN
printf "%s\n" "Reference-only export: device execution is disabled." >&2
exit 64
# PUBLIC_REFERENCE_GUARD_END
# Shared trusted shell library. Source only the package's pinned binding file.
# Caller supplies BB, TF_BINDING and TF_BASE; no eval of card content.
tf_fail() { echo "E5-TF REFUSED: $*" >&2; return 1; }
tf_sha() { "$BB" sha256sum "$1" | "$BB" cut -d ' ' -f1; }
tf_read() { "$BB" cat "$1" 2>/dev/null; }
tf_uuid_hex() { "$BB" od -An -tx1 -j 1128 -N 16 "$1" | "$BB" tr -d ' \n'; }
tf_ext4_magic() { "$BB" od -An -tx1 -j 1080 -N 2 "$1" | "$BB" tr -d ' \n'; }
tf_load() {
    [ -f "$TF_BINDING" ] && [ ! -L "$TF_BINDING" ] || { tf_fail binding-file; return 1; }
    . "$TF_BINDING"
    [ "$TF_SCHEMA" = e5-tf-v1 ] && [ "$TF_ENABLED" = 1 ] || { tf_fail binding-disabled; return 1; }
    [ -n "$TF_INSTALL_ID" ] && [ -n "$TF_KERNEL_RELEASE" ] || { tf_fail binding-incomplete; return 1; }
}
tf_internal() {
    TF_EMMC= TF_MISC=
    for node in /sys/class/block/mmcblk*; do
        [ -f "$node/device/type" ] || continue
        [ "$(tf_read "$node/device/type")" = MMC ] || continue
        [ "$(tf_read "$node/device/cid")" = "$TF_EMMC_CID" ] || continue
        [ -z "$TF_EMMC" ] || { tf_fail duplicate-internal; return 1; }
        TF_EMMC=${node##*/}
    done
    [ -n "$TF_EMMC" ] || { tf_fail internal-identity; return 1; }
    TF_MISC="${TF_DEV_PREFIX}/${TF_EMMC}p${TF_MISC_PART}"
    local n="/sys/class/block/${TF_EMMC}p${TF_MISC_PART}"
    "$BB" grep -qx PARTNAME=misc "$n/uevent" || { tf_fail misc-name; return 1; }
    [ "$(tf_read "$n/start")" = "$TF_MISC_START" ] && [ "$(tf_read "$n/size")" = "$TF_MISC_SECTORS" ] || { tf_fail misc-geometry; return 1; }
    [ -b "$TF_MISC" ] || { tf_fail misc-node; return 1; }
}
tf_userdata_identity() {
    # Fixed partition geometry on the already CID-bound internal device.
    # No filesystem magic/contents are read here.
    [ -n "$TF_EMMC" ] || { tf_fail userdata-internal-unbound; return 1; }
    TF_USERDATA="${TF_DEV_PREFIX}/${TF_EMMC}p70"
    local n="/sys/class/block/${TF_EMMC}p70" mm actual expected
    "$BB" grep -qx PARTNAME=userdata "$n/uevent" || { tf_fail userdata-name; return 1; }
    [ "$(tf_read "$n/start")" = 15241216 ] && [ "$(tf_read "$n/size")" = 45834240 ] || { tf_fail userdata-geometry; return 1; }
    [ ! -L "$TF_USERDATA" ] && [ -b "$TF_USERDATA" ] || { tf_fail userdata-node; return 1; }
    mm=$(tf_read "$n/dev")
    printf '%s\n' "$mm" | "$BB" grep -Eq '^[0-9]+:[0-9]+$' || { tf_fail userdata-device-number; return 1; }
    actual=$("$BB" stat -c '%t:%T' "$TF_USERDATA") || { tf_fail userdata-stat; return 1; }
    expected=$("$BB" printf '%x:%x' "${mm%:*}" "${mm#*:}") || return 1
    [ "$actual" = "$expected" ] || { tf_fail userdata-node-identity; return 1; }
    [ "$("$BB" blockdev --getsize64 "$TF_USERDATA")" = 23467130880 ] || { tf_fail userdata-device-size; return 1; }
    TF_USERDATA_MM=$mm
}
tf_userdata_unmounted() {
    local p n="/sys/class/block/${TF_EMMC}p70" seen=0
    [ -d "$n/holders" ] || { tf_fail userdata-holder-read; return 1; }
    for p in "$n"/holders/*; do
        [ ! -e "$p" ] || { tf_fail userdata-holder; return 1; }
    done
    for p in /proc/[0-9]*/task/[0-9]*; do
        [ -d "$p" ] || continue
        "$BB" grep -Eq '^Kthread:[[:space:]]+1$' "$p/status" 2>/dev/null && continue
        [ -r "$p/mountinfo" ] || { [ ! -d "$p" ] && continue; tf_fail userdata-mountinfo-unreadable; return 1; }
        "$BB" awk -v dev="$TF_USERDATA_MM" '$3==dev {bad=1} END {exit bad ? 1 : 0}' "$p/mountinfo" || { tf_fail userdata-mounted; return 1; }
        seen=$((seen + 1))
    done
    [ "$seen" -gt 0 ] || { tf_fail userdata-no-process-snapshot; return 1; }
}
tf_userdata_readonly() {
    [ "$("$BB" blockdev --getro "$TF_USERDATA")" = 1 ] &&
    [ "$(tf_read "/sys/class/block/${TF_EMMC}p70/ro")" = 1 ] || { tf_fail userdata-not-readonly; return 1; }
}
tf_userdata_protect() {
    # Volatile BLKROSET only. It does not mount, replay, repair, or write media.
    tf_userdata_identity && tf_userdata_unmounted || return 1
    "$BB" blockdev --setro "$TF_USERDATA" || { tf_fail userdata-setro; return 1; }
    tf_userdata_readonly
}
tf_userdata_check() {
    tf_userdata_identity && tf_userdata_unmounted && tf_userdata_readonly
}
tf_card() {
    TF_DISK= TF_ROOTDEV= TF_ROOT_MM=
    for node in /sys/class/block/mmcblk*; do
        [ -f "$node/device/type" ] || continue
        [ "$(tf_read "$node/device/type")" = SD ] || continue
        [ "$(tf_read "$node/device/cid")" = "$TF_CARD_CID" ] || continue
        [ -z "$TF_DISK" ] || { tf_fail duplicate-card; return 1; }
        TF_DISK=${node##*/}
    done
    [ -n "$TF_DISK" ] && [ "$TF_DISK" != "$TF_EMMC" ] || { tf_fail card-missing; return 1; }
    local base="/sys/class/block/$TF_DISK" n="/sys/class/block/${TF_DISK}p${TF_PART}"
    [ "$(tf_read "$base/size")" = "$TF_DISK_SECTORS" ] && [ "$(tf_read "$base/ro")" = 0 ] || { tf_fail card-size-or-ro; return 1; }
    [ "$(tf_read "$n/start")" = "$TF_PART_START" ] && [ "$(tf_read "$n/size")" = "$TF_PART_SECTORS" ] || { tf_fail root-geometry; return 1; }
    # MBR is checked directly; PARTUUID is not exported by every Android kernel.
    local diskdev="${TF_DEV_PREFIX}/${TF_DISK}" sig magic ptype other start count
    sig=$("$BB" od -An -tx1 -j 440 -N 4 "$diskdev" | "$BB" tr -d ' \n')
    magic=$("$BB" od -An -tx1 -j 510 -N 2 "$diskdev" | "$BB" tr -d ' \n')
    ptype=$("$BB" od -An -tx1 -j 450 -N 1 "$diskdev" | "$BB" tr -d ' \n')
    start=$("$BB" od -An -tu4 -j 454 -N 4 "$diskdev" | "$BB" tr -d ' \n')
    count=$("$BB" od -An -tu4 -j 458 -N 4 "$diskdev" | "$BB" tr -d ' \n')
    other=$("$BB" od -An -tx1 -v -j 462 -N 48 "$diskdev" | "$BB" tr -d ' 0\n')
    [ "$sig" = "$TF_MBR_SIG_LE" ] && [ "$magic" = 55aa ] && [ "$ptype" = 83 ] && [ -z "$other" ] &&
    [ "$start" = "$TF_PART_START" ] && [ "$count" = "$TF_PART_SECTORS" ] || { tf_fail mbr-binding; return 1; }
    if "$BB" grep -q '^PARTUUID=' "$n/uevent"; then
        "$BB" grep -qx "PARTUUID=$TF_PARTUUID" "$n/uevent" || { tf_fail root-partuuid; return 1; }
    fi
    [ "$(tf_read "$n/ro")" = 0 ] || { tf_fail root-readonly; return 1; }
    TF_ROOTDEV="${TF_DEV_PREFIX}/${TF_DISK}p${TF_PART}"
    [ -b "$TF_ROOTDEV" ] || { tf_fail root-node; return 1; }
    [ "$(tf_ext4_magic "$TF_ROOTDEV")" = 53ef ] || { tf_fail root-not-ext4; return 1; }
    [ "$(tf_uuid_hex "$TF_ROOTDEV")" = "$TF_FS_UUID_HEX" ] || { tf_fail root-fsuuid; return 1; }
    TF_ROOT_MM=$(tf_read "$n/dev")
    [ -n "$TF_ROOT_MM" ] || { tf_fail root-device-number; return 1; }
}
tf_empty_holders() {
    local node p
    for node in "/sys/class/block/$TF_DISK" "/sys/class/block/${TF_DISK}p$TF_PART"; do
        [ -d "$node/holders" ] || { tf_fail holder-read; return 1; }
        for p in "$node"/holders/*; do
            [ ! -e "$p" ] || { tf_fail card-holder; return 1; }
        done
    done
}
tf_idle() {
    # No target filesystem mounted in any observable process namespace.
    # An optional own mount is accepted ONLY in this process namespace and at
    # this exact path. Device-mapper/loop holders and swap remain forbidden.
    local allowed=${1:-} me ns p line seen=0 own
    tf_empty_holders || return 1
    me=$("$BB" readlink /proc/self/ns/mnt) || { tf_fail namespace-self; return 1; }
    for p in /proc/[0-9]*/task/[0-9]*; do
        [ -d "$p" ] || continue
        # No userspace files or mount namespace for a confirmed kernel task.
        "$BB" grep -Eq '^Kthread:[[:space:]]+1$' "$p/status" 2>/dev/null && continue
        ns=$("$BB" readlink "$p/ns/mnt" 2>/dev/null) || {
            [ ! -d "$p" ] && continue
            tf_fail namespace-unreadable; return 1
        }
        [ -r "$p/mountinfo" ] || { [ ! -d "$p" ] && continue; tf_fail mountinfo-unreadable; return 1; }
        own=0
        [ -n "$allowed" ] && [ "$ns" = "$me" ] && own=1
        "$BB" awk -v dev="$TF_ROOT_MM" -v disk="$(tf_read "/sys/class/block/$TF_DISK/dev")" -v own="$own" -v dst="$allowed" '
          / - nsfs / { bad=1 }
          $3==dev || $3==disk { if (!(own==1 && $3==dev && $4=="/" && $5==dst)) bad=1 }
          END { exit bad ? 1 : 0 }' "$p/mountinfo" || { tf_fail card-mounted; return 1; }
        seen=$((seen + 1))
    done
    [ "$seen" -gt 0 ] || { tf_fail no-process-snapshot; return 1; }
    # A swapfile or noncanonical alias is not guessed safe: refuse all active
    # swap while Android is preparing the card for switching.
    [ "$("$BB" awk 'END { print NR }' /proc/swaps)" = 1 ] || { tf_fail active-swap; return 1; }
    [ -n "${TF_IDLE_BIN:-}" ] && [ -x "$TF_IDLE_BIN" ] || { tf_fail occupancy-helper-missing; return 1; }
    "$TF_IDLE_BIN" "$TF_ROOT_MM" "$(tf_read "/sys/class/block/$TF_DISK/dev")" || { tf_fail occupancy-not-clear; return 1; }
}
tf_verify_root() {
    local root=$1
    [ -x "$root/sbin/init" ] && [ -s "$root/lib/firmware/wcnmodem.bin" ] || { tf_fail root-incomplete; return 1; }
    [ -f "$root/etc/e5/sd-root" ] && [ ! -L "$root/etc/e5/sd-root" ] || { tf_fail root-marker; return 1; }
    for f in tf-install-id tf-kernel-release tf-critical.sha256; do
        [ -f "$root/etc/e5/$f" ] && [ ! -L "$root/etc/e5/$f" ] || { tf_fail root-identity-file; return 1; }
    done
    [ "$(tf_read "$root/etc/e5/tf-install-id")" = "$TF_INSTALL_ID" ] || { tf_fail install-id; return 1; }
    [ "$(tf_read "$root/etc/e5/tf-kernel-release")" = "$TF_KERNEL_RELEASE" ] || { tf_fail kernel-identity; return 1; }
    [ "$(tf_sha "$root/etc/e5/tf-critical.sha256")" = "$TF_MANIFEST_SHA256" ] || { tf_fail manifest-identity; return 1; }
    # The manifest is host-validated, pinned, relative, and contains no user
    # config or writable state. Resolve absolute root symlinks through chroot.
    local verifier="$root/usr/local/bin/busybox" expected
    [ -f "$verifier" ] && [ ! -L "$verifier" ] || { tf_fail static-verifier-file; return 1; }
    expected=$("$BB" awk '$2=="usr/local/bin/busybox" { print $1 }' "$root/etc/e5/tf-critical.sha256")
    [ -n "$expected" ] && [ "$(tf_sha "$verifier")" = "$expected" ] || { tf_fail static-verifier-hash; return 1; }
    "$BB" chroot "$root" /usr/local/bin/busybox sha256sum -c /etc/e5/tf-critical.sha256 >/dev/null || { tf_fail critical-files; return 1; }
}
tf_running_root() {
    [ "$(uname -r)" = "$TF_KERNEL_RELEASE" ] || { tf_fail running-kernel; return 1; }
    tf_internal && tf_userdata_check && tf_card || return 1
    "$BB" awk -v dev="$TF_ROOT_MM" '$3==dev && $4=="/" && $5=="/" && $6 ~ /(^|,)rw(,|$)/ {ok=1} END {exit !ok}' /proc/self/mountinfo || { tf_fail not-bound-root; return 1; }
    # Any mounted F2FS or emergency-ro is a hard stop for switching/confirmation.
    "$BB" awk '/ - f2fs / || /emergency_ro/ {bad=1} END {exit bad ? 1 : 0}' /proc/self/mountinfo || { tf_fail unexpected-storage-state; return 1; }
    tf_verify_root / || return 1
    local errors="/sys/fs/ext4/${TF_DISK}p${TF_PART}/errors_count"
    [ -r "$errors" ] && [ "$(tf_read "$errors")" = 0 ] || { tf_fail ext4-errors; return 1; }
}

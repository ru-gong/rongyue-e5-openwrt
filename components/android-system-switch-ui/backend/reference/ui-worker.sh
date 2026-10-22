#!/system/bin/sh
# PUBLIC_REFERENCE_GUARD_BEGIN
printf "%s\n" "Reference-only export: device execution is disabled." >&2
exit 64
# PUBLIC_REFERENCE_GUARD_END
# Internal fixed worker, never an arbitrary shell-command runner.
set -eu
MOD=/data/adb/modules/e5_local_system_switch
. "$MOD/ui-common.sh"
ui_boot
[ "$#" = 0 ] || ui_refuse
ui_base
ui_file "$BASE/lock" && ui_file "$BASE/meta" && ui_file "$BASE/worker.log" || ui_refuse
# Inherited FD8 must still refer to the fixed private lock inode and hold it.
[ "$("$BB" stat -Lc '%d:%i' /proc/self/fd/8)" = "$("$BB" stat -c '%d:%i' "$BASE/lock")" ] || ui_refuse
"$BB" flock -n 8 || ui_refuse
IFS=' ' read -r META_BOOT META_PID META_TICKS STARTED extra < "$BASE/meta" || ui_refuse
[ "$META_BOOT" = "$BOOT" ] && [ "$META_PID:$META_TICKS" = 0:0 ] && [ -z "$extra" ] || ui_refuse
ui_process "$$" || ui_refuse
printf '%s %s %s %s\n' "$BOOT" "$$" "$TICKS" "$STARTED" > "$BASE/meta.next"
"$BB" mv "$BASE/meta.next" "$BASE/meta"
cd /
set +e
"$BB" sh "$MOD/action.sh"
rc=$?
set -e
# Only /dev tmpfs is written; no heartbeat or post-freeze /data write is added.
printf '%s\n' "$rc" > "$BASE/result.next"
"$BB" mv "$BASE/result.next" "$BASE/result"
printf 'E5_UI_TERMINAL %s\n' "$rc"
exit "$rc"

#!/system/bin/sh
# PUBLIC_REFERENCE_GUARD_BEGIN
printf "%s\n" "Reference-only export: device execution is disabled." >&2
exit 64
# PUBLIC_REFERENCE_GUARD_END
# Public API: exactly one of start, status, stream. No user command or path.
set -eu
MOD=/data/adb/modules/e5_local_system_switch
. "$MOD/ui-common.sh"
ui_boot
[ "$#" = 1 ] || ui_refuse
case "$1" in start|status|stream) ;; *) ui_refuse ;; esac
if [ "$1" = start ] && [ ! -e "$BASE" ] && [ ! -L "$BASE" ]; then
    if ui_external_busy; then
        STATE=UNKNOWN PHASE=UNKNOWN MESSAGE='已有其他切换正在执行，请勿重复提交。'
        ui_json; exit 1
    fi
    # mkdir is the atomic one-submission gate for this Android boot.
    ui_ram_parent
    if "$BB" mkdir -m 0700 "$BASE"; then
        ui_base
        : > "$BASE/lock"
        : > "$BASE/worker.log"
        exec 8<>"$BASE/lock"
        "$BB" flock -n 8 || ui_refuse
        ui_uptime
        printf '%s 0 0 %s\n' "$BOOT" "$NOW" > "$BASE/meta"
        # No pipe or terminal inherited from UI; no HUP-ignore changes to action.
        # FD8 stays inherited through setsid/worker/action until they exit.
        "$BB" setsid "$BB" sh "$MOD/ui-worker.sh" </dev/null >>"$BASE/worker.log" 2>&1 &
        exec 8>&-
        RUN=$BOOT-1 STATE=RUNNING PHASE=STARTING MESSAGE='任务已提交；请等待自动重启，可在本页查看进度。'
        ui_json; exit 0
    fi
fi
ui_snapshot
ui_json
[ "$1" = stream ] && { [ "$STATE" = RUNNING ] || [ "$STATE" = REBOOTING ]; } || exit 0
# One native read-only process watches the fixed tmpfs log. It performs no
# repeated su or shell subprocesses and exits on UI pipe closure.
exec "$MOD/e5-ui-stream" "$BOOT" "$STARTED" "$NUMBER"

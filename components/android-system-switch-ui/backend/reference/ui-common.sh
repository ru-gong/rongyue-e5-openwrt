#!/system/bin/sh
# PUBLIC_REFERENCE_GUARD_BEGIN
printf "%s\n" "Reference-only export: device execution is disabled." >&2
exit 64
# PUBLIC_REFERENCE_GUARD_END
# Fixed private protocol helpers. Never source a state file or accept a command.
BB=/data/adb/magisk/busybox
MOD=/data/adb/modules/e5_local_system_switch
BASE=/dev/e5-switch-ui
PATH=/system/bin:/system/xbin
export PATH
unset ENV BASH_ENV CDPATH
umask 077

ui_json() {
    # All string arguments are selected by this trusted source, not log text.
    printf '{"schema":"e5-switch-ui-v1","boot_id":"%s","run_id":"%s","state":"%s","phase":"%s","message":"%s","elapsed_seconds":%s,"exit_code":%s}\n' \
        "$BOOT" "$RUN" "$STATE" "$PHASE" "$MESSAGE" "$ELAPSED" "$CODE"
}
ui_refuse() {
    STATE=UNKNOWN PHASE=UNKNOWN MESSAGE='状态无法完整确认，请保持开机并联系维护。' CODE=null
    ui_json
    exit 1
}
ui_boot() {
    BOOT= RUN= STATE=UNKNOWN PHASE=UNKNOWN MESSAGE='状态未知。' ELAPSED=0 CODE=null
    [ "$("$BB" id -u)" = 0 ] || ui_refuse
    IFS= read -r BOOT < /proc/sys/kernel/random/boot_id || ui_refuse
    printf '%s\n' "$BOOT" | "$BB" grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' || { BOOT=; ui_refuse; }
    [ "$("$BB" readlink -f "$MOD")" = "$MOD" ] || ui_refuse
    [ "$("$BB" stat -c '%u:%g:%a' "$MOD")" = 0:0:700 ] || ui_refuse
}
ui_file() {
    [ -f "$1" ] && [ ! -L "$1" ] &&
    [ "$("$BB" stat -c '%u:%g:%a:%h' "$1")" = 0:0:600:1 ]
}
ui_ram_parent() {
    [ -d /dev ] && [ ! -L /dev ] || ui_refuse
    [ "$("$BB" stat -c '%u:%g' /dev)" = 0:0 ] || ui_refuse
    dev_mode=$("$BB" stat -c %a /dev) || ui_refuse
    case "$dev_mode" in ''|*[!0-7]*) ui_refuse ;; esac
    [ "$((0$dev_mode & 0022))" = 0 ] || ui_refuse
    # Exactly the whole /dev tmpfs; no bind/subtree or look-alike filesystem.
    "$BB" awk '$5=="/dev" {n++; if ($4!="/") bad=1; for(i=7;i<=NF;i++) if($i=="-"){if($(i+1)!="tmpfs")bad=1; break}} END{exit(n!=1||bad)?1:0}' /proc/self/mountinfo || ui_refuse
}
ui_base() {
    ui_ram_parent
    [ -d "$BASE" ] && [ ! -L "$BASE" ] &&
    [ "$("$BB" stat -c '%u:%g:%a' "$BASE")" = 0:0:700 ] &&
    [ "$("$BB" stat -c %d "$BASE")" = "$("$BB" stat -c %d /dev)" ] || ui_refuse
}
ui_uptime() {
    IFS=' ' read -r NOW ignored < /proc/uptime || ui_refuse
    case "$NOW" in ''|*[!0-9.]*) ui_refuse ;; esac
}
ui_process() {
    # Field 22 after removing the last ') ' is token 20; never match PID alone.
    [ -r "/proc/$1/stat" ] || return 1
    IFS= read -r proc_line < "/proc/$1/stat" || return 1
    proc_tail=${proc_line##*) }
    [ "$proc_tail" != "$proc_line" ] || return 1
    set -- $proc_tail
    [ "$#" -ge 20 ] && [ "$1" != Z ] || return 1
    shift 19
    TICKS=$1
    case "$TICKS" in ''|*[!0-9]*) return 1 ;; esac
}
ui_external_busy() {
    # A Magisk Action invocation has its own original lock; never bypass it.
    [ -e "$MOD/.operation.lock" ] || return 1
    ui_file "$MOD/.operation.lock" || ui_refuse
    exec 7<>"$MOD/.operation.lock"
    if "$BB" flock -n 7; then exec 7>&-; return 1; fi
    exec 7>&-
    return 0
}
ui_phase() {
    case "$NUMBER" in
        0) PHASE=STARTING; MESSAGE='任务已提交，正在准备检查。' ;;
        1) PHASE=IDENTITY; MESSAGE='核对设备、TF 卡和启动控制。' ;;
        2) PHASE=ANDROID_VERIFY; MESSAGE='校验 Android 保护分区，可能需要数分钟。' ;;
        3) PHASE=BOOT_VERIFY; MESSAGE='校验 OpenWrt 启动镜像。' ;;
        4) PHASE=TF_READONLY; MESSAGE='检查 TF 占用并只读校验系统文件。' ;;
        5) PHASE=CONTROL_BACKUP; MESSAGE='备份启动控制，保留回退能力。' ;;
        6) PHASE=TF_REQUEST; MESSAGE='重新校验 TF 并准备返回请求。' ;;
        7) PHASE=TF_READBACK; MESSAGE='只读复核返回请求和系统文件。' ;;
        8) PHASE=ARM; MESSAGE='设置并读回 OpenWrt 启动选择，请保持供电。' ;;
        9) PHASE=REBOOT; MESSAGE='正在安全重启，连接随后会断开。' ;;
        *) ui_refuse ;;
    esac
}
ui_snapshot() {
    RUN= STATE=IDLE PHASE=IDLE MESSAGE='准备就绪；确认后开始检查并返回 OpenWrt。' ELAPSED=0 CODE=null NUMBER=0
    if [ ! -e "$BASE" ] && [ ! -L "$BASE" ]; then
        if ui_external_busy; then STATE=UNKNOWN PHASE=UNKNOWN MESSAGE='已有其他切换正在执行，请勿重复提交。'; fi
        return
    fi
    ui_base
    ui_file "$BASE/lock" && ui_file "$BASE/meta" && ui_file "$BASE/worker.log" || ui_refuse
    [ "$("$BB" stat -c %s "$BASE/meta")" -le 256 ] || ui_refuse
    IFS=' ' read -r META_BOOT PID SAVED_TICKS STARTED extra < "$BASE/meta" || ui_refuse
    [ -z "$extra" ] && [ "$META_BOOT" = "$BOOT" ] || ui_refuse
    case "$PID:$SAVED_TICKS:$STARTED" in *[!0-9:.]*|'') ui_refuse ;; esac
    [ -n "$PID" ] && [ -n "$SAVED_TICKS" ] && [ -n "$STARTED" ] || ui_refuse
    RUN=$BOOT-1
    ui_uptime
    ELAPSED=$("$BB" awk -v now="$NOW" -v begin="$STARTED" 'BEGIN{if(begin>now||begin<0)exit 1;printf "%d",now-begin}') || ui_refuse
    [ "$("$BB" stat -c %s "$BASE/worker.log")" -le 1048576 ] || ui_refuse
    NUMBER=$("$BB" awk '/^\[[1-9]\/9\] / {n=substr($0,2,1)} END{print n+0}' "$BASE/worker.log") || ui_refuse
    ui_phase
    exec 8<>"$BASE/lock"
    if "$BB" flock -n 8; then
        exec 8>&-
        if [ -e "$BASE/result" ]; then
            ui_file "$BASE/result" || ui_refuse
            [ "$("$BB" stat -c %s "$BASE/result")" -le 16 ] || ui_refuse
            IFS= read -r CODE < "$BASE/result" || ui_refuse
            case "$CODE" in ''|*[!0-9]*) ui_refuse ;; esac
            [ "$CODE" -le 255 ] || ui_refuse
            STATE=FAILED; MESSAGE='切换未完成，请保持开机并提供阶段与退出码；不会自动重试。'
            [ "$NUMBER" -ge 8 ] || { STATE=REFUSED; MESSAGE='检查未通过，切换已停止；不会自动重试。'; }
            [ "$CODE" -ne 0 ] || { STATE=UNKNOWN; MESSAGE='程序结束但未确认重启，请联系维护。'; }
        else
            STATE=UNKNOWN; MESSAGE='任务已不在运行，但结果未完整保存；请勿重复提交。'
        fi
    else
        exec 8>&-
        if [ "$PID" = 0 ] && [ "$SAVED_TICKS" = 0 ]; then
            STATE=RUNNING
        elif ui_process "$PID" && [ "$TICKS" = "$SAVED_TICKS" ]; then
            STATE=RUNNING
            [ "$NUMBER" != 9 ] || STATE=REBOOTING
        else
            STATE=UNKNOWN; MESSAGE='任务进程身份无法确认，请保持开机并联系维护。'
        fi
    fi
}

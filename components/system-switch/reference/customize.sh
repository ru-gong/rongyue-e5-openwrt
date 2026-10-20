# SPDX-License-Identifier: MIT
# Sanitized research reference; private bindings and executable helper omitted.
printf "%s\n" "Reference only: this public snapshot cannot install or switch a device." >&2
exit 64

[ "$BOOTMODE" = true ] || abort '请在 Android 中安装'
[ "$ARCH" = arm64 ] || abort '本模块仅支持本机 arm64'
[ "$(getprop ro.serialno)" = UNSET_DEVICE_SERIAL ] || abort '本模块只适用于已核验的这台 E5'
[ "$(getprop ro.boot.slot_suffix)" = _a ] || abort '须从 Android A 安装'
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/e5-bootctl" 0 0 0755
set_perm "$MODPATH/action.sh" 0 0 0755
set_perm "$MODPATH/switch.sh" 0 0 0755
ui_print '已安装 E5 系统切换。点击模块「操作」进入 OpenWrt。'
ui_print '安装本身不切换系统；没有开机自动切换脚本。'

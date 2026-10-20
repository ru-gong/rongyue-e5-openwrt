#!/system/bin/sh
# SPDX-License-Identifier: MIT
# Sanitized research reference; private bindings and executable helper omitted.
printf "%s\n" "Reference only: this public snapshot cannot install or switch a device." >&2
exit 64

MODDIR=$(cd "${0%/*}" && pwd -P)
exec /data/adb/magisk/busybox sh "$MODDIR/switch.sh" reboot

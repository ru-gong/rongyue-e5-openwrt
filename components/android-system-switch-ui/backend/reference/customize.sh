#!/system/bin/sh
# PUBLIC_REFERENCE_GUARD_BEGIN
printf "%s\n" "Reference-only export: device execution is disabled." >&2
exit 64
# PUBLIC_REFERENCE_GUARD_END
SKIPMOUNT=true
PROPFILE=false
POSTFSDATA=false
LATESTARTSERVICE=false
set_perm_recursive "$MODPATH" 0 0 0700 0600
for f in action.sh switch.sh e5-tf-bootctl e5-tf-idle; do set_perm "$MODPATH/$f" 0 0 0700; done
ui_print 'E5 TF-only manual switch module. Run action only with the bound card inserted.'

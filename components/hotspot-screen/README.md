# E5 hotspot screen controls / 热点屏幕管理

Device-used source / 实机使用源码：**1.0.3-local**.

在机身屏幕的 **热点 → 修改热点密码** 或 **热点 → 管理连接设备 / 黑名单** 打开；安装插件后也可从“应用 → 热点管理”进入。支持触摸、方向键、确认键，以及改密时的实体数字键。

The plugin adds password editing, QR refresh, connected-client statistics,
disconnect controls and a persistent blacklist to the E5 infoscreen API v2.
It runs on an existing OpenWrt installation; it is not a firmware installer.

## Features and measurement scope / 功能与统计范围

- **Password and QR:** enter 8–63 printable ASCII characters using the screen keyboard or physical number keys. Saving requires confirmation and disconnects Wi-Fi clients. The controller waits for the radio to stop, starts it again, and checks both AP readiness and the runtime password before reporting success. The host's existing QR endpoint is refreshed without cache.
- **Connected clients:** show the associated device's DHCP name/IP, MAC, authorization state, available signal measurements, upload/download totals and rates. The list refreshes every two seconds.
- **Connection time:** a captured hostapd association event provides the start time. A connection already present when the management service starts is labelled “observed”; DHCP lease expiry is never used as connection time.
- **Traffic:** per-MAC bridge counters cover unicast Ethernet bytes through `wlan0`, including local/proxy traffic and IPv4/IPv6. They exclude Wi-Fi airtime/retransmission overhead and are not cellular billing counters. Counting starts after discovery, may omit the first 0–2 seconds, and resets for a new observed connection or management-service/system restart. Missing counters stay unknown.
- **Disconnect:** deauthenticate one associated device and temporarily prevent reconnection for 30 seconds. A phone may require manual reconnection afterwards.
- **Block/unblock:** persist a UCI deny list and synchronize hostapd's native ACL and a dedicated nftables set. Normal unblock does not send another deauthentication or restart the hotspot. Timed bans left by an older version are cleared only if present. A changed/randomized MAC is a different identity.

The controller does not convert an existing allow list. It rejects malformed,
multicast, broadcast and zero addresses and protects the upstream USB management
MAC. That shared gadget address and the test addresses in the code are protocol
defaults/synthetic fixtures, not recorded client identities.

## Compatibility / 适配前提

This integration was used on a single E5 running OpenWrt 25.12.5 with:

- Infoscreen API v2, its existing `/sdk/e5.js` and the host `/api/qr` endpoint.
- Python 3.10+, ucode/UCI, ubus, nftables bridge hooks and the OpenWrt `wifi` command.
- One AP on `wlan0`/`hostapd.wlan0` and generated `hostapd-*.conf` runtime files.
- A local hostapd control socket supporting `DENY_ACL`, `ATTACH` and `PING`.
- No packet offload that bypasses the bridge accounting hooks.

The host backend runs as root and listens locally. It must not be exposed as an
unauthenticated network service. The hostapd process is jailed on the tested
system: the controller's group-restricted client sockets live in its visible
control directory, not in an inaccessible `/tmp` namespace.

Passwords pass through mode-0600 RAM request files and a private Unix socket,
not shell arguments. Pre-change wireless configuration is privately backed up
on the device. Statistics stay in memory. No partition, Android slot, boot
control or NV access is implemented here.

## Build and test / 主机构建与测试

From the repository root:

```sh
python3 -m unittest discover -s components/hotspot-screen -p 'test_*.py' -v
node --check components/hotspot-screen/app.js
mkdir -p dist
python3 components/hotspot-screen/build.py dist
```

This produces `dist/hotspot-screen-1.0.3.tar.gz` and
`dist/HOTSPOT_PACKAGE.json`. Building and running host tests do not contact a
device. The runtime assets match the device-used source; the public builder
also bundles its license, notice and separate init-service file.

## Integration / 接入方式

After reviewing the trusted code and checking the assumptions above, the
upstream plugin manager can install an archive already copied to the device:

```sh
/usr/libexec/e5-infoscreen/plugin install /tmp/hotspot-screen-1.0.3.tar.gz
cp /etc/e5-infoscreen/plugins/hotspot/e5-hotspot /etc/init.d/e5-hotspot
chmod 755 /etc/init.d/e5-hotspot
/etc/init.d/e5-hotspot enable
/etc/init.d/e5-hotspot start
```

The separate service is required; the plugin manager alone does not install an
init service. Reopen the app to load its versioned entry. Installing the same
plugin ID replaces an earlier plugin, so stop its management service first
when upgrading; do not interrupt a running password operation.

`patch_parent.py` is a **host-side integration helper**, not an automatic
device patcher. It adds two entry buttons to copies of the matching author's
`index.html` and `app.js`, and invalidates password/QR display state on exit:

```sh
python3 components/hotspot-screen/patch_parent.py ORIGINAL_UI_DIR REVIEW_OUTPUT_DIR
```

Both directories must already exist. Start with unpatched matching host files,
keep their originals, and review the generated difference before replacing
files on a device. The helper does not include or download the full upstream
UI, deploy results, or refresh the running screen. Unsupported host revisions
must be adapted rather than blindly overwriting their files.

For software rollback, stop/disable the management service, restore the saved
host UI, remove this plugin and its dedicated `bridge e5hotspot` table, then
refresh the UI. Retain the user's current password/deny list unless explicitly
recovering a failed configuration change. Restoring an old password also needs
wireless reinitialization; raw backups must remain private.

## Validation status / 验证状态

The source passes **19 host-only tests** covering input rejection, private
backups, configuration conflicts/rollback, accounting baselines, radio readiness,
disabled-AP preservation, avoiding redundant deauthentication and legacy-ban
cleanup. These use isolated fixtures, not the radio hardware.

During device work, the user confirmed screen display, changing a password,
QR refresh and reconnection. Real counters increased; disconnect, list
synchronization and block/unblock operations were exercised. A phone that
disconnected after the initial password hot reload recovered after full radio
reinitialization; the exact lower-level cause was not uniquely established.
The new password path includes that reinitialization.

**Deferred:** a separate end-to-end reconnection after native-ACL unblock,
without changing the password or restarting the hotspot. That 1.0.3 trial
stopped at its initial no-client precondition, before blocking a device; the
user deferred further phone testing. Unit tests or the earlier password
recovery must not be reported as that missing hardware result.

Existing dual-SIM/SMS and storage limits remain in the [validation record](../../docs/validation.md).
Original code is [MIT licensed](LICENSE); see [NOTICE.md](NOTICE.md) and the
[third-party notices](../../THIRD_PARTY_NOTICES.md) for attribution.

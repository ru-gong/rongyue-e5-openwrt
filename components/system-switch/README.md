# E5 system switching / 双系统切换

This directory documents the **1.0.2-local** adaptation used on the project device. The published shell files are sanitized references, not an installable Magisk module.

## User flow / 日常使用

- **OpenWrt → Android:** on the E5 screen, open **高级 → 系统 → 切换到 Android** and confirm the reboot. The authenticated web interface also provides a switch action.
- **Android → OpenWrt:** boot and unlock Android, then open **Magisk → 模块 → E5 系统切换 · 进入 OpenWrt → 操作**.
- The device currently defaults to OpenWrt. An intentional switch to Android keeps Android selected; returning through the local Magisk action restores OpenWrt as the default.
- “Linux” in the upstream screen means OpenWrt in this installation. Hotspot connectivity is interrupted during switching and recovers after boot and cellular initialization.

完成安装后的日常切换不需要电脑、TF 卡或重新刷镜像。首次安装、恢复故障和为另一台设备建立基线属于另外的工作。

![System-switch controls](../../docs/images/system-switch.png)

## What the adaptation checks

The local Android action checks device identity, storage identity, the current Android slot, boot-control format/CRC, partition geometry, protected boot-chain digests, the installed OpenWrt image, and current filesystem-error indicators. It then backs up boot control, calls the pinned upstream `e5-bootctl`, checks the permitted write range, synchronizes and freezes data before the established reboot path.

Failure cleanup tries to restore the original **32-byte region at `misc + 2048`** and verifies the complete expected boot-control state. The module adds no boot-time action hooks and does not install a firmware image or sync the Android boot chain.

上述地址和检查是本机方案的历史实现描述，不是为所有 E5 确认过的刷写参数。无 TF 存储长期复发问题仍未解决。

## Public source boundary

`reference/switch.sh`, `action.sh` and `customize.sh` preserve the source structure but exit with status **64 before any device access**. Real serial/CID values, device-specific hashes and the image inode have been replaced by unset markers. The private `protected.sha256`, executable helper and installable ZIP are omitted.

The empty `.example` files are documentation, not sufficient provisioning inputs. Removing the stop guard or copying another device's values would not reproduce the original validation. No automatic binding or flashing utility is provided here.

The publication check executes only the early-stop behavior and checks shell syntax. Historical device tests are documented separately in [validation](../../docs/validation.md).

## Upstream

Boot-control helper and base switching design: [Enceka/e5-linux, commit `569f13d4ce15585f70817c2a1e03bb574a84720b`](https://github.com/Enceka/e5-linux/tree/569f13d4ce15585f70817c2a1e03bb574a84720b/magisk), MIT.

The helper binary used locally was unchanged from upstream. Magisk is an external runtime, not bundled here. The E5 screen-side switch entry belongs to the upstream firmware; the local adaptation described here provides the Android-side action and additional checks. See [third-party notices](../../THIRD_PARTY_NOTICES.md).

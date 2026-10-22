# TF-only boot and switching / TF 根与双系统切换核心

This component publishes selected, reviewable source from the TF migration and Android/OpenWrt switching work. **Every public shell entry exits 64 before any operation. Native default builds also exit 64.** It is not an initramfs, firmware package, installer or device provisioning tool.

本目录公开核心实现与合成测试，未公开任何设备绑定或可刷写产物。项目设备上的安装与双向切换实测是该设备的历史事实，不能外推为通用 E5 安装包。旧无 TF 方案在 [system-switch](../system-switch/README.md) 保留为历史记录。

## Architecture and default semantics

- The tested Linux boot runs from TF ext4. Firmware, vendor libraries, NV working copies and switching markers live on TF. Linux does not mount the internal Android userdata filesystem; it verifies the fixed partition identity and sets that partition's in-kernel read-only flag before mounting TF.
- The first TF root check is read-only with `noload`, followed by complete identity/manifest checks before the writable root mount. Failure enters a bounded-design RAM rescue path; it does not silently fall back to the old userdata root.
- The installed default is OpenWrt. An intentional selection of Android persists as Android. A validated Android return writes a one-use TF request; the successful TF path consumes it and restores the Linux default.
- The B boot-control slot is rearmed with two trial attempts, **not** marked permanently successful. Android A must already be successful, and CRC/slot/geometry/protection checks remain prerequisites.
- Card removal is rejected before a checked switch. This does not guarantee that removing the card or a boot-time failure automatically boots Android. Recovery remains an independently prepared operation.

内核的 userdata 只读标志约束正常启动/管理路径，不等于抵御拥有 root 权限的任意整盘写入。两套系统与 TF 的安全边界依赖完整固件、内核和个体绑定，不能只凭这些源码片段成立。

## Coverage

| Path | Published implementation |
| --- | --- |
| `reference/initramfs/init` | TF-only init, USB NCM/serial setup, startup link-up, read-only checks and rescue behavior |
| `reference/initramfs/tf-common.sh` | Identity, geometry, userdata protection, storage and immutable-root validation library |
| `reference/openwrt/opt/e5/e5-next-boot` | Default selection, one-use return request, transaction backup/rollback and boot-control rearm |
| `reference/openwrt/opt/e5/e5-os` | TF single-root status and refusal of legacy root switching |
| `reference/openwrt/etc/init.d/e5-boot-ok` | Conditional return confirmation / rearm service |
| `native/bootctl.c` | Restricted 32-byte boot-control transaction and CRC checks |
| `native/tf-idle.c` | Read-only task/descriptor/mapping occupancy checks |
| `tests/` | Synthetic boot-control, default/request transaction, userdata protection and publication-refusal tests |

Android-side action, mandatory private mount namespace, memory-only zram guard, foreground UI and detached worker are in [android-system-switch-ui](../android-system-switch-ui/README.md). There is intentionally one Android source copy in that component.

This is selected core coverage. It omits device writers, live transport/collection utilities, complete rootfs/build orchestration, raw storage tests, image packers, private manifests, boot images, native binaries and all individual provisioning inputs. The complete tested system also depended on upstream OpenWrt/e5-linux services, kernel modules and local rootfs integration outside this export.

## Binding and write boundary

The original implementation expects a separately reviewed binding file and immutable/protected manifests. The public reference does not provide values for device/card CID, filesystem/partition UUID, installation ID, paired boot image or protected partition digests. The checks remain visible so reviewers can understand why a mismatch stops execution.

The local switching design permits the defined boot-control transaction and TF markers. Initial migration separately involved B boot/initramfs preparation. It does not authorize rewriting Android A, GPT, super or physical NV. The NV working-copy arrangement and read-only protections are not reproduced by copying this directory.

Public default binaries never reach device-open code. `E5_PUBLIC_FIXTURE` additionally requires the helper-specific test macro. The boot-control fixture is restricted to owned, single-link regular files and refuses symlinks; it cannot use a block-device fd. Test scripts use temporary files and mocks, and strip the public shell guard only in those isolated copies.

## Host validation

Python 3 and a C compiler are sufficient; no SDK, root, device or network is needed:

```sh
python3 -B -m unittest discover -s components/tf-system-switch/tests -p 'test_*.py' -v
```

The tests exercise CRC/slot validity, exactly-32-byte change limits, fresh backup/readback, expected-state races, rollback, one-use markers, Android persistence, no unintended first-boot rearm, task occupancy, userdata geometry/mount/holder/RO checks and unconditional public refusal. They do not prove hardware behavior on a new unit.

[Source provenance](SOURCE-PROVENANCE.json) records logical source paths and publication changes. [Publication guards](PUBLICATION-GUARDS.json) enumerate the disabled paths. See [NOTICE](NOTICE.md) for upstream attribution and [repository validation](../../docs/validation.md) for the historical acceptance scope.

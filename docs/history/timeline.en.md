# From backups to screen controls: the project history

This records work on **one RongYue E5 from 13–21 October 2026**, including successes, stops and recoveries. It describes what happened; it is not an automatic flashing guide or a claim of compatibility with every E5.

The foundation is a [fixed revision of Enceka/e5-linux](https://github.com/Enceka/e5-linux/tree/569f13d4ce15585f70817c2a1e03bb574a84720b). The kernel, cellular support and screen framework come from upstream. This repository collects device-specific execution tools, compatibility fixes, a system-switching wrapper and the OpenClash screen app. The installed build contains documented local changes and is not an unmodified upstream release.

## 13 October: backups, root and the first rollback

Partition originals were saved before rooting Android A and checking an ordinary reboot. Later readback found that, although the host had issued writes to four A-slot partitions, the four corresponding B-slot partitions had also changed. The record was corrected. A cross-slot write path in the download helper could explain this, but no contemporaneous device trace established the exact timing. Subsequent B-slot installation avoided that named-partition write path.

After separately authorized system-image changes and userdata reconstruction, OpenWrt booted for the first time. USB and management services worked, but repeated AT timeouts caused cellular failure. Validation stopped, and the original B boot image and limited boot-control region were restored to return to Android. Android subsequently regained connectivity. This rollback retained the modified system and data; it was not a complete factory restoration.

## 14–19 October: fix the checks before continuing installation

Reinstallation repeatedly stopped before occupancy checks or directory operations could complete. The tools were adapted for valid zero process start times, temporary-directory constraints, file-descriptor counting limits and descriptors disappearing during a scan. Specific failure reasons, bounded execution times, source binding and transactions that preserve old directories were added.

Host tests, helper deployment and actual installation remained separate results. Failures preserved raw output and stop state. One successful scan could not replace a later check. On 19 October, another descriptor-table convergence failure stopped work before directory activation or B-slot writes. It was not misclassified as a USB timeout or bypassed by simply extending the time allowance.

## 20 October: installation completed, storage faults emerged

The final implementation allowed a limited number of complete rescans only for a small set of confirmed, terminated read-only scan races. Timeouts, missing acknowledgements and uncertain outcomes still stopped execution. Writes were not automatically retried; each block retained synchronization and independent readback. Old-directory archiving, new-directory activation, B-slot installation and the boot without SIM cards were validated separately. An unsupported BusyBox listing option was handled in the validation tool without replacing the device program.

F2FS errors appeared after the SIM cards were inserted, so work moved to offline recovery. The first rescue boot unexpectedly returned to Android, whose stock filesystem check changed metadata before a complete backup was taken. The later snapshot was explicitly labelled as the state **after automatic repair**. Both SIMs subsequently passed individual connectivity and switching tests, and the user confirmed hotspot access from a phone.

Later, before OpenClash installation, F2FS and the internal ext4 image suffered another failure. This time a complete fault snapshot was saved first, followed by approved targeted repair and restoration of a previously verified local root image. Neither recovery established that the recurring fault had been permanently resolved.

## The same day: daily switching and OpenClash

The local wrapper reused [upstream system-switching support](https://github.com/Enceka/e5-linux/blob/main/magisk/README.md) and added device identity, protected-region and readback checks. OpenWrt enters Android through its screen controls. Android returns through the Magisk module’s **Action** entry, restoring OpenWrt as the default. Real button activation, switching in both directions and an ordinary reboot were tested. A separate recovery step refreshed outdated Linux NV working copies while keeping physical NV read-only; the switching module does not perform that refresh automatically.

[OpenClash](https://github.com/vernesong/OpenClash) and [Mihomo](https://github.com/MetaCubeX/mihomo) were then installed and tested for proxy selection, forwarding, DNS and recovery after disabling the service. The screen app first added four routing modes, then proxy selection and manual HTTPS latency checks. The user confirmed the display on the actual device. Overview, signal, traffic, system-switching and OpenClash screenshots were finally assembled into presentation images without changing the captured status.

The current connection uses China Unicom SIM2. After the earlier dual-SIM success, China Mobile SIM1 was not detected following a later recovery and needs retesting. Actual SMS reception, sustained use without USB and long-term F2FS reliability on the installation without a microSD card remain unverified.

## Late 20 October into 21 October: hotspot password and client controls

The hotspot page gained password editing with QR refresh and a client manager
showing state, traffic and connection or observation time, with disconnect,
block and unblock controls. Dedicated bridge counters do not use DHCP lease
time as connection time or equate local/proxy bytes with cellular billing.

Real counters, disconnection, list synchronization and user password changes
were observed. One previously tested phone disconnected after the initial
password hot reload while other phones worked. Complete radio reinitialization
restored access, so that step and runtime-password verification became part of
the password path. The exact lower-level cause was not uniquely established.

Version 1.0.3 removes redundant deauthentication and timed bans for persistent
blocks and passes 19 host-only tests. The separate reconnect-after-unblock
trial stopped before a new block because its phone was no longer associated;
the user deferred it. Published validation retains that open result and
excludes raw credentials, QR codes, device identities and logs.

See [components](../../components/) for implementation code, [archive](../../archive/) for historical tools and materials, and the [project introduction](../project-intro.en.md) for current features. Historical passes apply to the observations made at that time; later evidence can change the current conclusion.

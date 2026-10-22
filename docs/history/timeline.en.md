# From backups to screen controls: the project history

This records work on **one RongYue E5 from 13–22 October 2026**, including successes, stops and recoveries. It describes what happened; it is not an automatic flashing guide or a claim of compatibility with every E5.

The early foundation was a [fixed revision of Enceka/e5-linux](https://github.com/Enceka/e5-linux/tree/569f13d4ce15585f70817c2a1e03bb574a84720b). The kernel, cellular support and screen framework come from upstream. This repository collects device-specific execution tools, compatibility fixes, a system-switching wrapper and the OpenClash screen app. The installed build contains documented local changes and is not an unmodified upstream release.

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

This stage used a root image inside userdata: the former layout without a TF card. Earlier two-SIM success did not cover every subsequent recovery state. Actual SMS reception and sustained untethered operation remained unverified. The later TF migration superseded this layout.

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

## 21 October: storage faults recurred during operation

During one boot without an intentional system switch, live logs again showed F2FS metadata inconsistency, stopped checkpoints, inner-loop write failures and ext4 emergency read-only state. SMS-state and NV working-copy writes were subsequently affected. Device-origin HTTPS could still succeed, so a read-only root cannot be equated with every client disconnect. Historical faults before OpenClash installation were retained as well.

The plan changed to a separate TF ext4 root while preserving the screen, OpenClash configuration and switching. A storage-related kernel correction was paired with the existing board adaptations, and the root was rebuilt from clean materials. The damaged old image was not treated as a healthy deployment source.

## 22 October: TF migration and selective restoration

Private configuration, protected partitions and a complete userdata snapshot were saved first. This snapshot was taken after Android's automatic check and before manual repair; it is not an untouched pre-check fault image. Offline checks did not support further manual repair, so none was performed.

After a full-card write/read comparison, a clean root was deployed and expanded. Screen, OpenClash, hotspot, network helpers and configuration were selectively restored with matching kernel/modules. Normal TF boot kept userdata kernel-read-only and unmounted, using NV working copies on TF. Automatic scanning paths were constrained to avoid reusing the old internal root image.

The first boot exposed a missing USB link-up step and a runtime lock incorrectly included in the immutable manifest. Targeted boot and manifest corrections followed without rewriting the TF filesystem or overwriting newer user configuration. The final manifest has 1,830 entries. Android switching also gained verified memory-only zram compatibility and a private mount namespace while retaining occupancy rejection and full checks. Failed attempts remain distinct from successful ones.

Migration validation covered the screen API into Android, an ordinary Android reboot staying there, return through the installed Action entry, and an ordinary TF reboot retaining the OpenWrt default. That formal Action return invoked the installed entry from a command; it must not be relabelled as a Magisk UI click test. Actual Magisk UI activation was observed separately afterward.

## The same day: Android power-menu entry and visible progress

The user reported manually rebooting about ten seconds after choosing Magisk Action; the saved log contained only early checks. A later actual Magisk UI invocation returned automatically in about eleven minutes, demonstrating that the full validation can take time. The new UI therefore adds an explicit confirmation, stages and elapsed time; an early CRC pass is not a signal to reboot manually.

The Android app adds an entry below the unlocked native power menu and invokes the existing switch flow through fixed operations. Identity, occupancy, validation and write order remain intact. A separate task runs independently of progress observation and keeps new runtime logs in memory. Unknown state cannot trigger automatic resubmission, and neither disconnect nor “rebooting” is treated as success.

Real UI testing covered cancellation with no task, entry/grant persistence across an ordinary Android reboot, one confirmation, the same worker continuing after Back to the launcher, and reopening the same task. Automatic disconnect occurred about 10 minutes 47 seconds after confirmation. A fresh TF OpenWrt boot was then observed independently, with matching default/next target and consumed return request.

Around one minute into this boot, WAN/DNS were not ready and device/USB checks failed. Without changing network configuration, services were ready around two minutes and each test origin returned two HTTPS 204 responses. Initial failures remained recorded; approved configuration and runtime battery/traffic differences were reviewed separately without replacing the baseline. Healthy services do not establish fresh physical-touch, phone Wi-Fi or long-term disconnect acceptance.

See [components](../../components/) for implementation code, [archive](../../archive/) for historical tools and materials, and the [project introduction](../project-intro.en.md) for current features. Historical passes apply to the observations made at that time; later evidence can change the current conclusion.

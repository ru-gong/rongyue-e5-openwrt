# RongYue E5: a portable OpenWrt hotspot with screen controls

This project turns one RongYue E5 into a portable OpenWrt hotspot that can be managed from its own screen. Connect to its Wi-Fi to get online, and use the screen to check connectivity, signal, data usage and device status. A new OpenClash screen app provides four routing modes, proxy selection and manual HTTPS latency checks. Android is retained alongside OpenWrt; after setup, everyday switching between them does not require a computer or another firmware flash. Connectivity, hotspot access and the main controls have been tested on this unit. SMS reception and long-term storage reliability remain under verification.

Status as of **20 October 2026**. This is a single-device implementation based on [Enceka/e5-linux](https://github.com/Enceka/e5-linux), with local adaptations, a screen app and system-switching entry points.

![RongYue E5 interface overview](images/e5-interface-overview.png)

## What it can do today

- **Share a cellular connection over Wi-Fi.** The device currently uses China Unicom in SIM2. In an on-site test, a second phone with its own mobile data disabled accessed both Baidu and Google through the E5 hotspot.
- **Show useful status on the device.** The overview displays connectivity, hotspot status, traffic rates, battery, memory and temperatures. The signal page shows network technology, band and signal measurements. The traffic page shows daily, monthly and historical usage.
- **Control OpenClash from the built-in screen.** Touch controls and the direction/confirm keys provide access to service status, routing modes, proxy selection and manual HTTPS latency checks.
- **Keep both Android and OpenWrt available.** The default system can be chosen to suit use. This unit currently defaults to OpenWrt.

## OpenClash controls on the screen

Open **Apps → OpenClash** to see the core status, active routing mode and selected proxy.

| Mode | How new connections are handled |
| --- | --- |
| Direct | External traffic connects directly |
| GFW | Destinations in the configured list use the proxy; others connect directly |
| Mainland whitelist | Chinese domains and China IP destinations connect directly; others use the proxy |
| Global | External traffic uses the selected proxy |

The current selection is mainland whitelist mode. Mode and proxy selections are saved and applied through the existing core interfaces without rebooting the device. Connections that are already established may continue using their previous route.

**Test all** sends an HTTPS probe through each proxy and shows its latency in milliseconds with the latest test time. This measures request latency, not download bandwidth, and does not automatically change the selected proxy. Both configured proxies have passed individual latency, selection and connectivity tests.

![OpenClash status, routing controls and proxy details](images/e5-openclash-focus.png)

The screenshots show status and stored latency results at capture time. Scrolling pages have been stitched vertically; the images do not establish continuous uptime or live performance.

## Switching between the two systems

**OpenWrt → Android:** On the E5 screen, open **Advanced → System → Switch to Android**, confirm, and wait for the reboot. The OpenWrt web management page also provides this action.

**Android → OpenWrt:** After Android has booted and been unlocked, open **Magisk → Modules → E5 System Switch · Enter OpenWrt → Action**, then wait for the reboot and network recovery. The Android side uses a Magisk module; the two systems have different control interfaces.

This unit currently defaults to OpenWrt. Deliberately switching to Android keeps it in Android for continued use. Returning through the Magisk action restores OpenWrt as the default. These everyday switches do not require a computer, a microSD card or reflashing an image. Initial installation, maintenance and fault recovery are separate procedures.

## What has—and has not—been verified

| Area | Current status |
| --- | --- |
| China Unicom SIM2 connectivity | Verified and currently in use |
| Hotspot client connectivity | Supported by on-site phone feedback and independent forwarding tests; the E5 was still connected by USB during the phone test |
| OpenClash modes, proxy selection and latency checks | Functionally tested on the device; the user also confirmed correct display on its built-in screen |
| Switching between systems, OpenWrt default and ordinary reboot | Verified |
| China Mobile SIM1 | Connectivity and switching passed earlier, but the card was not detected after a later recovery; card contact and operation need to be checked again |
| SMS | Backend retained; receipt of a real incoming message has not yet been verified |
| Sustained operation without USB | Long-term testing remains incomplete |
| Installation without a microSD card | Currently running, but the shared userdata F2FS filesystem and the internal ext4 image have suffered corruption; the recurring reliability issue is unresolved |

This project documents the features and test results of one device. Successful short tests and working screens do not establish long-term reliability, complete feature acceptance or compatibility with other units of the same model. It is not a production-readiness claim or a universal flashing procedure.

## Software foundation

The current combination is OpenWrt 25.12.5, [OpenClash](https://github.com/vernesong/OpenClash) v0.48.002, [Mihomo](https://github.com/MetaCubeX/mihomo) v1.19.32, screen app 1.1.1-local, and a device-specific system-switching module 1.0.2-local exposed through [Magisk](https://github.com/topjohnwu/Magisk). The screen app and switching adaptations build on the capabilities of these upstream projects.

Original code and documentation in this repository use the [MIT License](../LICENSE). Upstream works retain their own copyrights and licenses; see the [third-party notices](../THIRD_PARTY_NOTICES.md) for exact versions, sources and inclusion boundaries. The repository contains the screen plugin source, sanitized development sources and switching logic references. It does not include third-party firmware, proxy credentials or an installable copy of the device-bound switching package.

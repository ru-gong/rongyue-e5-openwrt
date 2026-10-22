# Rongyue E5 · Portable OpenWrt Wi-Fi

[中文](README.md) · [Project introduction](docs/project-intro.en.md)

A cellular hotspot, on-device network controls and Android / OpenWrt switching on the Rongyue E5. The built-in screen shows signal and data usage, manages the hotspot, and controls OpenClash routing modes and proxy selection.

**OpenWrt now runs from a TF (microSD) card; Android remains on internal storage.** Routine switching uses the device's screen without a computer or reflashing. Keep the provisioned card inserted while using OpenWrt.

## Features

- **Portable hotspot:** share cellular connectivity with phones and computers over Wi-Fi.
- **Screen dashboard:** view connectivity, signal, radio band, traffic, battery, temperatures and memory usage.
- **OpenClash controls:** choose four routing modes, save a proxy selection and run manual HTTPS latency checks.
- **Hotspot management:** change the password and refresh its QR code, inspect clients and traffic, disconnect, block or unblock clients.
- **System switching:** enter Android from the OpenWrt screen; return through an additional entry below Android's power menu and make OpenWrt the default.

![Overview, signal, OpenClash, traffic and system-switch screens](docs/images/e5-interface-overview.png)

## Control OpenClash on the device

Open **Apps → OpenClash** and use touch or the direction and confirm keys to:

- Choose **Direct, GFW, Mainland whitelist or Global** mode.
- Select a proxy; the selection is saved and applied.
- Choose **Test all** to view HTTPS request latency and the test time for each proxy.

Mode and proxy changes do not require a device reboot. Tests run on request and do not automatically change the selected proxy.

![OpenClash status, routing controls and proxy selection](docs/images/e5-openclash-focus.png)

## Switch between Android and OpenWrt

| Direction | Control and default behavior |
| --- | --- |
| OpenWrt → Android | **Advanced → System → Switch to Android**, then confirm; ordinary Android reboots stay in Android |
| Android → OpenWrt | Hold the power button, choose **Return to OpenWrt / Set as default** below the original menu, then confirm; validation is followed by an automatic reboot and restoration of the OpenWrt default |

![Additional OpenWrt entry below Android's power menu](docs/images/e5-android-power-menu.png)

The return flow shows actual stages and elapsed time. Closing and reopening the page displays the same task. One full return on this device took about **11 minutes**; this is an observation, not a deadline. Submit once, keep power connected and wait for the automatic reboot. Do not manually reboot or remove the card during the operation. Switching interrupts the hotspot; cellular and network services also need time to start.

See the [usage and TF architecture guide](docs/tf-system-switch.en.md). The Android app is `1.0-local`; the local switching module is `1.1.3-tf-local`.

## Hotspot password and client controls

**Hotspot → Change hotspot password** supports the screen keyboard and physical number keys. Saving refreshes the QR code; clients must reconnect. **Manage clients / Blacklist** shows connection state, upload/download totals and rates, and connection or observation time, with disconnect, block and unblock controls.

Counters start after discovery, include proxy and local traffic, and reset on restart. They are not cellular billing figures. See the [hotspot plugin guide](components/hotspot-screen/README.md) for implementation and validation limits.

## Documentation and source

- **Project introduction:** [English](docs/project-intro.en.md) / [中文](docs/project-intro.zh-CN.md)
- **Switching and architecture:** [English](docs/tf-system-switch.en.md) / [中文](docs/tf-system-switch.zh-CN.md)
- **Screen plugins:** [OpenClash](components/openclash-screen/README.md) · [Hotspot controls](components/hotspot-screen/README.md)
- **Current switching implementation:** [Android menu and progress UI](components/android-system-switch-ui/README.md) · [TF boot and switching reference](components/tf-system-switch/README.md)
- **Development history:** [English](docs/history/timeline.en.md) / [中文](docs/history/timeline.zh-CN.md) · [Historical source catalog](archive/CATALOG.md)
- **Validation:** [Device observations and limits](docs/validation.md) · [Host tools](tools/README.md)

## Status and sources

This is an integration project for one E5. TF migration, switching in both directions, default boot behavior and the new Android entry have device evidence. The exact scope of screen, client-network and stability validation is recorded in [validation](docs/validation.md). Migration and successful connectivity tests do not establish that historical intermittent disconnections are permanently fixed.

This repository provides source and sanitized implementation references, not complete firmware or a switching package ready for another device. Public boot and switching scripts refuse device operations by default. Private bindings, configuration and backups are excluded. The [former installation without a TF card](components/system-switch/README.md) is retained only as historical reference.

The base system and screen framework come from [Enceka/e5-linux](https://github.com/Enceka/e5-linux) and [Enceka/infoscreen](https://github.com/Enceka/infoscreen), with [OpenClash](https://github.com/vernesong/OpenClash), [Mihomo](https://github.com/MetaCubeX/mihomo) and [Magisk](https://github.com/topjohnwu/Magisk). Original project code and documentation use the [MIT License](LICENSE). Third-party works retain their copyrights and licenses; see [sources and licensing](THIRD_PARTY_NOTICES.md).

# Rongyue E5 · Portable OpenWrt with on-device controls

[中文](README.md) · [Shareable introduction](docs/project-intro.en.md) · [中文项目介绍](docs/project-intro.zh-CN.md)

An E5 portable network device that runs OpenWrt, exposes status and OpenClash controls on its own screen, and retains Android. This repository collects the local integration code, development history, device validation notes, and screenshots, building on [Enceka/e5-linux](https://github.com/Enceka/e5-linux) and other upstream projects.

## What the device currently does

- **Cellular Wi-Fi hotspot:** China Unicom SIM2 is the current uplink. A phone with its own mobile data disabled was tested through the E5 hotspot against domestic and overseas websites.
- **On-device status:** connection state, 5G signal and band, data usage, battery, memory, and temperatures.
- **OpenClash on the screen:** direct, GFW-list, mainland-whitelist, and global routing modes; node selection; manual HTTPS latency tests. Saved choices take effect through the existing core API.
- **Android and OpenWrt switching:** use the E5 screen to switch from OpenWrt to Android, and the Magisk module's **Action** button to return from Android to OpenWrt. Routine switching after installation needs no computer, microSD card, or reflashing.

![E5 interface overview](docs/images/e5-interface-overview.png)

## Explore the project

| Topic | Entry |
| --- | --- |
| Introduction to send with the screenshots | [English](docs/project-intro.en.md) / [中文](docs/project-intro.zh-CN.md) |
| OpenClash screen integration and build | [Component](components/openclash-screen/README.md) |
| System-switch behavior and implementation boundaries | [System switch](components/system-switch/README.md) |
| Installation, recovery, and development history | [Timeline](docs/history/timeline.en.md) / [中文](docs/history/timeline.zh-CN.md) |
| Historical development source | [Source archive](archive/README.md) |
| Tests and remaining work | [Validation](docs/validation.md) |
| Attribution and licensing | [Third-party notices](THIRD_PARTY_NOTICES.md) |

## Repository scope

`components/openclash-screen/` contains the screen plugin used on the device. `components/system-switch/reference/` preserves sanitized checks and rollback logic but **exits immediately and cannot be installed as a working module**. `archive/` contains development source and a version index; historical code is not a current deployment recipe.

The repository excludes Android/baseband firmware, partition images, NV calibration data, real proxy configurations, SSH credentials, device identities, and raw private backups. Upstream firmware, the base screen application, and third-party cores are referenced by source and license. This is not a complete firmware image or a universal flashing package.

## Validation status

As of **2026-10-20**, hotspot connectivity, OpenClash routing/node operations, screen display, round-trip system switching, and ordinary reboot behavior have been verified on this device. SIM2 is currently usable. SIM1 was not detected after a later recovery and requires another physical check. Actual SMS reception and sustained use with USB disconnected remain unverified.

The no-microSD arrangement using shared userdata/F2FS and an internal ext4 image has experienced storage corruption. Long-term recurrence remains unresolved. Results from this single device do not establish compatibility or reliability for every E5.

## Host-only checks

Requires Python 3.10+, Ruby with YAML/Psych, and a POSIX shell:

```sh
python3 scripts/check_publication.py
python3 -m unittest discover -s components/openclash-screen -p 'test_*.py' -v
```

These checks use temporary files and simulated controllers. They do not connect to an E5 or use real proxy nodes. Additional historical tooling has its own test documentation.

## License and credits

New code and documentation are licensed under the [MIT License](LICENSE). Third-party works retain their own copyright and license; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and `LICENSES/`. The base screen UI belongs to its upstream authors. This project's additions are the OpenClash screen integration, node controls, and device-specific switching adaptation.

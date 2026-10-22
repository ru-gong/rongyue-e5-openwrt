# Source attribution

`reference/initramfs/init` adapts the hardware/module/USB startup sequence from [Enceka/e5-linux at 569f13d4](https://github.com/Enceka/e5-linux/tree/569f13d4ce15585f70817c2a1e03bb574a84720b/boot). `native/bootctl.c` derives from the [e5-linux Magisk boot-control helper](https://github.com/Enceka/e5-linux/tree/569f13d4ce15585f70817c2a1e03bb574a84720b/magisk).

Copyright (c) 2026 Enceka. These portions are MIT licensed; preserve [the complete upstream MIT notice](../../LICENSES/MIT-Enceka.txt). Local TF isolation, validation and transaction changes are described in `SOURCE-PROVENANCE.json`. Original local code is covered by the repository [MIT license](../../LICENSE).

Linux, OpenWrt, BusyBox, Magisk, Android, firmware and SDK/toolchains are external dependencies with their own licenses. No firmware, third-party binary or SDK is redistributed by this component. Calling their interfaces does not relicense those projects. See [third-party notices](../../THIRD_PARTY_NOTICES.md).

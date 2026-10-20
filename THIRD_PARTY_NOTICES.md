# 来源与第三方许可证 / Sources and third-party licenses

核验日期 / Reviewed: **2026-10-20**. 版本与许可证以所引用提交的原文为准，而非仓库当前的徽章。固定 URL、原文文件及 SHA-256 见 [sources.json](sources.json)；原文保存在 [LICENSES](LICENSES/)。

Versions and licenses below are tied to the cited source revision, not inferred from a repository's current badge. Exact URLs and license-text hashes are recorded in [sources.json](sources.json).

## 本仓库的授权范围 / Scope of this repository's license

[根目录 MIT 许可证](LICENSE)，Copyright (c) 2026 ru-gong，适用于本项目原创的热点及 OpenClash 屏幕插件、集成与检查工具、测试和整理文档。第三方代码、保留的上游片段和截图所展示的上游界面仍保留其原作者版权及对应许可证。本项目的 MIT 授权不能替代 OpenWrt、Linux、Mihomo、Magisk 等依赖自身的条款，也不为商标、厂商固件或其他未收录材料授予额外权利。

The root MIT license, Copyright (c) 2026 ru-gong, covers this project's original OpenClash and hotspot screen plugins, integration and inspection tools, tests, and authored documentation. Third-party code, retained source excerpts, and upstream UI depicted in screenshots keep their original copyrights and licenses. It does not relicense external dependencies, trademarks, vendor firmware, or materials not included here.

## 组件与来源 / Components and sources

| 组件 / Component | 用途与版本 / Role and version | 许可证 / License | 本仓库分发范围 / Included here |
| --- | --- | --- | --- |
| **Enceka / e5-linux** | E5 的 Linux/OpenWrt 适配、启动控制及安装方案基础；[固定提交 569f13d4](https://github.com/Enceka/e5-linux/tree/569f13d4ce15585f70817c2a1e03bb574a84720b) | 脚本、工具与文档 [MIT](LICENSES/MIT-Enceka.txt)，Copyright (c) 2026 Enceka；内核/驱动保留各文件的 GPL/SPDX | 本地集成参考与历史脚本中的有限上游片段；不包含整机固件或上游完整树 / Local integration references and limited historical source excerpts; no complete firmware or upstream tree |
| **Enceka / infoscreen** | 概览、信号、流量、设置等 E5 屏幕框架及 SDK；[固定提交 09b7ec82](https://github.com/Enceka/infoscreen/tree/09b7ec822e56062f1891136c78860d5e257493c6) | [MIT](LICENSES/MIT-Enceka.txt)，Copyright (c) 2026 Enceka | 界面截图与历史转换器中保留的少量 API/UI 片段；本地 OpenClash 插件调用已有 SDK，未打包 SDK / Screenshots and limited API/UI excerpts; existing SDK is referenced, not bundled |
| **vernesong / OpenClash** | LuCI 代理管理与服务层，v0.48.002；[固定提交 e553e82e](https://github.com/vernesong/OpenClash/tree/e553e82e01c697aefbe1555261a503f425e00ccd) | [MIT](LICENSES/MIT-OpenClash-v0.48.002.txt)，Copyright (c) 2019-2026 vernesong | 外部依赖，未打包 OpenClash APK 或上游源码 / External dependency; no APK or upstream source bundled |
| **MetaCubeX / Mihomo** | 实际代理核心，v1.19.32；[固定提交 88dcbf7f](https://github.com/MetaCubeX/mihomo/tree/88dcbf7f1614a67c3b36b848ee3592dfa92ada36) | 本机使用版本为 [GNU GPL v3](LICENSES/GPL-3.0-Mihomo-v1.19.32.txt) | 外部依赖；本地插件通过 HTTP API 控制既有核心，未打包核心或复制其实现 / External core accessed through its HTTP API; no core binary or implementation bundled |
| **topjohnwu / Magisk** | Android root 与模块操作入口；canary 28103 / [1e3edb88](https://github.com/topjohnwu/Magisk/tree/1e3edb888375c75777120a018637b5d945df6d15) | [GNU GPL v3](LICENSES/GPL-3.0-Magisk-canary-28103.txt) | 外部运行环境；仅保留本项目失效、脱敏的模块参考脚本，未打包 APK / External runtime; only disabled, sanitized local module references are included |
| **OpenWrt** | 25.12.5 系统基础；[固定提交 f0a60eee](https://github.com/openwrt/openwrt/tree/f0a60eee2fe051741c643ea6118718aae1ef17fb) | 构建系统 [GPL-2.0-only](LICENSES/OpenWrt-v25.12.5-COPYING.txt)；[GPLv2 原文](LICENSES/GPL-2.0-OpenWrt-v25.12.5.txt)；软件包另按各自许可 | 外部系统，不包含 rootfs、内核或整套包 / External system; no rootfs, kernel, or package distribution bundled |
| **dikeckaan / mu300-linux** | E5 上游 VBC 音频转换器所注明的移植来源；[项目](https://github.com/dikeckaan/mu300-linux) | [MIT](LICENSES/MIT-mu300-linux.txt)，Copyright (c) 2026 dikeckaan | 仅致谢与来源引用，未收录转换器或其输出 / Attribution and source reference only; no converter or output bundled |
| **TomKing062 / spreadtrum_flash** | 历史备份/刷写工具基线 [5da19929](https://github.com/TomKing062/spreadtrum_flash/tree/5da19929d60296ed8ba69d28a67b1bb234607320) | 该分支固定提交未核实到完整、清晰的授权文本 / No clear complete license grant verified for this fork at the cited revision | **仅引用，不分发**该分支 C/C++ 源码、二进制、Lib 或含其源码的大段补丁 / **Reference only**, excluded from source archive |
| **ilyakurdyukov / spreadtrum_flash** | 上述工具所引用的原作者项目；[项目](https://github.com/ilyakurdyukov/spreadtrum_flash) | 原作者版本 [Unlicense](LICENSES/Unlicense-spreadtrum-original.txt) | 仅引用；原作者授权不能自动替代 TomKing062 新增代码的授权 / Reference only; original license does not automatically cover the fork's additions |

**Mihomo 版本说明：**核验时 GitHub 仓库元数据将当前仓库识别为 MIT，但本项目实际安装的 `v1.19.32` / `88dcbf7f...` 的 `LICENSE` 原文是 GPLv3，因此此处使用 GPLv3。许可证随引用版本记录，不能用新的元数据追溯改写旧版本的许可证。

**Mihomo version note:** GitHub's repository metadata identified the current repository as MIT during this review, while the installed `v1.19.32` tag's license text is GPLv3. This document therefore records GPLv3 for that specific version.

## 归档源码中的上游片段 / Upstream excerpts in the source archive

历史源码的原路径、脱敏后文件与阶段映射见 [archive/index.json](archive/index.json)。哈希命名和 `.source` 后缀不改变版权与许可。

- 原路径 `tools/e5_cellular_candidate_prepare_20261013/prepare_candidate.py` 含用于精确替换的 Enceka 屏幕 API/UI 片段；这些片段保留 Enceka MIT 许可。相邻的新检查、转换及测试逻辑是本项目补充。
- 对 Enceka `e5-linux` / `infoscreen` 的其他短源码引用，同样保留 [MIT-Enceka.txt](LICENSES/MIT-Enceka.txt)。上游的 MIT 许可允许保留原文后作修改，但本项目不将上游作者工作宣称为原创。
- `e5_wan_candidate_prepare_20261013/prepare_candidate.py` 的独立输入检查与转换框架可以保留；涉及原 ModemManager 协议脚本实现的 `late-registration.functions.sh`、实际抽取的上游树及生成的补丁没有收录。
- 许可证未核清、含私有材料、设备身份或不可公开依赖的文件仅以索引/过程说明记述，不重新授权或改换后缀后发布其内容。

The archive index maps original paths to sanitized source files. Hash naming and `.source` extensions do not change copyright. Retained Enceka API/UI excerpts remain MIT-licensed by Enceka; surrounding original safeguards and tests are local additions. Upstream extraction trees, generated patches, the ModemManager-derived registration payload, and the unclarified flashing-tool fork are excluded.

## 系统切换与屏幕功能的致谢 / System-switch and screen attribution

E5 的上游启动控制 helper 是 Enceka 的 [`magisk/e5-linux-switch/bootctl.c`](https://github.com/Enceka/e5-linux/blob/569f13d4ce15585f70817c2a1e03bb574a84720b/magisk/e5-linux-switch/bootctl.c)。本机使用记录中的 helper 未修改，SHA-256 为 `a1e4e50e45ad0dfa2cb4342b5233cabac9ffe3a0fafcdeac82b58087b06dd575`；本仓库**不打包该二进制或本机绑定的安装 ZIP**。本项目补充本机身份/完整性检查、启动目标处理及操作流程记录；它没有从零重新开发 E5 的 Linux 适配和屏幕框架。

The boot-control helper comes from Enceka's pinned `bootctl.c`. Its locally recorded binary was unchanged; this repository does not bundle that binary or the device-bound installation ZIP. Local contributions add identity/integrity checks, integration, and documented operation. The underlying E5 Linux adaptation and screen framework are credited to their upstream authors.

OpenClash 屏幕插件的四模式控制、节点选择与 HTTPS 延迟操作依据 [Mihomo API 文档](https://wiki.metacubex.one/en/api/)和 [GLOBAL 策略组文档](https://wiki.metacubex.one/en/config/proxy-groups/built-in/)，调用已有核心接口。本项目是独立的设备集成与记录仓库，不代表这些上游项目的官方发布。

热点插件 `components/hotspot-screen` 为本项目新增代码，调用独立安装的 hostapd、nftables、UCI/ucode 和 infoscreen SDK，不打包这些程序或 SDK。`patch_parent.py` 含少量 Enceka MIT 屏幕 HTML/JS 匹配锚点与上下文，保留原作者权利和上述 MIT 许可证；不包含完整上游界面。原生 ACL/ubus 与桥接计数属于接口使用，没有复制 hostapd 或 nftables 的 GPL 实现代码。具体说明见组件 NOTICE。

The screen plugin uses the documented Mihomo API for modes, proxy selection, and HTTPS delay checks. This is an independent device-integration and documentation project, not an official release of the upstream projects.

## 分发边界 / Distribution boundary

本仓库不包含厂家专有 Android/基带固件、FDL、NV、分区镜像、完整 rootfs、第三方安装二进制、私人节点或订阅、管理凭据、短信内容和设备完整备份。仅使用或引用外部软件，不等于把它重新授权为本项目 MIT。未来若要分发 GPL 软件或修改后的固件，需单独整理对应源代码、构建材料及其许可证义务。

This repository excludes proprietary vendor/Android/modem firmware, FDLs, NV and partition images, full root filesystems, third-party installer binaries, private proxies/subscriptions, management credentials, messages, and full-device backups. External dependencies are not relicensed under the root MIT license. Future redistribution of GPL binaries or modified firmware needs its own corresponding-source, build-material, and license review.

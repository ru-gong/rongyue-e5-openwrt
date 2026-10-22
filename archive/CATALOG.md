# 过程源码浏览目录 / Browse process sources

按阶段浏览原始路径与脱敏源码。文件名保留日期和版本；同一内容可能由多个路径引用。先阅读 [归档说明](README.md)，这些 `.source` 文件不可直接部署。

Browse original paths and sanitized sources by category. Dates and version labels are retained; several paths can reference the same content. Read the [archive notes](README.md) first. These `.source` files are not deployment packages.

| 阶段 / Category | 原始路径数 / Paths |
| --- | ---: |
| [准备与支持 / Preparation and support](catalog/01-preparation-and-support.md) | 160 |
| [观察与备份 / Observation and backup](catalog/02-observation-and-backup.md) | 43 |
| [安装过程 / Installation workflow](catalog/03-installation-workflow.md) | 371 |
| [占用扫描器 / Occupancy scanner](catalog/03-occupancy-scanner.md) | 176 |
| [恢复与启动控制 / Recovery and boot control](catalog/04-recovery-and-boot-control.md) | 158 |
| [蜂窝、双卡与验收 / Cellular, dual-SIM and acceptance](catalog/05-cellular-and-acceptance.md) | 300 |

完整机器索引见 [index.json](index.json)，包含去重哈希、字节数、替换计数及源码候选排除原因。

The full [index.json](index.json) includes deduplication hashes, byte counts, redaction counts, and reasons for excluded source candidates.

## 后续 TF 与 Android 界面实现 / Later TF and Android UI work

2026 年 10 月 23 日新增的核心实现按组件整理，独立于上述历史去重归档。
每个组件的 `SOURCE-PROVENANCE.json` 记录逻辑来源路径、公开版本的修改和文件校验值；
不包含设备绑定、固件、签名材料或原始设备记录。

The later core implementations are organized as components, separately from the
historical deduplicated archive. Each `SOURCE-PROVENANCE.json` maps logical source
paths, publication changes and published file hashes. Device bindings, firmware,
signing material and raw device records are excluded.

- [Android 电源菜单、进度页与后台 / Android power-menu UI and progress backend](../components/android-system-switch-ui/README.md)
- [TF 启动、系统选择与保护检查 / TF boot and system-switch references](../components/tf-system-switch/README.md)
- [TF 方案与使用说明（中文）](../docs/tf-system-switch.zh-CN.md) / [TF design and usage (English)](../docs/tf-system-switch.en.md)

这些是可审阅并运行隔离主机测试的参考源码，设备执行入口已停用，不是通用安装包。
These references support source review and isolated host tests; device execution
entry points are disabled and they are not general-purpose installation packages.

# 主机验证工具 / Host validation tools

这里保留两组可在主机上独立验证的代码，不需要连接 E5。历史安装、回退与双卡流程的源码见 [archive](../archive/README.md)；这些工具不提供设备部署入口。

These two self-contained tools can be validated on a host without connecting an E5. Historical installation, recovery, and dual-SIM workflow sources are in [archive](../archive/README.md). These tools provide no device deployment entry point.

| 目录 / Directory | 用途 / Purpose | 本次验证 / Verification |
| --- | --- | --- |
| [occupancy-scanner](occupancy-scanner/README.md) | 原生占用扫描器与隔离的主机夹具 / Native occupancy scanner and isolated host fixtures | 132 项：128 通过，4 项 Linux 专用跳过 / 132 tests: 128 passed, 4 Linux-specific skips |
| [snapshot-validator](snapshot-validator/README.md) | 单 gzip 流、大小、SHA-256 与 CRC 校验 / Single gzip stream, size, SHA-256 and CRC validation | 11 项通过 / 11 passed |

结果来自 2026-10-20 的 macOS 主机测试。没有据此宣称 Linux 专用场景、真机部署或刷机流程已通过；本次未运行附带的 Linux 命名空间集成夹具。可机读结果见 [validation-results.json](validation-results.json)。

Results are from macOS host tests on 2026-10-20. They do not establish Linux-specific coverage, on-device deployment, or flashing acceptance. The included Linux namespace integration harnesses were not run for this publication. See [validation-results.json](validation-results.json) for machine-readable results.

许可与引用说明见 [LICENSE](../LICENSE) 和 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

See [LICENSE](../LICENSE) and [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) for licensing and attribution.

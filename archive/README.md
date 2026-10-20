# 过程源码归档 / Process source archive

这里保留 E5 项目从准备、只读观察、安装与回退，到占用扫描器、双卡恢复和验收逻辑的源码演变。当前界面与 OpenClash 功能另见仓库的 `components/`；可独立运行的主机验证代码见 [tools](../tools/README.md)。

This archive preserves the development of preparation, read-only observation, installation and recovery, occupancy scanning, dual-SIM rearming, and acceptance logic. Current screen and OpenClash components live in `components/`; independently runnable host validation tools are in [tools](../tools/README.md).

## 阅读方式 / How to read

可先打开 [按阶段浏览的源码目录 / Browse sources by category](CATALOG.md)，直接从原始路径进入对应源码。

[index.json](index.json) 将 **1,208 个原始相对路径** 映射到 **624 个去重后的源码版本**。每个条目记录原始相对路径、阶段分类、归档路径、脱敏后 SHA-256、字节数和替换类型计数。不同阶段的相同内容共用一个文件；被脱敏为相同内容的版本也会合并。原始目录名中的日期和版本标记保留，用来追踪演变。

[index.json](index.json) maps **1,208 original relative paths** to **624 distinct sanitized source versions**. Each entry records the original path, category, archived path, sanitized SHA-256, byte count, and counts of redaction types. Identical sanitized content shares a file, including versions that become identical after redaction. Dates and version labels in original directory names preserve the development sequence.

| 索引分类 / Index category | 范围 / Coverage | 原始路径数 / Paths |
| --- | --- | ---: |
| `01-preparation-and-support` | Android 安装准备、运行前约束、部署收尾 / Android preparation, runtime constraints, deployment closure | 160 |
| `02-observation-and-backup` | 只读抓取、被动日志、诊断 / Read-only capture, passive logging, diagnostics | 43 |
| `03-installation-workflow` | 分阶段部署、容量限制、事务记录、激活 / Staged provisioning, bounded storage, transaction records, activation | 371 |
| `03-occupancy-scanner` | 文件描述符、命名空间、生命周期、关闭文件与复用处理 / File descriptors, namespaces, lifecycle, closed files and reuse | 176 |
| `04-recovery-and-boot-control` | 启动链、恢复入口、回退与快照校验 / Boot lineage, recovery entry, rollback and snapshot validation | 158 |
| `05-cellular-and-acceptance` | 蜂窝网络、双卡恢复、WAN 调整及验收 / Cellular, dual-SIM rearming, WAN changes and acceptance | 300 |

这些是阅读分类，不是部署顺序。不同目录会互相引用，引用的设备状态、生成物和第三方输入不会随此归档发布。

These are reading categories, not deployment steps. Historical scripts refer to other directories, generated artifacts, device state, and third-party inputs that are deliberately absent from this publication.

在仓库根目录查找某个版本：

To locate a version from the repository root:

```sh
python3 - <<'PY'
import json
from pathlib import Path

index = json.loads(Path("archive/index.json").read_text())
for entry in index["sources"]:
    if "e5_scanner_new_slot_prepare_20261019/native_occupancy_scanner.c" in entry["source_path"]:
        print(entry["source_path"], "->", "archive/" + entry["archived_path"])
PY
```

## 脱敏与运行边界 / Redaction and execution boundary

`sources/` 中的文件统一以 `.source` 结尾，供阅读、比较和研究。它们不是可安装的软件包，也不是可直接运行的刷机、安装或系统切换工具。原始代码中的检查逻辑保留，但主机目录、设备序列号、UUID、IP、MAC、32 位十六进制标识和 64 位哈希绑定被替换为占位值。历史测试与脚本可能依赖这些绑定；本归档没有声称脱敏后仍能通过原设备验收。

Files in `sources/` end in `.source` and are provided for reading, comparison, and research. They are not installable packages or runnable flashing, installation, or system-switching tools. Check logic is retained, while host paths, serial numbers, UUIDs, IP addresses, MAC addresses, 32-character hexadecimal identifiers, and 64-character hash pins are replaced with placeholders. Historical tests and scripts can depend on those bindings; passing the original device acceptance tests is not claimed for this sanitized archive.

不应通过改后缀、删除检查或填入其他设备身份来直接部署这些历史版本。某些历史源码包含分区写入、挂载、恢复与重启操作。仓库中可重跑的主机测试与这类部署代码分开列在 [tools](../tools/README.md)。

Do not deploy historical versions by renaming files, removing checks, or substituting another device's identity. Some historical sources contain partition writes, mount operations, recovery actions, and reboots. The host tests that can be rerun are separately documented in [tools](../tools/README.md).

## 收录边界 / Inclusion boundary

- 收录本项目 `tools/e5_*` 中的过程源码、测试及少量说明文件；当前组件另行整理。 / Includes process sources, tests, and selected explanatory files under the project's `tools/e5_*`; current components are organized separately.
- 不收录原始设备 JSON、状态清单、绑定配置、日志、抓包、个人目录、订阅、密钥、固件、分区备份、ELF、库或其他二进制。 / Excludes raw device JSON, state and binding manifests, logs, packet captures, private folders, subscriptions, keys, firmware, partition backups, ELF files, libraries, and other binaries.
- 不收录第三方完整源码树、生成输入输出和无法确认许可的 Spreadtrum 刷写工具源码或源码补丁。 / Excludes complete third-party source trees, generated inputs and outputs, and Spreadtrum flashing sources or source patches whose redistribution license is unconfirmed.
- OpenWrt ModemManager 的 `late-registration.functions.sh` 派生载荷与相关补丁未收录；索引记录排除原因。 / The OpenWrt ModemManager-derived `late-registration.functions.sh` payload and related patches are omitted; the index records the exclusion.
- 索引中的排除表仅覆盖本次源码候选文件，不列举私有资料的全部文件名。 / The exclusions table covers source candidates only and does not inventory private material.

文件后缀及脱敏处理不改变原有许可。项目原创代码与引用的 Enceka `e5-linux` MIT 片段须分别按 [LICENSE](../LICENSE) 和 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) 理解。

Neither the suffix nor redaction changes the applicable license. Consult [LICENSE](../LICENSE) and [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) for original project code and the included MIT-licensed fragments from Enceka `e5-linux`.

# 占用扫描器 / Occupancy scanner

此目录从 `tools/e5_scanner_new_slot_prepare_20261019` 整理而来，保留 C 扫描器、历史对照版本、合成夹具测试及 Linux 集成测试源码。主机路径、设备身份和绑定值已脱敏。

This directory is derived from `tools/e5_scanner_new_slot_prepare_20261019`. It includes the C scanner, historical controls, synthetic fixture tests, and Linux integration harness sources. Host paths, device identities, and binding values have been sanitized.

扫描器围绕受保护文件检查打开的文件描述符、进程根目录和工作目录、内存映射、挂载命名空间及 loop 设备，并对进程身份变化、文件描述符复用、未知状态、超时和取消进行保守处理。返回的结果只针对一次扫描及其约束，不是后续写入操作的授权。

The scanner checks open file descriptors, process roots and working directories, memory mappings, mount namespaces, and loop devices for protected-file occupancy. It handles identity changes, descriptor reuse, unknown state, deadlines, and cancellation conservatively. A result applies only to that scan and its constraints; it does not authorize a later write operation.

## 运行主机测试 / Run host tests

需要 Python 3 和支持 C11 的 `cc`。在本目录运行：

Requires Python 3 and a C11-compatible `cc`. Run from this directory:

```sh
python3 -B -m unittest -v \
  test_native_occupancy_scanner test_kcmp \
  test_final_identity_diagnostics test_lifecycle test_fd_objects
```

测试在临时目录编译程序，并创建合成 `/proc` 与 `/sys` 夹具。主机测试模式通过 `E5_SCANNER_HOST_TEST` 编译选项显式启用。扫描器正常构建保留 `DEVICE_EXECUTION_ENABLED=0`，设备执行入口关闭。

The tests compile the program in temporary directories and create synthetic `/proc` and `/sys` fixtures. Host fixture mode is explicitly compiled with `E5_SCANNER_HOST_TEST`. Normal scanner builds retain `DEVICE_EXECUTION_ENABLED=0`, which disables the device execution entry point.

2026-10-20 在 macOS 上运行 132 项：128 项通过，4 项真实 Linux KCMP/子进程清理检查按平台跳过。测试还验证了默认构建的禁用状态。

On macOS on 2026-10-20, 132 tests ran: 128 passed and 4 real Linux KCMP/child-cleanup checks were skipped by platform. The suite also verified the disabled state of the default build.

## Linux 夹具范围 / Linux harness scope

`linux_*_harness.py` 与两个 `*_workload.c` 保留了专门的集成研究环境：它们会创建进程、文件描述符及隔离的 PID/挂载命名空间，其中部分操作需要 Linux 权限。`prior_scanner.c` 与 `pre_newslot_scanner.c` 用于历史行为对照。它们不属于上面的主机单元测试命令，本次发布未运行这些集成夹具。

The `linux_*_harness.py` files and two `*_workload.c` files preserve specialized integration fixtures. They create processes, descriptors, and isolated PID/mount namespaces; some operations require Linux privileges. `prior_scanner.c` and `pre_newslot_scanner.c` are historical controls. These harnesses are not part of the host unit-test command above and were not run for this publication.

完整历史版本可通过 [归档索引](../../archive/index.json) 查找。许可见 [LICENSE](../../LICENSE) 和 [第三方引用说明](../../THIRD_PARTY_NOTICES.md)。

Full historical versions can be located with the [archive index](../../archive/index.json). See [LICENSE](../../LICENSE) and [third-party notices](../../THIRD_PARTY_NOTICES.md).

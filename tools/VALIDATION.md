# 主机测试记录 / Host validation record

2026-10-20 在 macOS 上，对本仓库发布的源码运行了以下测试。没有连接或操作 E5，没有运行 Linux 命名空间集成夹具，也没有重跑设备安装或刷机流程。

The following tests were run against the sources published in this repository on macOS on 2026-10-20. No E5 was connected or modified. Linux namespace integration harnesses and device installation or flashing workflows were not run.

| 测试 / Suite | 运行 / Run | 通过 / Passed | 跳过 / Skipped | 失败或错误 / Failures or errors |
| --- | ---: | ---: | ---: | ---: |
| Occupancy scanner | 132 | 128 | 4 | 0 |
| Snapshot validator | 11 | 11 | 0 | 0 |

在仓库根目录可以重跑：

To rerun from the repository root:

```sh
(
  cd tools/occupancy-scanner
  python3 -B -m unittest -v \
    test_native_occupancy_scanner test_kcmp \
    test_final_identity_diagnostics test_lifecycle test_fd_objects
)
(
  cd tools/snapshot-validator
  python3 -B -m unittest -v test_snapshot_validation
)
```

Scanner 测试在临时目录构建 C11 程序并使用合成夹具，验证受保护占用、身份漂移、超时、取消、文件描述符复用与默认禁用状态。4 个跳过项只适用于 Linux 上的真实 KCMP 子进程及取消、过期、SIGSYS 后清理行为。三个 scanner C 源文件的 `DEVICE_EXECUTION_ENABLED` 均为 `0`。

Scanner tests compile C11 programs in temporary directories and use synthetic fixtures to test protected occupancy, identity drift, deadlines, cancellation, descriptor reuse, and the disabled default. The four skips cover actual owned-child KCMP and cleanup after cancellation, expiration, or SIGSYS on Linux. All three scanner C sources set `DEVICE_EXECUTION_ENABLED` to `0`.

Snapshot validator 测试使用合成 gzip 数据，验证分块处理、CRC、截断、大小及 SHA-256、单流约束与输入上限。校验函数只接收字节块和输出流，不包含网络或设备入口。

Snapshot validator tests use synthetic gzip data to check chunking, CRC, truncation, raw size and SHA-256, single-stream constraints, and input limits. The function takes byte chunks and an output stream and contains no network or device entry point.

这些结果只证明本次主机测试覆盖范围内的行为。历史归档已脱敏，不能将其旧验收记录视为脱敏版本的运行结果。机器可读记录见 [validation-results.json](validation-results.json)。

These results establish only the behavior covered by these host tests. The historical archive has been sanitized; earlier acceptance records are not results for the sanitized versions. Machine-readable results are in [validation-results.json](validation-results.json).

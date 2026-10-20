# 快照完整性校验 / Snapshot integrity validation

`snapshot_validation.py` 从 `tools/e5_userdata_rescue_prepare_20261020/receive_snapshot.py` 提取纯校验函数 `validate_chunks`。该版本没有网络接收、设备连接、刷写或文件系统修复入口。

`snapshot_validation.py` extracts the pure `validate_chunks` function from `tools/e5_userdata_rescue_prepare_20261020/receive_snapshot.py`. This version has no network receiver, device connection, flashing, or filesystem repair interface.

函数接收 gzip 字节块迭代器、保存压缩数据的输出流，以及独立获得的预期原始大小、SHA-256 和压缩输入上限。它限制逐块解压大小，校验 gzip CRC、恰好一个完整 gzip 流、原始字节数和 SHA-256；不接受尾随数据或拼接流。

The function takes an iterator of gzip byte chunks, an output stream for the compressed data, and independently obtained expected raw size, SHA-256, and compressed-input limit. It bounds each decompression block and validates the gzip CRC, exactly one complete gzip stream, raw byte count, and SHA-256. Trailing data and concatenated streams are rejected.

函数在校验完成前已经向输出流写入压缩数据。调用方应使用临时文件，并且仅在函数成功返回后将其标记为有效快照；失败时清理或隔离不完整输出。预期大小和哈希必须来自可信的独立来源。

The function writes compressed bytes to the output before validation finishes. Callers should use a temporary file and mark it valid only after successful return, then delete or quarantine incomplete output on failure. Expected size and hash must come from a trusted independent source.

## 测试 / Tests

需要 Python 3，无第三方 Python 依赖。在本目录运行：

Requires Python 3 with no third-party Python dependencies. Run from this directory:

```sh
python3 -B -m unittest -v test_snapshot_validation
```

2026-10-20 在 macOS 上运行 11 项，全部通过。覆盖分块输入、截断、CRC 错误、错误大小与哈希、拼接流、输入上限及受限解压行为。测试使用合成数据，不读取真实快照。

All 11 tests passed on macOS on 2026-10-20. They cover fragmented input, truncation, CRC errors, size and hash mismatches, concatenated streams, input limits, and bounded decompression. Tests use synthetic data and do not read real snapshots.

历史接收流程的脱敏参考源码见 [归档索引](../../archive/index.json)。许可见 [LICENSE](../../LICENSE) 和 [第三方引用说明](../../THIRD_PARTY_NOTICES.md)。

Sanitized references for the historical receiver workflow are in the [archive index](../../archive/index.json). See [LICENSE](../../LICENSE) and [third-party notices](../../THIRD_PARTY_NOTICES.md).

"""Offline gzip integrity validation extracted from the E5 snapshot receiver.

No network, device access, flashing or filesystem repair interface.
"""
import hashlib
import zlib


def validate_chunks(chunks, output, *, expected_bytes, expected_sha256, compressed_cap):
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    raw_hash, gz_hash = hashlib.sha256(), hashlib.sha256()
    raw_bytes = gz_bytes = 0
    for chunk in chunks:
        if not chunk: continue
        if decoder.eof: raise ValueError('bytes after gzip stream')
        gz_bytes += len(chunk)
        if gz_bytes > compressed_cap: raise ValueError('compressed cap')
        output.write(chunk); gz_hash.update(chunk)
        pending = chunk
        while pending:
            block = decoder.decompress(pending, 8 << 20)
            raw_bytes += len(block)
            if raw_bytes > expected_bytes: raise ValueError('raw size exceeds fixed partition')
            raw_hash.update(block)
            if decoder.unused_data: raise ValueError('trailing or concatenated stream')
            pending = decoder.unconsumed_tail
    if not decoder.eof: raise ValueError('truncated gzip stream')
    if raw_bytes != expected_bytes: raise ValueError('wrong raw partition byte count')
    if raw_hash.hexdigest() != expected_sha256: raise ValueError('independent source SHA mismatch')
    return {'raw_bytes': raw_bytes, 'raw_sha256': raw_hash.hexdigest(),
            'gzip_bytes': gz_bytes, 'gzip_sha256': gz_hash.hexdigest(),
            'gzip_crc_verified': True, 'exactly_one_gzip_stream': True}

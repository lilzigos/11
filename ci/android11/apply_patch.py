#!/usr/bin/env python3
"""Rebuild the exact signed APK using its original APK and the supplied patch.

Python 3.8+ standard library only; no network and no Android SDK required.
"""
import argparse
import errno
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile

MAGIC = b"SGMPATCH\x01"
CHUNK = 1024 * 1024


def read_exact(stream, length):
    data = stream.read(length)
    if len(data) != length:
        raise ValueError("Patch is incomplete / 补丁文件不完整")
    return data


def sha256(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            result.update(block)
    return result.hexdigest()


def apply(original, patch, output):
    original, patch, output = (Path(p).resolve() for p in (original, patch, output))
    if output in (original, patch) or output.exists():
        raise ValueError("Output must be a new filename / 输出文件名必须尚不存在")
    temporary = None
    try:
        with gzip.open(patch, "rb") as recipe:
            if read_exact(recipe, len(MAGIC)) != MAGIC:
                raise ValueError("Unsupported patch format / 补丁格式不支持")
            header_size = struct.unpack("<I", read_exact(recipe, 4))[0]
            if not 0 < header_size <= 65536:
                raise ValueError("Invalid patch header")
            header = json.loads(read_exact(recipe, header_size))
            if header.get("schema") != 1:
                raise ValueError("Unsupported patch schema")
            source_size, target_size = header["source_size"], header["target_size"]
            operation_count = header["operation_count"]
            if (not isinstance(source_size, int) or not isinstance(target_size, int)
                    or not 0 < target_size < 10 * 1024**3
                    or not isinstance(operation_count, int) or not 0 < operation_count <= 100000):
                raise ValueError("Invalid patch sizes")
            print("Checking original APK / 正在校验原始 APK...", flush=True)
            if original.stat().st_size != source_size or sha256(original) != header["source_sha256"]:
                raise ValueError("Original APK SHA256 differs / 原始 APK 版本或内容不匹配，未写入输出")
            output.parent.mkdir(parents=True, exist_ok=True)
            digest, written = hashlib.sha256(), 0
            with original.open("rb") as source, tempfile.NamedTemporaryFile(
                    mode="wb", prefix="." + output.name + ".", suffix=".partial",
                    dir=output.parent, delete=False) as target:
                temporary = Path(target.name)
                print("Rebuilding original Unity APK / 正在重建原版 Unity APK...", flush=True)
                for _ in range(operation_count):
                    operation = read_exact(recipe, 1)
                    if operation == b"C":
                        offset, length = struct.unpack("<QQ", read_exact(recipe, 16))
                        if offset + length > source_size:
                            raise ValueError("Copy operation exceeds source")
                        source.seek(offset)
                        current = source
                    elif operation == b"D":
                        length = struct.unpack("<Q", read_exact(recipe, 8))[0]
                        current = recipe
                    else:
                        raise ValueError("Unknown patch operation")
                    if not length or written + length > target_size:
                        raise ValueError("Patch exceeds output size")
                    while length:
                        block = read_exact(current, min(CHUNK, length))
                        target.write(block)
                        digest.update(block)
                        written += len(block)
                        length -= len(block)
                if read_exact(recipe, 1) != b"E" or recipe.read(1):
                    raise ValueError("Unexpected data after patch")
                if written != target_size or digest.hexdigest() != header["target_sha256"]:
                    raise ValueError("Rebuilt APK SHA256 differs / 重建文件校验失败，不会交付该文件")
                target.flush()
                os.fsync(target.fileno())
        # Publish a verified file without ever replacing an existing file.
        # Android shared storage and FAT filesystems may not support hard links.
        try:
            os.link(temporary, output)
        except OSError as error:
            unsupported = {errno.EPERM, errno.EACCES, errno.EXDEV, errno.ENOSYS,
                           getattr(errno, "EOPNOTSUPP", errno.EPERM),
                           getattr(errno, "ENOTSUP", errno.EPERM)}
            if error.errno not in unsupported:
                raise
            created = False
            try:
                with output.open("xb") as published, temporary.open("rb") as verified:
                    created = True
                    shutil.copyfileobj(verified, published, CHUNK)
                    published.flush()
                    os.fsync(published.fileno())
            except BaseException:
                if created:
                    output.unlink(missing_ok=True)
                raise
        temporary.unlink()
        temporary = None
        print("Verified / 完整校验通过: " + str(output), flush=True)
        print("SHA256: " + header["target_sha256"], flush=True)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", help="Original base.apk / 原始 APK")
    parser.add_argument("--patch", default=str(Path(__file__).with_name("SGM003.patch.gz")))
    parser.add_argument("--output", default="SGM_Offline_TC_Candidate003.apk")
    args = parser.parse_args()
    try:
        apply(args.original, args.patch, args.output)
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        parser.exit(1, "Failed / 失败: " + str(error) + "\n")


if __name__ == "__main__":
    main()

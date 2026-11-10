"""Unpack the payload of a SumatraPDF installer (an "LzSA" archive).

SumatraPDF's installer is the viewer executable with its files appended as a
resource: ``.rsrc/RCDATA/1`` once 7z has opened the installer. The format
(utils/LzmaSimpleArchive in the SumatraPDF source) is

    "LzSA"   u32 file count
    per file u32 id, u32 compressed size, u32 uncompressed size,
             u32 CRC-32 of the uncompressed data, u64 FILETIME, NUL-terminated name
    u32      CRC-32 of the header
    per file the compressed data in the same order: one method byte (1: the
             x86 BCJ filter followed by LZMA1), the LZMA properties byte, the
             u32 dictionary size, then the raw LZMA1 stream.

Nothing is executed. Every file is checked against its stored CRC-32 and
length, and the script exits non-zero on the first mismatch, so a payload that
does not decode exactly is never turned into a file.

    python3 extract_lzsa.py <payload> <output directory>
"""

import lzma
import os
import struct
import sys
import zlib


def unpack(data, destination):
    if data[:4] != b"LzSA":
        raise SystemExit("not an LzSA archive: %r" % data[:4])
    count = struct.unpack_from("<I", data, 4)[0]
    position = 8
    entries = []
    for _ in range(count):
        _id, compressed, size, crc = struct.unpack_from("<IIII", data, position)
        position += 24  # the four fields and the 8-byte FILETIME
        end = data.index(b"\0", position)
        name = data[position:end].decode("ascii")
        position = end + 1
        if name != os.path.basename(name) or name in ("", ".", ".."):
            raise SystemExit("refusing archive member name %r" % name)
        entries.append((name, compressed, size, crc))
    position += 4  # header CRC-32
    os.makedirs(destination, exist_ok=True)
    for name, compressed, size, crc in entries:
        blob = data[position:position + compressed]
        position += compressed
        if len(blob) != compressed or blob[0] != 1:
            raise SystemExit("%s: unsupported or truncated member" % name)
        props = blob[1]
        dictionary = struct.unpack_from("<I", blob, 2)[0]
        lc = props % 9
        rest = props // 9
        filters = [{"id": lzma.FILTER_X86},
                   {"id": lzma.FILTER_LZMA1, "lc": lc, "lp": rest % 5,
                    "pb": rest // 5, "dict_size": dictionary}]
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=filters)
        out = decoder.decompress(blob[6:], max_length=size)
        if len(out) != size or zlib.crc32(out) & 0xFFFFFFFF != crc:
            raise SystemExit("%s: length or CRC-32 mismatch" % name)
        with open(os.path.join(destination, name), "wb") as handle:
            handle.write(out)
        print("%s: %d bytes, CRC-32 %08x ok" % (name, size, crc))
    if position != len(data):
        raise SystemExit("%d trailing bytes after the last member"
                         % (len(data) - position))


if __name__ == "__main__":
    with open(sys.argv[1], "rb") as handle:
        unpack(handle.read(), sys.argv[2])

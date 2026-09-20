#!/usr/bin/env python3
"""Extract a committed shellcode blob from an upstream source file.

Several projects in the open issues ship their loader as a compiled blob
checked into the repository - sRDI keeps it as a Python bytes literal, donut
as a C array. Those blobs are MSVC-compiled, which is exactly the build this
environment cannot reproduce and exactly what is encountered in the wild, so
extracting them is better reference material than a MinGW rebuild would be.

Nothing upstream is executed: the literal is located by pattern and decoded
with ast.literal_eval or a hex parse.

    python3 extract_blob.py python Python/ShellcodeRDI.py rdiShellcode32 out.bin
    python3 extract_blob.py carray loader/loader_exe_x64.h out.bin
"""

import argparse
import ast
import re
import sys


def extract_python_bytes(source_path, name):
    """Pull a `name = b"..."` literal out of a Python source file."""
    with open(source_path, encoding="utf-8", errors="replace") as handle:
        source = handle.read()
    match = re.search(r"^\s*%s\s*=\s*(b['\"].*?['\"])\s*$" % re.escape(name),
                      source, re.MULTILINE | re.DOTALL)
    if not match:
        raise SystemExit("no bytes literal named %r in %s" % (name, source_path))
    value = ast.literal_eval(match.group(1))
    if not isinstance(value, bytes):
        raise SystemExit("%s in %s is not a bytes literal" % (name, source_path))
    return value


def extract_c_array(source_path):
    """Pull the byte values out of a C array initialiser."""
    with open(source_path, encoding="utf-8", errors="replace") as handle:
        source = handle.read()
    body = source[source.index("{") + 1:source.rindex("}")]
    values = re.findall(r"0[xX][0-9a-fA-F]{1,2}", body)
    if not values:
        raise SystemExit("no byte values found in %s" % source_path)
    return bytes(int(value, 16) & 0xFF for value in values)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=["python", "carray"])
    parser.add_argument("source")
    parser.add_argument("rest", nargs="+",
                        help="for 'python': <symbol> <output>; for 'carray': <output>")
    args = parser.parse_args()

    if args.kind == "python":
        if len(args.rest) != 2:
            parser.error("python extraction needs <symbol> <output>")
        symbol, output = args.rest
        blob = extract_python_bytes(args.source, symbol)
    else:
        if len(args.rest) != 1:
            parser.error("carray extraction needs <output>")
        output = args.rest[0]
        blob = extract_c_array(args.source)

    with open(output, "wb") as handle:
        handle.write(blob)
    print("%s: %d bytes" % (output, len(blob)), file=sys.stderr)


if __name__ == "__main__":
    main()

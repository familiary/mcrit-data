#!/usr/bin/env python3
"""Decrypt a Meterpreter DLL as distributed in the metasploit-payloads gem.

Rapid7 compiles Meterpreter with MSVC and publishes the result in the
`metasploit-payloads` RubyGem, which is the build that is encountered in the
wild and which this environment cannot reproduce - the modern Windows SDK and
`metsrv`'s own `struct _CLIENT_ID` collide, and upstream's `v141_xp`/`v120_xp`
toolsets are gone from every runner image. Harvesting the published binary is
what `scripts/corpus/README.md` recommends for exactly this case.

Since gem 2.0.x the shipped files are not PE images: each is an `msf` header
followed by a ciphertext. That is obfuscation of files at rest, not operator
configuration - the key is a constant committed in the gem's own
`lib/metasploit-payloads/crypto.rb`, identical in every copy of a given
version, with no per-build or per-install material anywhere in it. So this
reads the key table out of the pinned source file rather than carrying key
bytes of its own, which keeps the secret where upstream publishes it and makes
the version pin govern the decryption too.

Nothing is executed and nothing is configured: one AES-CBC pass turns a file
on disk into the PE image upstream compiled, for SMDA to disassemble.

    python3 decrypt_msf.py lib/metasploit-payloads/crypto.rb in.dll out.dll
"""

import argparse
import os
import re
import sys


HEADER_MAGIC = b"msf"
# 'msf' plus the cipher, IV and key version bytes, per ENCRYPTED_PAYLOAD_HEADER.
HEADER_LENGTH = len(HEADER_MAGIC) + 3

_RUBY_ESCAPES = {
    "\\": "\\", '"': '"', "'": "'", "n": "\n", "t": "\t",
    "r": "\r", "0": "\0", "e": "\x1b", "a": "\a", "b": "\b",
    "f": "\f", "v": "\v", "s": " ",
}


class DecryptError(Exception):
    """A gem file, or the key table in it, is not shaped as expected."""


def _decode_ruby_string(text):
    """Decode the body of a Ruby double-quoted literal to bytes.

    The key table writes every byte as ``\\xHH``, so this only has to handle
    hex escapes plus the single-character ones, and it refuses anything else
    rather than silently dropping a backslash.
    """
    out = bytearray()
    index = 0
    while index < len(text):
        char = text[index]
        if char != "\\":
            out.extend(char.encode("utf-8"))
            index += 1
            continue
        if index + 1 >= len(text):
            raise DecryptError("string literal ends in a backslash")
        marker = text[index + 1]
        if marker == "x":
            digits = re.match(r"[0-9a-fA-F]{1,2}", text[index + 2:])
            if not digits:
                raise DecryptError(r"\x escape with no hex digits")
            out.append(int(digits.group(0), 16))
            index += 2 + len(digits.group(0))
        elif marker in _RUBY_ESCAPES:
            out.extend(_RUBY_ESCAPES[marker].encode("utf-8"))
            index += 2
        else:
            raise DecryptError("unsupported escape \\%s in the key table" % marker)
    return bytes(out)


def _matching_brace(text, open_index):
    """Index of the ``}`` closing the ``{`` at ``open_index``.

    Ruby string literals in this file can contain braces, so quoted runs are
    skipped rather than counted.
    """
    depth = 0
    index = open_index
    while index < len(text):
        char = text[index]
        if char in "\"'":
            quote = char
            index += 1
            while index < len(text):
                if text[index] == "\\":
                    index += 2
                    continue
                if text[index] == quote:
                    break
                index += 1
            else:
                raise DecryptError("unterminated string literal in the key table")
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise DecryptError("unbalanced braces in the key table")


def _numbered_entries(body):
    """Yield ``(number, body)`` for each ``N => { ... }`` directly in ``body``.

    Only entries at this nesting level: each match consumes its own braces, so
    the ``1 => {`` of a cipher's ``ivs`` table is not mistaken for a cipher.
    """
    pattern = re.compile(r"(\d+)\s*=>\s*\{")
    position = 0
    while True:
        match = pattern.search(body, position)
        if not match:
            return
        start = match.end() - 1
        end = _matching_brace(body, start)
        yield int(match.group(1)), body[start + 1:end]
        position = end + 1


def _single_valued(body, field):
    """Read ``field: { N => { value: "..." } }`` into ``{N: bytes}``."""
    match = re.search(r"\b%s\s*:\s*\{" % re.escape(field), body)
    if not match:
        raise DecryptError("no %r table in the cipher entry" % field)
    start = match.end() - 1
    inner = body[start + 1:_matching_brace(body, start)]
    values = {}
    for number, entry in _numbered_entries(inner):
        value = re.search(r'\bvalue\s*:\s*"((?:[^"\\]|\\.)*)"', entry)
        if value:
            values[number] = _decode_ruby_string(value.group(1))
    if not values:
        raise DecryptError("the %r table has no value entries" % field)
    return values


def parse_ciphers(crypto_rb_path):
    """Parse the CIPHERS table out of the gem's crypto.rb.

    Returns ``{version: {"name": str, "ivs": {n: bytes}, "keys": {n: bytes}}}``.
    """
    with open(crypto_rb_path, encoding="utf-8", errors="replace") as handle:
        source = handle.read()
    match = re.search(r"\bCIPHERS\s*=\s*\{", source)
    if not match:
        raise DecryptError("no CIPHERS table in %s" % crypto_rb_path)
    start = match.end() - 1
    table = source[start + 1:_matching_brace(source, start)]
    ciphers = {}
    for version, body in _numbered_entries(table):
        name = re.search(r"\bname\s*:\s*['\"]([^'\"]+)['\"]", body)
        if not name:
            continue
        ciphers[version] = {
            "name": name.group(1),
            "ivs": _single_valued(body, "ivs"),
            "keys": _single_valued(body, "keys"),
        }
    if not ciphers:
        raise DecryptError("the CIPHERS table in %s parsed empty" % crypto_rb_path)
    return ciphers


def _strip_pkcs7(plaintext):
    """Remove PKCS#7 padding, which OpenSSL's aes-256-cbc always adds."""
    if not plaintext:
        raise DecryptError("decryption produced no output")
    pad = plaintext[-1]
    if 1 <= pad <= 16 and plaintext[-pad:] == bytes([pad]) * pad:
        return plaintext[:-pad]
    # A PE whose length is already a multiple of the block size still gets a
    # full block of padding, so a missing pad means the wrong key, not a
    # legitimately unpadded image.
    raise DecryptError("no PKCS#7 padding on the plaintext; wrong key or IV")


def decrypt(data, ciphers):
    """Decrypt one gem file. A file with no `msf` header is returned as is."""
    if not data.startswith(HEADER_MAGIC):
        return data
    if len(data) <= HEADER_LENGTH:
        raise DecryptError("file is an `msf` header and nothing else")
    cipher_version, iv_version, key_version = data[3], data[4], data[5]
    entry = ciphers.get(cipher_version)
    if entry is None:
        raise DecryptError("the key table has no cipher version %d" % cipher_version)
    if entry["name"] != "aes-256-cbc":
        # chacha20 is listed as version 1 and nothing has ever shipped with
        # it. Rather than guess at OpenSSL's 16-byte IV convention untested,
        # say which cipher turned up.
        raise DecryptError("cipher version %d is %r, which this helper does not "
                           "implement" % (cipher_version, entry["name"]))
    try:
        key = entry["keys"][key_version]
        iv = entry["ivs"][iv_version]
    except KeyError:
        raise DecryptError("no key %d / IV %d for cipher version %d"
                           % (key_version, iv_version, cipher_version))
    if len(key) != 32 or len(iv) != 16:
        raise DecryptError("aes-256-cbc needs a 32-byte key and 16-byte IV; "
                           "the table gave %d and %d" % (len(key), len(iv)))
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    body = data[HEADER_LENGTH:]
    if len(body) % 16:
        raise DecryptError("ciphertext is %d bytes, not a multiple of the "
                           "16-byte block" % len(body))
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    return _strip_pkcs7(decryptor.update(body) + decryptor.finalize())


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("crypto_rb",
                        help="lib/metasploit-payloads/crypto.rb from the gem")
    parser.add_argument("source", help="the distributed, encrypted file")
    parser.add_argument("output", help="where to write the PE image")
    args = parser.parse_args(argv)

    try:
        ciphers = parse_ciphers(args.crypto_rb)
        with open(args.source, "rb") as handle:
            plaintext = decrypt(handle.read(), ciphers)
    except DecryptError as error:
        sys.stderr.write("decrypt_msf: %s: %s\n" % (args.source, error))
        return 1
    if plaintext[:2] != b"MZ":
        sys.stderr.write("decrypt_msf: %s: plaintext does not start with MZ\n"
                         % args.source)
        return 1
    directory = os.path.dirname(os.path.abspath(args.output))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(args.output, "wb") as handle:
        handle.write(plaintext)
    return 0


if __name__ == "__main__":
    sys.exit(main())

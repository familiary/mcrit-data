"""Cross toolchains used to produce the reference builds.

Only compilers that can be driven unattended from Linux are listed. MSVC
builds in this repository came from real Visual Studio installations and
cannot be reproduced here; recipes that need them have to be marked blocked
rather than approximated.
"""

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Toolchain:
    id: str
    # Short form used in generated filenames, e.g. "mingw13".
    short_id: str
    arch: str
    bitness: int
    prefix: str
    cc: str
    cxx: str
    windres: str
    strip: str
    ar: str
    ranlib: str
    cflags: str = "-O2"
    env: Dict[str, str] = field(default_factory=dict)

    def available(self):
        return shutil.which(self.cc) is not None

    def version(self):
        """Compiler version string, recorded as build provenance."""
        out = subprocess.run([self.cc, "-dumpfullversion", "-dumpversion"],
                             capture_output=True, text=True, check=True)
        return out.stdout.split()[0]

    def build_env(self):
        """Environment variables recipes can rely on for autotools/cmake."""
        env = {
            "CC": self.cc,
            "CXX": self.cxx,
            "AR": self.ar,
            "RANLIB": self.ranlib,
            "WINDRES": self.windres,
            # Reference data is far more useful with symbols, and SMDA reads
            # the COFF symbol table MinGW emits, so never strip.
            "STRIP": "true",
            "CFLAGS": self.cflags,
            "CXXFLAGS": self.cflags,
        }
        env.update(self.env)
        return env

    def placeholders(self):
        return {
            "cc": self.cc,
            "cxx": self.cxx,
            "prefix": self.prefix,
            "windres": self.windres,
            "ar": self.ar,
            "ranlib": self.ranlib,
            "arch": self.arch,
            "bitness": str(self.bitness),
            "cflags": self.cflags,
            "host": self.prefix.rstrip("-"),
            # MemoryModule and friends select the cross compiler by CPU name.
            "platform": self.prefix.split("-")[0],
            # LuaJIT builds host tools first and needs them to match the
            # target's pointer size, so a 32-bit target needs a 32-bit host cc.
            "hostcc": "gcc" if self.bitness == 64 else "gcc -m32",
            # lz4's lib/Makefile keys its DLL rule off this spelling.
            "mingw_os": "MINGW64" if self.bitness == 64 else "MINGW32",
            # OpenSSL's Configure target names.
            "openssl_target": "mingw64" if self.bitness == 64 else "mingw",
            # 7-Zip names its makefiles and output directories this way.
            "asm_arch": "x64" if self.bitness == 64 else "x86",
        }


def _mingw(arch, bitness, triple, gcc_major):
    return Toolchain(
        id="mingw%s_%s" % (gcc_major, arch),
        short_id="mingw%s" % gcc_major,
        arch=arch,
        bitness=bitness,
        prefix="%s-" % triple,
        cc="%s-gcc" % triple,
        cxx="%s-g++" % triple,
        windres="%s-windres" % triple,
        strip="%s-strip" % triple,
        ar="%s-ar" % triple,
        ranlib="%s-ranlib" % triple,
    )


# GCC major version is resolved lazily so the ids stay truthful if the host
# toolchain is upgraded.
def _detect_mingw_major(triple):
    cc = "%s-gcc" % triple
    if shutil.which(cc) is None:
        return None
    out = subprocess.run([cc, "-dumpversion"], capture_output=True, text=True)
    match = re.match(r"(\d+)", out.stdout.strip())
    return match.group(1) if match else None


_TOOLCHAINS = {}


def _register_mingw():
    for arch, bitness, triple in (("x86", 32, "i686-w64-mingw32"),
                                  ("x64", 64, "x86_64-w64-mingw32")):
        major = _detect_mingw_major(triple)
        if major is None:
            continue
        toolchain = _mingw(arch, bitness, triple, major)
        _TOOLCHAINS[toolchain.id] = toolchain
        # Stable alias so recipes do not have to name the host GCC version.
        _TOOLCHAINS["mingw_%s" % arch] = toolchain


_register_mingw()


def get_toolchain(toolchain_id) -> Toolchain:
    if toolchain_id not in _TOOLCHAINS:
        raise KeyError("unknown or unavailable toolchain %r, have: %s"
                       % (toolchain_id, ", ".join(sorted(_TOOLCHAINS))))
    return _TOOLCHAINS[toolchain_id]


def available_toolchains() -> List[str]:
    return sorted(_TOOLCHAINS)

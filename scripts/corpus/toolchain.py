"""Toolchains used to produce the reference builds.

Two families are supported. The mingw-w64 cross compilers run anywhere and
are what a Linux checkout uses. MSVC is registered only when cl.exe is on
PATH - that is, on Windows inside a Visual Studio developer environment,
which in practice means a windows-2022 GitHub Actions runner. Several open
issues need ATL, MASM or the WDK and are simply not buildable with GCC, so
they are covered by the MSVC side rather than approximated.
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
    # "mingw" or "msvc"; selects how probes and compiler flags are spelled.
    kind: str = "mingw"

    def version(self):
        """Compiler banner line, recorded as build provenance.

        The first line is what every provenance record in this corpus already
        carries for GCC ("...-gcc (GCC) 13.2.0"), so cl is read the same way -
        which needs a separate path, because cl has no version flag and
        prints its banner on stderr.
        """
        if self.kind == "msvc":
            out = subprocess.run([self.cc], capture_output=True, text=True)
            text = out.stderr or out.stdout
        else:
            out = subprocess.run([self.cc, "--version"], capture_output=True,
                                 text=True, check=True)
            text = out.stdout
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines[0] if lines else "unknown"

    def probe_command(self, compiler, source, target, shared):
        """Command line that builds a CRT baseline probe with this toolchain."""
        if self.kind == "msvc":
            # cl writes its output next to the source unless told otherwise,
            # and /LD selects a DLL.
            command = [compiler, "/nologo", "/O2", source, "/Fe:" + target]
            return command + (["/LD"] if shared else [])
        return [compiler, "-O2", "-o", target, source] + (["-shared"] if shared else [])

    def build_env(self):
        """Environment variables recipes can rely on for autotools/cmake."""
        if self.kind == "msvc":
            # The developer environment already exports everything cl, link,
            # ml64 and MSBuild need; overriding CC/AR here would break them.
            return dict(self.env)
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
            # MSBuild and vcvarsall spellings.
            "msbuild_platform": "x64" if self.bitness == 64 else "Win32",
            "masm": "ml64" if self.bitness == 64 else "ml",
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


def _msvc(arch, bitness, version):
    """MSVC as exposed inside a Visual Studio developer environment."""
    return Toolchain(
        id="msvc%s_%s" % (version, arch),
        short_id="msvc%s" % version,
        arch=arch,
        bitness=bitness,
        prefix="",
        cc="cl",
        cxx="cl",
        windres="rc",
        strip="",
        ar="lib",
        ranlib="",
        cflags="/O2",
        kind="msvc",
    )


def _detect_msvc():
    """Return (toolset, arch) when cl.exe is on PATH, else None.

    The developer environment decides which target cl produces, so the
    architecture is read from cl's own banner rather than chosen here.
    """
    if shutil.which("cl") is None:
        return None
    out = subprocess.run(["cl"], capture_output=True, text=True)
    banner = (out.stderr or out.stdout).splitlines()[0] if (out.stderr or out.stdout) else ""
    arch = "x64" if "x64" in banner else "x86"
    # "Compiler Version 19.44.x" -> VS 2022 is the 19.3x-19.4x range.
    match = re.search(r"Version (\d+)\.(\d+)", banner)
    toolset = "143"
    if match and int(match.group(1)) == 19:
        minor = int(match.group(2))
        toolset = "143" if minor >= 30 else "142" if minor >= 20 else "141"
    return toolset, arch


_TOOLCHAINS = {}


def _register_msvc():
    detected = _detect_msvc()
    if detected is None:
        return
    toolset, arch = detected
    bitness = 64 if arch == "x64" else 32
    toolchain = _msvc(arch, bitness, toolset)
    _TOOLCHAINS[toolchain.id] = toolchain
    _TOOLCHAINS["msvc_%s" % arch] = toolchain


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
_register_msvc()


def get_toolchain(toolchain_id) -> Toolchain:
    if toolchain_id not in _TOOLCHAINS:
        raise KeyError("unknown or unavailable toolchain %r, have: %s"
                       % (toolchain_id, ", ".join(sorted(_TOOLCHAINS))))
    return _TOOLCHAINS[toolchain_id]


def available_toolchains() -> List[str]:
    return sorted(_TOOLCHAINS)

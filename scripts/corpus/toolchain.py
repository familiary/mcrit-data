"""Toolchains used to produce the reference builds.

Three families are supported. The mingw-w64 cross compilers run anywhere and
are what a Linux checkout uses for the PE side. MSVC is registered only when
cl.exe is on PATH - that is, on Windows inside a Visual Studio developer
environment, which in practice means a windows-2022 GitHub Actions runner.
Several open issues need ATL, MASM or the WDK and are simply not buildable
with GCC, so they are covered by the MSVC side rather than approximated.

The third is the host's own gcc/g++ targeting Linux and ELF, registered when
gcc is on PATH and (for the 32-bit half) the -m32 multilib is installed. It
is the only one here that does not produce a PE, and it exists because the
portable half of this corpus - the header-only string obfuscators, obfstr -
is used on Linux too, and a PE-only corpus cannot recognise it there.
"""

import os
import re
import shutil
import subprocess
import sys
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
    # "mingw", "msvc" or "linux"; selects how probes and compiler flags are
    # spelled, and which container the artefacts come out in.
    #
    # "linux" is a third value rather than a reuse of "mingw", even though
    # GCC-on-Linux spells its flags exactly the way GCC-on-Windows does and
    # every kind test outside baseline.py would have done the right thing.
    # The one that would not is the important one: crt_glue's four default
    # probes are #include <windows.h> with __declspec(dllexport) entry points
    # and calls to _vscprintf, _gmtime32_s and _strtoi64, none of which exist
    # on glibc. Under kind="mingw" every one of them would have failed to
    # build, which is not a neutral event here - it leaves the artefacts
    # filtered against an empty baseline and fails the run (see
    # baseline.probe_failures). A name that selects the wrong probe set is a
    # name that lies, so the two are separated.
    kind: str = "mingw"
    # The -m32/-m64 the native compiler needs to pick an ABI, empty for the
    # cross compilers which target exactly one. Exposed to recipes as
    # {archflag} so one build line can serve both architectures.
    arch_flag: str = ""

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
        """Command line that builds a CRT baseline probe with this toolchain.

        The MSVC probe is built with debug info on purpose. MSVC keeps symbols
        in a PDB rather than in a COFF symbol table, so without one SMDA
        recovers the probe's functions unnamed - and the glue filter matches on
        symbol *and* PicHash, so an unnamed baseline matches nothing at all.
        That is not a degraded filter, it is no filter: every MSVC artefact
        came through with an empty removed_runtime_functions list and ~19% of
        VX-API was MSVC startup glue and ATL wearing the VX-API family name.
        """
        if self.kind == "msvc":
            # cl writes its output next to the source unless told otherwise,
            # and /LD selects a DLL.
            command = [compiler, "/nologo", "/O2", "/Zi",
                       "/Fd:" + target + ".pdb", source, "/Fe:" + target]
            command += ["/LD"] if shared else []
            return command + ["/link", "/DEBUG", "/PDB:" + target + ".pdb"]
        if self.kind == "linux":
            # The ABI has to be named (one gcc serves both) and a shared
            # object has to be position-independent, which is not the default
            # for the compile step even though it is for the link. Kept in a
            # branch of its own so the MinGW command line below stays exactly
            # the bytes it was: that baseline is a measured constant the rest
            # of this corpus was filtered against.
            return ([compiler, self.arch_flag, "-O2", "-fPIC", "-o", target,
                     source] + (["-shared"] if shared else []))
        return [compiler, "-O2", "-o", target, source] + (["-shared"] if shared else [])

    def probe_pdb(self, target):
        """Where probe_command puts the PDB, or "" when there is not one."""
        return target + ".pdb" if self.kind == "msvc" else ""

    def build_env(self):
        """Environment variables recipes can rely on for autotools/cmake."""
        if self.kind == "msvc":
            # The developer environment already exports everything cl, link,
            # ml64 and MSBuild need; overriding CC/AR here would break them.
            return dict(self.env)
        if self.kind == "linux":
            # No WINDRES: there is no resource compiler on this side, and
            # exporting it empty is worse than not exporting it at all - an
            # autotools build that tests whether it is set would find it set
            # and then try to run "". The ABI flag travels in CC/CXX rather
            # than only in CFLAGS because a link step invoked through CC must
            # carry it too, or a 32-bit object is handed to a 64-bit link.
            env = {
                "CC": ("%s %s" % (self.cc, self.arch_flag)).strip(),
                "CXX": ("%s %s" % (self.cxx, self.arch_flag)).strip(),
                "AR": self.ar,
                "RANLIB": self.ranlib,
                # Same reason as the MinGW side below: SMDA reads the ELF
                # symbol table, so a build system that strips by default
                # would quietly yield anonymous reference data.
                "STRIP": "true",
                "CFLAGS": self.cflags,
                "CXXFLAGS": self.cflags,
            }
            env.update(self.env)
            return env
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
        # The CPU name and the target triple come off the compiler prefix,
        # which the cross compilers have and the native one does not. Derived
        # from the bitness instead there, rather than left empty: a recipe
        # that spells a Rust target as {platform}-unknown-linux-gnu would
        # otherwise expand it to "-unknown-linux-gnu" and cargo would report
        # an unknown target, which names neither the cause nor this file.
        if self.kind == "linux":
            cpu = "x86_64" if self.bitness == 64 else "i686"
            host = "%s-linux-gnu" % cpu
        else:
            cpu = self.prefix.split("-")[0]
            host = self.prefix.rstrip("-")
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
            # -m32/-m64 for the native Linux compilers, empty for the cross
            # compilers and for cl, which each target exactly one ABI. A
            # recipe can therefore spell one build line for both.
            "archflag": self.arch_flag,
            "host": host,
            # MemoryModule and friends select the cross compiler by CPU name.
            "platform": cpu,
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


def _gcc(arch, bitness, gcc_major):
    """The host's own GCC, targeting Linux and ELF rather than a PE.

    Both architectures come out of one compiler driver, selected by -m32 or
    -m64, so unlike the MinGW pair there is no per-arch binary to look for -
    which is why the 32-bit half is gated on the multilib check below instead.
    """
    return Toolchain(
        id="gcc%s_%s" % (gcc_major, arch),
        short_id="gcc%s" % gcc_major,
        arch=arch,
        bitness=bitness,
        prefix="",
        cc="gcc",
        cxx="g++",
        windres="",
        strip="strip",
        ar="ar",
        ranlib="ranlib",
        # The ABI flag belongs in CFLAGS as well as in CC: a build system
        # that compiles with $(CC) $(CFLAGS) but links with $(CC) alone, or
        # the other way round, needs it in whichever one it uses.
        cflags="-O2 -m%d" % bitness,
        kind="linux",
        arch_flag="-m%d" % bitness,
    )


def _detect_gcc_major():
    cc = "gcc"
    if shutil.which(cc) is None:
        return None
    out = subprocess.run([cc, "-dumpversion"], capture_output=True, text=True)
    match = re.match(r"(\d+)", out.stdout.strip())
    return match.group(1) if match else None


def _has_multilib():
    """Whether this gcc can target 32-bit at all.

    A host without gcc-multilib still has a perfectly good gcc, so the two
    have to be separated: registering linux_x86 there would turn a host that
    simply cannot build 32-bit ELF into a host that reports a build failure
    for every 32-bit recipe. -print-multi-lib is asked rather than a test
    compile because registration happens at import time, on every command.

    It answers for the C runtime only. The 32-bit libstdc++ headers are a
    separate package (g++-multilib), and a host with one and not the other
    fails at the compile step with the compiler's own error, which names the
    missing header - clear enough not to be worth a second probe here.
    """
    out = subprocess.run(["gcc", "-print-multi-lib"], capture_output=True,
                         text=True)
    return any(line.startswith("32;") or ";@m32" in line
               for line in out.stdout.splitlines())


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


def _register_gcc():
    # Host-gated, unlike the other two. "gcc" on PATH on a Windows runner is
    # MSYS2's or Strawberry Perl's and targets a PE, so registering it here
    # would put a toolchain called linux_x64 in front of a reader that cannot
    # produce an ELF at all. Nothing would build from it - the MSVC leg
    # selects recipes by what they declare - but available_toolchains() would
    # be stating something untrue on every run of `list`.
    if os.name != "posix" or sys.platform.startswith("darwin"):
        return
    major = _detect_gcc_major()
    if major is None:
        return
    architectures = [("x64", 64)]
    if _has_multilib():
        architectures.append(("x86", 32))
    for arch, bitness in architectures:
        toolchain = _gcc(arch, bitness, major)
        _TOOLCHAINS[toolchain.id] = toolchain
        # Two version-less spellings, both meaning this toolchain.
        #
        # "gcc_x64" is the one the id folds onto by dropping its version
        # digits, which is the rule build_corpus._normalise_toolchain and
        # refresh_provenance._toolchain_of both apply to read a slug; leaving
        # it unregistered would make the concrete id an illegal thing for a
        # recipe to declare, which it is not for mingw or msvc.
        #
        # "linux_x64" is the one recipes use and the one that says what is
        # actually different about this toolchain - not the compiler, which
        # is the same GCC the mingw cross compilers are built from, but the
        # target: glibc and ELF instead of Windows and PE.
        _TOOLCHAINS["gcc_%s" % arch] = toolchain
        _TOOLCHAINS["linux_%s" % arch] = toolchain


_register_mingw()
_register_msvc()
_register_gcc()


# Alias prefixes that name the same toolchain as a versioned id's prefix, for
# the two callers that have only a recorded id or a filename to go on and
# cannot ask this host what it has registered. Keyed the way those callers
# read an id: strip the version digits, then fold.
ALIAS_PREFIXES = {"gcc": "linux"}


def canonical_alias(toolchain_id):
    """Fold any spelling of a toolchain onto the alias recipes declare.

    ``mingw13_x86`` and ``mingw_x86`` are the same toolchain and always were,
    which a version-digit strip handles on its own. ``gcc13_x64``,
    ``gcc_x64`` and ``linux_x64`` are the same toolchain too, and that one
    needs the table above: the id is named after the compiler and the alias
    after the target, so no rule over the string alone relates them.

    Anything unrecognised comes back with its digits stripped and nothing
    else done to it, which is what every caller here did before.
    """
    folded = re.sub(r"^([a-z]+)\d+_", r"\1_", toolchain_id)
    prefix, _, rest = folded.partition("_")
    if not rest:
        return folded
    return "%s_%s" % (ALIAS_PREFIXES.get(prefix, prefix), rest)


def image_format(toolchain_id):
    """The container a toolchain produces, from an id as a record spells it.

    Either ``"PE"`` or ``"ELF"``; readme.py labels every table row with it.

    Derived from the id rather than recorded beside it so that the ~200
    records this corpus already carries answer the question too: they name
    mingw13_x64 or msvc143_x86 and were all PE, and a field added now would
    have been absent from every one of them and defaulted to something.
    """
    alias = canonical_alias(toolchain_id or "")
    return "ELF" if alias.startswith("linux_") else "PE"


def get_toolchain(toolchain_id) -> Toolchain:
    if toolchain_id not in _TOOLCHAINS:
        raise KeyError("unknown or unavailable toolchain %r, have: %s"
                       % (toolchain_id, ", ".join(sorted(_TOOLCHAINS))))
    return _TOOLCHAINS[toolchain_id]


def available_toolchains() -> List[str]:
    return sorted(_TOOLCHAINS)

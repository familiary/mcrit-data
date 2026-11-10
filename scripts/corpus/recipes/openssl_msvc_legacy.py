"""OpenSSL 1.0.x built with MSVC, and the 3.x releases of the MSVC leg.

Targeted by backlog issue #32 (the 1.0.x branch). openssl_msvc.py covers
1.1.1w only; this adds 1.0.2u, and 3.0.15 and 3.5.8 so that the MSVC axis
spans the same releases as the MinGW one.

**1.0.2u uses a different build system.** There is no ``nmake build_libs``
and no ``Configure``-generated makefile for MSVC before 1.1.0: the flow is
``perl Configure <target>``, ``perl util\\mkfiles.pl >MINFO``, then
``util\\mk1mf.pl`` to write ``ms\\ntdll.mak``, then ``nmake -f ms\\ntdll.mak``.
That is what the release's own ``appveyor.yml`` does for VC-WIN32 (``do_ms``)
and VC-WIN64A (``do_win64a``) with ``no-asm``, and the steps below are those
two batch files spelled out, because ``do_win64a.bat`` does not pass ``no-asm``
to ``mk1mf.pl`` and so would enable the ml64 assembler routes on x64 only.
``no-asm`` is chosen for the reason openssl_msvc.py gives at length: it is the
NASM-free configuration, and the x86 leg has no other. VC-WIN64A needs ``ml64``
for ``ms\\uptable.obj`` (the applink table) whether or not asm is on; ml64 ships
with MSVC.

``perl util/mk1mf.pl`` cannot be run on a Linux host (the file lists use
backslashes: ``no rule for crypto\\constant_time_test``), so the generated
``ntdll.mak`` could not be inspected here. What was read instead is
``util/pl/VC-32.pl``, which sets, for a shared build, ``/MD`` and
``/Ox /O2 /Ob2`` (Win32) or ``/Ox`` (Win64), ``/Zi`` on both compiles and
``/debug`` at link, and writes the DLL link line from ``$(MLFLAGS)`` - a macro
whose value is the literal ``/nologo /subsystem:console /opt:ref /debug
/dll``. So ``MLFLAGS`` is overridden on the nmake command line (a command-line
macro wins over the makefile's), restating all of it with the mandated
``/Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF`` in place of ``/opt:ref``,
which would discard unreferenced functions. ``/dll`` has to stay in it.

The DLLs are ``out32dll\\libeay32.dll`` and ``ssleay32.dll`` on both
bitnesses, with ``libeay32.pdb`` and ``ssleay32.pdb`` beside them (link
/debug without /pdb names the PDB after the image). nmake builds everything,
openssl.exe and the test programs included, as upstream's CI does; only the
two DLLs are taken.

**3.0.15 and 3.5.8** are the openssl_msvc.py recipe unchanged except for the
version. The memory concern in that docstring (``export_reports`` peaked at
9.4 GB for the 13206-function 3.5.8 MinGW libcrypto, on a 15 GB host) applies
to 3.5.8; the runner has 16 GB.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from .openssl_msvc import _CONFIGURE_X64, _CONFIGURE_X86, _NORMALISE

# What the 1.0.x shared link says, with /opt:ref replaced. See docstring.
_MLFLAGS = ('"MLFLAGS=/nologo /subsystem:console /debug /Brepro '
            '/INCREMENTAL:NO /OPT:NOREF /OPT:NOICF /dll"')

_IF64 = 'if "{arch}"=="x64" '
_IF86 = 'if "{arch}"=="x86" '


def _msvc_1_0(version, sha256, url):
    return Recipe(
        family="OpenSSL",
        version=version,
        upstream="https://github.com/openssl/openssl",
        license="OpenSSL / SSLeay",
        source=Source(url=url, sha256=sha256),
        build=[
            BuildStep(_IF86 + "perl Configure VC-WIN32 no-asm"),
            BuildStep(_IF64 + "perl Configure VC-WIN64A no-asm"),
            BuildStep("perl util\\mkfiles.pl >MINFO"),
            # The applink table, which VC-WIN64A needs even with no-asm.
            BuildStep(_IF64 + "perl ms\\uplink-x86_64.pl masm >ms\\uptable.asm"),
            BuildStep(_IF64 + "ml64 -c -Foms\\uptable.obj ms\\uptable.asm"),
            BuildStep(_IF86 + "perl util\\mk1mf.pl dll no-asm VC-WIN32 >ms\\ntdll.mak"),
            BuildStep(_IF64 + "perl util\\mk1mf.pl dll no-asm VC-WIN64A >ms\\ntdll.mak"),
            BuildStep("perl util\\mkdef.pl 32 libeay >ms\\libeay32.def"),
            BuildStep("perl util\\mkdef.pl 32 ssleay >ms\\ssleay32.def"),
            BuildStep("nmake /nologo /f ms\\ntdll.mak " + _MLFLAGS),
            BuildStep("dir out32dll", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="out32dll/libeay32.dll", component="libcrypto",
                     pdb="out32dll/libeay32.pdb"),
            Artifact(path="out32dll/ssleay32.dll", component="libssl",
                     pdb="out32dll/ssleay32.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        requires=["perl"],
        build_flags="/Ox /O2 /Ob2 /MD /Zi (VC-WIN32; /Ox /MD /Zi on VC-WIN64A), "
                    "upstream mk1mf defaults, no-asm; /nologo /subsystem:console "
                    "/debug /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF /dll "
                    "at link, replacing upstream's /opt:ref",
        notes="1.0.x MSVC, built through mk1mf (ms\\ntdll.mak) as the "
              "release's own appveyor.yml does, with no-asm: the only "
              "NASM-free configuration, which drops the hand-written "
              "assembly of the primitives (see openssl_msvc.py for what that "
              "costs) and adds their C fallbacks. The DLLs are libeay32.dll "
              "and ssleay32.dll. Built against the DLL runtime, so the MSVC "
              "C runtime is imported and stays attributed to data/MSVC. "
              "openssl.exe is built by nmake but not taken.",
    )


def _msvc_modern(version, sha256, url):
    return Recipe(
        family="OpenSSL",
        version=version,
        upstream="https://github.com/openssl/openssl",
        license="Apache-2.0",
        source=Source(url=url, sha256=sha256),
        build=[
            BuildStep(_CONFIGURE_X64),
            BuildStep(_CONFIGURE_X86),
            BuildStep("nmake build_libs"),
            BuildStep(_NORMALISE),
            BuildStep("dir", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="libcrypto.dll", component="libcrypto",
                     pdb="libcrypto.pdb"),
            Artifact(path="libssl.dll", component="libssl",
                     pdb="libssl.pdb"),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        requires=["perl"],
        build_flags="/W3 /wd4090 /O2 /MD /Zi /Gs0 /GF /Gy (VC-WIN32 / "
                    "VC-WIN64A release defaults, unmodified), no-asm; "
                    "/nologo /debug /Brepro /OPT:NOREF /OPT:NOICF at link, "
                    "replacing upstream's /nologo /debug",
        notes="Built no-asm, the only configuration that needs no NASM; "
              "openssl_msvc.py describes what that changes (about 5 per cent "
              "of libcrypto's translation units: the primitives' assembly "
              "is absent and their C fallbacks are present). No "
              "dependencies. Built against the DLL runtime, so the MSVC C "
              "runtime is imported and stays attributed to data/MSVC. "
              "openssl.exe is not built.",
    )


RECIPES = {
    "OpenSSL_1.0.2u_msvc": _msvc_1_0(
        "1.0.2u", "ecd0c6ffb493dd06707d38b14bb4d8c2288bb7033735606569d8f90f89669d16",
        "https://www.openssl.org/source/old/1.0.2/openssl-1.0.2u.tar.gz"),
    "OpenSSL_3.0.15_msvc": _msvc_modern(
        "3.0.15", "23c666d0edf20f14249b3d8f0368acaee9ab585b09e1de82107c66e1f3ec9533",
        "https://github.com/openssl/openssl/releases/download/openssl-3.0.15/openssl-3.0.15.tar.gz"),
    "OpenSSL_3.5.8_msvc": _msvc_modern(
        "3.5.8", "a8f84a39918ec6415ce765d9b429d313ba97b8143169c172e734b9514464f5b2",
        "https://github.com/openssl/openssl/releases/download/openssl-3.5.8/openssl-3.5.8.tar.gz"),
}


# The final sweep: 1.0.1u (skipped for want of Windows evidence; 64% PicHash
# overlap with 1.0.2u on ELF) and 1.0.0t (skipped because nothing cites it),
# through the same mk1mf route as 1.0.2u.
RECIPES["OpenSSL_1.0.1u_msvc"] = _msvc_1_0(
    "1.0.1u", "4312b4ca1215b6f2c97007503d80db80d5157f76f8f7d3febbe6b4c56ff26739",
    "https://www.openssl.org/source/old/1.0.1/openssl-1.0.1u.tar.gz")
RECIPES["OpenSSL_1.0.0t_msvc"] = _msvc_1_0(
    "1.0.0t", "5ab6e348c6c2a95d457e7a00e0aa653bfc7eb4df7b24e7c9ab63163ac0299097",
    "https://www.openssl.org/source/old/1.0.0/openssl-1.0.0t.tar.gz")


# 0.9.x for MSVC: the releases' own ms\do_ms.bat sequence (and
# ms\do_win64a.bat for 0.9.8zh x64, the only 0.9.x with a 64-bit Windows
# target), dll no-asm, with the corpus link flags given through MLFLAGS as
# for 1.0.x. 0.9.6 and 0.9.7e have no 64-bit Windows target: x86 only.
def _msvc_09(version, sha256, x64):
    recipe = _msvc_1_0(version, sha256,
                       "https://www.openssl.org/source/old/0.9.x/openssl-%s.tar.gz"
                       % version)
    steps = [BuildStep(_IF86 + "perl Configure VC-WIN32 no-asm"),
             BuildStep("perl util\\mkfiles.pl >MINFO"),
             BuildStep(_IF86 + "perl util\\mk1mf.pl dll no-asm VC-WIN32 >ms\\ntdll.mak")]
    if x64:
        steps[1:1] = [BuildStep(_IF64 + "perl Configure VC-WIN64A no-asm")]
        steps += [BuildStep(_IF64 + "perl ms\\uplink.pl win64a >ms\\uptable.asm"),
                  BuildStep(_IF64 + "ml64 -c -Foms\\uptable.obj ms\\uptable.asm"),
                  BuildStep(_IF64 + "perl util\\mk1mf.pl dll no-asm VC-WIN64A >ms\\ntdll.mak")]
    steps += [BuildStep("perl util\\mkdef.pl 32 libeay >ms\\libeay32.def"),
              BuildStep("perl util\\mkdef.pl 32 ssleay >ms\\ssleay32.def"),
              BuildStep("nmake /nologo /f ms\\ntdll.mak " + _MLFLAGS),
              BuildStep("dir out32dll", allow_failure=True)]
    recipe.build = steps
    recipe.toolchains = ["msvc_x86", "msvc_x64"] if x64 else ["msvc_x86"]
    recipe.notes = recipe.notes.replace("1.0.x MSVC", "0.9.x MSVC").replace(
        "as the release's own appveyor.yml does", "as the release's own "
        "ms\\do_ms.bat does")
    return recipe


RECIPES["OpenSSL_0.9.8zh_msvc"] = _msvc_09(
    "0.9.8zh", "f1d9f3ed1b85a82ecf80d0e2d389e1fda3fca9a4dba0bf07adbf231e1a5e2fd6", True)
RECIPES["OpenSSL_0.9.7e_msvc"] = _msvc_09(
    "0.9.7e", "25121b5dbd2b830929519325e033086ce45861cff2d0000d928f48261b1e0b7c", False)
RECIPES["OpenSSL_0.9.6_msvc"] = _msvc_09(
    "0.9.6", "5215b670c2674df9a642565ea68a67e6d955d8efcca1aa1b4e6a5b4fd2744ee8", False)


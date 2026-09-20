"""VX-API (mcrit-data issue #4) - MSVC only.

A collection of Win32 API-abuse routines. It cannot be built with GCC: a
handful of its 251 sources need ATL, and two use structured exception
handling, which mingw's GCC does not implement. More importantly, every
real-world sighting of this code is MSVC-compiled, so a GCC build would be a
proxy for something nobody ships.

This recipe therefore runs only under MSVC, which in practice means the
windows-2022 GitHub Actions runner (see .github/workflows/). Upstream ships
no static-library or DLL configuration, so the sources are compiled into one
and linked into a DLL with /OPT:NOREF, which keeps routines that nothing
calls - the point here is coverage, not a minimal binary.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# /Zi plus a shared /Fd writes debug info for every translation unit into one
# PDB, which is where MSVC keeps symbols; without it SMDA can only name
# exported functions and this DLL exports none.
# /MD is load-bearing. cl defaults to /MT, which statically links the CRT:
# the first build that way came back 46% MSVC C runtime by function count,
# 924 of them the __crt_stdio_output printf machinery, all of it attributed
# to VX-API and all of it overlapping data/MSVC, which is this corpus's
# reference for exactly that code. With /MD the CRT stays in ucrtbase and
# only import thunks appear. BlackBone's own project already builds this way.
_COMPILE = ('for %f in (VX-API\\*.cpp) do @cl /nologo /c /O2 /MD /Zi /std:c++20 '
            '/EHsc /DUNICODE /D_UNICODE /IVX-API /Fdvxapi.pdb /Fo:obj\\ "%f" '
            '2>nul & rem')

# /FORCE:UNRESOLVED is load-bearing. The sources needing ATL or SEH are
# skipped, so anything referencing them is left unresolved and the link would
# otherwise stop at LNK1120. What is wanted here is the compiled function
# bodies, not a loadable DLL, and /OPT:NOREF keeps routines nothing calls.
# /OPT:NOICF as well as /OPT:NOREF. Identical COMDAT folding is on by
# default in a release link and merges functions with identical bodies,
# so StringConcat and StringCopy came back as one entry. Folding is
# right for a shipping binary and wrong here, where each routine is
# supposed to be its own reference sample.
# /Brepro makes the link reproducible: without it MSVC stamps the PE with
# the build time, so two runs over identical source produce artefacts
# with different digests and provenance records that cannot be compared.
_LINK = ('link /nologo /DLL /DEBUG /Brepro /OPT:NOREF /OPT:NOICF '
         '/FORCE:UNRESOLVED '
         '/PDB:vxapi.pdb /OUT:vxapi.dll obj\\*.obj '
         'ws2_32.lib dnsapi.lib iphlpapi.lib crypt32.lib dbghelp.lib '
         'wtsapi32.lib urlmon.lib powrprof.lib imm32.lib comctl32.lib '
         'wevtapi.lib setupapi.lib wbemuuid.lib shlwapi.lib advapi32.lib '
         'user32.lib shell32.lib ole32.lib oleaut32.lib gdi32.lib '
         'winmm.lib psapi.lib userenv.lib netapi32.lib version.lib')


RECIPES = {
    "VX-API_2.01.015": Recipe(
        family="VX-API",
        version="2.01.015",
        upstream="https://github.com/vxunderground/VX-API",
        license="MIT",
        source=Source(git_url="https://github.com/vxunderground/VX-API.git",
                      git_ref="69e5232de6474a7e698619fe7760dc0e3c292258"),
        build=[
            BuildStep("md obj", allow_failure=True),
            # Sources that need ATL or SEH fail individually; the rest still
            # compile, so the per-file loop tolerates those and the link step
            # is what decides whether enough was produced.
            BuildStep(_COMPILE, allow_failure=True),
            BuildStep(_LINK),
        ],
        artifacts=[Artifact(path="vxapi.dll", component="vxapi.dll",
                            pdb="vxapi.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /MD /Zi /std:c++20",
        notes="A small number of sources need ATL or __try/__except and are "
              "skipped; the rest of the collection is present. Built against "
              "the DLL runtime, so the MSVC C runtime is imported rather than "
              "linked in and stays attributed to data/MSVC. The link uses "
              "/FORCE:UNRESOLVED because references into the skipped sources "
              "cannot resolve - the artefact is reference material, not a "
              "loadable DLL.",
    ),
}

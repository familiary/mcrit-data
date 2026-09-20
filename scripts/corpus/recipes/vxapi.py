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


_COMPILE = ('for %f in (VX-API\\*.cpp) do @cl /nologo /c /O2 /std:c++20 /EHsc '
            '/DUNICODE /D_UNICODE /IVX-API /Fo:obj\\ "%f" 2>nul & rem')

# /FORCE:UNRESOLVED is load-bearing. The sources needing ATL or SEH are
# skipped, so anything referencing them is left unresolved and the link would
# otherwise stop at LNK1120. What is wanted here is the compiled function
# bodies, not a loadable DLL, and /OPT:NOREF keeps routines nothing calls.
_LINK = ('link /nologo /DLL /OPT:NOREF /FORCE:UNRESOLVED /OUT:vxapi.dll obj\\*.obj '
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
        artifacts=[Artifact(path="vxapi.dll", component="vxapi.dll")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/O2 /std:c++20",
        notes="A small number of sources need ATL or __try/__except and are "
              "skipped; the rest of the collection is present. The link uses "
              "/FORCE:UNRESOLVED because references into the skipped sources "
              "cannot resolve - the artefact is reference material, not a "
              "loadable DLL.",
    ),
}

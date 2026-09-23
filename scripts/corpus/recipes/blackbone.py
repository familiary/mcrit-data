"""BlackBone (mcrit-data issue #8) - MSVC only.

A Windows memory-hacking library: process and module management, manual PE
mapping, local and remote hooking, pattern search. It needs ATL and the DIA
SDK, both of which ship with Visual Studio and neither of which exists for
GCC, and its syscall stubs are MASM.

The solution only exposes Debug and Release, both of which build BlackBone as
a static library that SMDA cannot read. The project file itself also carries
a Release(DLL) configuration, so it is built directly - which means
SolutionDir has to be passed explicitly, because the project's OutDir is
defined relative to it and building a .vcxproj on its own would otherwise
resolve it to the project directory.

Release(DLL) statically compiles the vendored AsmJit and rewolf-wow64ext
sources into the same image, so those functions are present in this reference
data under the BlackBone family. That matches what an analyst meets in the
wild - upstream ships no configuration that leaves them out - but it is
recorded in the notes so the attribution is not mistaken for BlackBone's own
code. BeaEngine is different: it is linked through a prebuilt import library,
so only its thunks appear and its code stays in its own DLL.

The kernel driver has its own solution and is not built here: it is
blackbonedrv.py, a separate family, from the same commit. That recipe's
docstring argues the split - the two images share no code, and both recipes
pinning one commit would put two entries on the `(BlackBone, 2023-07-17)`
key that refresh_provenance.py cannot tell apart, since its narrowing is by
toolchain alias and both declare msvc_x64. The ``notes`` below still say the
driver is not built, which is true of the artefacts this family already
holds; correct it in the same commit that imports the driver's data.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_CONFIG = "Release(DLL)"

# The project asks for /std:c++latest, which on v143 implies /permissive-,
# under which ProcessModules.cpp does not compile: it writes
# modName->ptr<std::decay_t<decltype(ustr)>::type>(), and a dependent
# qualified-id in a template argument list still needs "typename" even in
# C++20. Rather than touch upstream source, /permissive is appended through
# AdditionalOptions, which MSBuild emits last so it overrides the implied
# /permissive-. The same file carries /Brepro for the link, without which
# MSVC stamps the PE with the build time and two runs over identical source
# produce artefacts with different digests - the x86 DLL did exactly that
# between two green runs. Nothing else is added; the project's own
# optimization and standard settings are left alone.
_CONFORMANCE = (
    'python -c "'
    "open('conformance.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<AdditionalOptions>/permissive</AdditionalOptions>'"
    "'</ClCompile><Link>'"
    "'<AdditionalOptions>/Brepro</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup></Project>')"
    '"')

# PlatformToolset has to be overridden: the project asks for v142, which the
# windows-2022 runner image does not carry - it ships VS2022 and v143 only.
_MSBUILD = ('msbuild src\\BlackBone\\BlackBone.vcxproj '
            '/p:Configuration="%s" /p:Platform={msbuild_platform} '
            '/p:PlatformToolset=v143 /p:SolutionDir=%%CD%%\\ '
            '/p:ForceImportBeforeCppTargets=%%CD%%\\conformance.props '
            '/m /v:minimal' % _CONFIG)


RECIPES = {
    "BlackBone_2023-07-17": Recipe(
        family="BlackBone",
        version="2023-07-17",
        upstream="https://github.com/DarthTon/Blackbone",
        license="MIT",
        source=Source(git_url="https://github.com/DarthTon/Blackbone.git",
                      git_ref="5ede6ce50cd8ad34178bfa6cae05768ff6b3859b"),
        build=[BuildStep(_CONFORMANCE), BuildStep(_MSBUILD)],
        artifacts=[
            Artifact(path="build\\{msbuild_platform}\\%s\\BlackBone.dll" % _CONFIG,
                     component="BlackBone.dll",
                     pdb="build\\{msbuild_platform}\\%s\\BlackBone.pdb" % _CONFIG),
        ],
        toolchains=["msvc_x86", "msvc_x64"],
        # One Artifact serves both architectures, and the project does not
        # configure them the same way, so both are named. Release(DLL)|Win32
        # asks for Optimization=Full (/Ox) with InlineFunctionExpansion
        # AnySuitable (/Ob2), FavorSizeOrSpeed Speed (/Ot) and
        # BufferSecurityCheck off (/GS-); Release(DLL)|x64 asks for MaxSpeed
        # (/O2) with SDLCheck on (/sdl) and leaves the buffer checks in. The
        # earlier "/O2 for both" was wrong for x86 and silent about the rest.
        # LanguageStandard and the link-time settings matter as much as the
        # /O level for what the artefact looks like: /std:c++latest decides
        # which templates are instantiated, whole-program optimization
        # inlines across translation units, and /OPT:ICF folds identical
        # bodies together - see the notes.
        build_flags="Release(DLL) configuration: x86 /Ox /Ob2 /Ot /GS-, "
                    "x64 /O2 /sdl; both /GL /Gy /Oi /MD /std:c++latest and "
                    "/LTCG /OPT:REF /OPT:ICF at link; /permissive and "
                    "/Brepro appended by this recipe",
        # The x86 named ratio is 0.523, which clears the default
        # min_named_ratio of 0.5 by very little. It is not lowered here: the
        # build does keep symbols, and what drags the ratio down is counted
        # rather than missing, which is what the note explains.
        notes="Release(DLL) links the vendored AsmJit and rewolf-wow64ext "
              "sources into the same image, so functions from those projects "
              "are present here under the BlackBone family; BeaEngine is "
              "imported from its own DLL and is not. The kernel driver is "
              "not built. The project links with EnableCOMDATFolding, i.e. "
              "/OPT:ICF, so routines that compiled to identical bodies are "
              "present once, under whichever name the linker kept; the "
              "VX-API recipe in this repository passes /OPT:NOICF to prevent "
              "exactly that, but here it is upstream's own Release(DLL) "
              "setting and is left alone. Read the x86 function count with "
              "that in mind as well: of its 1953 functions only 1021 carry a "
              "name and only 808 reach ten instructions, because MSVC's "
              "32-bit exception handling emits a small unwind funclet or "
              "handler thunk per scope - 932 of them here, none as long as "
              "ten instructions and 861 of two or three - which SMDA counts "
              "and the PDB does not name. num_functions therefore overstates "
              "usable x86 coverage by roughly a factor of two. The x64 "
              "sample has no such funclets, its exception handling being "
              "table-driven, and is 1759 of 1759 named.",
    ),
}

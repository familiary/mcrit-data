"""Hidden - JKornev/hidden, a WDM filter driver with its own user-mode client.

UNVERIFIED. Nothing here has been compiled: this container has neither MSVC
nor a WDK, so every claim below is read off the source and the project files
rather than measured. The "Open risks" list at the end says which of them
would bite first, the way blackbonedrv.py did before its first round.

What the project is. A Windows kernel-mode driver that registers filesystem
and registry filters and a process-notify callback, and hides or protects
objects matching rules it is given from user mode. Hidden/ holds the driver:
FsFilter.c and RegFilter.c are the two minifilter/CmRegisterCallback halves,
PsMonitor.c, PsRules.c and PsTable.c the process side, ExcludeList.c the rule
store, Configs.c the registry-backed configuration, Device.c the
DeviceIoControl surface described by DeviceAPI.h, and Driver.c the entry
point. HiddenLib/ is a small static library wrapping that ioctl surface,
HiddenCLI/ a command-line client linked against it, HiddenTests/ a test
harness linked against the same library.

Why it is here. The corpus already carries BlackBoneDrv, and the same
argument applies: this is known, published tooling whose compiled code an
analyst will meet in samples, and a reference fingerprint is what lets it be
named rather than re-reverse-engineered. It is disassembled, never loaded.

Which projects are built, and which are not. Hidden.sln carries five
projects. Two are built here:

  Hidden/Hidden.vcxproj       ConfigurationType Driver, DriverType WDM,
                              PlatformToolset WindowsKernelModeDriver10.0
                              -> Hidden.sys
  HiddenCLI/HiddenCLI.vcxproj ConfigurationType Application, toolset v142
                              -> HiddenCLI.exe, statically linked against
                                 HiddenLib.lib through a ProjectReference

Three are not:

  Hidden Package/             ConfigurationType Utility, DriverType Package.
                              Produces no binary at all - it runs Inf2Cat
                              over Hidden.inf to emit Hidden.cat, which is a
                              catalogue, not code. Upstream's README tells
                              you to build this project, and following that
                              advice would drag catalogue signing into CI for
                              zero additional functions. Skipped deliberately;
                              see "Not the package project" below.
  HiddenLib/                  A static library, and .lib is an archive rather
                              than a PE. Its code reaches the corpus anyway,
                              linked into HiddenCLI.exe.
  HiddenTests/                A second consumer of the same HiddenLib, so it
                              would contribute the library's code twice under
                              two slugs and little else.

Not the package project. "Hidden Package" is ConfigurationType Utility with
DriverType Package and an Inf2Cat task, and its only ProjectReference is back
to Hidden. Building Hidden.vcxproj directly gets the .sys without ever
entering the packaging graph, which is why this recipe names the .vcxproj and
not the .sln - building the solution would pull the package project in.
SignMode=Off and SkipPackageVerification=true are passed anyway, as
blackbonedrv.py passes them, because they cost nothing and a WDK that decides
to validate a driver target regardless of packaging is a cheaper thing to
pre-empt than to diagnose from a log.

Platform toolset, and the two halves needing opposite treatment. The kernel
project names WindowsKernelModeDriver10.0, which is the WDK's own toolset
rather than a Visual C++ version, so it must NOT be retargeted - there is no
older-toolset string to replace, exactly as in blackbonedrv.py. The three
user-mode projects name v142, which windows-2022 does not carry; blackbone.py
already retargets v142 -> v143 for the same reason, so HiddenCLI gets
/p:PlatformToolset=v143 and the driver does not. This is the one place where
a single recipe has to pass different toolset properties to two projects, and
it is why there are two msbuild steps rather than one over the solution.

WDK version is not pinned by the project. Neither kernel project declares
WindowsTargetPlatformVersion, so the WDK that gets used is whatever the
runner has - the workflow's probe reported 10.0.26100 for the BlackBoneDrv
round. That means this build is not reproducible across runner images from
the recipe alone, and the resolved version has to be read out of the build
log and recorded. TargetVersion is pinned to Windows10 on the command line
for the same reason blackbonedrv.py pins it.

Zydis is compiled into the driver. Hidden/Disasm/ carries a vendored copy of
Zydis 3.1.0 and Zycore 1.0.0 (ZYDIS_VERSION 0x0003000100000000,
ZYCORE_VERSION 0x0001000000000000), built into the .sys with
ZYCORE_STATIC_DEFINE, ZYDIS_STATIC_DEFINE and ZYAN_NO_LIBC, and used by
KernelAnalyzer.c. Two consequences worth stating rather than discovering
later: a meaningful share of Hidden.sys's functions are Zydis's and not this
project's, and because ZYAN_NO_LIBC changes what Zydis compiles, they will
not necessarily match a Zydis built the ordinary way. The notes say so, and
this is a good argument for adding Zydis as a family in its own right.

x64 only, and not because the project says so. All five projects declare
Debug|Win32, Debug|x64, Release|Win32 and Release|x64, and nothing in the
driver sources refuses x86 the way BlackBoneDrv.h:3 does. The first round
declared both legs on that basis and the x86 leg failed, for a reason that
belongs to the WDK rather than to this project (run 36101417064, job
107964495363):

    WindowsDriver.common.targets(271,5): error :
     'Win32' is not a valid architecture for Kernel mode drivers or UMDF drivers

That is the WDK's own architecture guard, hit during target evaluation - no
cl.exe or link.exe ever ran. WDK 10.0.26100 carries kernel-mode import
libraries for x64 and ARM64 only; the same run's probe lists
Lib\10.0.26100.0\km\arm64 and km\x64 and there is no km\x86 directory at all.
So an x86 kernel driver cannot be built on this runner by any recipe, and this
one is x64 only as a property of the toolchain rather than of the project.

Worth knowing before trusting the probe: it reports the
WindowsKernelModeDriver10.0 toolset PRESENT and lists a Platforms\Win32
directory for it. The toolset directory exists for Win32; the targets file and
the import libraries still refuse it. PRESENT there does not mean buildable.

That decision costs the x86 build of HiddenCLI, which is user-mode and would
very likely have compiled, because toolchains is declared per recipe rather
than per artefact. That is a deliberate trade for now: the user-mode half has
never been built at all - the driver step fails first, so the CLI step has
never run on either leg - and splitting it into its own family on the
BlackBone/BlackBoneDrv pattern is worth doing once it is known to build,
not before. If the x64 CLI comes back healthy, a HiddenCLI family declaring
both legs is the follow-up.

Upstream pins nothing and builds nothing. No .gitmodules, no submodules, no
nuget packages, no Directory.Build.props, no makefile, no CI workflow, and a
README "Building" section that gives GUI steps only. The msbuild command
lines below are this recipe's construction, not upstream's.

Settled by round 1 (run 36101417064), so not risks any more:

  - The x86 driver leg fails, and cannot be made to pass. See "x64 only"
    above. The recipe now declares msvc_x64 alone.

Open risks, in the order they would bite. None of these has been tested yet:
the driver step failed first on the only leg that ran, so nothing below has
ever executed.

  1. The v142 -> v143 retarget on HiddenCLI. blackbone.py does the same
     retarget successfully, but that is a different codebase; C++ that built
     under VS2019 can need a fix or two under v143.
  2. HiddenLib and the pinned OutDir. HiddenCLI links HiddenLib. If that is a
     ProjectReference, msbuild propagates the pinned OutDir/IntDir to it and
     the link resolves. If instead the project names the .lib through
     AdditionalDependencies with an explicit
     $(SolutionDir)$(Platform)\\$(Configuration)\\ path, then pinning OutDir
     moves the library out from under it and the link fails with LNK1104. The
     fix in that case is to stop pinning OutDir for the CLI step only, and
     adjust that artefact's path - never for the driver step, where the pin is
     what keeps upstream's committed output directory out of the corpus.
  3. fltmgr.lib. The driver links $(DDK_LIB_PATH)\\fltmgr.lib explicitly. The
     workflow's probe covers ntoskrnl.lib, hal.lib, wmilib.lib and netio.lib
     but not fltmgr.lib, and round 1 never reached a link step, so its
     presence is still unconfirmed - the string does not appear anywhere in
     that run's log. It is part of the same km lib directory and should be
     there.
  4. /INTEGRITYCHECK is in the driver's AdditionalOptions. It is a link-time
     flag that sets a PE characteristic requiring a signature at load time.
     It does not require signing to link, and nothing here loads the image.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

# Written into the source root and force-imported, so no upstream project
# file is edited. Same mechanism as blackbonedrv.py, with one change: the
# compiler PDB is named $(IntDir)$(ProjectName).compiler.pdb rather than a
# hardcoded stem, because two different projects import this one props file
# and a fixed name would have them writing to each other's PDB.
_PROPS = (
    'python -c "'
    "open('corpus-msvc.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'<ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb"
    "</ProgramDataBaseFileName>'"
    "'<WholeProgramOptimization>false</WholeProgramOptimization>'"
    "'<TreatWarningAsError>false</TreatWarningAsError>'"
    "'</ClCompile><Link>'"
    "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
    "'<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>'"
    "'<OptimizeReferences>false</OptimizeReferences>'"
    "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
    "'<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>'"
    "'<AdditionalOptions>%(AdditionalOptions) /Brepro /INCREMENTAL:NO"
    "</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup></Project>')"
    '"')

# The driver. No PlatformToolset override - the project already names the
# WDK's own toolset. OutDir is pinned to out\ so both projects land in one
# place and neither lands in upstream's $(SolutionDir)$(Platform)\$(Config)\,
# which differs between Win32 and x64 and would need two artefact paths.
# IntDir is split per project so the two compiler PDBs cannot collide.
_MSBUILD_DRV = ('msbuild Hidden\\Hidden.vcxproj '
                '/p:Configuration=Release /p:Platform={msbuild_platform} '
                '/p:TargetVersion=Windows10 /p:SignMode=Off '
                '/p:SkipPackageVerification=true '
                '/p:WholeProgramOptimization=false '
                '/p:OutDir=%CD%\\out\\ /p:IntDir=%CD%\\obj\\drv\\ '
                '/p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props '
                '/m /v:minimal')

# The user-mode client. PlatformToolset IS overridden here, v142 -> v143.
# HiddenLib is built as a ProjectReference of this project and inherits these
# global properties, which is what puts HiddenLib.lib in out\ too; the .lib
# is not collected, its code arrives inside HiddenCLI.exe.
_MSBUILD_CLI = ('msbuild HiddenCLI\\HiddenCLI.vcxproj '
                '/p:Configuration=Release /p:Platform={msbuild_platform} '
                '/p:PlatformToolset=v143 '
                '/p:WholeProgramOptimization=false '
                '/p:OutDir=%CD%\\out\\ /p:IntDir=%CD%\\obj\\cli\\ '
                '/p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props '
                '/m /v:minimal')

# As in blackbonedrv.py: everything before the first semicolon is inherited
# rather than chosen, and this records that rather than inventing a flag
# list. If a build succeeds, the compile line in its log is what this string
# should be rewritten from.
_FLAGS = ("Release|x64. All five of the solution's projects declare Debug and "
          "Release for both Win32 and x64 and the sources refuse neither, but "
          "WDK 10.0.26100 does: WindowsDriver.common.targets rejects Win32 "
          "for kernel-mode drivers outright, and the kit carries km import "
          "libraries for x64 and ARM64 only, with no km\\x86 directory at "
          "all. So the architecture is the toolchain's choice here, not the "
          "project's. The driver is ConfigurationType Driver "
          "with DriverType WDM on the WindowsKernelModeDriver10.0 toolset, "
          "so ntoskrnl.lib, hal.lib and the /GS support library come from "
          "the WDK's property sheets; the project adds "
          "$(DDK_LIB_PATH)\\fltmgr.lib for the filesystem filter and "
          "/INTEGRITYCHECK, a link-time PE characteristic that has no effect "
          "on the code and requires no signing to link. Neither kernel "
          "project declares WindowsTargetPlatformVersion, so the WDK version "
          "is whatever the runner carries rather than anything upstream "
          "pinned, and TargetVersion is pinned to Windows10 on the command "
          "line. The driver compiles Zydis 3.1.0 and Zycore 1.0.0 from "
          "Hidden/Disasm with ZYCORE_STATIC_DEFINE, ZYDIS_STATIC_DEFINE and "
          "ZYAN_NO_LIBC. The user-mode client is retargeted v142 -> v143 "
          "because windows-2022 carries no v142; the driver is not "
          "retargeted, its toolset being the WDK's own rather than a Visual "
          "C++ version. This recipe forces /Zi (DebugInformationFormat "
          "ProgramDatabase) with separate compiler and linker PDBs, a full "
          "/DEBUG, /OPT:NOREF /OPT:NOICF, no whole-program optimization at "
          "either end (/p:WholeProgramOptimization=false plus "
          "LinkTimeCodeGeneration Default), /Brepro, /INCREMENTAL:NO, and "
          "TreatWarningAsError false. Signing is turned off with "
          "SignMode=Off and driver-package validation with "
          "SkipPackageVerification=true, neither of which reaches the "
          "compiler or the linker. RuntimeLibrary is left alone: the driver "
          "has no ucrt to move out of the image, and the client's is "
          "upstream's choice. The Hidden Package project, which runs Inf2Cat "
          "to produce a catalogue and no code, is not built; the binaries "
          "are linked and disassembled, never packaged, signed, installed or "
          "loaded")

_LICENSE = ("No licence of any kind: no LICENSE or COPYING file and no "
            "copyright or licence line in the README or in any source file "
            "of this project. The only licence text anywhere in the "
            "repository belongs to vendored third-party code - "
            "Hidden/Disasm/Zydis and Hidden/Disasm/Zycore are Zydis 3.1.0 "
            "and Zycore 1.0.0, both MIT with per-file headers naming Florian "
            "Bernd and Joel Hoener, and both are compiled into Hidden.sys. "
            "So the driver artefact carries MIT-licensed code inside an "
            "otherwise unlicensed project, and the user-mode client carries "
            "none of it. GitHub's own licence metadata could not be read "
            "from this environment - the API was blocked by the egress proxy "
            "- so this is taken from the source tree itself, which is the "
            "stronger evidence in any case")

RECIPES = {
    "Hidden_2022-07-14": Recipe(
        family="Hidden",
        # HEAD of master, commit 4c60797d, dated 2022-07-14. The repository
        # publishes no tags and no releases, so the commit date is the
        # version the way other unreleased projects in this corpus are
        # versioned.
        version="2022-07-14",
        upstream="https://github.com/JKornev/hidden",
        license=_LICENSE,
        source=Source(
            git_url="https://github.com/JKornev/hidden.git",
            git_ref="4c60797d4bb47ddd40f3b306b4b2344ba7cd4c24"),
        build=[
            BuildStep(_PROPS),
            BuildStep(_MSBUILD_DRV),
            BuildStep(_MSBUILD_CLI),
            # build.py reports a missing artefact by the path it expected and
            # nothing else. /s because a WDK that ignores the pinned OutDir
            # would put the driver one level down in a directory named after
            # the project.
            BuildStep("dir /s out", allow_failure=True),
        ],
        artifacts=[
            # TargetName is $(ProjectName) - neither project declares one -
            # and TargetExt comes from ConfigurationType: .sys for Driver,
            # .exe for Application. OutDir is pinned to out\ above.
            Artifact(path="out\\Hidden.sys",
                     component="Hidden.sys",
                     # The LINKER pdb, pinned by ProgramDatabaseFile in the
                     # props. The compiler pdb is obj\drv\Hidden.compiler.pdb
                     # and must not be named here.
                     pdb="out\\Hidden.pdb"),
            Artifact(path="out\\HiddenCLI.exe",
                     component="HiddenCLI.exe",
                     pdb="out\\HiddenCLI.pdb"),
        ],
        # x64 only, and measured rather than inferred. Round 1 declared both
        # legs - the project offers Win32 and x64 for all five of its projects
        # and no source refuses x86 - and the x86 leg failed in the WDK's own
        # architecture guard before a compiler ran: "'Win32' is not a valid
        # architecture for Kernel mode drivers or UMDF drivers". WDK
        # 10.0.26100 has km import libraries for x64 and ARM64 only. So this
        # matches blackbonedrv.py's single leg for a different reason: that
        # recipe is x64-only because the project is, this one because the kit
        # is. The cost is the x86 HiddenCLI, which is user-mode and would
        # probably have built - see the docstring on splitting it out once the
        # user-mode half is known to build at all.
        toolchains=["msvc_x64"],
        build_flags=_FLAGS,
        # Left at the default True. For HiddenCLI.exe it will do real work -
        # that is an ordinary user-mode C++ image linked against the ucrt,
        # which is exactly what baseline.py measures. For Hidden.sys the
        # honest expectation is that it matches little, for blackbonedrv.py's
        # reason: a .sys carries statically linked kernel runtime, but not
        # the user-mode ucrt/vcruntime the baseline is built from. What the
        # filter cannot recognise stays under this family and the notes say
        # so rather than a False here hiding it.
        drop_crt_glue=True,
        # Left at the default 0.5, with PDBs forced on for both artefacts.
        # Risk 3 in the docstring is HiddenCLI on x86: C++ with exception
        # handling produces 32-bit unwind funclets that carry no name, and
        # blackbone.py's x86 leg lands at 0.523 against this same floor. If a
        # leg comes in under it, that is a finding about the build to record,
        # not a reason to lower the floor.
        notes="A WDM filter driver that hides and protects filesystem "
              "objects, registry keys and processes, together with the "
              "user-mode client that drives it. The driver registers a "
              "filesystem minifilter (FsFilter.c) and a registry callback "
              "(RegFilter.c), watches process creation (PsMonitor.c) against "
              "a rule set (PsRules.c, PsTable.c, ExcludeList.c), reads its "
              "configuration from the registry (Configs.c) and exposes the "
              "whole surface through one DeviceIoControl switch (Device.c, "
              "DeviceAPI.h), entered from Driver.c. Two artefacts, from one "
              "solution: Hidden.sys is the driver, HiddenCLI.exe the "
              "command-line client with HiddenLib statically linked into it - "
              "the .lib itself is an archive rather than a PE and is not "
              "collected separately, so a match on HiddenCLI.exe may be a "
              "match on the library rather than on the client. HiddenTests, "
              "a second consumer of the same library, is not built for that "
              "reason, and Hidden Package is not built because it runs "
              "Inf2Cat to produce a catalogue and emits no code. A large "
              "share of Hidden.sys is not this project's code: "
              "Hidden/Disasm holds a vendored Zydis 3.1.0 and Zycore 1.0.0, "
              "compiled in and called from KernelAnalyzer.c, so any match "
              "landing in the decoder is a match on Zydis. It is built with "
              "ZYAN_NO_LIBC, which changes what Zydis compiles, so those "
              "functions will not necessarily agree with a Zydis built the "
              "ordinary way - a reason to carry Zydis as a family of its own "
              "rather than to read it through this one. The image also "
              "carries whatever kernel-mode runtime the WDK links in, which "
              "the compiler-runtime filter cannot recognise because the "
              "baseline it measures against is a user-mode ucrt/vcruntime "
              "build; those functions are filed under this family and are "
              "not this project's code. The driver is linked and "
              "disassembled, never loaded: it is unsigned, and Hidden.inf "
              "and the Hidden Package project - the two things that would "
              "make it installable - are deliberately left out of the build.",
    ),
}

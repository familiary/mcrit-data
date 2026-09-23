"""BlackBoneDrv (mcrit-data issue #8) - BlackBone's kernel driver. MSVC x64 only.

UNVERIFIED. Nothing here has been compiled: this container has neither MSVC
nor a WDK, so every claim below is read off the source and the project file
rather than measured. The "Open risks" list at the end says which of them
would bite first and what to try next, the way apicallproxy.py named
``/p:DriverType=WDM`` before its first round.

What the project is. The kernel half of DarthTon/Blackbone, whose user-mode
library this repository already builds as the ``BlackBone`` family. The
driver does from ring 0 what the library cannot do from ring 3: it manually
maps an image into another process (MMap.c), injects and queues APCs
(Inject.c, Loader.c), remaps one process's memory into another (Remap.c),
edits VAD nodes and PTEs to hide or reprotect regions (VadRoutines.c,
VadHelpers.c), hooks the SSDT and patches handle-table entries
(Routines.c), and exposes the lot to user mode through a single
DeviceIoControl switch in Dispatch.c. It shares no code with the user-mode
library - see "Family naming" below.

Its own solution, and its own everything. src/BlackBoneDrv/BlackBoneDrv.sln
carries exactly one project, BlackBoneDrv.vcxproj, and the top-level
BlackBone.sln does not reference it at all. That is why blackbone.py builds
the library and stops there.

Which configuration, and why Win10Release. BlackBoneDrv.vcxproj declares
eight Configuration x Platform combinations (lines 4-35) and **every one of
them is x64**; there is no Win32 or ARM configuration anywhere, and
BlackBoneDrv.h:3 makes that explicit with ``#ifdef _M_IX86 / #error "x86
systems are not supported"``. So ``toolchains=["msvc_x64"]``, declared the
way syswhispers.py declares its single leg, with no special case anywhere.

The eight are four OS targets x Debug/Release: Win7, Win8, Win8.1, Win10.
They are not variants of one build - each defines a different ``_WIN*_``
macro (vcxproj lines 168, 184, 199, 220, 234, 249, 260, 270) and
NativeStructs.h:5-15 switches the whole undocumented-structure layout on it,
because EPROCESS, MMVAD and the handle table are laid out differently in
each kernel. Win10Release is the one to build: it is first in upstream's own
CI matrix (.github/workflows/driver.yaml:13), it is the only one whose
structures describe a kernel anyone still runs, and BlackBoneDrv.c:271-273
gates it to build 10240 through 20H1.

The APICallProxy lesson - only one ItemDefinitionGroup carrying the link
libraries, every other configuration failing to link - does **not** apply
here, and that was worth checking rather than assuming. BlackBoneDrv.vcxproj
declares no AdditionalDependencies in any of its eight ItemDefinitionGroups;
the only ``<Link>`` element any of them carries is OutputFile. A WDM driver
project gets ntoskrnl.lib, hal.lib and the /GS support library from the
WindowsKernelModeDriver10.0 property sheets, so all eight configurations are
equally linkable and the choice between them is about which kernel's
structures are compiled in, not about which one links.

Platform toolset. No retargeting. All eight configurations already name
``WindowsKernelModeDriver10.0`` (vcxproj lines 56, 64, 71, 78, 86, 93, 100,
107), which is what the WDK probe found present on run 35855463795 and what
msbuild reported using on APICallProxy's run 35858415869. That is the WDK's
own toolset rather than a Visual C++ toolset version, so the v142 -> v143
retarget blackbone.py needs, and the v140 -> v143 retarget heavensgate2.py
needs, have no counterpart here: there is no older-toolset string to
replace.

Not KMDF. ``<DriverType>WDM</DriverType>`` at vcxproj:50 sits in a Globals
PropertyGroup ahead of Microsoft.Cpp.Default.props, so it applies to all
eight configurations. The image entry point is therefore GsDriverEntry
calling BlackBoneDrv.c's DriverEntry, and no WdfDriverEntry.lib or WdfLdr.lib
is linked. APICallProxy's risk 1 - a KMDF project file over a driver that
includes no WDF header - simply does not exist here, which removes the one
failure that recipe could not settle from source.

139 functions of its own, counted in the source under ``_WIN10_`` rather
than estimated: BlackBoneDrv.c 5, Dispatch.c 1, Inject.c 4, Loader.c 14,
MMap.c 19, NotifyRoutine.c 1, Private.c 13, Remap.c 25, Routines.c 21,
Utils.c 23, VadHelpers.c 4, VadRoutines.c 5, ldrreloc.c 4. Those are the 13
ClCompile items at vcxproj:285-297 and nothing else - no header defines a
function body, so there is no header contribution to add. Two subtractions
are already in that number: Private.c's ZwProtectVirtualMemory is inside
``#if defined(_WIN8_) || defined (_WIN7_)`` (Private.c:469-511) and is not
compiled here, so Private.c contributes 13 of its 14; and VadHelpers.c's
MiInsertNode is commented out in its entirety (VadHelpers.c:345-518), so
that file contributes 4 rather than 5. Everything else the version macros
gate is a statement or a field access inside a function body, not a whole
function.

139 against MIN_USEFUL_FUNCTIONS of 8 clears the floor by a factor of
seventeen, and the CRT-glue drop that is applied first cannot touch it:
``is_glue`` needs both the baseline symbol name and the PicHash to match,
and the baseline is a user-mode ucrt/vcruntime DLL, so nothing named
BBMapUserImage or MiRebalanceNode is a candidate. No ``min_functions``
override is needed or set.

Eight of the 139 are not this project's code, and one of the eight carries a
licence this repository has to state. ldrreloc.c's four functions -
LdrRelocateImage, LdrRelocateImageWithBias, LdrProcessRelocationBlock and
LdrProcessRelocationBlockLongLong - are Windows Research Kernel source,
carrying "Copyright (c) Microsoft Corporation. All rights reserved. You may
only use this code if you agree to the terms of the Windows Research Kernel
Source Code License agreement (see License.txt)" at ldrreloc.c:6-9, and
there is no License.txt anywhere in the tree. VadHelpers.c's four -
MiPromoteNode, MiRebalanceNode, MiRemoveNode and MiFindNodeOrParent - carry
no copyright header at all, but they are the same kernel's Mm AVL routines
verbatim, down to the WRK-style "Routine Description:/Environment: Kernel
mode. The PFN lock is held for some of the tables." comment blocks and the
COUNT_BALANCE_MAX macro that VadHelpers.h:59 defines away to nothing. Both
sets are **in the artefact**, which is why they are in ``license`` and in
``notes`` rather than only here - the same treatment apicallproxy.py gives
wbenny/KSOCKET. apiset.h is also Microsoft's ("Copyright (c) 2008 Microsoft
Corporation", apiset.h:3) but declares structures only and contributes no
code.

Family naming: a separate family, not an Artifact.component under
BlackBone. Two reasons, and the second is mechanical.

First, there is no overlap to share a family with. The user-mode artefact is
a C++ DLL linked /MD against the ucrt, statically carrying vendored AsmJit
and rewolf-wow64ext; this is C compiled /kernel against ntifs.h, with a
different entry point, a different runtime and not one function in common.
Filing them together would tell an analyst matching a BlackBone hit that
kernel-mode code was a plausible source of it.

Second, ``scripts/refresh_provenance.py`` could not tell them apart. It
indexes on ``(artifact.family or recipe.family, recipe.version)``
(refresh_provenance.py:61-64), and both recipes pin the same commit, so both
would be version "2023-07-17". Two candidates for one key sends _resolve
down the narrowing path at refresh_provenance.py:116-146, which separates
candidates by the toolchain alias in the slug - and that cannot separate
these two, because blackbone.py declares msvc_x86 *and* msvc_x64 and this
recipe declares msvc_x64, so an x64 slug matches both. ``narrowed`` would
hold two entries and every x64 record of the family would be reported
Unmatched. A distinct family avoids that rather than working around it.
``python3 scripts/refresh_provenance.py --check`` reports 0 unmatched with
the naming as it stands.

Open risks, in the order they would bite.

1. A structure redefinition against a 2024 WDK. This is the likeliest
   failure by a distance, and it is the one with no clean lever. The
   ``_WIN10_`` path defines two names unguarded that the WDK's own headers
   also define on some versions: ``typedef struct _RTL_AVL_TREE``
   (NativeStructs10.h:24) and ``union _EX_PUSH_LOCK``
   (NativeStructs10.h:31). Neither has an ``#ifndef`` around it, and
   NativeStructs10.h:109 relies on the WDK for ``struct _RTL_BALANCED_NODE``
   in the same breath, which shows the two header sets do meet. If
   ntifs.h's chain declares either name - and ``_EX_PUSH_LOCK`` would clash
   as a *tag kind* mismatch as well, the WDK spelling it a struct - the
   first translation unit dies on C2011 and nothing links.

   Evidence it will not: upstream's own CI built exactly this configuration
   on ``windows-latest`` with no extra properties
   (.github/workflows/driver.yaml:23), and upstream's own README.md:97
   carries a green Driver badge. Evidence it might: that CI last ran at this
   pin, July 2023, against whatever WDK the runner image carried then; the
   probe reports 10.0.26100 today, which is a Windows 11 24H2 WDK and about
   four years newer than anything upstream tested.

   Two fallbacks, in order, and both are properties rather than patches.
   Lower ``/p:TargetVersion`` (Windows8, or drop the property and let the
   empty element at vcxproj:83-84 stand): the WDK guards a good deal of
   ntifs.h behind NTDDI_VERSION, so a lower target can hide the declaration
   that clashes. If that does not do it, switch ``_CONFIG`` to "Win8
   Release" or "Win7 Release" - NativeStructs8.h and NativeStructs7.h use
   ``_MM_AVL_TABLE``/``_MMADDRESS_NODE`` and define neither ``_RTL_AVL_TREE``
   nor ``_EX_PUSH_LOCK``, so the clash cannot arise there at all. That costs
   the Win10 structure layouts, which is a real loss of reference value and
   is why it is second.

2. ``ExAllocatePoolWithTag`` as an error rather than a warning. The driver
   calls it at 20 sites across nine of the 13 sources, and WDKs from
   10.0.22000 on mark it DECLSPEC_DEPRECATED_DDK, which is C4996. Driver
   projects compile /WX by default, so that alone would fail the build.
   TreatWarningAsError is turned off in the props below for exactly this,
   and it changes no emitted code.

3. Whether SMDA reads a .sys. Still expectation rather than measurement:
   PeFileLoader.isCompatible is a bare "MZ" test, bitness comes from the
   COFF machine field, and nothing inspects the native subsystem or the
   driver entry point. APICallProxy will settle this one way or the other
   before or alongside this recipe; neither has a measured .sys yet.

4. The committed prebuilt. src/BlackBoneDrv/bin/x64/Win10Release/ already
   holds a ``BlackBoneDrv10.sys`` that upstream compiled in 2020 and
   committed, and that is precisely where this project's unmodified OutDir
   (vcxproj:154) would put a fresh one. A build that produced nothing would
   then hand the pipeline a four-year-old binary and it would be recorded as
   MSVC 19.44 output. OutDir is pinned away from it below, which is not
   tidiness - it is the difference between an artefact and a fabrication.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Win10Release of the four Release configurations; see the docstring for why
# this one and what to switch to if it will not compile. The spelling has no
# space in it, unlike "Win8.1 Release" and "Win7 Release", which is one less
# quoting hazard on a cmd.exe line.
_CONFIG = "Win10Release"

# Settings forced through a props file imported with
# ForceImportBeforeCppTargets - the technique blackbone.py, apicallproxy.py
# and wowgrail.py use - so that no upstream file is modified. A forced import
# lands just before Microsoft.Cpp.targets, after both the project body and
# the WDK's own property sheets, so an ItemDefinitionGroup here overrides
# each of them. It does not touch <Link><OutputFile>, which the project sets
# at vcxproj:263 and which is wanted as it stands.
#
# DebugInformationFormat is stated rather than inherited. Win10Release's
# ClCompile group (vcxproj:255-261) sets CompileAs, AdditionalIncludeDirectories
# and PreprocessorDefinitions and nothing else - in particular no
# DebugInformationFormat - so whether the compiler emits debug information is
# whatever the WindowsKernelModeDriver10.0 sheets default to. For a driver
# that is almost certainly ProgramDatabase, but "almost certainly" is not a
# basis for a corpus artefact: MSVC keeps symbols in a PDB rather than a COFF
# symbol table, a .sys exports nothing to fall back on, and a build that
# quietly compiled without /Zi would come back as 139 anonymous functions and
# be refused by min_named_ratio with nothing in the log to say why.
#
# ProgramDataBaseFileName and ProgramDatabaseFile are both named and they
# point at different files in different directories. /Fd is the compiler PDB
# and /PDB: the linker PDB; aiming both at one path makes link.exe write the
# file it is reading type information from. $(TargetName) is BlackBoneDrv10
# here - vcxproj:156 appends "10" to the project name - so the linker PDB and
# the .sys keep the same stem and cannot drift apart if that ever changes.
# Artifact(pdb=...) below names the linker one.
#
# OptimizeReferences and EnableCOMDATFolding are turned off, and this is a
# deliberate departure from blackbone.py, which leaves upstream's /OPT:REF
# /OPT:ICF alone for the user-mode DLL. There those are settings upstream
# explicitly chose in BlackBone.vcxproj; here the project states no <Link>
# settings beyond OutputFile in any of its eight configurations, so /OPT:REF
# and /OPT:ICF would be a toolset default nobody chose. /OPT:REF would
# discard whatever the IOCTL switch in Dispatch.c never reaches - Utils.c's
# GenPrologueT/GenEpilogueT/GenCallT/GenSyncT wrappers are the obvious
# candidates - and /OPT:ICF is the sharper of the two: this is C with a great
# many short list- and tree-walking helpers, and folding keeps one body under
# whichever name the linker chose. That is the fold that cost vxapi its
# StringConcat/StringCopy pair.
#
# LinkTimeCodeGeneration is stated as well as WholeProgramOptimization being
# cleared on the command line, because the two reach the link by different
# routes and only the pair together guarantees no /LTCG - the reasoning
# wowgrail.py and callobfuscator.py set out. Thirteen translation units give
# /LTCG plenty of boundaries to inline across, and function boundaries are
# exactly what this corpus records.
#
# RuntimeLibrary is deliberately NOT overridden, for the reason
# apicallproxy.py gives: every user-mode MSVC recipe here replaces /MT with
# /MD so the C runtime stays in ucrtbase.dll and is attributed to data/MSVC,
# and a driver has no such choice - there is no ucrt in kernel mode, and
# forcing /MD would either be ignored or break the link.
#
# TreatWarningAsError false: see risk 2 in the docstring. Twenty
# ExAllocatePoolWithTag call sites against a WDK that deprecates it, under a
# toolset that compiles /WX. It changes no emitted code, only whether a
# warning aborts the build, and it is the same class of adjustment
# blackbone.py makes when it appends /permissive to get this same upstream's
# source through a newer compiler. Drop it if a build shows it is not needed.
#
# /Brepro drops the link timestamp so two runs over identical source give
# identical sha256s; the BlackBone x86 DLL is what found that. It is appended
# after %(AdditionalOptions) rather than replacing it, because a driver link
# is where the toolset plausibly does pass switches that way - /kernel,
# /DRIVER, the native subsystem - and dropping them would be a link failure
# with no obvious cause. The single unpaired "%" is safe on a cmd.exe command
# line; cmd only substitutes a %NAME% pair.
#
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# above do not suppress it - only /OPT:REF|ICF|ORDER do. The project sets no
# LinkIncremental in any of its eight configurations, so it would come from
# an MSBuild default, and an incrementally linked image reaches every
# function through a table of one-instruction jump thunks at five-byte stride
# that SMDA recovers as functions in their own right.
# smdaify.assert_not_incrementally_linked refuses a run of more than 32 of
# them (config.MAX_INCREMENTAL_THUNK_RUN).
_PROPS = (
    'python -c "'
    "open('corpus-msvc.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'<ProgramDataBaseFileName>$(IntDir)BlackBoneDrv.compiler.pdb"
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

# The .sln here, not the .vcxproj - the opposite of what blackbone.py and
# apicallproxy.py do, and for reasons that are specific rather than a change
# of mind. blackbone.py builds the project file because the solution does not
# expose the Release(DLL) configuration it wants; apicallproxy.py builds the
# project file because its solution carries eight projects and a failure in
# any of the seven unwanted ones would take the driver down. Neither applies:
# BlackBoneDrv.sln holds exactly one project (BlackBoneDrv.sln:5) and every
# configuration this recipe might want is declared in it
# (BlackBoneDrv.sln:9-16). What does apply is that this is upstream's own
# verified command line - .github/workflows/driver.yaml:23 runs
# "MSBuild.exe src\BlackBoneDrv\BlackBoneDrv.sln /p:Platform=x64
# /p:Configuration=Win10Release" and nothing else - so building the solution
# removes a whole class of difference from the only build anyone has seen
# succeed. If the solution build misbehaves, BlackBoneDrv.vcxproj takes the
# same properties: OutDir and IntDir are pinned below, which is the only
# thing $(SolutionDir) is used for in this project, so the SolutionDir trap
# blackbone.py documents cannot bite either way.
#
# PlatformToolset is NOT retargeted; see the docstring. All eight
# configurations already name WindowsKernelModeDriver10.0, which is the WDK's
# own toolset rather than a Visual C++ version, and it is either installed or
# the probe said ABSENT and this recipe does not run.
#
# TargetVersion is stated because Win10Release leaves the element empty
# (vcxproj:83-84), which selects nothing rather than selecting a default -
# the same hole APICallProxy had at its line 73. Windows10 is what the
# project's Win10 sibling would mean and what the _WIN10_ structures commit
# to. It is a global property, so a WDK that spelled it differently ignores
# it rather than failing on it; it is also the first thing to lower if
# risk 1 fires.
#
# SignMode=Off because the packaging tail would otherwise go looking for a
# test certificate. A driver needs a signature to load and nothing here loads
# it - this one is linked and disassembled.
#
# SkipPackageVerification=true is belt and braces here rather than
# load-bearing, and the difference is worth recording because on APICallProxy
# it was the whole build. There InfVerif ran BeforeTargets="PreBuildEvent"
# and rejected an INF for not declaring PnpLockdown=1, so nothing compiled at
# all. This tree ships no INF - there is no .inf file anywhere in it and no
# <Inf> item in the project - so the target's own '@(Inf)' != '' condition is
# false and it cannot run; vcxproj:58-109 also sets SupportsPackaging false in
# all eight configurations. The property is passed anyway because it is
# global and free, and because a WDK that synthesised an INF for a Driver
# project would otherwise repeat a failure this repository has already paid
# for once.
#
# /p:WholeProgramOptimization=false is a command-line global property rather
# than a props entry because it is read in a PropertyGroup evaluated before
# Microsoft.Cpp.props, which a forced import is too late to reach. See the
# note above _PROPS for why /LTCG matters here.
#
# OutDir and IntDir are pinned, and risk 4 in the docstring is why. The
# project's own OutDir (vcxproj:154) is
# $(SolutionDir)bin\$(Platform)\$(ConfigurationName)\, which is exactly where
# upstream committed a prebuilt BlackBoneDrv10.sys in 2020. Building into a
# clean directory means a build that produced nothing fails as a missing
# artefact rather than quietly handing the pipeline somebody else's binary.
# It also keeps the compiler PDB out of the linker PDB's directory.
_MSBUILD = ('msbuild src\\BlackBoneDrv\\BlackBoneDrv.sln '
            '/p:Configuration=%s /p:Platform={msbuild_platform} '
            '/p:TargetVersion=Windows10 /p:SignMode=Off '
            '/p:SkipPackageVerification=true '
            '/p:WholeProgramOptimization=false '
            '/p:OutDir=%%CD%%\\out\\ /p:IntDir=%%CD%%\\obj\\ '
            '/p:ForceImportBeforeCppTargets=%%CD%%\\corpus-msvc.props '
            '/m /v:minimal' % _CONFIG)

# Everything before the first semicolon is inherited rather than chosen. The
# project's Win10Release ClCompile group (vcxproj:255-261) states CompileAs,
# an empty AdditionalIncludeDirectories and one preprocessor define, and
# nothing about optimization, warning level, runtime library or debug format;
# its Link group states only OutputFile. So the rest of the compile and link
# line is whatever the WindowsKernelModeDriver10.0 property sheets on the
# runner say, which cannot be named precisely from a container with no WDK in
# it. This records that fact rather than inventing a flag list, and names
# only what the recipe forces. If a build ever succeeds, the compile line in
# its log is what this string should be rewritten from.
_FLAGS = ("Win10Release|x64, the Win10 one of the project's four Release "
          "configurations; it defines _WIN10_, which selects "
          "NativeStructs10.h and with it the Windows 10 EPROCESS, MMVAD and "
          "handle-table layouts. All eight of the project's configurations "
          "are x64 and it carries no Win32 or ARM configuration at all. "
          "ConfigurationType Driver with DriverType WDM on the "
          "WindowsKernelModeDriver10.0 toolset, so ntoskrnl.lib, hal.lib and "
          "the /GS support library come from the WDK's property sheets - the "
          "project declares no AdditionalDependencies in any configuration. "
          "Beyond CompileAs C and the _WIN10_ define the project states no "
          "ClCompile or Link settings, so optimization, warning level, "
          "runtime library and debug format are the toolset's defaults "
          "rather than anything upstream chose. This recipe forces /Zi "
          "(DebugInformationFormat ProgramDatabase) with separate compiler "
          "and linker PDBs, a full /DEBUG, /OPT:NOREF /OPT:NOICF, no "
          "whole-program optimization at either end "
          "(/p:WholeProgramOptimization=false plus LinkTimeCodeGeneration "
          "Default), /Brepro, /INCREMENTAL:NO, and TreatWarningAsError "
          "false; TargetVersion is pinned to Windows10 because the "
          "configuration leaves the element empty, signing is turned off "
          "with SignMode=Off and driver-package validation with "
          "SkipPackageVerification=true, neither of which reaches the "
          "compiler or the linker - the driver is linked and disassembled, "
          "never packaged, signed, installed or loaded. RuntimeLibrary is "
          "left alone: a kernel driver has no ucrt to move out of the image")


RECIPES = {
    # Same pin as blackbone.py, because it is the same repository and the
    # same commit: git_ref 5ede6ce5 is the head of master at the time the
    # user-mode recipe was written, and its commit date is 2023-07-17, which
    # is the version string both recipes use. The registry key differs
    # because the family does - "BlackBone_2023-07-17" is taken.
    "BlackBoneDrv_2023-07-17": Recipe(
        family="BlackBoneDrv",
        version="2023-07-17",
        upstream="https://github.com/DarthTon/Blackbone",
        # The repository's LICENSE is MIT, "Copyright (c) 2015 DarthTon".
        # Two things inside this artefact are not covered by it, and unlike
        # apicallproxy.py's hde64.h - which sits in a project that is not
        # built - both of these are compiled into the .sys.
        license="MIT (Copyright (c) 2015 DarthTon) for the project; two "
                "pieces of the driver are not covered by it and both are in "
                "this artefact. src/BlackBoneDrv/ldrreloc.c is Windows "
                "Research Kernel source, \"Copyright (c) Microsoft "
                "Corporation. All rights reserved.\", usable only under the "
                "Windows Research Kernel Source Code License agreement, "
                "which it points at as \"License.txt\" - a file that does not "
                "exist anywhere in the repository; it contributes "
                "LdrRelocateImage, LdrRelocateImageWithBias, "
                "LdrProcessRelocationBlock and "
                "LdrProcessRelocationBlockLongLong. "
                "src/BlackBoneDrv/VadHelpers.c carries no copyright header "
                "but is the same kernel's Mm AVL code verbatim, comment "
                "blocks and COUNT_BALANCE_MAX macro included, contributing "
                "MiPromoteNode, MiRebalanceNode, MiRemoveNode and "
                "MiFindNodeOrParent. src/BlackBoneDrv/apiset.h is Microsoft's "
                "too (\"Copyright (c) 2008 Microsoft Corporation\") but "
                "declares structures only and contributes no code",
        source=Source(git_url="https://github.com/DarthTon/Blackbone.git",
                      git_ref="5ede6ce50cd8ad34178bfa6cae05768ff6b3859b"),
        build=[
            BuildStep(_PROPS),
            BuildStep(_MSBUILD),
            # build.py reports a missing artefact by the path it expected and
            # nothing else, and no .sys has yet come out of this pipeline at
            # a path anyone has seen. /s because a WDK that ignored
            # SupportsPackaging=false would put the driver one level down, in
            # a directory named after the project.
            BuildStep("dir /s out", allow_failure=True),
        ],
        artifacts=[
            # $(OutDir)$(TargetName)$(TargetExt) - the project's own Link
            # OutputFile (vcxproj:263) - with OutDir pinned to out\ on the
            # command line and TargetName made BlackBoneDrv10 by vcxproj:156,
            # which appends "10" to the project name for both Win10
            # configurations. TargetExt is .sys from ConfigurationType
            # Driver. Upstream's committed bin\x64\Win10Release\ copy has the
            # same name, which is the reason OutDir is pinned away from it.
            Artifact(path="out\\BlackBoneDrv10.sys",
                     component="BlackBoneDrv10.sys",
                     # The LINKER pdb, pinned by ProgramDatabaseFile in the
                     # props as $(OutDir)$(TargetName).pdb. The compiler pdb
                     # is obj\BlackBoneDrv.compiler.pdb and must not be named
                     # here.
                     pdb="out\\BlackBoneDrv10.pdb"),
        ],
        # x64 only, and this one is not a judgement call: all eight of the
        # project's configurations are x64 (BlackBoneDrv.vcxproj:4-35) and
        # BlackBoneDrv.h:3 refuses to compile for _M_IX86 outright.
        # syswhispers.py declares a single leg the same way, with no special
        # case anywhere.
        toolchains=["msvc_x64"],
        build_flags=_FLAGS,
        # Left at the default True, for apicallproxy.py's reasoning rather
        # than syswhispers.py's. syswhispers turns it off because
        # /NODEFAULTLIB means there is genuinely no runtime in the image to
        # drop; that does not transfer. A .sys does carry statically linked
        # runtime - the /GS support the WDK links in, GsDriverEntry - it is
        # simply not the runtime baseline.py measures, which is a user-mode
        # DLL linked against ucrt and vcruntime. So the honest expectation is
        # that the filter matches little or nothing. It is left on rather
        # than turned off because turning it off would assert that
        # expectation and nothing here has measured it, while leaving the
        # default asserts nothing and cannot cost anything: is_glue requires
        # the symbol name as well as the PicHash to match the baseline, so it
        # cannot take a function named BBMapUserImage, and anything it does
        # match - __security_check_cookie is the plausible candidate, its x64
        # body being the same three instructions in both worlds - is MSVC
        # runtime that belongs to data/MSVC. What the filter cannot recognise
        # stays under this family, and the notes say so rather than a False
        # here hiding it.
        drop_crt_glue=True,
        # Left at the default 0.5. The PDB is forced on above and this is C
        # with no exception handling, so there are none of the 32-bit unwind
        # funclets that drag blackbone.py's x86 ratio down to 0.523 - and no
        # x86 leg here in any case. The expectation is that very nearly all
        # 139 functions carry a name; if a build comes back near the floor,
        # that is a finding about the build rather than a reason to lower it.
        notes="The kernel half of BlackBone, in its own solution and sharing "
              "no code with the user-mode library recorded under the "
              "BlackBone family - that one is C++ linked against the ucrt, "
              "this is C compiled against ntifs.h. A WDM driver "
              "(DriverType WDM, not KMDF) that manually maps images into "
              "other processes, injects and queues APCs, remaps one "
              "process's memory into another, edits VAD nodes and PTEs to "
              "hide or reprotect regions, hooks the SSDT and patches "
              "handle-table entries, all reached from user mode through a "
              "single DeviceIoControl switch in Dispatch.c. 139 functions of "
              "its own across 13 translation units, counted in the source "
              "under _WIN10_: BlackBoneDrv.c 5, Dispatch.c 1, Inject.c 4, "
              "Loader.c 14, MMap.c 19, NotifyRoutine.c 1, Private.c 13, "
              "Remap.c 25, Routines.c 21, Utils.c 23, VadHelpers.c 4, "
              "VadRoutines.c 5, ldrreloc.c 4. Eight of the 139 are not this "
              "project's code and are present here under this family: "
              "ldrreloc.c's four Ldr* relocation routines are Windows "
              "Research Kernel source and say so in the file, and "
              "VadHelpers.c's MiPromoteNode, MiRebalanceNode, MiRemoveNode "
              "and MiFindNodeOrParent are the same kernel's Mm AVL code "
              "carried in without a copyright header - so a match on any of "
              "those eight is a match on Windows kernel source rather than "
              "on BlackBone. The build is Win10Release, which defines "
              "_WIN10_ and selects the Windows 10 structure layouts; the "
              "Win7, Win8 and Win8.1 configurations compile the same sources "
              "against different EPROCESS, MMVAD and handle-table "
              "definitions and are not built. The image also carries "
              "whatever kernel-mode runtime the WDK links in, and the "
              "compiler-runtime filter cannot recognise it because the "
              "baseline it measures against is a user-mode ucrt/vcruntime "
              "build; those functions are therefore filed under this family "
              "and are not this project's code. The driver is linked and "
              "disassembled, never loaded: it is unsigned, and loading it "
              "would put an unauthenticated kernel-mode primitive for "
              "cross-process memory remapping and SSDT hooking on the "
              "machine.",
    ),
}

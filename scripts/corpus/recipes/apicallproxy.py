"""APICallProxy (MahmoudZohdy) - a KMDF kernel driver. MSVC x64 only.

PARTLY VERIFIED. One CI round has been spent on this module, run
35858415869, and it moved some of what follows from reasoning to measurement
while leaving the rest exactly where it was.

Verified. The WDK is present and the toolset resolves: msbuild reported
"Building 'APICallProxy' with toolset 'WindowsKernelModeDriver10.0' and the
'Desktop' target platform", which is the probe's PRESENT answer arriving as
a build line rather than as a probe. TargetVersion, SignMode and the forced
props import were all accepted without complaint. The .vcxproj-not-.sln
choice, the pinned OutDir and IntDir and the command line's shape are
therefore sound.

Not verified, and not for want of trying: nothing was compiled and nothing
was linked. The build failed in package validation, ahead of the compiler -
see the note above _MSBUILD for the error, the WDK target that raises it and
the property that turns it off. That failure had not been predicted at all;
the "Open risks" list below predicted a link failure, and the build never
reached the link. So every claim here about what the compile emits, whether
the KMDF entry point resolves, how many functions come back and what SMDA
makes of a .sys remains reasoning from the sources. Risk 1 in particular is
untouched: it is still the most likely next failure, and it is still
unsettled.

What the project is. A driver that exposes the Nt*/Zw* kernel API surface to
user mode through a single DeviceIoControl entry point, so that a user-mode
program can have the *kernel* open the process, write the memory or queue the
APC on its behalf, and the call never appears on the user-mode side where an
EDR's hooks are. main.cpp's APIProxyDeviceControl switches on an IOCTL code
from IOCTLCodes.h and dispatches to one of the APIProxy* routines in the
seven headers beside it.

One artefact, and only one. The solution carries eight projects; seven of
them are user-mode .exe helpers - APCInjection, DisableDSE,
RegisterLoadDriver, WinsockClient, WinsockServer, ReverseShellServer,
ReverseShellClient - holding one to four functions each, which is under
MIN_USEFUL_FUNCTIONS (8) and stays under it, because the floor is applied
after the compiler-runtime drop. They are not a fallback and they are not
combined into one artefact; combining them would invent a binary upstream
does not ship. APICallProxy.sys is the whole of the reference value here.

75 functions of its own, counted in the source rather than estimated:
FileSystem.h 6, General.h 14, Network.h 12, Process.h 4, Registry.h 5,
Thread.h 3, Utility.h 27 and main.cpp 4. (The README row for this project
says "about 71"; 75 is the counted number and the row is the loose one.)
main.cpp is the single ClCompile item and includes all seven headers, each
of which defines its functions at namespace scope rather than declaring
them, so one translation unit carries all 75.

Roughly 25 of those 75 are not this project's code. The socket layer is
wbenny/KSOCKET, carried in by hand rather than by reference, and the
correspondence is exact: Utility.h's KsGetAddrInfo, KsFreeAddrInfo,
KsCreateSocket, KsCloseSocket, KsBind, KsAccept, KsConnect, KsSendRecv,
KsSend and KsRecv keep KSOCKET's own names; APIProxyAsyncContextAllocate,
-Free, -Reset, -CompletionRoutine and -WaitForCompletion are its
KspAsyncContext* helpers renamed; APIProxyAddrInfoToAddrInfoEx,
APIProxyAddrInfoExToAddrInfo, APIProxyFreeAddrInfoUtility and
APIProxyFreeAddrInfoEx are berkeley.c's KspUtil* four; APIProxyhtonl,
-htons, -ntohl and -ntohs are berkeley.c's htonl/htons/ntohl/ntohs, the same
one-line RtlUlongByteSwap/RtlUshortByteSwap bodies; and Network.h's
APIProxyWSAStartup and APIProxyWSACleanup are KsInitialize and KsDestroy
with the WSK registration moved from file scope into a caller-owned struct.
That is recorded in ``notes`` the way blackbone.py records its vendored
AsmJit, because an analyst matching against this family should know which
quarter of it is somebody else's.

MSVC only, and MinGW is not close. PlatformToolset is
WindowsKernelModeDriver10.0, the code uses __try/__except in 35 places, and
it compiles against ntifs.h/ntddk.h/wdm.h/wsk.h and links ntoskrnl.lib,
hal.lib, wmilib.lib, netio.lib and the two KMDF stubs. None of that has a
GCC form. No MinGW recipe is written and none is possible.

Release|x64 and only that. APICallProxy.vcxproj declares eight
Configuration x Platform combinations but carries exactly one
ItemDefinitionGroup, at line 148, conditioned on Release|x64, and that group
is where the link libraries live. Every other configuration would compile
and then fail to link for want of ntoskrnl. The Win32 and ARM/ARM64
configurations would not be wanted anyway: a 32-bit kernel is not a target
anyone builds for now, and the source is x64-only in practice.

Driver signing is not a consideration. A driver must be signed to *load*;
nothing here loads it, it is linked and disassembled. SignMode=Off is passed
so the packaging tail does not go looking for a test certificate.

Open risks, in the order they would bite. All three are still open: the one
failure seen so far was none of them, and is recorded above rather than here
because it is now fixed rather than pending.

1. The KMDF link. The project declares DriverType KMDF and links
   WdfDriverEntry.lib and WdfLdr.lib, which makes FxDriverEntry the image
   entry point, but main.cpp includes no WDF header at all - it is a plain
   WDM driver that fills in DriverObject->MajorFunction by hand. Whether
   FxDriverEntry's references to the KMDF bind information resolve without
   <wdf.h> having been included somewhere is the one thing that could fail
   the link outright, and it cannot be settled here. Upstream presumably
   built this, which is evidence but not proof. If it does fail, the next
   thing to try is /p:DriverType=WDM, which moves the entry point back to
   GsDriverEntry and leaves the two Wdf*.lib entries as unreferenced
   imports.
2. Whether SMDA reads a .sys at all. It should: PeFileLoader.isCompatible
   is a bare "MZ" test, bitness comes from the COFF machine field and the
   sections are mapped generically, so the native subsystem and the driver
   entry point are nothing the loader inspects. That is read off the
   installed SMDA rather than measured on a driver, and no .sys has been
   through this pipeline before, so it is stated as expectation.
3. The WDK's own compile defaults. The project sets no ClCompile
   ItemDefinitionGroup in any configuration, so optimization, warning level
   and debug format all come from the toolset. The ones that matter to this
   corpus are forced below rather than inherited.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# Settings forced through a props file imported with
# ForceImportBeforeCppTargets - the technique blackbone.py, wowgrail.py and
# callobfuscator.py use - so that no upstream file is modified. A forced
# import lands just before Microsoft.Cpp.targets, after the toolset's own
# property sheets, so an ItemDefinitionGroup here overrides both the project
# and the WDK.
#
# DebugInformationFormat is the reason this file exists. APICallProxy.vcxproj
# has no ClCompile ItemDefinitionGroup in any of its eight configurations, so
# whether the compiler emits debug information is whatever the
# WindowsKernelModeDriver10.0 property sheets happen to default to. That
# default is almost certainly ProgramDatabase - a driver that ships without
# symbols cannot be debugged and the WDK knows it - but "almost certainly" is
# not a basis for a corpus artefact: MSVC keeps symbols in a PDB rather than
# in a COFF symbol table, a .sys exports nothing to fall back on, and a build
# that quietly compiled without /Zi would come back as 75 anonymous
# functions and be refused by min_named_ratio with nothing to say why. So it
# is stated. callobfuscator.py had to state it for the opposite reason -
# there the project explicitly asked for None - and the conclusion is the
# same either way.
#
# ProgramDataBaseFileName and ProgramDatabaseFile are both named, and they
# are named at different paths. /Fd is the compiler PDB and /PDB: the linker
# PDB; pointing both at one file makes link.exe write the file it is reading
# type information from. Pinning IntDir apart from OutDir would already
# separate them, but the WDK moves driver output around for packaging and
# this removes the question. Artifact(pdb=...) below names the linker one.
#
# OptimizeReferences and EnableCOMDATFolding are turned off, and here that
# is load-bearing rather than tidy. Nothing calls most of these 75
# functions directly: APIProxyDeviceControl dispatches through a switch, so
# /OPT:REF has live references to follow, but the four byte-order helpers
# are reached only from the socket paths and are two instructions each.
# /OPT:ICF is the sharper problem - APIProxyhtonl and APIProxyntohl have
# byte-identical bodies (both are "return RtlUlongByteSwap(x)"), as do
# APIProxyhtons and APIProxyntohs, so folding would keep one of each pair
# under whichever name the linker chose. That is exactly the fold that cost
# vxapi its StringConcat/StringCopy pair.
#
# LinkTimeCodeGeneration is stated as well as WholeProgramOptimization being
# cleared on the command line, because the two reach the link by different
# routes and only the pair together guarantees no /LTCG - the reasoning
# wowgrail.py and callobfuscator.py set out. It matters more than usual
# here: all 75 functions are in one translation unit, so whole-program
# inlining has no module boundary to stop at and the function boundaries
# this corpus records are exactly what it is licensed to move.
#
# RuntimeLibrary is deliberately NOT overridden, and this is where a kernel
# recipe parts company with every user-mode MSVC recipe in this directory.
# Those replace upstream's /MT with /MD so the MSVC C runtime stays in
# ucrtbase.dll and is attributed to data/MSVC. A driver has no such choice:
# there is no ucrt in kernel mode, the C support a driver gets comes from
# ntoskrnl and from the WDK's own static libraries, and forcing /MD would
# either be ignored or break the link.
#
# TreatWarningAsError false: the WDK turns /WX on for driver projects by
# default, and this is 2022 source going through whatever toolset the runner
# carries. It changes no emitted code - only whether a warning aborts the
# build - and it is the same class of adjustment blackbone.py makes when it
# appends /permissive to get upstream source through a newer compiler. Drop
# it if a build shows it is not needed.
#
# /Brepro drops the link timestamp so two runs over identical source give
# identical sha256s; the BlackBone x86 DLL is what found that. It is appended
# after %(AdditionalOptions) rather than replacing it, which the three
# user-mode recipes using this technique do not bother with: a driver link is
# where the toolset plausibly does pass switches that way - /kernel,
# /DRIVER, the native subsystem - and dropping them would be a link failure
# with no obvious cause. The single unpaired "%" is safe on a cmd.exe command
# line; cmd only substitutes a %NAME% pair.
#
# /INCREMENTAL:NO because /DEBUG implies /INCREMENTAL and the /OPT:NO* forms
# above do not suppress it - only /OPT:REF|ICF|ORDER do. The project sets no
# LinkIncremental in any configuration, so it would come from an MSBuild
# default, and an incrementally linked image reaches every function through a
# table of one-instruction jump thunks at five-byte stride that SMDA recovers
# as functions in their own right. smdaify.assert_not_incrementally_linked
# refuses a run of more than 32 of them (config.MAX_INCREMENTAL_THUNK_RUN),
# and on a 75-function sample such a table would dwarf the subject.
_PROPS = (
    'python -c "'
    "open('corpus-msvc.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'<ProgramDataBaseFileName>$(IntDir)APICallProxy.compiler.pdb"
    "</ProgramDataBaseFileName>'"
    "'<WholeProgramOptimization>false</WholeProgramOptimization>'"
    "'<TreatWarningAsError>false</TreatWarningAsError>'"
    "'</ClCompile><Link>'"
    "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
    "'<ProgramDatabaseFile>$(OutDir)APICallProxy.pdb</ProgramDatabaseFile>'"
    "'<OptimizeReferences>false</OptimizeReferences>'"
    "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
    "'<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>'"
    "'<AdditionalOptions>%(AdditionalOptions) /Brepro /INCREMENTAL:NO"
    "</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup></Project>')"
    '"')

# The .vcxproj directly rather than the .sln, as blackbone.py and wowgrail.py
# do. Building the solution would build all eight projects, and a failure in
# any one of the seven user-mode helpers - none of which is wanted here -
# would take the driver down with it. The project defines no OutDir in terms
# of $(SolutionDir), so nothing is lost by not passing one.
#
# PlatformToolset is NOT retargeted. Every other MSVC recipe here overrides
# v142 to v143 because the runner ships VS2022 only; WindowsKernelModeDriver10.0
# is not a Visual C++ toolset version, it is the WDK's own, and it is either
# installed or the probe said ABSENT and this recipe does not run.
#
# TargetVersion is stated because Release|x64 leaves the element empty
# (APICallProxy.vcxproj:73), which selects nothing rather than selecting a
# default; Windows10 is what the project's other seven configurations ask
# for. SignMode=Off skips Inf2Cat and SignTool: a driver needs a signature to
# load and nothing here loads it. Both are global properties, so if a future
# WDK spells either differently it is ignored rather than fatal.
#
# /p:WholeProgramOptimization=false is a command-line global property rather
# than a props entry because it is read in a PropertyGroup evaluated before
# Microsoft.Cpp.props, which a forced import is too late to reach. See the
# note above _PROPS for why /LTCG matters on a one-translation-unit driver.
#
# OutDir and IntDir are pinned rather than inherited. The WDK's defaults put
# a driver's link output and its packaged copy in different places, and the
# package directory is named after the project, so inheriting them means
# guessing at the artefact path from a container that has no WDK to look at.
# Pinning also keeps the compiler PDB out of the linker PDB's directory.
#
# SkipPackageVerification=true is what CI run 35858415869 was spent finding
# out, and it is not optional. Without it the build gets no further than
#
#   APICallProxy.inf(5-5): error 1324: [Version] section should specify
#     PnpLockdown=1 to prevent external apps from modifying installed
#     driver files.
#
# and exits 1 having compiled nothing at all - the log goes straight from
# StampInf's two "Stamping" lines to that error, with no ClCompile output,
# which at /v:minimal is how a compile that did not happen looks.
#
# The mechanism is in the WDK's own WindowsDriver.Common.targets, read at
# 10.0.26100.0, the version the runner's probe reports:
#
#   <Target Name="InfVerif" Condition="'@(Inf)' != '' ..."
#           AfterTargets="StampInf" BeforeTargets="PreBuildEvent">
#     <DPVerifierTask Condition="'@(InfItems)' != ''
#                      and '$(SkipPackageVerification)' != 'true' ..." />
#
# BeforeTargets="PreBuildEvent" is why nothing compiled: package validation
# runs ahead of the whole compile-and-link chain, so an INF that upstream
# wrote in 2022 to pre-PnpLockdown rules fails the project before the driver
# is ever built. SkipPackageVerification is the only condition on the task,
# and it gates all three of its version-selected invocations.
#
# Skipping it is right rather than merely expedient. PnpLockdown is an
# install-time directive about who may overwrite a driver file on a running
# system; this recipe links a .sys and disassembles it and installs nothing,
# so the check has no subject here. The alternative would be adding
# PnpLockdown=1 to upstream's INF, which is patching upstream source to
# satisfy a rule that does not apply. It is a global property, so a WDK that
# spelled it differently would ignore it rather than fail on it, which is the
# same reasoning TargetVersion and SignMode are passed under.
_MSBUILD = ('msbuild APICallProxy\\APICallProxy\\APICallProxy.vcxproj '
            '/p:Configuration=Release /p:Platform={msbuild_platform} '
            '/p:TargetVersion=Windows10 /p:SignMode=Off '
            '/p:SkipPackageVerification=true '
            '/p:WholeProgramOptimization=false '
            '/p:OutDir=%CD%\\out\\ /p:IntDir=%CD%\\obj\\ '
            '/p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props '
            '/m /v:minimal')

# Everything before the semicolon is inherited rather than chosen: the
# project states no ClCompile settings at all, in any configuration, so the
# compile runs on WindowsKernelModeDriver10.0's defaults. Naming them
# precisely is not possible from here - they are whatever the runner's WDK
# property sheets say - so this records that fact rather than inventing a
# flag list, and names only what this recipe forces. If a build ever
# succeeds, the compile line in its log is what this string should be
# rewritten from.
_FLAGS = ("Release|x64, the project's only configuration carrying link "
          "libraries: netio.lib, ntoskrnl.lib, hal.lib, wmilib.lib, "
          "$(KernelBufferOverflowLib) and KMDF's WdfLdr.lib and "
          "WdfDriverEntry.lib. The project sets no ClCompile settings in any "
          "configuration, so optimization, warning level and runtime library "
          "are the WindowsKernelModeDriver10.0 toolset's defaults rather "
          "than anything upstream chose. This recipe forces /Zi "
          "(DebugInformationFormat ProgramDatabase) with separate compiler "
          "and linker PDBs, a full /DEBUG, /OPT:NOREF /OPT:NOICF, no "
          "whole-program optimization at either end "
          "(/p:WholeProgramOptimization=false plus LinkTimeCodeGeneration "
          "Default), /Brepro, /INCREMENTAL:NO, and TreatWarningAsError "
          "false; signing is turned off with SignMode=Off and driver-package "
          "INF validation with SkipPackageVerification=true, neither of which "
          "reaches the compiler or the linker - the driver is linked and "
          "disassembled, never packaged or installed. RuntimeLibrary is "
          "left alone - a kernel driver has no ucrt to move out of the image")


RECIPES = {
    # No tags exist upstream - "git tag" on the clone is empty - so the pin is
    # the full 40-char commit hash of main and the version string is that
    # commit's date, the same convention wowgrail.py uses.
    "APICallProxy_2022-12-09": Recipe(
        family="APICallProxy",
        version="2022-12-09",
        upstream="https://github.com/MahmoudZohdy/APICallProxy",
        # LICENSE is the MIT text, "Copyright (c) 2022 MahmoudZohdy". Two
        # things in the tree are not covered by it and neither carries terms
        # of its own here, which is what this field has to say and the
        # README's licence column could not:
        #
        #  - the socket layer in APICallProxy/Utility.h and Network.h is
        #    wbenny/KSOCKET. That project is itself MIT ("Copyright (c) 2019
        #    Petr Benes", LICENSE.txt), so there is no licence conflict, but
        #    its copyright line is not reproduced anywhere in this tree - the
        #    only acknowledgement is a bare URL in the README's Reference
        #    section. This code IS in the artefact.
        #  - APICallProxy/DisableDSE/hde64.h is Vyacheslav Patkov's Hacker
        #    Disassembler Engine 64, carrying "Copyright (c) 2008-2009,
        #    Vyacheslav Patkov. All rights reserved." and no grant of
        #    permission at all. It is NOT in this artefact - DisableDSE is
        #    one of the seven user-mode projects, which are not built - but
        #    it is recorded because it is part of what this repository
        #    redistributes.
        license="MIT (Copyright (c) 2022 MahmoudZohdy); the Ks*/WSK socket "
                "layer in APICallProxy/Utility.h and Network.h is derived "
                "from wbenny/KSOCKET, itself MIT (Copyright (c) 2019 Petr "
                "Benes) but reproduced here without its copyright line or "
                "licence text, credited only by URL in the README's "
                "Reference section; APICallProxy/DisableDSE/hde64.h is "
                "Vyacheslav Patkov's Hacker Disassembler Engine 64, "
                "\"Copyright (c) 2008-2009 ... All rights reserved\" with no "
                "licence grant in the tree - it is not in this artefact, "
                "DisableDSE being one of the user-mode projects that are not "
                "built",
        source=Source(git_url="https://github.com/MahmoudZohdy/APICallProxy.git",
                      git_ref="3a897e36a3f974d971c2d3dab63c296ac287cb91"),
        build=[
            BuildStep(_PROPS),
            BuildStep(_MSBUILD),
            # build.py reports a missing artefact by the path it expected and
            # nothing else. The WDK's packaging step copies driver output
            # into a subdirectory named after the project, and which of the
            # two paths holds the .sys and its PDB has not been observed from
            # here, so this puts the whole tree into the log the workflow
            # prints on failure. /s because the interesting copy may be one
            # level down.
            BuildStep("dir /s out", allow_failure=True),
        ],
        artifacts=[
            # The linker writes $(OutDir)$(TargetName)$(TargetExt), and
            # TargetName defaults to the project name with no <TargetName>
            # element present. If the WDK's packaging moves it, the "dir /s"
            # step above says where to.
            Artifact(path="out\\APICallProxy.sys",
                     component="APICallProxy.sys",
                     # The LINKER pdb, pinned by ProgramDatabaseFile in the
                     # props; the compiler pdb is obj\APICallProxy.compiler.pdb
                     # and must not be named here.
                     pdb="out\\APICallProxy.pdb"),
        ],
        # x64 only; see the module docstring. Release|x64 is the only
        # configuration that links, and SysWhispers declares a single leg the
        # same way with no special case anywhere.
        toolchains=["msvc_x64"],
        build_flags=_FLAGS,
        # Left at the default True, deliberately, and the reasoning is not
        # the one syswhispers.py uses.
        #
        # There it is turned off because /NODEFAULTLIB means there is
        # genuinely no runtime in the image to drop. That does not transfer
        # here: a .sys does carry statically linked runtime - the /GS support
        # from $(KernelBufferOverflowLib), GsDriverEntry or FxDriverEntry,
        # whatever the KMDF stub pulls in - it is simply not the runtime
        # baseline.py measures, which is a user-mode DLL linked /MD and /MT
        # against ucrt and vcruntime. So the honest expectation is that the
        # filter matches little or nothing.
        #
        # It is left on rather than turned off because turning it off would
        # assert that expectation, and nothing here has measured it. Leaving
        # the default asserts nothing and cannot cost anything: is_glue
        # requires both the symbol name and the PicHash to match the
        # baseline, so it cannot take a function named APIProxyOpenProcess,
        # and anything it does match - __security_check_cookie is the
        # plausible candidate, its x64 body being the same three
        # instructions in both worlds - is MSVC runtime that belongs to
        # data/MSVC. What the filter cannot recognise stays under this
        # family; that is recorded in the notes rather than hidden by a
        # False here.
        drop_crt_glue=True,
        notes="A KMDF kernel driver that proxies the Nt*/Zw* API surface for "
              "user mode over a single DeviceIoControl entry point, so the "
              "call is made by the kernel and never appears on the "
              "user-mode side. 75 functions of its own in one translation "
              "unit - main.cpp includes all seven headers, which define "
              "rather than declare - across FileSystem.h 6, General.h 14, "
              "Network.h 12, Process.h 4, Registry.h 5, Thread.h 3, "
              "Utility.h 27 and main.cpp 4. Roughly 25 of the 75 are "
              "wbenny/KSOCKET's code carried into the tree by hand and are "
              "present here under the APICallProxy family: Utility.h's ten "
              "Ks* routines keep KSOCKET's own names, its five "
              "APIProxyAsyncContext* helpers are KSOCKET's KspAsyncContext* "
              "renamed, its four APIProxyAddrInfo*/FreeAddrInfo* conversions "
              "and its four byte-order helpers are berkeley.c's KspUtil* and "
              "htonl/htons/ntohl/ntohs, and Network.h's APIProxyWSAStartup "
              "and APIProxyWSACleanup are KsInitialize and KsDestroy with "
              "the WSK registration moved into a caller-owned struct. The "
              "remaining APIProxy* routines are thin dispatch wrappers over "
              "those and are this project's own. The seven user-mode .exe "
              "projects in the same solution hold one to four functions "
              "each, below MIN_USEFUL_FUNCTIONS, and are not built. The "
              "image also carries whatever kernel-mode runtime the WDK "
              "links in - the /GS support from KernelBufferOverflowLib, the "
              "KMDF WdfDriverEntry stub - and the compiler-runtime filter "
              "cannot recognise it, because the baseline it measures against "
              "is a user-mode ucrt/vcruntime build; those functions are "
              "therefore filed under this family and are not this project's "
              "code. The driver is linked and disassembled, never loaded: it "
              "is unsigned, and loading it would put an unauthenticated "
              "kernel-mode proxy for NtWriteVirtualMemory and "
              "NtQueueApcThread on the machine.",
    ),
}

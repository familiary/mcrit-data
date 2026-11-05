"""JIEJIE.NET - dcsoft-yyf/JIEJIE.NET, an open-source .NET assembly
obfuscator, and the first managed (CIL) family in the corpus.

Why it is here, and how little that says
----------------------------------------

FortiGuard Labs' QuickFox write-up (4 August 2026,
https://www.fortinet.com/blog/threat-research/quickfox-supply-chain-attack-used-to-deploy-fdmtp-implant)
says of the generation-2 FDMTP loader, Microsoft.ServiceHosting.Tools.dll:
"The generation 2 sample is obfuscated using the JieJie .NET Protector
tool", with a footnote linking this repository. That one sentence is the
whole of the evidence. No code comparison is shown, no hash of the loader is
matched against anything here, and nothing in this recipe was checked
against that sample.

It also matters what this family is. It indexes **the obfuscator's own
code** - the program an operator runs - and not what that program writes
into the assemblies it protects. A loader obfuscated with JIEJIE.NET does not
contain JIEJIE.NET's engine, so this data will not by itself recognise the
QuickFox loader, or any other protected assembly. It recognises JIEJIE.NET.

The one plausible exception is stated as unverified. The engine injects
runtime helper types into every assembly it protects, under namespace
``__DC20211119`` (``JIEJIEHelper``: resource and string decoding;
``JIEJIEPerformanceCounter``). They reach the target as IL text kept in
``CodeTemplate.cs``, but the same types are also compiled into the tool
from ``JIEJIEHelper.cs`` and ``JIEJIEPerformanceCounter.cs``, so 59 of the
artefact's methods are their compiled C#. Whether any of them shares a
PicHash with the injected copy in a protected assembly was not measured, and
there is reason to doubt it for some: at the pinned commit
``SMF_ResStream..ctor`` in the template already reads in a loop that the
C# source does not have (the commit pinned below changed only the
template).

What is pinned, and why that commit
-----------------------------------

The newest tag, ``2022-11-7``, is older than most of the upstream log.
Commit f28e1d2ad78da7160a00197725f8bd42783b9f8c (2026-01-01, "Update
CodeTemplate.cs", the README log's "Fix bug for encryption resource") is the
last commit that touches ``source/``; the three commits after it, up to
6446d7f on 2026-04-09, change README.md only. Which version the QuickFox
operators used is unknown, and this is not a claim that it was this one.

Which project, and why not the .NET Framework one
-------------------------------------------------

``source/`` holds three projects over the same engine:

* ``JIEJIENETForCore.Console.csproj`` - SDK-style, netcoreapp3.1, defines
  DOTNETCORE. Builds with the .NET SDK on Linux. This is what is built.
* ``JIEJIE.NET.Console.csproj`` - the .NET Framework console. Since commit
  2f81218 (2024-10-19) the file in the repository is not a project file at
  all: it begins with an "E-SafeNet LOCK" header, i.e. it was committed
  encrypted by a DLP client. It cannot be built without writing a project
  file of our own, which would be a source modification.
* ``JIEJIE.NET.GUI.csproj`` - legacy-format, .NET Framework 4.0, WinForms.
  Intact, but its resx carries System.Drawing bitmaps, which the .NET SDK's
  MSBuild refuses (MSB3822/MSB3823) without changing how resources are
  generated; it needs full-Framework MSBuild on Windows plus v4.0 reference
  assemblies. Not built. What it would add was measured on upstream's own
  prebuilts: their Framework console shares 641 of its 685 functions of ten
  instructions or more with this recipe's Debug artefact by PicHash, so the
  DOTNETCORE split costs a few dozen bodies, not the family.

Debug and Release, both
-----------------------

Every binary upstream commits (``jiejie.net_pub v1.2022.1.6``,
``v1.2023.11.07``, Framework and Core alike) is a **Debug** build:
DebuggableAttribute 0x107 (optimisations disabled), and about 9,300 ``nop``
instructions in the Core console against 9 in a Release build. Until
2f81218 the Core project did not even declare a Release configuration. So
what an analyst meets as "JIEJIE.NET" is most likely Debug code, and the
two configurations barely share a hash. Measured against upstream's
``v1.2023.11.07`` Core console (848 methods, 693 of ten instructions or
more), whose source is two years older than the pin:

    this recipe, Debug     662 of those 693 PicHashes shared
    this recipe, Release     6 of those 693 PicHashes shared

Both are built, from the project's own two configurations, as separate
components. Upstream's prebuilts are compared against and are not the
artefact.

Function counts
---------------

SMDA's CIL backend emits one function per MethodDef with an IL body, so the
count is checkable against metadata exactly. Both artefacts have 858, and
they partition the same way, read from the TypeDef/NestedClass tables:

    858 = 799 in namespace JIEJIE        (the engine and console; 37 of
                                          them are closure and lambda
                                          methods the C# compiler generated
                                          from the project's own lambdas)
        +  59 in namespace __DC20211119  (43 JIEJIEHelper,
                                          16 JIEJIEPerformanceCounter: the
                                          injected-helper source above)

No ``<PrivateImplementationDetails>`` type is emitted, so there is no
compiler-runtime body (``ComputeStringHash`` and the like) in either
artefact; ``drop_crt_glue`` is off because no managed baseline exists, not
because something is being kept. Instructions: 74,718 Debug, 51,756
Release. Every function is named, by its bare method name.

Build
-----

Unpatched; the project's own configurations. Two properties keep the
sha256 independent of where the build ran, and both are needed. The SDK
turns SourceLink on by default and, finding the checkout's .git, writes its
absolute path into the PDB, whose content hash becomes the assembly's MVID,
COFF timestamp and debug-directory id: two pipeline runs in two work
directories gave two digests. ``-p:ContinuousIntegrationBuild=true`` maps
that root to ``/_/``; ``-p:PathMap`` maps the PDB path written into the
debug directory, which the first does not. With both, two work directories
give one digest. ``-p:OutputPath`` separates the two configurations, which the
project points at the same directory; it does not change the assembly. The
netcoreapp3.1 targeting pack and the three PackageReferences
(Microsoft.Win32.Registry 5.0.0, System.Drawing.Common 5.0.2,
System.Resources.Extensions 5.0.0) come from nuget.org at restore; they are
referenced, not merged, so none of their code is in the artefacts.
netcoreapp3.1 is out of support and the SDK warns about it.

Licence: the repository carries the GPL-2.0 text in LICENSE. The source
headers also say "You can use this software unlimited, but CAN NOT modify
source code anytime", which conflicts with it; nothing here modifies it.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_PROJECT = "JIEJIENETForCore.Console.csproj"

# One restore+build per configuration. Two OutputPaths because upstream's
# project sends both configurations to bin_JIEJIENETForCore.Console\.
_BUILD = [
    BuildStep("dotnet build %s -c %s -nologo -p:ContinuousIntegrationBuild=true "
              "-p:PathMap={source_root}=/_/ -p:OutputPath=corpus-out/%s/"
              % (_PROJECT, configuration, configuration),
              cwd="source")
    for configuration in ("Debug", "Release")
]

_FLAGS = ("dotnet build %s -c %%s (upstream's configuration: DefineConstants "
          "TRACE;DOTNETCORE, AllowUnsafeBlocks, Optimize=%%s), netcoreapp3.1, "
          "-p:ContinuousIntegrationBuild=true -p:PathMap=<checkout>=/_/" % _PROJECT)

_NOTES = (
    "The obfuscator's own code, not its output. FortiGuard Labs (2026-08-04) "
    "says the generation-2 FDMTP loader Microsoft.ServiceHosting.Tools.dll in "
    "the QuickFox supply-chain attack 'is obfuscated using the JieJie .NET "
    "Protector tool'; that sentence is the only evidence, no code comparison "
    "is shown, and nothing here was checked against that sample. A protected "
    "assembly does not contain this engine, so this family recognises "
    "JIEJIE.NET itself. 59 of the 858 methods are namespace __DC20211119 "
    "(JIEJIEHelper, JIEJIEPerformanceCounter), the C# source of the helpers "
    "the tool injects into protected assemblies as IL text; whether they "
    "match the injected copies was not measured. Upstream's committed "
    "binaries are Debug builds, so both configurations are built. Pinned to "
    "f28e1d2, the last commit touching source/; the version the attackers "
    "used is unknown. The .NET Framework projects are not built: the console "
    "project file is committed E-SafeNet-encrypted and the GUI needs "
    "full-Framework MSBuild.")

RECIPES = {
    "jiejie_2026-01-01": Recipe(
        family="JIEJIE.NET",
        version="2026-01-01",
        source=Source(
            git_url="https://github.com/dcsoft-yyf/JIEJIE.NET.git",
            git_ref="f28e1d2ad78da7160a00197725f8bd42783b9f8c"),
        build=_BUILD,
        artifacts=[
            Artifact("source/corpus-out/Debug/JIEJIENETForCore.Console.dll",
                     component="console_debug",
                     build_flags=_FLAGS % ("Debug", "false")),
            Artifact("source/corpus-out/Release/JIEJIENETForCore.Console.dll",
                     component="console_release",
                     build_flags=_FLAGS % ("Release", "true")),
        ],
        toolchains=["dotnet_cil"],
        upstream="https://github.com/dcsoft-yyf/JIEJIE.NET",
        license="GPL-2.0",
        notes=_NOTES,
        # No managed glue baseline exists (crt_glue refuses this toolchain),
        # and none is needed here: the assembly carries no
        # <PrivateImplementationDetails> type, so no compiler-runtime body.
        drop_crt_glue=False,
        build_flags=_FLAGS % ("Debug|Release", "false|true"),
    ),
}

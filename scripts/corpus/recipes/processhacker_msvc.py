"""Process Hacker 2.39: ProcessHacker.exe, peview.exe and the twelve plugin DLLs.

The user-mode half of tracker #66, beside kphlib (kph.c and the phlib code
it reaches) and the KProcessHacker driver. Same pinned commit,
4310de8c43f7600e344b789ffabad79b79878f6a (tag v2.39), GPL-3.0.

Two recipes and two families, for one mechanical reason: build.py fails a
recipe outright when any declared artefact is missing, so one plugin that
does not build would cost ProcessHacker.exe as well. The plugins are their
own DLLs with their own code (they import phlib and the application API
from ProcessHacker.exe through ProcessHacker.lib), so they are filed as
ProcessHackerPlugins; ProcessHacker.exe and peview.exe are ProcessHacker.

Build route, upstream's own (build/internal/dobuildrelease.cmd):
ProcessHacker.sln for phlib and ProcessHacker, build/sdk/makesdk.cmd for the
plugin SDK, then plugins/Plugins.sln. The .vcxproj files are built one by
one with msbuild rather than the solutions, so the fixlib, CustomSignTool
and phlib-test projects are not built.

Changes against upstream's project settings, all on the msbuild command
line or in a forced props file (no source file is edited):

* /p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 - the
  projects name v140 and SDK 10.0.10586.0, neither on windows-2022.
* /MD instead of upstream's /MT (corpus rule: the C runtime is imported and
  stays attributed to data/MSVC), no /GL and no /LTCG (upstream's Release
  sets WholeProgramOptimization and, for the plugins, LTCG), link
  /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO, /Zi with the linker PDB in
  the output directory, TreatWarningAsError off. Everything else -
  /O2, /Gz (StdCall), /GS- for the application, /sdl for the plugins,
  /arch:SSE on x86, subsystem 5.01/5.02 - is upstream's.
* The generated fpshim.c of kphlib_msvc.py: phlib\\format.c calls the
  UCRT-internal __acrt_fp_format, which ucrt.lib does not export, so the
  same generated object (one function, __acrt_fp_format via the exported
  _snprintf_s_l) is linked into ProcessHacker.exe and peview.exe. It is not
  the UCRT's code and is recorded as a generated glue survivor.
* The pre-build event (update_rev.bat, which runs the committed prebuilt
  UpdateGitRevision.exe over the git history) is switched off with
  /p:PreBuildEventUseInBuild=false, and include\\phapprev.h is written with
  the content update_rev.bat itself writes when that tool is absent
  (PHAPP_VERSION_REVISION 0). The version resource therefore says 2.39.0,
  not the release build's revision.
* build/sdk/phapppub_gen.cmd runs the committed prebuilt
  tools\\GenerateHeader\\GenerateHeader\\bin\\Release\\GenerateHeader.exe. The
  recipe compiles that tool from its committed C# source (Program.cs,
  HeaderGen.cs) with the .NET Framework csc.exe over that path first, so no
  prebuilt upstream binary is run; makesdk.cmd is then run as shipped.

Vendored code compiled into ProcessHacker.exe: PCRE2 10.21 (2016-01-12,
ProcessHacker\\pcre, BSD) and Mini-XML 2.8 (ProcessHacker\\mxml, LGPL-2 with
exception); phlib is linked whole as the application's own library. The
OnlineChecks plugin carries json-c (plugins\\OnlineChecks\\json-c).
"""

import base64

from ..recipe import Artifact, BuildStep, Recipe, Source

_REF = "4310de8c43f7600e344b789ffabad79b79878f6a"
_SOURCE = Source(git_url="https://github.com/processhacker/processhacker.git",
                 git_ref=_REF)
_UPSTREAM = "https://github.com/processhacker/processhacker/tree/v2.39"
_LICENSE = "GPL-3.0-or-later (source headers)"

_PROPS_XML = (
    "<Project><PropertyGroup>"
    "<WholeProgramOptimization>false</WholeProgramOptimization>"
    "<LinkIncremental>false</LinkIncremental>"
    "<IntDir>$(OutDir)obj\\$(ProjectName)\\</IntDir>"
    "</PropertyGroup><ItemDefinitionGroup><ClCompile>"
    "<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>"
    "<WholeProgramOptimization>false</WholeProgramOptimization>"
    "<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>"
    "<ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName>"
    "<TreatWarningAsError>false</TreatWarningAsError>"
    "<AdditionalOptions>/GL- %(AdditionalOptions)</AdditionalOptions>"
    "</ClCompile><Link>"
    "<GenerateDebugInformation>true</GenerateDebugInformation>"
    "<OptimizeReferences>false</OptimizeReferences>"
    "<EnableCOMDATFolding>false</EnableCOMDATFolding>"
    "<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>"
    "<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>"
    "<AdditionalDependencies>$(CorpusExtraObj);%(AdditionalDependencies)</AdditionalDependencies>"
    "<AdditionalOptions>/Brepro /INCREMENTAL:NO %(AdditionalOptions)</AdditionalOptions>"
    "</Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib>"
    "</ItemDefinitionGroup></Project>\n")

# Byte for byte the shim kphlib_msvc.py generates.
_SHIM_C = (
    "#include <stdio.h>\n#include <locale.h>\n"
    "errno_t __cdecl __acrt_fp_format(double const* value, char* result, "
    "size_t count, char* scratch, size_t scratch_count, int format, "
    "int precision, unsigned __int64 options, _locale_t locale)\n{\n"
    "    char f[8];\n"
    "    (void)scratch; (void)scratch_count; (void)options;\n"
    "    f[0] = '%'; f[1] = '.'; f[2] = '*'; f[3] = (char)format; f[4] = 0;\n"
    "    return _snprintf_s_l(result, count, _TRUNCATE, f, locale, precision, "
    "*value) < 0 ? 34 : 0;\n}\n")

# What update_rev.bat writes when UpdateGitRevision.exe is not available.
_PHAPPREV_H = ("#ifndef PHAPPREV_H\r\n#define PHAPPREV_H\r\n\r\n"
               "#define PHAPP_VERSION_REVISION 0 \r\n\r\n"
               "#endif // PHAPPREV_H\r\n")


def _write(name, text):
    data = base64.b64encode(text.encode("ascii")).decode("ascii")
    return BuildStep('python -c "import base64;open(r\'%s\',\'wb\')'
                     '.write(base64.b64decode(\'%s\'))"' % (name, data))


_MSB = ("msbuild %s /p:Configuration=Release /p:Platform={msbuild_platform} "
        "/p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 "
        "/p:SolutionDir=%s /p:WholeProgramOptimization=false "
        "/p:PreBuildEventUseInBuild=false /p:BuildProjectReferences=false "
        "/p:ForceImportBeforeCppTargets=%%CD%%\\corpus-um.props%s "
        "/m /v:minimal")

_FPSHIM = " /p:CorpusExtraObj=%CD%\\out\\fpshim.obj"


def _app_steps():
    return [
        _write("corpus-um.props", _PROPS_XML),
        _write("fpshim.c", _SHIM_C),
        _write("ProcessHacker\\include\\phapprev.h", _PHAPPREV_H),
        BuildStep("if not exist out mkdir out"),
        BuildStep(r"cl /nologo /c /O2 /MD /Zi /D_CRT_SECURE_NO_WARNINGS "
                  r"fpshim.c /Foout\fpshim.obj /Fdout\fpshim.pdb"),
        BuildStep(_MSB % (r"phlib\phlib.vcxproj", "%CD%\\", "")),
        BuildStep(_MSB % (r"ProcessHacker\ProcessHacker.vcxproj", "%CD%\\",
                          _FPSHIM)),
    ]


PLUGINS = ("DotNetTools", "ExtendedNotifications", "ExtendedServices",
           "ExtendedTools", "HardwareDevices", "NetworkTools", "OnlineChecks",
           "SbieSupport", "ToolStatus", "Updater", "UserNotes",
           "WindowExplorer")

_GENHDR = (r"%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe /nologo "
           r"/out:tools\GenerateHeader\GenerateHeader\bin\Release\GenerateHeader.exe "
           r"tools\GenerateHeader\GenerateHeader\Program.cs "
           r"tools\GenerateHeader\GenerateHeader\HeaderGen.cs")

_SDK_CHECK = ('python -c "import os,sys;'
              "need=['sdk/include/phapppub.h','sdk/include/phdk.h',"
              "'sdk/include/phappresource.h','sdk/lib/'+('amd64' if '{arch}'=='x64' "
              "else 'i386')+'/ProcessHacker.lib'];"
              "miss=[p for p in need if not os.path.isfile(p)];"
              "print('sdk ok' if not miss else 'sdk missing: '+', '.join(miss));"
              'sys.exit(1 if miss else 0)"')


def _plugin_steps():
    steps = _app_steps() + [
        BuildStep(_GENHDR),
        BuildStep(r"cd build\sdk && makesdk.cmd", allow_failure=True),
        BuildStep(_SDK_CHECK),
    ]
    for plugin in PLUGINS:
        steps.append(BuildStep(
            _MSB % (r"plugins\%s\%s.vcxproj" % (plugin, plugin),
                    "%CD%\\plugins\\", "")))
    steps.append(BuildStep(r"dir /s /b bin\*.dll bin\*.exe", allow_failure=True))
    return steps


_FLAGS = ("v2.39 Release, v143 toolset (projects name v140), SDK 10.0; "
          "upstream's /O2 /Gz /GS- (application) or /sdl (plugins), "
          "/arch:SSE on x86; /MD instead of upstream's /MT; /Zi; no /GL, no "
          "/LTCG; link /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO; "
          "TreatWarningAsError off; pre-build revision step off "
          "(PHAPP_VERSION_REVISION 0)")

RECIPES = {
    "ProcessHacker_2.39_msvc": Recipe(
        family="ProcessHacker", version="2.39", source=_SOURCE,
        upstream=_UPSTREAM, license=_LICENSE,
        toolchains=["msvc_x86", "msvc_x64"],
        build=_app_steps() + [
            BuildStep(_MSB % (r"tools\peview\peview.vcxproj", "%CD%\\",
                              _FPSHIM)),
            BuildStep(r"dir /s /b bin\*.exe bin\*.pdb", allow_failure=True),
        ],
        artifacts=[
            Artifact(path="bin/Release{bitness}/ProcessHacker.exe",
                     component="ProcessHacker.exe",
                     pdb="bin/Release{bitness}/ProcessHacker.pdb"),
            Artifact(path="bin/Release{bitness}/peview.exe",
                     component="peview.exe",
                     pdb="bin/Release{bitness}/peview.pdb"),
        ],
        build_flags=_FLAGS + "; generated fpshim.obj (__acrt_fp_format via "
                    "_snprintf_s_l) linked into both executables",
        notes="ProcessHacker.exe and peview.exe of the pinned v2.39 source, "
              "built from their .vcxproj files with the v143 toolset and a "
              "forced props file (/MD, no /GL or /LTCG, /OPT:NOREF "
              "/OPT:NOICF /Brepro /INCREMENTAL:NO). phlib is statically "
              "linked into both, so they overlap data/kphlib; "
              "ProcessHacker.exe also compiles the vendored PCRE2 10.21 and "
              "Mini-XML 2.8. The generated fpshim.c (one function, "
              "__acrt_fp_format, not the UCRT's code) is linked in as in "
              "kphlib. The pre-build revision step is off and phapprev.h is "
              "upstream's own fallback (revision 0). Linked and disassembled "
              "only, never run.",
    ),
    "ProcessHackerPlugins_2.39_msvc": Recipe(
        family="ProcessHackerPlugins", version="2.39", source=_SOURCE,
        upstream=_UPSTREAM, license=_LICENSE,
        toolchains=["msvc_x86", "msvc_x64"],
        build=_plugin_steps(),
        artifacts=[Artifact(path="bin/Release{bitness}/plugins/%s.dll" % p,
                            component="%s.dll" % p,
                            pdb="bin/Release{bitness}/plugins/%s.pdb" % p)
                   for p in PLUGINS],
        build_flags=_FLAGS + "; plugin SDK from build/sdk/makesdk.cmd, with "
                    "GenerateHeader.exe compiled from its committed C# "
                    "source first",
        notes="The twelve plugins of plugins/Plugins.sln at v2.39 "
              "(SamplePlugin excluded), each its own DLL importing phlib and "
              "the application API from ProcessHacker.exe through "
              "ProcessHacker.lib. ProcessHacker.exe is built first only to "
              "produce that import library (it is recorded by "
              "ProcessHacker_2.39_msvc). OnlineChecks compiles the vendored "
              "json-c. Linked and disassembled only, never loaded.",
    ),
}

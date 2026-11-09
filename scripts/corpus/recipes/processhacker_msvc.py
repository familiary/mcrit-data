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
* /Zc:inline- on x64 only (RemoveUnreferencedCodeData=false).
  ProcessHacker.def exports PhIsExecutingInWow64, which phconfig.h defines
  as a FORCEINLINE function on _WIN64 (global.c defines it only for x86).
  Upstream's /GL build leaves that to link-time code generation; without
  /GL the v143 default /Zc:inline drops the unreferenced inline body from
  every object, and the x64 link failed with "ProcessHacker.def : error
  LNK2001: unresolved external symbol PhIsExecutingInWow64" and LNK1120
  (scratch run 42674927927). /Zc:inline- keeps the compiler emitting it.
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

Measured (scratch run 42678836328, windows-2022, MSVC 19.44.35229, wide-stdio
glue baseline merged on the scratch branch only; the first attempt, run
42674927927, built every x86 artefact and failed x64 on the LNK2001 above).
Kept + removed by the glue baseline = image; then functions of 10+
instructions / distinct PicHashes; every one of those is named (PDB):

    ProcessHacker.exe  x64 3363+204=3567  2371/2291   x86 3150+196=3346  2395/2299
    peview.exe         x64 1096+172=1268   689/667    x86  972+170=1142   654/630

    plugin                 x64 kept+removed=total     x86 kept+removed=total
    DotNetTools            266+135=401   92/89        227+125=352   81/77
    ExtendedNotifications  186+152=338   61/60        180+141=321   66/65
    ExtendedServices       219+134=353   67/67        195+127=322   61/61
    ExtendedTools          606+144=750  247/238       536+147=683  242/229
    HardwareDevices        357+137=494  140/135       332+130=462  142/137
    NetworkTools           215+140=355   46/45        208+130=338   46/45
    OnlineChecks           303+170=473  120/116       293+163=456  132/129
    SbieSupport             65+129=194   13/13         54+121=175   10/10
    ToolStatus             287+131=418   86/84        263+123=386   78/74
    Updater                202+136=338   46/46        196+139=335   47/46
    UserNotes              189+129=318   57/56        166+121=287   54/53
    WindowExplorer         452+135=587  104/102       406+128=534   89/88

The plugin counts are padded by one-instruction import thunks into
ProcessHacker.exe; judge them on the 10+ column. x64 ProcessHacker.exe
carries 327 function names the x86 image lacks, almost all FORCEINLINE
helpers from the phlib and phnt headers (InitializeListHead,
PhCompareString, PhEqualStringRef2, PhAcquireQueuedLockShared, ...) that
/Zc:inline- keeps emitted and /OPT:NOREF keeps linked. They are Process
Hacker's own header code, but an upstream /GL /OPT:REF build would inline
or drop them rather than carry them as separate functions.

Overlap, distinct PicHashes of 10+ instructions:
* data/kphlib (kph.c + reached phlib) is mostly inside ProcessHacker.exe:
  507 of kphlib's 580 x64 hashes (87.4%) and 479 of 575 x86 (83.3%); the
  same 507/479 are in peview.exe. Both link phlib whole-object, kphlib
  links only what kph.c reaches.
* peview.exe against ProcessHacker.exe: 637 of 667 (95.5%) x64, 605 of 630
  (96.0%) x86 - peview is almost entirely phlib.
* The twelve plugins together against ProcessHacker + peview: 26 of 871
  (x64), 9 of 869 (x86); against KProcessHacker: 0.
* data/pcre2 (10.39 and 10.45, MSVC) against ProcessHacker + peview: 5 (x64)
  and 2 (x86) hashes; the vendored PCRE2 is 10.21, five years older.
* x86 against x64, all fourteen artefacts: 1 hash.

Glue survivors (MSVC startup the baseline's console-main EXE probes do not
emit): both executables keep the wWinMain flavour of the VC startup,
x64 / x86 instruction counts and PicHashes: __scrt_common_main_seh 92
11271104747006965853 / 110 15412194987082466279, pre_c_initialization 48
973123914783528695 / 53 7114945967067284721, invoke_main 12
18071112188852371364 / 11 8721064936966453011, wWinMainCRTStartup 4
10082331731223971200 / 2 13477325577764728392,
__scrt_winmain_policy::set_app_type 2 13166271553064441970 / 4
2389322068591341037, __scrt_wide_argv_policy::configure_argv 5
2758688040441024273 / 5 11359937782907268588,
__scrt_wide_environment_policy::initialize_environment 1
6102989692441836808 (both), and on x86 peview a 10-instruction
__scrt_common_main_seh$+0x124 fragment (13184720424441161382). The same
startup hashes survive in the PuTTY GUI tools (putty_msvc.py). Generated:
__acrt_fp_format (fpshim.c) x64 1616887169466728392, x86
5217805753421424442, the same hashes as in kphlib. The plugins keep no CRT
name; their DllMain is Process Hacker's own (142-143 instructions).

validate --deep (sparse tree: kphlib, KProcessHacker and these two
families) reports one FAIL: PicHash 12799676210337176181 (21 instructions)
under ProcessHacker, ProcessHackerPlugins and kphlib as the same symbol
RtlInitUnicodeString. That is phnt's own FORCEINLINE RtlInitUnicodeString
(phnt/include/ntrtl.h:1375, PHNT_NO_INLINE_INIT_STRING not defined) emitted
out of line in the x64 images - Process Hacker code split across three
families of one project, not runtime glue; the classifier cannot tell the
two apart. No shared tooling was changed for it.
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
    "<RemoveUnreferencedCodeData Condition=\"'$(Platform)'=='x64'\">false</RemoveUnreferencedCodeData>"
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
          "/Zc:inline- on x64 (keeps the inline PhIsExecutingInWow64 that "
          "ProcessHacker.def exports); "
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

"""EDRSandblast reusable core and static API, built as an x64 DLL.

CI measurement, SMDA 4.8.0/MCRIT 1.9.0: 375 kept + 92 removed = 467 image functions; 237 have >=10 instructions with 225 unique PicHashes. The x64 reference complements its MinGW-free upstream MSVC build. The printf/wprintf wrapper that survived the earlier import (0x01b000030f8b5bfc) is removed by the wide-stdio glue baseline; no named glue wrapper remains at or above the floor. Vendored SysWhispers2 stubs are included as shipped. DLL is linked and disassembled only.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PROPS = 'python -c "open(\'corpus-msvc.props\',\'w\').write(\'<Project><PropertyGroup><WholeProgramOptimization>false</WholeProgramOptimization><LinkIncremental>false</LinkIncremental><IntDir>$(OutDir)obj\\\\$(ProjectName)\\\\</IntDir></PropertyGroup><ItemDefinitionGroup><ClCompile><RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary><Optimization>MaxSpeed</Optimization><WholeProgramOptimization>false</WholeProgramOptimization><DebugInformationFormat>ProgramDatabase</DebugInformationFormat><ProgramDataBaseFileName>$(IntDir)$(ProjectName).compiler.pdb</ProgramDataBaseFileName><TreatWarningAsError>false</TreatWarningAsError><AdditionalOptions>/GL- %(AdditionalOptions)</AdditionalOptions></ClCompile><Link><GenerateDebugInformation>true</GenerateDebugInformation><OptimizeReferences>false</OptimizeReferences><EnableCOMDATFolding>false</EnableCOMDATFolding><LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration><ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile><AdditionalOptions>/Brepro /INCREMENTAL:NO %(AdditionalOptions)</AdditionalOptions></Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration></Lib></ItemDefinitionGroup></Project>\')"'

RECIPES = {
 "EDRSandblast_2024-08-30_msvc": Recipe(
  family="EDRSandblast", version="2024-08-30",
  source=Source(git_url="https://github.com/wavestone-cdt/EDRSandblast.git", git_ref="0710fad92dbcdf373ed30c536b99012fcd46dbcc"),
  upstream="https://github.com/wavestone-cdt/EDRSandblast", license="CC-BY-4.0 (README); vendored SysWhispers2 stubs",
  toolchains=["msvc_x64"],
  build=[BuildStep(_PROPS),
   BuildStep('msbuild EDRSandblast\\EDRSandblast.vcxproj /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=v143 /p:TargetName=EDRSandblast_Core /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props /m /v:normal'),
   BuildStep('msbuild EDRSandblast_StaticLibrary\\EDRSandblast_StaticLibrary.vcxproj /p:Configuration=Release /p:Platform=x64 /p:PlatformToolset=v143 /p:TargetName=EDRSandblast_API /p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false /p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props /m /v:normal'),
   BuildStep('link /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /OUT:out\\EDRSandblast.dll /PDB:out\\EDRSandblast.pdb /WHOLEARCHIVE:out\\EDRSandblast_Core.lib /WHOLEARCHIVE:out\\EDRSandblast_API.lib kernel32.lib user32.lib gdi32.lib shlwapi.lib winhttp.lib pathcch.lib advapi32.lib dbghelp.lib version.lib shell32.lib ole32.lib oleaut32.lib uuid.lib netapi32.lib ntdll.lib crypt32.lib psapi.lib ucrt.lib vcruntime.lib msvcrt.lib msvcprt.lib'), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/EDRSandblast.dll", component="EDRSandblast.dll", pdb="out/EDRSandblast.pdb")],
  build_flags="Release x64 /O2 /MD /Zi /GL-; whole core + API archives; /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
  notes="Complete upstream core and static API archives, linked whole into a corpus DLL. x64 only per upstream. SysWhispers2 code is vendored and recorded separately from the corpus SysWhispers v1 family. System dependencies are dynamic. No CLI or LSASS example is collected. Linked and disassembled only; never executed or used with a driver.",
 ),
}

# x86 only. The Win32|Release configurations of the pinned project differ from
# x64 in two ways that matter and one that does not (see the recipe docstring):
# EDRSandblast_StaticLibrary has no Win32 IncludePath for EDRSandblast\Includes,
# so the props add it as an include directory; EDRSandblast_Core is configured
# as an Application on Win32, which the command line turns back into a static
# library with /p:ConfigurationType=StaticLibrary.
_PROPS_X86 = _PROPS.replace("<TreatWarningAsError>false</TreatWarningAsError>", "<TreatWarningAsError>false</TreatWarningAsError><AdditionalIncludeDirectories>$(SolutionDir)EDRSandblast\\\\Includes;%(AdditionalIncludeDirectories)</AdditionalIncludeDirectories>")

# Generated placeholders for the nine syscall stubs that upstream ships only as
# SW2_Syscalls_stubs.x64.asm. Each body is `mov eax, 0xC0000002; ret`
# (STATUS_NOT_IMPLEMENTED, cdecl); no upstream code is involved.
_X86_STUB_NAMES = ("NtGetNextProcess NtQueryInformationProcess NtClose NtAllocateVirtualMemory "
                   "NtOpenProcess NtQueryVirtualMemory NtReadVirtualMemory NtCreateFile NtWriteFile")
_X86_STUBS = ('python -c "n=\'' + _X86_STUB_NAMES + '\'.split();'
              'open(\'corpus_sw2_x86_stubs.c\',\'w\').write(\'/* generated by the corpus recipe: placeholders, no upstream code */\\n\'+'
              '\'\'.join(\'long \'+x+\'(){return (long)0xC0000002;}\\n\' for x in n))"')

_MSB86 = ("msbuild {proj} /p:Configuration=Release /p:Platform=Win32 /p:PlatformToolset=v143 /p:TargetName={tn} "
          "/p:SolutionDir=%CD%\\ /p:OutDir=%CD%\\out\\ /p:WholeProgramOptimization=false "
          "/p:ForceImportBeforeCppTargets=%CD%\\corpus-msvc.props {extra}/m /v:normal")

RECIPES["EDRSandblast_2024-08-30_msvc_x86"] = Recipe(
  family="EDRSandblast", version="2024-08-30",
  source=Source(git_url="https://github.com/wavestone-cdt/EDRSandblast.git", git_ref="0710fad92dbcdf373ed30c536b99012fcd46dbcc"),
  upstream="https://github.com/wavestone-cdt/EDRSandblast", license="CC-BY-4.0 (README); vendored SysWhispers2 stubs (x64 only; replaced here by generated placeholders)",
  toolchains=["msvc_x86"],
  build=[BuildStep(_PROPS_X86),
   BuildStep(_X86_STUBS),
   BuildStep(_MSB86.format(proj="EDRSandblast\\EDRSandblast.vcxproj", tn="EDRSandblast_Core", extra="/p:ConfigurationType=StaticLibrary ")),
   BuildStep(_MSB86.format(proj="EDRSandblast_StaticLibrary\\EDRSandblast_StaticLibrary.vcxproj", tn="EDRSandblast_API", extra="")),
   BuildStep('cl /nologo /c /O2 /MD /GL- /Gy /Zi /DUNICODE /D_UNICODE /Fo:out\\corpus_sw2_x86_stubs.obj /Fd:out\\corpus_sw2_x86_stubs.compiler.pdb corpus_sw2_x86_stubs.c'),
   BuildStep('link /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /OUT:out\\EDRSandblast.dll /PDB:out\\EDRSandblast.pdb /WHOLEARCHIVE:out\\EDRSandblast_Core.lib /WHOLEARCHIVE:out\\EDRSandblast_API.lib out\\corpus_sw2_x86_stubs.obj kernel32.lib user32.lib gdi32.lib shlwapi.lib winhttp.lib pathcch.lib advapi32.lib dbghelp.lib version.lib shell32.lib ole32.lib oleaut32.lib uuid.lib netapi32.lib ntdll.lib crypt32.lib psapi.lib ucrt.lib vcruntime.lib msvcrt.lib msvcprt.lib'), BuildStep("dir /s out", allow_failure=True)],
  artifacts=[Artifact(path="out/EDRSandblast.dll", component="EDRSandblast.dll", pdb="out/EDRSandblast.pdb")],
  build_flags="Release Win32 /O2 /MD /Zi /GL-; core built as a static library by /p:ConfigurationType=StaticLibrary; extra include directory EDRSandblast\\Includes from the props; 9 generated placeholder syscall stubs (corpus_sw2_x86_stubs.c, no upstream code); /DLL /NOENTRY /DEBUG /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO. NOT byte-identical to an unmodified upstream build",
  notes="x86 build of the same core and static API archives, linked whole into a corpus DLL. Upstream ships its direct-syscall stubs only as SW2_Syscalls_stubs.x64.asm and excludes it from Release|Win32, so the nine stub symbols (NtGetNextProcess, NtQueryInformationProcess, NtClose, NtAllocateVirtualMemory, NtOpenProcess, NtQueryVirtualMemory, NtReadVirtualMemory, NtCreateFile, NtWriteFile) have no x86 definition. The recipe generates corpus_sw2_x86_stubs.c with nine placeholder functions (each returns STATUS_NOT_IMPLEMENTED) and links it in; the generated stubs carry no upstream code, and this image is NOT byte-identical to an unmodified upstream build. No upstream source file is changed. Linked and disassembled only; never executed.",
)

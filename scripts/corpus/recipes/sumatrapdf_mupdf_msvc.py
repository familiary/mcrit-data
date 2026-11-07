"""SumatraPDF 3.3.3's rendering DLL, pinned by tracker issue #67.

The evidence is structural: the report names an unmodified 3.3.3 viewer
beside a modified libmupdf.dll, without identifying upstream functions.
This recipe builds only the unmodified upstream rendering DLL.

Maintainer decision still outstanding: this DLL embeds MuPDF and its codec,
font and archive dependencies under one family. The 3.3.3 source includes
zlib, libjpeg-turbo, freetype, jbig2dec, openjpeg, lcms2, harfbuzz, mujs,
gumbo, DjVu, WebP and unarr (including bzip2 and LZMA). zlib, bzip2 and LZMA
touch existing corpus families; this recipe does not decide whether that
vendoring depth should be accepted. The issue's licence question is recorded
as a maintainer decision, not an obstacle inferred by the recipe.

The 3.3.3 tag already commits VS2019 projects, unlike the current upstream
VS2022/premake description in the issue. Those projects can be retargeted by
command-line properties without regenerating or patching source. A separate
props file overrides /MT, whole-program optimization and linker folding.
MinGW/Linux MuPDF-direct builds would describe a different component and
remain a separate maintainer choice.

Windows probe 42337199081 built both architectures. x86: 11,176 kept plus
253 removed equals 11,429 image functions (11,019 kept functions named).
x64: 10,696 kept plus 246 removed equals 10,942 (10,670 kept named).
Unique PicHashes at >=10 instructions: x86 8,906; x64 8,145; intersection 2.
Both architectures therefore add code shapes not present in the other.

Overlap against all existing variants in each dependency family, again at
>=10 instructions: libzlib x86 54 / x64 36; bzip2 0 / 17; liblzma 0 / 1.
These are measured vendoring overlaps, not an attribution decision. There
is no MinGW or Linux build of this exact Windows-only upstream DLL here.

Measured runtime survivors: printf x86 PicHash 12296465484064796685 (20
instructions), printf x64 121597203084696572 (25). These inline CRT wrappers
survive the measured baseline; no shared tooling was changed. The x64
printf survivor is the known MSVC baseline gap. The logged compile uses
/Ox /MD without /GL. Link readback confirms /OPT:NOREF /OPT:NOICF /Brepro
/INCREMENTAL:NO and no /LTCG activation (/LTCGOUT names only an output path).
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_PROPS = (
    'python -c "'
    "open('corpus-msvc.props','w').write("
    "'<Project><PropertyGroup><LinkIncremental>false</LinkIncremental>'"
    "'<WholeProgramOptimization>false</WholeProgramOptimization>'"
    "'</PropertyGroup><ItemDefinitionGroup><ClCompile>'"
    "'<RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'<WholeProgramOptimization>false</WholeProgramOptimization>'"
    "'<TreatWarningAsError>false</TreatWarningAsError>'"
    "'</ClCompile><Link>'"
    "'<GenerateDebugInformation>DebugFull</GenerateDebugInformation>'"
    "'<OptimizeReferences>false</OptimizeReferences>'"
    "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
    "'<LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>'"
    "'<AdditionalOptions>/Brepro /INCREMENTAL:NO /DEF:$(MSBuildThisFileDirectory)src\\\\libmupdf.def</AdditionalOptions>'"
    "'</Link><Lib><LinkTimeCodeGeneration>false</LinkTimeCodeGeneration>'"
    "'</Lib></ItemDefinitionGroup></Project>')"
    '"'
)

RECIPES = {
    "sumatrapdf_3.3.3_libmupdf_msvc": Recipe(
        family="MuPDF",
        version="SumatraPDF-3.3.3",
        upstream="https://github.com/sumatrapdfreader/sumatrapdf",
        license="GPL-3.0 / AGPL-3.0 and bundled dependencies",
        source=Source(
            git_url="https://github.com/sumatrapdfreader/sumatrapdf.git",
            git_ref="21678b88191b57ef0d8a4eded97532731ef57f43"),
        build=[
            BuildStep(_PROPS),
            BuildStep(
                'msbuild vs2019\\libmupdf.vcxproj /m:2 /v:normal '
                '/p:Configuration=Release /p:Platform={msbuild_platform} '
                '/p:PlatformToolset=v143 /p:WindowsTargetPlatformVersion=10.0 '
                '/p:WholeProgramOptimization=false '
                '/p:ForceImportBeforeCppTargets="{source_root}\\corpus-msvc.props"'),
        ],
        artifacts=[Artifact(
            path="out\\rel{bitness}\\libmupdf.dll", component="libmupdf",
            pdb="out\\rel{bitness}\\libmupdf.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        requires=["msbuild"],
        build_flags="/Ox /MD; no /GL or /LTCG; /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
        notes="Unmodified SumatraPDF 3.3.3 rendering DLL; bundled dependency attribution remains a maintainer decision in tracker #67.",
    ),
}

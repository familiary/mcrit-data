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

Counts, >=10-instruction PicHash overlaps and measured glue survivors are
pending the scoped Windows probe; this recipe is not completed corpus data.
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
        build_flags="/O2 /MD; no /GL or /LTCG; /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO",
        notes="Unmodified SumatraPDF 3.3.3 rendering DLL; bundled dependency attribution remains a maintainer decision in tracker #67.",
    ),
}

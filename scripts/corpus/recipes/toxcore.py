"""c-toxcore (draft)."""

from ..recipe import Artifact, BuildStep, Recipe, Source

_SODIUM = Source(url="https://download.libsodium.org/libsodium/releases/libsodium-1.0.20.tar.gz",
                 sha256="ebb65ef6ca439333c2bb41a0c1990587288da07f6c7fd07cb3a18cc18d30ce19")

_SODIUM_BUILD = ("mkdir -p sodium-src-{arch} && tar xf {libsodium_src} -C sodium-src-{arch} "
                 "--strip-components=1 && cd sodium-src-{arch} && "
                 "./configure --host={host} --prefix=$PWD/../sodium-{arch} "
                 "--enable-shared --disable-static && make -j$(nproc) && make install")

_CMAKE_COMMON = ("-DCMAKE_BUILD_TYPE=Release -DBUILD_TOXAV=OFF -DENABLE_STATIC=OFF "
                 "-DENABLE_SHARED=ON -DUNITTEST=OFF -DAUTOTEST=OFF -DDHT_BOOTSTRAP=OFF "
                 "-DBOOTSTRAP_DAEMON=OFF -DBUILD_MISC_TESTS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5")

_CMAKE_PE = ("PKG_CONFIG_PATH=$PWD/sodium-{arch}/lib/pkgconfig cmake -S . -B build-{arch} "
             "-DCMAKE_SYSTEM_NAME=Windows -DCMAKE_C_COMPILER={cc} -DCMAKE_CXX_COMPILER={cxx} "
             "-DCMAKE_RC_COMPILER={windres} -DCMAKE_FIND_ROOT_PATH=/usr/{host} "
             + _CMAKE_COMMON)


# Relink without the vendored cmp (see the docstring): cmp.c.obj is dropped from the
# object archive CMake already built, cmp is linked on its own to give an import
# library, and the toxcore link line CMake wrote is run again with it appended.
_SPLIT_PE = ("cd build-{arch} && D=CMakeFiles/toxcore_shared.dir && "
             "{cc} -O3 -shared -o cmp.dll $D/third_party/cmp/cmp.c.obj "
             "-Wl,--out-implib,libcmp.dll.a && {ar} d $D/objects.a cmp.c.obj && "
             "sh -c \"$(tail -n 1 $D/link.txt) libcmp.dll.a\"")


def _mingw(version, ref, cmp=True):
    return Recipe(
        family="c-toxcore", version=version,
        upstream="https://github.com/TokTok/c-toxcore", license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/TokTok/c-toxcore.git", git_ref=ref),
        extra_sources={"libsodium_src": _SODIUM},
        build=[BuildStep(_SODIUM_BUILD), BuildStep(_CMAKE_PE),
               BuildStep("cmake --build build-{arch} -j$(nproc) --target toxcore_shared"),
               *([BuildStep(_SPLIT_PE)] if cmp else []),
               BuildStep("find build-{arch} -name '*.dll'", allow_failure=True)],
        artifacts=[Artifact(path="build-{arch}/libtoxcore.dll", component="libtoxcore.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
    )


_SODIUM_ELF = ("mkdir -p sodium-src-{arch} && tar xf {libsodium_src} -C sodium-src-{arch} "
               "--strip-components=1 && cd sodium-src-{arch} && "
               "./configure --host={host} --prefix=$PWD/../sodium-{arch} "
               "--enable-shared --disable-static && make -j$(nproc) && make install")

_CMAKE_ELF = ("PKG_CONFIG_PATH=$PWD/sodium-{arch}/lib/pkgconfig cmake -S . -B build-{arch} "
              "-DSTRICT_ABI=ON " + _CMAKE_COMMON)

_SPLIT_ELF = ("cd build-{arch} && D=CMakeFiles/toxcore_shared.dir && "
              "{cc} {archflag} -O3 -shared -o libcmp.so $D/third_party/cmp/cmp.c.o && "
              "{ar} d $D/objects.a cmp.c.o && "
              "sh -c \"$(grep -e ' -shared ' $D/link.txt | head -n 1) -L. -lcmp\"")


def _elf(version, ref, cmp=True):
    return Recipe(
        family="c-toxcore", version=version,
        upstream="https://github.com/TokTok/c-toxcore", license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/TokTok/c-toxcore.git", git_ref=ref),
        extra_sources={"libsodium_src": _SODIUM},
        build=[BuildStep(_SODIUM_ELF), BuildStep(_CMAKE_ELF),
               BuildStep("cmake --build build-{arch} -j$(nproc) --target toxcore_shared"),
               *([BuildStep(_SPLIT_ELF)] if cmp else []),
               BuildStep("ls -l build-{arch}", allow_failure=True)],
        artifacts=[Artifact(path="build-{arch}/libtoxcore.so", component="libtoxcore.so")],
        toolchains=["linux_x86", "linux_x64"],
    )


RECIPES = {
    "c-toxcore_0.2.24": _mingw("0.2.24", "v0.2.24"),
    "c-toxcore_0.2.18": _mingw("0.2.18", "v0.2.18"),
    "c-toxcore_0.2.12": _mingw("0.2.12", "v0.2.12", cmp=False),
    "c-toxcore_0.2.24_linux": _elf("0.2.24", "v0.2.24"),
}

# --- MSVC ------------------------------------------------------------------

_PTHREADS = Source(
    url="https://sourceforge.net/projects/pthreads4w/files/"
        "pthreads4w-code-v3.0.0.zip/download",
    sha256="b81136effb7185c77601fe2e0e6ac19bd996912e4814cebdd3010b0fac9e259b")

_PROPS = (
    'python -c "'
    "open('msvcprops.props','w').write("
    "'<Project><ItemDefinitionGroup><ClCompile>'"
    "'<DebugInformationFormat>ProgramDatabase</DebugInformationFormat>'"
    "'</ClCompile><Link>'"
    "'<GenerateDebugInformation>true</GenerateDebugInformation>'"
    "'<ProgramDatabaseFile>$(OutDir)$(TargetName).pdb</ProgramDatabaseFile>'"
    "'<EnableCOMDATFolding>false</EnableCOMDATFolding>'"
    "'<OptimizeReferences>false</OptimizeReferences>'"
    "'<AdditionalOptions>/Brepro</AdditionalOptions>'"
    "'</Link></ItemDefinitionGroup></Project>')"
    '"')

_HELPER = 'python {repo}/scripts/corpus/exercisers/toxcore_msvc.py'

_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
            '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')


def _msvc(version, ref, cmp=True, legacy=False):
    cmake = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
             '-DCMAKE_BUILD_TYPE=Release -DCMAKE_VERBOSE_MAKEFILE=ON '
             '"-DCMAKE_PREFIX_PATH=%CD%\\tox-deps" '
             '"-DPKG_CONFIG_EXECUTABLE=%CD%\\tox-deps\\pkg-config.bat" '
             + _CMAKE_COMMON + ' -DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON '
             + _CFLAGS + ' ' + _LDFLAGS)
    return Recipe(
        family="c-toxcore", version=version,
        upstream="https://github.com/TokTok/c-toxcore", license="GPL-3.0-or-later",
        source=Source(git_url="https://github.com/TokTok/c-toxcore.git", git_ref=ref),
        extra_sources={"libsodium_src": _SODIUM, "pthreads_src": _PTHREADS},
        build=[
            BuildStep("mkdir sodium pth"),
            BuildStep("tar -xf {libsodium_src} -C sodium --strip-components=1"),
            BuildStep("tar -xf {pthreads_src} -C pth --strip-components=1"),
            BuildStep(_PROPS),
            BuildStep('msbuild sodium\\builds\\msvc\\vs2022\\libsodium\\libsodium.vcxproj '
                      '/p:Configuration=ReleaseDLL /p:Platform={msbuild_platform} '
                      '/p:PlatformToolset=v143 '
                      '/p:ForceImportBeforeCppTargets=%CD%\\msvcprops.props '
                      '/m /v:minimal'),
            BuildStep("nmake /nologo /E VC", cwd="pth"),
            BuildStep(_HELPER + " prepare sodium pth tox-deps"
                      + (" legacy" if legacy else "")),
            BuildStep(cmake),
            BuildStep("type build-{arch}\\CMakeFiles\\toxcore_shared.dir\\flags.make",
                      allow_failure=True),
            BuildStep("cmake --build build-{arch} --target toxcore_shared"),
            BuildStep("type build-{arch}\\CMakeFiles\\toxcore_shared.dir\\link.txt",
                      allow_failure=True),
            BuildStep(_HELPER + " link build-{arch} tox-out-{arch} sodium pth {arch}"),
            BuildStep("dir tox-out-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="tox-out-{arch}/toxcore.dll", component="toxcore.dll",
                            pdb="tox-out-{arch}/toxcore.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
    )


RECIPES.update({
    "c-toxcore_0.2.24_msvc": _msvc("0.2.24", "v0.2.24"),
    "c-toxcore_0.2.18_msvc": _msvc("0.2.18", "v0.2.18", legacy=True),
    "c-toxcore_0.2.12_msvc": _msvc("0.2.12", "v0.2.12", cmp=False, legacy=True),
})

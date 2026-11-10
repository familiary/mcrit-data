"""hwloc - the Portable Hardware Locality library XMRig links for NUMA-aware
RandomX dataset allocation and CPU affinity.

Tracker issue #8 (XMRig) asks for -DWITH_HWLOC=OFF first, and the XMRig
family is built that way; hwloc itself was then covered by no family. XMRig
6.25.0 vendors hwloc 2.12.1 in src/3rdparty/hwloc (its VERSION file says
major=2 minor=12 release=1, and its .c files are a subset of the release
tarball's hwloc/ directory) and compiles that copy into the miner on MSVC
only; on every other compiler its cpu.cmake calls find_package(HWLOC) and
links a system or separately built libhwloc. So the family is upstream's own
2.12.1 release, built as the shared library a hwloc-enabled XMRig links:

  * Linux x86/x64: the release's autotools build, libhwloc.so.15.
  * MinGW x86/x64: the same configure with --host, libhwloc-15.dll.
  * MSVC x86/x64: the release's contrib/windows-cmake project (the build
    upstream documents for Windows), hwloc.dll, /MD.

Optional backends that need other libraries (libxml2, PCI, libudev, OpenCL,
CUDA, NVML, RSMI, LevelZero, GL, cairo) are disabled explicitly rather than
left to whatever a host happens to have, so every axis builds the same core:
topology discovery (x86 CPUID, Linux sysfs or Windows APIs), bitmaps,
binding, distances, memory attributes, CPU kinds and the minimal XML
import/export. Nothing in the tree is patched.

The XMRig family's 6.25.0-hwloc variant links these libraries (Linux, MinGW)
or, on MSVC, compiles XMRig's vendored copy of the same release (see
xmrig.py).
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


VERSION = "2.12.1"
SOURCE = Source(
    url="https://download.open-mpi.org/release/hwloc/v2.12/hwloc-2.12.1.tar.bz2",
    sha256="38a90328bb86259f9bb2fe1dc57fd841e111d1e6358012bef23dfd95d21dc66b")

_UPSTREAM = "https://www.open-mpi.org/projects/hwloc/"
_LICENSE = "BSD-3-Clause (COPYING; Inria, Universite de Bordeaux, Cisco and others)"

# The optional components, all off; see the module docstring.
CONFIGURE_OPTIONS = ("--enable-shared --disable-static --disable-libxml2 "
                     "--disable-cairo --disable-pci --disable-libudev "
                     "--disable-opencl --disable-cuda --disable-nvml "
                     "--disable-rsmi --disable-levelzero --disable-gl "
                     "--disable-plugins --disable-doxygen")

_NOTES = ("hwloc %s release tarball (sha256 pinned), the library XMRig 6.25.0 "
          "vendors in src/3rdparty/hwloc and links when built with "
          "WITH_HWLOC=ON. Optional backends needing other libraries are "
          "disabled; the core topology, bitmap, binding, distances, memattrs, "
          "cpukinds and minimal-XML code is built. No source is patched. "
          % VERSION)

_MSVC_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Zi"'
_MSVC_LDFLAGS = ('-DCMAKE_SHARED_LINKER_FLAGS_RELEASE='
                 '"/INCREMENTAL:NO /DEBUG /Brepro /OPT:NOREF /OPT:NOICF"')


RECIPES = {
    "hwloc_2.12.1_linux": Recipe(
        family="hwloc", version=VERSION, upstream=_UPSTREAM, license=_LICENSE,
        source=SOURCE,
        build=[
            BuildStep("./configure " + CONFIGURE_OPTIONS),
            BuildStep("make -j$(nproc) -C hwloc"),
            BuildStep("cp -L hwloc/.libs/libhwloc.so libhwloc.so.15"),
        ],
        artifacts=[Artifact(path="libhwloc.so.15", component="libhwloc.so.15")],
        toolchains=["linux_x86", "linux_x64"],
        build_flags="autotools default (-O2 -g stripped of nothing), "
                    "configure " + CONFIGURE_OPTIONS,
        notes=_NOTES + "Linux ELF shared library built with configure/make.",
    ),
    "hwloc_2.12.1": Recipe(
        family="hwloc", version=VERSION, upstream=_UPSTREAM, license=_LICENSE,
        source=SOURCE,
        build=[
            BuildStep("./configure --host={host} " + CONFIGURE_OPTIONS),
            BuildStep("make -j$(nproc) -C hwloc"),
            BuildStep("cp hwloc/.libs/libhwloc-15.dll libhwloc-15.dll"),
        ],
        artifacts=[Artifact(path="libhwloc-15.dll", component="libhwloc-15.dll")],
        toolchains=["mingw_x86", "mingw_x64"],
        build_flags="autotools default (-O2 -g), configure --host "
                    + CONFIGURE_OPTIONS,
        notes=_NOTES + "MinGW DLL built with configure --host/make.",
    ),
    "hwloc_2.12.1_msvc": Recipe(
        family="hwloc", version=VERSION, upstream=_UPSTREAM, license=_LICENSE,
        source=SOURCE,
        build=[
            BuildStep('cmake -S contrib/windows-cmake -B build-{arch} '
                      '-G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release '
                      "-DBUILD_SHARED_LIBS=ON -DHWLOC_ENABLE_TESTING=OFF "
                      "-DHWLOC_SKIP_LSTOPO=ON -DHWLOC_SKIP_TOOLS=ON "
                      "-DHWLOC_WITH_LIBXML2=OFF -DHWLOC_WITH_OPENCL=OFF "
                      "-DHWLOC_WITH_CUDA=OFF " + _MSVC_CFLAGS + " "
                      + _MSVC_LDFLAGS),
            BuildStep("cmake --build build-{arch} --target hwloc"),
            BuildStep("dir build-{arch}", allow_failure=True),
        ],
        artifacts=[Artifact(path="build-{arch}/hwloc.dll", component="hwloc.dll",
                            pdb="build-{arch}/hwloc.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        build_flags="/MD /O2 /Ob2 /DNDEBUG /Zi; /INCREMENTAL:NO /DEBUG "
                    "/Brepro /OPT:NOREF /OPT:NOICF at link "
                    "(contrib/windows-cmake, Release)",
        notes=_NOTES + "MSVC DLL from the release's contrib/windows-cmake "
                       "project, the Windows build upstream documents.",
    ),
}

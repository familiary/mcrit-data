"""Win32-OpenSSH (Microsoft's Windows fork of OpenSSH), built with MSVC.

Backlog issue #46 asked for OpenSSH as the base of the SSHDoor and Ebury
trojans; the corpus README recorded Win32-OpenSSH as "its own recipe if one
turns up", because the fork is a different code base from OpenSSH portable
(the Windows port of the I/O layer, the service and agent, the console host,
a replacement for the POSIX process model) and portable's reference data does
not describe it. This is that recipe. The images are filed under the OpenSSH
family with the version "Win32_<tag>", so
OpenSSH_Win32_10.4.0.0_msvc_x64_ssh.exe sits beside OpenSSH_9.6p1_*.

Where the source is. github.com/PowerShell/Win32-OpenSSH is the issue tracker,
the wiki and a release table (its README: "active development ... is being
done in https://github.com/PowerShell/openssh-portable"); its tags
(v9.8.3.0p2-Preview) hold only that README. The source is PowerShell/
openssh-portable, tag v10.4.0.0 (commit
274893f8d1fe86c4d128b514c3af4bc10cdc0c99, 2026-10-20), the newest of its tags
(v9.8.3.0, v10.0.0.0, v10.4.0.0). The checkout is as tagged.

How the fork gets its dependencies, read from contrib/win32/openssh at the
tag. v9.8.3.0 still downloaded prebuilt LibreSSL.zip and ZLib.zip release
assets (GetLibreSSL.ps1, GetZLib.ps1, versions in paths.targets). From
v10.0.0.0 the dependencies are a vcpkg manifest (vcpkg.json: zlib 1.3.2,
libressl 4.3.3, libfido2 1.17.0, libcbor 0.14.0, all pinned in `overrides`),
two overlay ports (libressl, libfido2) and custom triplets
(vcpkg_triplets/{x86,x64}-custom.cmake), consumed by the projects through
$(SolutionDir)\\vcpkg_installed\\$(VcpkgTriplet)\\$(VcpkgTriplet)\\{include,lib,
bin}. OpenSSH-build.ps1 is the documented entry point (it needs an
interactive, elevated PowerShell with vcpkg integrated); this recipe drives
the same Win32-OpenSSH.sln, whole (msbuild /t:<project> on it fails with
MSB4057 'The target "ssh" does not exist in the project' at config.vcxproj), on
the runner's vcpkg instead.

Linkage, from vcpkg_triplets and the projects. LibreSSL is a DLL
(VCPKG_LIBRARY_LINKAGE dynamic for the libressl port): the executables import
libcrypto, so no cryptographic code is in an image and there is nothing of
data/OpenSSL to subtract (LibreSSL is not OpenSSL either). zlib, libfido2 and
libcbor are static libraries; zlib is linked into ssh, sshd, sshd-session and
sshd-auth ($(ZLibName) is in their AdditionalDependencies), and
libfido2/libcbor only into ssh-sk-helper, which is not built here. The
executables are built with /MT upstream; this recipe builds /MD, see below.

Deviations from upstream's build, every one recipe-applied (the helper
scripts/corpus/exercisers/win32openssh.py and the msbuild command line) and
none in the tree:
  1. /MD for everything (MultiThreaded in the projects, so a props file
     imported through ForceImportBeforeCppTargets sets MultiThreadedDLL), and
     the vcpkg ports for zlib, libfido2 and libcbor with the DLL runtime too
     (an overlay triplet, x86-md / x64-md, copied from upstream's *-custom
     triplets with VCPKG_CRT_LINKAGE dynamic, VCPKG_BUILD_TYPE release).
     /MT zlib would not link into an /MD image (LNK2038).
  2. No /GL (WholeProgramOptimization false) and no LTCG; link
     /OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO, in place of upstream's
     /opt:ref /opt:icf. The rest of upstream's link options stay:
     /debug /debugtype:cv,fixup /ignore:4099 /CETCOMPAT, and the compile
     options (/O2-class MaxSpeed, /Gy, /ZH:SHA_256, /guard:cf, /Qspectre).
     /Zi (DebugInformationFormat ProgramDatabase) is added so PDBs name the
     functions.
  3. WindowsTargetPlatformVersion=10.0 (the newest installed SDK) in place of
     paths.targets' 10.0.22621.0; PostBuildEventUseInBuild=false (the config
     project's post-build step only copies install scripts); VcpkgEnabled=false
     because the dependencies are installed first by a step of their own.
  4. The vcpkg manifest. Upstream's vcpkg.json pins builtin-baseline
     a345bbdc68cdfda65603e24413b21afb28f110fb, and with that baseline vcpkg
     refuses to resolve it: measured with vcpkg-tool 2026 against that commit,
     `error: no version database entry for libcbor at 0.14.0. Available
     versions: 0.11.0#1 0.11.0 0.10.2 0.9.0 0.8.0#1 0.8.0` (its baseline.json
     has zlib 1.3.1, libcbor 0.11.0; v10.0.0.0 asks for libcbor 0.13.0 and
     fails the same way). The recipe therefore writes a copy of the manifest
     with the same dependencies and the same overrides and the baseline moved
     to vcpkg tag 2026.10.16 (9eec002df1cd109f8f104cd966a763daf9751489), the
     tag measured whose database has every version the overrides name (the only candidate tried).
     libressl and libfido2 are the overlay ports of the tree, unmodified.
  5. Preprocessor: _ACRTIMP= and _DCRTIMP= (empty) for every compile. The
     fork's win32compat\\inc headers rename CRT functions with macros
     (#define system w32_system) and declare the replacements plainly; under
     /MD the SDK declares the same functions __declspec(dllimport), and cl
     stops with C2375 for w32_rename (corecrt_io.h) and w32_system
     (process.h). Emptying the macros makes the SDK declarations plain, so CRT
     calls go through import-library thunks. The vcpkg include and library
     directories are added by the props file (vcpkg's msbuild integration,
     which would add them, is off): without them
     `includes.h(173,10): error C1083: Cannot open include file:
     'openssl/opensslv.h'` in openbsd_compat.vcxproj.
  6. /wd4703 on every compile. Without /GL the compiler back end runs per
     file and reports C4703 "potentially uninitialized local pointer
     variable" (130 error lines over the two architectures, in auth2-hostbased.c, misc.c,
     sftp-client.c ...), which /sdl (SDLCheck true in every project) promotes
     to errors; under upstream's /GL the check never runs. The warning is
     disabled; /sdl stays.
  7. Aliases (not needed in the end): paths.targets links zs.lib and
     keygen.vcxproj libcrypto.lib; the helper would copy zlib.lib / crypto.lib
     to those names if absent, and logged no ALIAS: the ports install
     zs.lib and libcrypto.lib themselves.

Which programs. ssh, sshd, sshd-session, sshd-auth, scp and sftp (the six of
the OpenSSH 10 portable set, as in openssh.py), and the two programs that
exist only in the fork: ssh-agent (a Windows service in the fork) and
ssh-shellhost (the console host sshd starts for a session). ssh-keygen,
ssh-add, ssh-keyscan, sftp-server and the helpers are not built.

Pinning, disclosed. The OpenSSH source is pinned by commit. The vcpkg
dependencies are pinned by the manifest's version overrides (zlib 1.3.2,
libressl 4.3.3, libfido2 1.17.0, libcbor 0.14.0), the baseline commit above
and the SHA512 of each port's source archive, which vcpkg verifies; the
archives are not pinned by sha256 in this recipe, because the GitHub archive
URLs (zlib, libfido2, libcbor) answer 403 from the machine this was written
on, so no sha256 could be computed. The only sha256 known is LibreSSL
4.3.3's tarball (ff97c432457f349e6ba3d416ab903bc7468f1436f0f32efe5fff808de292c7b8,
github.com/libressl/portable release asset, matching the overlay port's
SHA512 e18aa701...). The vcpkg tool on the runner is whatever the windows-2022
image carries (2026-10-29 at the build).

Built (run 42514138261 on scratch/win32ossh-msvc, MSVC 19.44; kept + removed
as runtime + excluded by name = image total, from provenance.json, x64 / x86):
  ssh           2,337 + 216 +  98 = 2,651 / 2,396 + 220 +  98 = 2,714
  sshd          1,909 + 216 +   0 = 2,125 / 1,953 + 218 +   0 = 2,171
  sshd-session  2,556 + 217 +  98 = 2,871 / 2,611 + 222 +  98 = 2,931
  sshd-auth     2,502 + 217 +  98 = 2,817 / 2,553 + 222 +  98 = 2,873
  scp           1,056 + 212 +   0 = 1,268 / 1,086 + 212 +   0 = 1,298
  sftp          1,053 + 212 +   0 = 1,265 / 1,081 + 213 +   0 = 1,294
  ssh-agent     1,562 + 210 +   0 = 1,772 / 1,605 + 211 +   0 = 1,816
  ssh-shellhost    86 + 170 +   0 =   256 /    94 + 157 +   0 =   251
sshd does not link zlib (its compression is in sshd-session and sshd-auth).
Of the kept functions, distinct PicHashes of 10 or more instructions per
image, x64: ssh 1,644, sshd 1,278, sshd-session 1,825, sshd-auth 1,774, scp
682, sftp 677, ssh-agent 1,008, ssh-shellhost 38 (2,410 distinct over the
eight); x86 2,383 over the eight. ssh and sshd-session share 1,460 of them
on x64, ssh and sftp 549 (x86: 1,583 and 592). Overlap with the OpenSSH
portable images in data/OpenSSH (ELF, 11,248 distinct on x64, 33,874 on x86):
0 on both architectures, so this is new reference data, not a copy of the
portable releases. Libcrux (ML-KEM / ML-DSA) is part of the fork's tree and
stays: it is OpenSSH's own code.

Exclusion, by exact name, of what is not OpenSSH: see _win32openssh_zlib.py
(98 zlib 1.3.2 names, tiers P/W/N: 53/33/12 on x64, 14/59/25 on x86, all in
ssh, sshd-session and sshd-auth). LibreSSL, the C runtime and the Windows
libraries are imported, so nothing of them is in the images.

What survives that is not the fork's: the glue baseline removes the CRT and
SDK code it can name (157 to 222 functions per image); small named survivors
of 3 to 9 instructions include SDK inlines (ReadNoFence, McGenEventRegister,
__castguard_check_failure_os_handled_wrapper, __scrt_wide_argv_policy::
configure_argv on x86). snprintf and vsnprintf, the stdio inlines that
zlib.lib and the fork's objects both define, are not in the exclusion table.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source
from ._win32openssh_zlib import zlib_functions

_COMMIT = "274893f8d1fe86c4d128b514c3af4bc10cdc0c99"

_HELPER = "python {repo}/scripts/corpus/exercisers/win32openssh.py %s {asm_arch}"
_TARGETS = ("ssh sshd sshd-session sshd-auth scp sftp ssh-agent "
            "ssh-shellhost")
# The solution's other programs, added in the final sweep as new components
# (the eight above were the first scope); the images committed before stay.
_TOOLS = "ssh-add ssh-keygen ssh-keyscan sftp-server ssh-sk-helper ssh-pkcs11-helper"
_EXES = _TARGETS.split() + _TOOLS.split()

_FLAGS = ("Release configuration of the Win32-OpenSSH.sln projects, v143, "
          "Windows SDK 10.0; /MD in place of /MT, /GL and LTCG off, /O2-class "
          "MaxSpeed /Gy /guard:cf /Qspectre as upstream, /Zi added; link "
          "/OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO /debug "
          "/debugtype:cv,fixup /CETCOMPAT; dependencies from vcpkg "
          "(zlib 1.3.2 static /MD, LibreSSL 4.3.3 as a DLL) with the vcpkg "
          "baseline moved to tag 2026.10.16")


def _recipe(version, commit, exclude=()):
    return Recipe(
        family="OpenSSH",
        version=version,
        upstream="https://github.com/PowerShell/openssh-portable",
        license="BSD-style, per file (see LICENCE in the tree); the fork's "
                "additions are under the same terms",
        source=Source(git_url="https://github.com/PowerShell/openssh-portable.git",
                      git_ref=commit),
        build=[
            BuildStep(_HELPER % "prep"),
            BuildStep(_HELPER % "vcpkg"),
            BuildStep(_HELPER % "msbuild" + " " + _TARGETS + " " + _TOOLS),
            BuildStep(_HELPER % "locate"),
            BuildStep(_HELPER % "report", allow_failure=True),
        ],
        artifacts=[Artifact(path="corpusout\\%s.exe" % name,
                            component="%s.exe" % name,
                            pdb="corpusout\\%s.pdb" % name)
                   for name in _EXES],
        toolchains=["msvc_x86", "msvc_x64"],
        exclude_functions=list(exclude),
        build_flags=_FLAGS,
        notes="Microsoft's Windows fork of OpenSSH (PowerShell/openssh-portable "
              "tag v10.4.0.0, commit %s), not OpenSSH portable. Source "
              "unpatched; /MD, no /GL or LTCG and the vcpkg baseline are "
              "recipe-applied (recipe docstring). LibreSSL is a DLL "
              "(imported, not in the images); the statically linked zlib "
              "1.3.2 is excluded by exact name (_win32openssh_zlib.py). The "
              "CRT is imported (/MD) and stays attributed to data/MSVC."
              % commit,
    )


_LEGACY_FLAGS = (
    "Release configuration of the Win32-OpenSSH.sln projects, PlatformToolset "
    "v143 (upstream's projects name v140/v141 before 9.4), Windows SDK 10.0; "
    "/MD in place of /MT, /GL and LTCG off, /Zi added; link /OPT:NOREF "
    "/OPT:NOICF /Brepro /INCREMENTAL:NO /debug /debugtype:cv,fixup /CETCOMPAT; "
    "dependencies are the prebuilt LibreSSL (DLL), zlib and libfido2 zips that "
    "the tag's own GetLibreSSL.ps1, GetZlib.ps1 and GetFIDO2.ps1 download "
    "(versions in paths.targets)")


def _sweep_recipe(tag, commit, programs, exclude=(), prep_args=""):
    """Another Win32-OpenSSH tag, added in the final sweep.

    v10.0.0.0 has a vcpkg manifest and goes through exactly the same steps as
    v10.4.0.0. Tags before it (9.8.3.0 and older) have no manifest: the
    helper's legacy mode writes the same props file minus the vcpkg paths and
    lets the tag's own pre-build event fetch its prebuilt dependencies.
    """
    vcpkg = tag == "10.0.0.0"
    recipe = _recipe("Win32_" + tag, commit, exclude)
    targets = " ".join(programs)
    recipe.build[2] = BuildStep(_HELPER % "msbuild" + " " + targets)
    if prep_args:
        recipe.build[0] = BuildStep(_HELPER % "prep" + " " + prep_args)
    recipe.artifacts = [Artifact(path="corpusout\\%s.exe" % name,
                                 component="%s.exe" % name,
                                 pdb="corpusout\\%s.pdb" % name)
                        for name in programs]
    recipe.notes = (
        "Microsoft's Windows fork of OpenSSH (PowerShell/openssh-portable "
        "tag v%s, commit %s), not OpenSSH portable. Source unpatched; /MD, no "
        "/GL or LTCG%s are recipe-applied (recipe docstring). LibreSSL is a "
        "DLL (imported, not in the images); the statically linked zlib is "
        "excluded by exact name (_win32openssh_zlib.py). The CRT is imported "
        "(/MD) and stays attributed to data/MSVC."
        % (tag, commit, " and the vcpkg baseline" if vcpkg else
           " and toolset v143"))
    if not vcpkg:
        recipe.build_flags = _LEGACY_FLAGS
    return recipe


_ALL = _EXES
_PRE98 = [n for n in _EXES if n not in ("sshd-session", "sshd-auth")]
_PRE100 = [n for n in _EXES if n != "sshd-auth"]
# 8.1.0.0 and 8.6.0.0 have no ssh-sk-helper or ssh-pkcs11-helper project.
_PRE89 = [n for n in _PRE98 if n not in ("ssh-sk-helper", "ssh-pkcs11-helper")]

RECIPES = {
    "OpenSSH_Win32_10.4.0.0_msvc": _recipe("Win32_10.4.0.0", _COMMIT,
                                           [zlib_functions()]),
}

for _tag, _commit, _programs in (
        ("10.0.0.0", "b8c08ef9da9450a94a9c5ef717d96a7bd83f3332", _ALL),
        ("9.8.2.0", "efa17c848b3e579d8a4a0e71edf6d233b5e30917", _PRE100),
        ("9.8.0.0", "64f148cc3beeaa7460a96c9be3b0ef122f4c1435", _PRE100),
        ("9.5.0.0", "59aba65cf2e2f423c09d12ad825c3b32a11f408f", _PRE98),
        ("9.4.0.0", "f72324ffa1fbf076291cbe92d968dc0b6040a2fe", _PRE98)):
    # Tags before 9.4 name v140/v141 projects; their win32compat macros need
    # the SDK's POSIX-name declarations off (run 42775680583, C2373), and
    # 8.1.0.0's paths.targets asks for a zlib release with no asset.
    _args = ""
    if _tag.split(".")[:2] < ["9", "4"] and int(_tag.split(".")[0]) < 10:
        _args = "nonstdc"
    if _tag == "8.1.0.0":
        _args += (" zlib=V1.2.11:"
                  "67ac5ccdbfdc64c275b7ad3d70fcf702f5f8086b10f2c7a91d8f71709f8a7339")
    RECIPES["OpenSSH_Win32_%s_msvc" % _tag] = _sweep_recipe(
        _tag, _commit, _programs, [zlib_functions()], prep_args=_args)

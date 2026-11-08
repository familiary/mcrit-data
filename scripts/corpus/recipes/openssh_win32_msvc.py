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
the same Win32-OpenSSH.sln with msbuild on the runner's vcpkg instead.

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
     first tag measured whose database has every version the overrides name.
     libressl and libfido2 are the overlay ports of the tree, unmodified.
  5. Aliases: paths.targets links zs.lib and keygen.vcxproj libcrypto.lib;
     the helper copies whatever vcpkg installed under those names
     (zlib.lib, crypto.lib) if they are absent (logged as ALIAS).

Which programs. ssh, sshd, sshd-session, sshd-auth, scp and sftp (the six of
the OpenSSH 10 portable set, as in openssh.py), and the two programs that
exist only in the fork: ssh-agent (a Windows service in the fork) and
ssh-shellhost (the console host sshd starts for a session). ssh-keygen,
ssh-add, ssh-keyscan, sftp-server and the helpers are not built.

Exclusion, by exact name, of what is not OpenSSH: see _win32openssh_zlib.py.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source

_COMMIT = "274893f8d1fe86c4d128b514c3af4bc10cdc0c99"

_HELPER = "python {repo}/scripts/corpus/exercisers/win32openssh.py %s {asm_arch}"
_TARGETS = ("ssh sshd sshd-session sshd-auth scp sftp ssh-agent "
            "ssh-shellhost")
_EXES = _TARGETS.split()

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
            BuildStep(_HELPER % "msbuild" + " " + _TARGETS),
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


RECIPES = {
    "OpenSSH_Win32_10.4.0.0_msvc": _recipe("Win32_10.4.0.0", _COMMIT),
}

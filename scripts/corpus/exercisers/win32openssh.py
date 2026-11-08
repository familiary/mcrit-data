"""Build steps of the Win32-OpenSSH MSVC recipe (openssh_win32_msvc.py).

Run from the source root of a PowerShell/openssh-portable checkout on a
Windows runner with a Visual Studio developer environment, one subcommand per
build step (the recipe's docstring says why each exists):

  prep ARCH       write the props file, the vcpkg manifest and the triplet
  vcpkg ARCH      install zlib, LibreSSL, libfido2 and libcbor with vcpkg
  msbuild ARCH T  build solution targets T (space separated)
  locate ARCH     copy the built executables and PDBs to corpusout\\
  report ARCH     print the symbol and import evidence the exclusion tables
                  are derived from

ARCH is x86 or x64. Nothing in the upstream tree is modified: the files this
writes are new, beside it, and the vcpkg tree goes under
contrib\\win32\\openssh\\vcpkg_installed, where upstream's projects look for it.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys

# vcpkg tag 2026.10.16. Upstream's manifest pins builtin-baseline
# a345bbdc68cdfda65603e24413b21afb28f110fb, whose versions database has no
# libcbor 0.14.0 and no zlib 1.3.2 (baseline.json: libcbor 0.11.0, zlib 1.3.1),
# so `vcpkg install` stops with "no version database entry for libcbor at
# 0.14.0". This commit lists every version the manifest's overrides name.
VCPKG_BASELINE = "9eec002df1cd109f8f104cd966a763daf9751489"

OPENSSH = os.path.join("contrib", "win32", "openssh")

# _ACRTIMP= : the fork's win32compat\\inc headers rename CRT functions with
# macros (#define system w32_system) and declare the replacement plainly; the
# SDK's own declaration of the same function carries __declspec(dllimport)
# under /MD (_ACRTIMP), and cl stops with C2375 "redefinition; different
# linkage" for w32_system and w32_rename. Emptying _ACRTIMP makes the SDK
# declarations plain, so calls to the CRT go through the import library's
# thunks instead of straight through the IAT. The vcpkg include and library
# directories are what vcpkg's msbuild integration adds to every project
# when it is on; it is off here, and openbsd_compat.vcxproj has no include
# path of its own for openssl/opensslv.h.
PROPS = """<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemDefinitionGroup>
    <ClCompile>
      <RuntimeLibrary>MultiThreadedDLL</RuntimeLibrary>
      <WholeProgramOptimization>false</WholeProgramOptimization>
      <DebugInformationFormat>ProgramDatabase</DebugInformationFormat>
      <PreprocessorDefinitions>_ACRTIMP=;%%(PreprocessorDefinitions)</PreprocessorDefinitions>
      <AdditionalIncludeDirectories>%(vcpkg)s\\include;%%(AdditionalIncludeDirectories)</AdditionalIncludeDirectories>
    </ClCompile>
    <Lib>
      <LinkTimeCodeGeneration>false</LinkTimeCodeGeneration>
    </Lib>
    <Link>
      <GenerateDebugInformation>true</GenerateDebugInformation>
      <AdditionalLibraryDirectories>%(vcpkg)s\\lib;%(vcpkg)s\\bin;%%(AdditionalLibraryDirectories)</AdditionalLibraryDirectories>
      <LinkTimeCodeGeneration>Default</LinkTimeCodeGeneration>
      <EnableCOMDATFolding>false</EnableCOMDATFolding>
      <OptimizeReferences>false</OptimizeReferences>
      <AdditionalOptions>/debug /debugtype:cv,fixup /opt:noref /opt:noicf /incremental:no /ignore:4099 /CETCOMPAT /Brepro</AdditionalOptions>
    </Link>
  </ItemDefinitionGroup>
</Project>
"""

# Upstream's vcpkg_triplets\\{x86,x64}-custom.cmake with one change: the C
# runtime is the DLL one for every port. Upstream builds zlib, libfido2 and
# libcbor as static libraries against the static runtime (/MT), which cannot
# be linked into an /MD image (LNK2038). LibreSSL stays a DLL, as upstream has
# it, so none of its code is in an image. Release only: no debug trees.
TRIPLET = """set(VCPKG_TARGET_ARCHITECTURE %(arch)s)
set(VCPKG_ENV_PASSTHROUGH __VCVARSALL_SPECTRE)
set(VCPKG_CXX_FLAGS "/Qspectre /guard:cf /W3")
set(VCPKG_C_FLAGS "/Qspectre /guard:cf /W3")
set(VCPKG_LINKER_FLAGS "/guard:cf /DYNAMICBASE /CETCOMPAT")
set(VCPKG_BUILD_TYPE release)
set(VCPKG_CRT_LINKAGE dynamic)

if(${PORT} MATCHES "libressl")
	set(VCPKG_LIBRARY_LINKAGE dynamic)
else()
	set(VCPKG_LIBRARY_LINKAGE static)
endif()

if(${PORT} MATCHES "zlib")
	set(VCPKG_CXX_FLAGS "${VCPKG_C_FLAGS} /sdl")
	set(VCPKG_C_FLAGS "${VCPKG_C_FLAGS} /sdl")
endif()
"""

EXES = ["ssh", "sshd", "sshd-session", "sshd-auth", "scp", "sftp",
        "ssh-agent", "ssh-shellhost"]


def say(*parts):
    print(" ".join(str(p) for p in parts), flush=True)


def triplet(arch):
    return "%s-md" % arch


def installed(arch):
    """Where upstream's projects look: vcpkg_installed\\<t>\\<t>\\{include,lib,bin}."""
    return os.path.join(OPENSSH, "vcpkg_installed", triplet(arch), triplet(arch))


def vcpkg_root():
    root = os.environ.get("VCPKG_INSTALLATION_ROOT") or os.environ.get("VCPKG_ROOT")
    if not root or not os.path.isdir(root):
        sys.exit("no vcpkg on this runner (VCPKG_INSTALLATION_ROOT)")
    return root


def run(cmd, env=None, quiet=False):
    say("$", " ".join(cmd))
    result = subprocess.run(cmd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            errors="replace")
    if not quiet:
        say(result.stdout.rstrip())
    return result.returncode, result.stdout


def prep(arch):
    with open("msvcprops.props", "w") as handle:
        handle.write(PROPS % {"vcpkg": os.path.abspath(installed(arch))})
    os.makedirs(os.path.join("corpus-vcpkg", "triplets"), exist_ok=True)
    with open(os.path.join(OPENSSH, "vcpkg.json")) as handle:
        manifest = json.load(handle)
    say("upstream manifest baseline:", manifest.get("builtin-baseline"))
    say("upstream overrides:", json.dumps(manifest.get("overrides")))
    manifest["builtin-baseline"] = VCPKG_BASELINE
    with open(os.path.join("corpus-vcpkg", "vcpkg.json"), "w") as handle:
        json.dump(manifest, handle, indent=2)
    with open(os.path.join("corpus-vcpkg", "triplets",
                           triplet(arch) + ".cmake"), "w") as handle:
        handle.write(TRIPLET % {"arch": arch})

    root = vcpkg_root()
    git = ["git", "-C", root]
    code, out = run(git + ["rev-parse", "--is-shallow-repository"], quiet=True)
    say("vcpkg root", root, "shallow:", out.strip())
    if out.strip() == "true":
        run(git + ["fetch", "--unshallow", "--quiet", "origin"])
    run(git + ["fetch", "--quiet", "origin", VCPKG_BASELINE])
    code, out = run(git + ["cat-file", "-t", VCPKG_BASELINE])
    if code != 0:
        sys.exit("the vcpkg baseline commit is not available")
    run([os.path.join(root, "vcpkg.exe"), "version"])

    # What the Spectre-mitigated (upstream's default) configuration needs.
    tools = os.environ.get("VCToolsInstallDir", "")
    spectre = os.path.join(tools, "lib", "spectre", "x64" if arch == "x64" else "x86")
    say("SPECTRE-LIBS", spectre, "PRESENT" if os.path.isdir(spectre) else "ABSENT")
    sdks = sorted(glob.glob(r"C:\Program Files (x86)\Windows Kits\10\Include\10.*"))
    say("WINDOWS-SDKS", ", ".join(os.path.basename(s) for s in sdks))
    say("VCToolsVersion", os.environ.get("VCToolsVersion"))


def vcpkg(arch):
    root = vcpkg_root()
    env = dict(os.environ)
    env.update({"VCPKG_ROOT": root,
                "VCPKG_DISABLE_METRICS": "1",
                "VCPKG_PLATFORM_TOOLSET": "v143"})
    if env.get("VSINSTALLDIR"):
        env["VCPKG_VISUAL_STUDIO_PATH"] = env["VSINSTALLDIR"].rstrip("\\")
    cmd = [os.path.join(root, "vcpkg.exe"), "install",
           "--triplet", triplet(arch),
           "--x-manifest-root=corpus-vcpkg",
           "--x-install-root=" + os.path.abspath(
               os.path.join(OPENSSH, "vcpkg_installed", triplet(arch))),
           "--overlay-ports=" + os.path.abspath(
               os.path.join(OPENSSH, "vcpkg_overlay_ports")),
           "--overlay-triplets=" + os.path.abspath(
               os.path.join("corpus-vcpkg", "triplets")),
           "--disable-metrics"]
    code, out = run(cmd, env=env, quiet=True)
    lines = out.splitlines()
    say("\n".join(lines[-80:]))
    if code != 0:
        for log in glob.glob(os.path.join(root, "buildtrees", "*", "*-err.log")) + \
                glob.glob(os.path.join(root, "buildtrees", "*", "*-out.log")):
            say("::group::%s" % log)
            with open(log, errors="replace") as handle:
                say("".join(handle.readlines()[-40:]))
        sys.exit("vcpkg install failed (%d)" % code)
    base = installed(arch)
    for sub in ("lib", "bin"):
        say(sub, sorted(os.listdir(os.path.join(base, sub))))
    # Names the projects ask for (paths.targets: zs.lib; keygen: libcrypto.lib)
    # against the names vcpkg's ports install. Copies, not renames.
    lib = os.path.join(base, "lib")
    for wanted, candidates in (("zs.lib", ["zlib.lib", "z.lib", "zlibstatic.lib"]),
                               ("libcrypto.lib", ["crypto.lib"])):
        if not os.path.exists(os.path.join(lib, wanted)):
            for candidate in candidates:
                if os.path.exists(os.path.join(lib, candidate)):
                    shutil.copy(os.path.join(lib, candidate),
                                os.path.join(lib, wanted))
                    say("ALIAS", candidate, "->", wanted)
                    break
    say("LIBRESSL-INCLUDE", os.path.isfile(os.path.join(base, "include", "openssl", "evp.h")))


def msbuild(arch, targets):
    # The whole solution, as upstream builds it: `/t:<project>` on this
    # solution reaches every project as a target of that name and stops at
    # config.vcxproj (MSB4057), so `targets` is only logged.
    say("wanted programs:", " ".join(targets))
    sln = os.path.join(OPENSSH, "Win32-OpenSSH.sln")
    cmd = [shutil.which("msbuild") or "msbuild", sln,
           "/p:Configuration=Release", "/p:Platform=" + arch,
           "/p:PlatformToolset=v143", "/p:WindowsTargetPlatformVersion=10.0",
           "/p:WholeProgramOptimization=false", "/p:LinkIncremental=false",
           "/p:PostBuildEventUseInBuild=false",
           "/p:VcpkgEnabled=false", "/p:VcpkgEnableManifest=false",
           "/p:VcpkgTriplet=" + triplet(arch),
           "/p:ForceImportBeforeCppTargets=" + os.path.abspath("msvcprops.props"),
           "/m", "/v:minimal", "/nologo", "/nr:false"]
    if os.environ.get("OPENSSH_NO_SPECTRE"):
        cmd.append("/p:SpectreMitigation=false")
    code, out = run(cmd, quiet=True)
    lines = out.splitlines()
    say("\n".join(lines[-40:]))
    errors = [l for l in lines if re.search(r"\berror\b", l)]
    seen = []
    for line in errors:
        if line not in seen:
            seen.append(line)
    say("ERRORS (%d distinct):" % len(seen))
    say("\n".join(seen[:60]))
    if code != 0:
        # The solution also holds the unit-test projects, which this recipe
        # does not need; a failure there must not hide programs that built.
        missing = [n for n in EXES if not glob.glob(
            os.path.join("bin", "**", n + ".exe"), recursive=True)]
        if missing:
            sys.exit("msbuild failed (%d); not built: %s" % (code, " ".join(missing)))
        say("PARTIAL: msbuild exited %d but every wanted program exists" % code)


def locate(arch):
    os.makedirs("corpusout", exist_ok=True)
    for name in EXES:
        found = [p for p in glob.glob(os.path.join("bin", "**", name + ".exe"),
                                      recursive=True) if "Release" in p]
        if not found:
            say("MISSING", name)
            continue
        exe = sorted(found, key=os.path.getmtime)[-1]
        say("FOUND", exe, os.path.getsize(exe))
        shutil.copy(exe, "corpusout")
        pdb = exe[:-4] + ".pdb"
        if os.path.exists(pdb):
            shutil.copy(pdb, "corpusout")
        else:
            say("NO-PDB", pdb)


_SYM = re.compile(r"^\s*[0-9A-F]+\s+[0-9A-F]+\s+SECT[0-9A-F]+\s+\w+\s+\(\)\s+"
                  r"(External|Static)\s+\|\s+(\S+)")


def functions(paths):
    """Defined function symbols of .lib / .obj files, via dumpbin /symbols."""
    names = []
    for i in range(0, len(paths), 40):
        chunk = paths[i:i + 40]
        code, out = run(["dumpbin", "/nologo", "/symbols"] + chunk, quiet=True)
        for line in out.splitlines():
            match = _SYM.match(line)
            if match:
                names.append(match.group(2))
    return names


def report(arch):
    platform = "Win32" if arch == "x86" else "x64"
    base = installed(arch)
    zlib = [os.path.join(base, "lib", n) for n in ("zlib.lib", "zs.lib")
            if os.path.exists(os.path.join(base, "lib", n))][:1]
    say("ZLIB-ARCHIVE", zlib)
    for name in sorted(set(functions(zlib))):
        say("ZLIBFN\t%s\t%s" % (arch, name))
    objs = glob.glob(os.path.join(OPENSSH, platform, "Release", "**", "*.obj"),
                     recursive=True)
    libs = glob.glob(os.path.join(OPENSSH, "lib", "**", "*.lib"), recursive=True)
    say("OPENSSH-OBJECTS", len(objs), "LIBS", libs)
    seen = set()
    for name in functions(objs):
        seen.add(name)
    for name in sorted(seen):
        say("OSSHFN\t%s\t%s" % (arch, name))
    for name in EXES:
        exe = os.path.join("corpusout", name + ".exe")
        if os.path.exists(exe):
            code, out = run(["dumpbin", "/nologo", "/dependents", exe], quiet=True)
            deps = [l.strip() for l in out.splitlines() if l.strip().lower().endswith(".dll")]
            say("DEPENDENTS\t%s\t%s" % (name, " ".join(deps)))


def main(argv):
    if len(argv) < 3 or argv[2] not in ("x86", "x64"):
        sys.exit(__doc__)
    command, arch = argv[1], argv[2]
    if command == "prep":
        prep(arch)
    elif command == "vcpkg":
        vcpkg(arch)
    elif command == "msbuild":
        msbuild(arch, argv[3:] or EXES)
    elif command == "locate":
        locate(arch)
    elif command == "report":
        report(arch)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)

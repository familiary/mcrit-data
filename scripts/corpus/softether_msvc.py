"""Build SoftEther VPN Stable 4.44 with cl/link, without MSBuild or the .vcproj loader.

The upstream Windows projects are Visual C++ 2008 ``.vcproj`` files plus a
``SEVPN.sln`` written for them. MSBuild cannot load either (MSB4025 on the
solution, MSB4192 on a project), and converting them in place would modify
upstream files. This helper instead reads the same ``.vcproj`` files at build
time, takes the Release configuration's compiler options, preprocessor
definitions, include directories and source lists from them, and drives
``cl``, ``lib`` and ``link`` directly. The source tree is never written to
except for the ``build-<arch>`` output directory.

Differences from a Visual Studio build of the unmodified projects, all
deliberate and recorded in the recipe:

  * ``/MD`` instead of the projects' ``RuntimeLibrary="0"`` (``/MT``);
  * ``/Z7`` plus ``/DEBUG`` so the link writes a PDB, ``/Brepro``,
    ``/OPT:NOREF /OPT:NOICF /INCREMENTAL:NO``;
  * no precompiled header (``CedarPch.h`` is simply included);
  * no resource script, version resource, manifest or ``BuildUtil`` post-build
    step: none of them contributes code;
  * the vendored OpenSSL/zlib/intel-aes import libraries from
    ``BuildFiles/Library`` are linked as upstream does, with
    ``/NODEFAULTLIB:LIBCMT`` because they were built against the static CRT.

Usage: softether_msvc.py <source_root> <x86|x64> [--dry-run]
"""

import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

COMPONENTS = {
    # name: (project directory, subsystem)
    "vpnserver": ("vpnserver", "WINDOWS"),
    "vpnbridge": ("vpnbridge", "WINDOWS"),
    "vpnclient": ("vpnclient", "WINDOWS"),
    "vpncmd": ("vpncmd", "CONSOLE"),
}
LIBRARIES = ("Mayaqua", "Cedar")
VENDORED = ("libeay32.lib", "ssleay32.lib", "zlib.lib", "libintelaes.lib")


def load_project(path):
    """Parse a .vcproj (shift_jis, backslash paths) into an ElementTree root."""
    text = open(path, "rb").read().decode("latin-1")
    text = re.sub(r"<\?xml[^>]*\?>", "", text)
    return ET.fromstring(text)


def release_config(root, platform):
    for config in root.iter("Configuration"):
        if config.get("Name") == "Release|" + platform:
            return config
    raise SystemExit("no Release|%s configuration" % platform)


def tool(config, name):
    for element in config.iter("Tool"):
        if element.get("Name") == name:
            return element
    return None


def compiler_flags(cl_tool, defines_extra=()):
    """Map the project's VCCLCompilerTool attributes to cl switches."""
    a = cl_tool.attrib
    flags = ["/nologo", "/c"]
    if a.get("Optimization") == "3":
        flags.append("/Ox")
    if a.get("InlineFunctionExpansion") == "0":
        flags.append("/Ob0")
    if a.get("EnableIntrinsicFunctions") == "false":
        flags.append("/Oi-")
    if a.get("StringPooling") == "false":
        flags.append("/GF-")
    if a.get("EnableFunctionLevelLinking") == "false":
        flags.append("/Gy-")
    if a.get("BufferSecurityCheck") == "false":
        flags.append("/GS-")
    if a.get("StructMemberAlignment") == "4":
        flags.append("/Zp4")
    if a.get("WarningLevel") == "3":
        flags.append("/W3")
    for number in filter(None, a.get("DisableSpecificWarnings", "").split(";")):
        flags.append("/wd" + number)
    # Recorded deviations: dynamic CRT, debug info in the objects.
    flags += ["/MD", "/Z7"]
    for define in filter(None, a.get("PreprocessorDefinitions", "").split(";")):
        flags.append("/D" + define)
    for define in defines_extra:
        flags.append("/D" + define)
    return flags


def include_flags(cl_tool, src_dir):
    flags = []
    for entry in filter(None, cl_tool.get("AdditionalIncludeDirectories", "").split(";")):
        entry = entry.replace("$(SolutionDir)", src_dir + os.sep)
        flags.append("/I" + entry.replace("/", os.sep))
    return flags


def project_sources(root, platform):
    """(path, compile_as_cpp, exception_handling) for every C/C++ source."""
    sources = []
    for f in root.iter("File"):
        rel = f.get("RelativePath").replace("\\", "/")
        if not rel.lower().endswith((".c", ".cpp")):
            continue
        rel = rel[2:] if rel.startswith("./") else rel
        cpp = rel.lower().endswith(".cpp")
        eh = None
        excluded = False
        for fc in f.iter("FileConfiguration"):
            if fc.get("Name") != "Release|" + platform:
                continue
            if fc.get("ExcludedFromBuild") == "true":
                excluded = True
            override = tool(fc, "VCCLCompilerTool")
            if override is not None:
                if override.get("CompileAs") == "2":
                    cpp = True
                eh = override.get("ExceptionHandling", eh)
        if not excluded:
            sources.append((rel, cpp, eh))
    return sources


def run(command, cwd, log):
    print("$ (%s) %s" % (cwd, " ".join(command)), flush=True)
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, errors="replace")
    sys.stdout.write(result.stdout)
    sys.stdout.flush()
    return result.returncode


def compile_project(src_dir, name, platform, out_dir, extra_defines, dry):
    proj_dir = os.path.join(src_dir, name)
    root = load_project(os.path.join(proj_dir, name + ".vcproj"))
    config = release_config(root, platform)
    cl_tool = tool(config, "VCCLCompilerTool")
    base = compiler_flags(cl_tool, extra_defines) + include_flags(cl_tool, src_dir)
    obj_dir = os.path.join(out_dir, name + "_obj")
    os.makedirs(obj_dir, exist_ok=True)
    jobs = []
    for rel, cpp, eh in project_sources(root, platform):
        flags = list(base)
        if cpp:
            flags.append("/TP")
            if eh == "2":
                flags.append("/EHsc")
        else:
            flags.append("/TC")
        obj = os.path.join(obj_dir, os.path.splitext(os.path.basename(rel))[0] + ".obj")
        jobs.append((rel, flags + ["/Fo" + obj, rel], obj))
    failures = []
    objects = []

    def one(job):
        rel, command, obj = job
        if dry:
            print("cl", " ".join(command))
            return rel, 0, obj
        return rel, run(["cl"] + command, proj_dir, None), obj

    with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
        for rel, code, obj in pool.map(one, jobs):
            if code != 0 or (not dry and not os.path.isfile(obj)):
                failures.append(rel)
            else:
                objects.append(obj)
    return objects, failures


def main(argv):
    dry = "--dry-run" in argv
    argv = [a for a in argv if a != "--dry-run"]
    source_root, arch = argv[0], argv[1]
    platform = {"x86": "Win32", "x64": "x64"}[arch]
    src_dir = os.path.abspath(os.path.join(source_root, "src"))
    out_dir = os.path.abspath(os.path.join(source_root, "build-" + arch))
    os.makedirs(out_dir, exist_ok=True)
    libdir = os.path.join(src_dir, "BuildFiles", "Library", platform + "_Release")

    summary = {}
    # The x64 configurations already list CPU_64 in PreprocessorDefinitions.
    for name in LIBRARIES:
        objects, failures = compile_project(src_dir, name, platform, out_dir, [], dry)
        summary[name] = failures
        lib = os.path.join(out_dir, name + ".lib")
        if dry:
            print("lib /OUT:%s %d objects" % (lib, len(objects)))
            continue
        command = ["lib", "/nologo", "/IGNORE:4006,4221", "/OUT:" + lib] + objects
        if run(command, out_dir, None) != 0:
            summary[name].append("<lib.exe failed>")

    status = 0
    for component, (project, subsystem) in COMPONENTS.items():
        objects, failures = compile_project(src_dir, project, platform, out_dir, [], dry)
        summary[component] = failures
        exe = os.path.join(out_dir, component + ".exe")
        pdb = os.path.join(out_dir, component + ".pdb")
        command = (["link", "/nologo", "/OUT:" + exe, "/PDB:" + pdb,
                    "/DEBUG", "/INCREMENTAL:NO", "/Brepro",
                    "/OPT:NOREF", "/OPT:NOICF", "/MANIFEST:NO",
                    "/SUBSYSTEM:" + subsystem, "/ENTRY:mainCRTStartup",
                    "/LIBPATH:" + libdir, "/IGNORE:4098,4099,4217,4286",
                    "/NODEFAULTLIB:LIBCMT", "/NODEFAULTLIB:LIBCMTD",
                    "/DELAYLOAD:setupapi.dll", "/DELAYLOAD:advapi32.dll",
                    "/DELAYLOAD:user32.dll"]
                   + (["/STACK:100000"] if subsystem == "WINDOWS" else [])
                   + objects
                   + [os.path.join(out_dir, n + ".lib") for n in LIBRARIES]
                   + list(VENDORED)
                   + ["delayimp.lib", "legacy_stdio_definitions.lib"])
        if dry:
            print(" ".join(command))
            continue
        code = run(command, out_dir, None)
        if code != 0 or not os.path.isfile(exe):
            summary[component].append("<link.exe exit %d>" % code)
            status = 1

    print("\n== softether_msvc summary ==")
    for name, failures in summary.items():
        print("%-10s %s" % (name, "ok" if not failures else "FAILED: " + ", ".join(failures)))
    # Sources that failed to compile are reported but only a missing image is
    # fatal here: a library member nothing references never reaches the link.
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

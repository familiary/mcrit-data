"""Prepare dependency exports and MSBuild overrides for MeshAgent."""

import argparse
import glob
import os
import re
import subprocess
import xml.etree.ElementTree as ET


def exports(args):
    objects = sorted(path for pattern in args.objects for path in glob.glob(pattern))
    if not objects:
        raise RuntimeError("no dependency objects found")
    symbols = set()
    for obj in objects:
        output = subprocess.check_output(["dumpbin", "/symbols", obj], text=True)
        for line in output.splitlines():
            if "UNDEF" in line or "External" not in line or "|" not in line:
                continue
            name = line.split("|", 1)[1].strip().split()[0]
            if name.startswith(("@", "?", "__", ".")):
                continue
            if args.arch == "x86" and name.startswith("_"):
                name = name[1:]
            if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name):
                symbols.add(name)
    if not symbols:
        raise RuntimeError("no dependency exports found")
    with open(args.output, "w") as stream:
        stream.write("EXPORTS\n" + "\n".join(sorted(symbols)) + "\n")


def props(args):
    namespace = "http://schemas.microsoft.com/developer/msbuild/2003"
    ns = {"m": namespace}
    project = ET.parse(args.project).getroot()
    condition = "'$(Configuration)|$(Platform)'=='Release|%s'" % args.platform
    group = next(item for item in project.findall("m:ItemDefinitionGroup", ns)
                 if item.attrib.get("Condition") == condition)
    libraries = group.find("m:Link/m:AdditionalDependencies", ns).text.split(";")
    libraries = [item for item in libraries if "openssl" not in item.lower()
                 and "%(" not in item]
    libraries += [name + ".lib" for name in (
        "kernel32", "user32", "gdi32", "advapi32", "shell32", "ole32",
        "oleaut32", "uuid", "comdlg32", "winspool", "odbc32", "odbccp32")]
    libraries += [os.path.join(args.ssl, "libcrypto.lib"),
                  os.path.join(args.ssl, "libssl.lib"),
                  os.path.join(args.deps, "corpus-duktape.lib"),
                  os.path.join(args.deps, "corpus-zlib.lib")]
    ET.register_namespace("", namespace)
    root = ET.Element("{%s}Project" % namespace)
    properties = ET.SubElement(root, "PropertyGroup")
    for key, value in {
        "WholeProgramOptimization": "false", "LinkIncremental": "false",
        "PostBuildEventUseInBuild": "false", "TargetName": args.name,
    }.items():
        ET.SubElement(properties, key).text = value
    items = ET.SubElement(root, "ItemGroup")
    ET.SubElement(items, "ClCompile", Remove="..\\microscript\\duktape.c;..\\meshcore\\zlib\\*.c")
    definitions = ET.SubElement(root, "ItemDefinitionGroup")
    compile_options = ET.SubElement(definitions, "ClCompile")
    for key, value in {
        "RuntimeLibrary": "MultiThreadedDLL", "WholeProgramOptimization": "false",
        "DebugInformationFormat": "ProgramDatabase",
        "AdditionalOptions": "/Brepro %(AdditionalOptions)",
    }.items():
        ET.SubElement(compile_options, key).text = value
    link = ET.SubElement(definitions, "Link")
    for key, value in {
        "AdditionalDependencies": ";".join(libraries),
        "GenerateDebugInformation": "true", "OptimizeReferences": "false",
        "EnableCOMDATFolding": "false", "LinkTimeCodeGeneration": "Default",
        "AdditionalOptions": "/Brepro /INCREMENTAL:NO %(AdditionalOptions)",
        "ProgramDatabaseFile": "$(OutDir)" + args.name + ".pdb",
        "OutputFile": "$(OutDir)" + args.name + ".exe",
    }.items():
        ET.SubElement(link, key).text = value
    ET.SubElement(ET.SubElement(definitions, "PostBuildEvent"), "Command").text = ""
    ET.ElementTree(root).write(args.output, encoding="utf-8", xml_declaration=True)


parser = argparse.ArgumentParser()
commands = parser.add_subparsers(dest="command", required=True)
export_parser = commands.add_parser("exports")
export_parser.add_argument("--arch", required=True)
export_parser.add_argument("--output", required=True)
export_parser.add_argument("objects", nargs="+")
props_parser = commands.add_parser("props")
for option in ("project", "platform", "name", "ssl", "deps", "output"):
    props_parser.add_argument("--" + option, required=True)
arguments = parser.parse_args()
exports(arguments) if arguments.command == "exports" else props(arguments)

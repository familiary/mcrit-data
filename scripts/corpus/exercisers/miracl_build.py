"""Build the pinned MIRACL C library without changing its source tree."""

from __future__ import annotations

import argparse
import re
import shlex
import shutil
import subprocess
from pathlib import Path


def _configuration(flavor: str, bitness: int) -> tuple[str, str, str]:
    if flavor == "linux":
        return ("lib/linux64" if bitness == 64 else "lib/linux",
                "include/mirdef.h64" if bitness == 64 else "include/mirdef.lnx",
                "source/mrmuldv.g64" if bitness == 64 else "source/mrmuldv.gcc")
    if flavor == "mingw":
        return ("lib/mingw.bat",
                "include/mirdef.mgw" if bitness == 64 else "include/mirdef.lnx",
                "source/mrmuldv.g64" if bitness == 64 else "source/mrmuldv.gcc")
    if flavor == "msvc":
        return ("lib/ms64doit.bat" if bitness == 64 else "lib/ms32doit.bat",
                "include/mirdef.w64" if bitness == 64 else "include/mirdef.h32",
                "source/mrmuldv.w64" if bitness == 64 else "source/mrmuldv.c32")
    raise ValueError("unsupported compiler family: %s" % flavor)


def _translation_units(root: Path, build_script: Path) -> list[Path]:
    files: list[Path] = []
    for line in build_script.read_text(encoding="utf-8", errors="replace").splitlines():
        command = line.strip().lower()
        if not (command.startswith("gcc -c") or command.startswith("cl /c")):
            continue
        for name in re.findall(r"(?<![\w./\\-])([a-z0-9_.-]+\.c)(?![\w.])",
                               line, re.IGNORECASE):
            if name.lower() == "mrmuldv.c":
                continue
            path = root / "source" / name
            if path.is_file() and path not in files:
                files.append(path)
    if not files:
        raise RuntimeError("no upstream C translation units found in %s" % build_script)
    return files


def _run(command: list[str], root: Path) -> None:
    print("+ " + subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=root, check=True)


def build(args: argparse.Namespace) -> Path:
    root = Path.cwd()
    build_script_name, config_name, muldiv_name = _configuration(args.flavor, args.bitness)
    units = _translation_units(root, root / build_script_name)
    muldiv = root / muldiv_name
    if not muldiv.is_file():
        raise FileNotFoundError(muldiv)

    build_dir = root / "build_miracl"
    object_dir = build_dir / "obj"
    config_dir = build_dir / "config"
    include_dir = build_dir / "include"
    object_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    if include_dir.exists():
        shutil.rmtree(include_dir)
    shutil.copytree(root / "include", include_dir)
    shutil.copyfile(root / config_name, include_dir / "mirdef.h")
    units.append(muldiv)

    extension = "dll" if args.flavor in ("mingw", "msvc") else "so"
    output = build_dir / ("miracl-%s.%s" % (args.arch, extension))

    if args.flavor == "msvc":
        objects: list[Path] = []
        for source in units:
            obj = object_dir / (source.stem + ".obj")
            compiler_pdb = object_dir / (source.stem + ".pdb")
            _run([args.cc, "/nologo", "/TC", "/c", "/O2", "/MD", "/Zi", "/GL-",
                  "/W3", "/I" + str(include_dir),
                  "/Fo" + str(obj), "/Fd" + str(compiler_pdb), str(source)], root)
            objects.append(obj)
        linker_pdb = build_dir / ("miracl-%s.pdb" % args.arch)
        _run(["link", "/DLL", "/NOENTRY", "/DEBUG", "/OPT:NOREF",
              "/OPT:NOICF", "/Brepro", "/INCREMENTAL:NO",
              "/OUT:" + str(output), "/PDB:" + str(linker_pdb),
              *[str(obj) for obj in objects]], root)
        return output

    compiler = shlex.split(args.cc)
    arch_flags = ["-m%d" % args.bitness] if args.flavor == "linux" else []
    objects = []
    for source in units:
        obj = object_dir / (source.stem + ".o")
        visibility = ["-fvisibility=hidden"] if args.flavor == "linux" else []
        command = (compiler + arch_flags + ["-O2", "-g", "-fPIC"] + visibility + ["-x", "c", "-c",
                   "-I" + str(include_dir),
                   str(source), "-o", str(obj)])
        _run(command, root)
        objects.append(obj)

    linker_flags = ["-shared", "-o", str(output)]
    if args.flavor == "linux":
        linker_flags.insert(0, "-fvisibility=hidden")
    else:
        linker_flags.insert(0, "-Wl,--no-insert-timestamp")
    _run(compiler + arch_flags + linker_flags + [str(obj) for obj in objects], root)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flavor", choices=("linux", "mingw", "msvc"), required=True)
    parser.add_argument("--arch", choices=("x86", "x64"), required=True)
    parser.add_argument("--bitness", type=int, choices=(32, 64), required=True)
    parser.add_argument("--cc", required=True)
    args = parser.parse_args()
    result = build(args)
    print("built %s" % result.relative_to(Path.cwd()), flush=True)


if __name__ == "__main__":
    main()

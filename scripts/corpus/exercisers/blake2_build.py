"""Build standalone BLAKE2 reference or SSE2 implementations as one image."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path


SOURCES = {
    "ref": ("blake2b-ref.c", "blake2bp-ref.c", "blake2s-ref.c",
            "blake2sp-ref.c", "blake2xb-ref.c", "blake2xs-ref.c"),
    "sse": ("blake2b.c", "blake2bp.c", "blake2s.c", "blake2sp.c",
            "blake2xb.c", "blake2xs.c"),
}


def _run(command: list[str], root: Path) -> None:
    print("+ " + subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=root, check=True)


def build(args: argparse.Namespace) -> Path:
    root = Path.cwd()
    source_dir = root / args.mode
    build_dir = root / "build"
    object_dir = build_dir / ("obj-%s-%s" % (args.mode, args.arch))
    object_dir.mkdir(parents=True, exist_ok=True)
    bitness_flag = ["-m%d" % args.bitness] if args.flavor == "linux" else []
    sources = [source_dir / name for name in SOURCES[args.mode]]
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(source)

    output = build_dir / ("blake2-%s-%s.%s" %
                          (args.mode, args.arch,
                           "dll" if args.flavor in ("mingw", "msvc") else "so"))
    objects: list[Path] = []
    if args.flavor == "msvc":
        for source in sources:
            obj = object_dir / (source.stem + ".obj")
            compiler_pdb = object_dir / (source.stem + ".pdb")
            command = [args.cc, "/nologo", "/TC", "/c", "/O2", "/MD",
                       "/Zi", "/GL-", "/W3"]
            if args.mode == "sse":
                command.append("/D__SSE2__")
                if args.bitness == 32:
                    command.append("/arch:SSE2")
            command += ["/Fo" + str(obj), "/Fd" + str(compiler_pdb), str(source)]
            _run(command, root)
            objects.append(obj)
        linker_pdb = build_dir / ("blake2-%s-%s.pdb" % (args.mode, args.arch))
        _run(["link", "/DLL", "/NOENTRY", "/DEBUG", "/OPT:NOREF",
              "/OPT:NOICF", "/Brepro", "/INCREMENTAL:NO",
              "/OUT:" + str(output), "/PDB:" + str(linker_pdb),
              *[str(obj) for obj in objects], "vcruntime.lib", "ucrt.lib",
              "kernel32.lib"], root)
        return output

    compiler = shlex.split(args.cc)
    for source in sources:
        obj = object_dir / (source.stem + ".o")
        command = (compiler + bitness_flag + ["-O2" if args.mode == "ref" else "-O3",
                   "-g", "-fPIC"])
        if args.mode == "sse":
            command.append("-msse2")
        command += ["-x", "c", "-c", str(source), "-o", str(obj)]
        _run(command, root)
        objects.append(obj)

    linker_flags = ["-shared", "-o", str(output)]
    if args.flavor == "mingw":
        linker_flags.insert(0, "-Wl,--no-insert-timestamp")
    _run(compiler + bitness_flag + linker_flags +
         [str(obj) for obj in objects], root)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("ref", "sse"), required=True)
    parser.add_argument("--flavor", choices=("linux", "mingw", "msvc"), required=True)
    parser.add_argument("--arch", choices=("x86", "x64"), required=True)
    parser.add_argument("--bitness", type=int, choices=(32, 64), required=True)
    parser.add_argument("--cc", required=True)
    args = parser.parse_args()
    result = build(args)
    print("built %s" % result.relative_to(Path.cwd()), flush=True)


if __name__ == "__main__":
    main()

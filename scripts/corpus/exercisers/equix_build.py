"""Build Tor's vendored Equi-X and HashX C units as one reference image."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path


SOURCES = (
    "src/ext/equix/hashx/src/blake2.c",
    "src/ext/equix/hashx/src/compiler.c",
    "src/ext/equix/hashx/src/compiler_a64.c",
    "src/ext/equix/hashx/src/compiler_x86.c",
    "src/ext/equix/hashx/src/context.c",
    "src/ext/equix/hashx/src/hashx.c",
    "src/ext/equix/hashx/src/program.c",
    "src/ext/equix/hashx/src/program_exec.c",
    "src/ext/equix/hashx/src/siphash.c",
    "src/ext/equix/hashx/src/siphash_rng.c",
    "src/ext/equix/hashx/src/virtual_memory.c",
    "src/ext/equix/src/context.c",
    "src/ext/equix/src/equix.c",
    "src/ext/equix/src/solver.c",
)


def _run(command: list[str], root: Path) -> None:
    print("+ " + subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=root, check=True)


def build(args: argparse.Namespace) -> Path:
    root = Path.cwd()
    build_dir = root / "build_equix"
    object_dir = build_dir / ("obj-%s" % args.arch)
    object_dir.mkdir(parents=True, exist_ok=True)
    include_dirs = [root / "src/ext/equix/hashx/include",
                    root / "src/ext/equix/hashx/src",
                    root / "src/ext/equix/include",
                    root / "src/ext/equix/src"]
    for source in SOURCES:
        if not (root / source).is_file():
            raise FileNotFoundError(root / source)

    extension = "dll" if args.flavor in ("mingw", "msvc") else "so"
    output = build_dir / ("equix-hashx-%s.%s" % (args.arch, extension))
    defines = ["-DHASHX_SIZE=8", "-DEQUIX_STATIC=1", "-DHASHX_STATIC=1"]
    objects: list[Path] = []

    if args.flavor == "msvc":
        for index, source_name in enumerate(SOURCES):
            source = root / source_name
            obj = object_dir / ("%02d-%s.obj" % (index, source.stem))
            compiler_pdb = object_dir / ("%02d-%s.pdb" % (index, source.stem))
            command = [args.cc, "/nologo", "/TC", "/std:c11", "/c",
                       "/O2", "/MD", "/Zi", "/GL-", "/W3", "/DHASHX_SIZE=8",
                       "/DEQUIX_STATIC=1", "/DHASHX_STATIC=1"]
            command += ["/I" + str(path) for path in include_dirs]
            command += ["/Fo" + str(obj), "/Fd" + str(compiler_pdb), str(source)]
            _run(command, root)
            objects.append(obj)
        linker_pdb = build_dir / ("equix-hashx-%s.pdb" % args.arch)
        _run(["link", "/DLL", "/NOENTRY", "/DEBUG", "/OPT:NOREF",
              "/OPT:NOICF", "/Brepro", "/INCREMENTAL:NO",
              "/OUT:" + str(output), "/PDB:" + str(linker_pdb),
              *[str(obj) for obj in objects]], root)
        return output

    compiler = shlex.split(args.cc)
    bitness = ["-m%d" % args.bitness] if args.flavor == "linux" else []
    for index, source_name in enumerate(SOURCES):
        source = root / source_name
        obj = object_dir / ("%02d-%s.o" % (index, source.stem))
        command = (compiler + bitness + ["-O2", "-g", "-fPIC", "-std=gnu11"] +
                   defines + ["-I" + str(path) for path in include_dirs] +
                   ["-c", str(source), "-o", str(obj)])
        _run(command, root)
        objects.append(obj)

    linker_flags = ["-shared", "-o", str(output)]
    if args.flavor == "mingw":
        linker_flags.insert(0, "-Wl,--no-insert-timestamp")
    _run(compiler + bitness + linker_flags +
         [str(obj) for obj in objects], root)
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

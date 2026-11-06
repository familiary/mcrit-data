"""Build Tor's client binary against dynamic dependencies for a target."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tarfile
from pathlib import Path


def _run(command: list[str], root: Path, env: dict[str, str]) -> None:
    print("+ " + subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=root, env=env, check=True)


def _extract_source(archive: str, destination: Path) -> Path:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    with tarfile.open(archive, "r:*") as bundle:
        bundle.extractall(destination, filter="data")
    children = list(destination.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return destination


def build(args: argparse.Namespace) -> Path:
    root = Path.cwd()
    build_dir = root / "build_tor"
    prefix = build_dir / ("deps-%s" % args.arch)
    libevent_build = build_dir / ("libevent-%s" % args.arch)
    prefix.mkdir(parents=True, exist_ok=True)
    libevent_build.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    if args.flavor == "linux":
        cc = "%s -m%d" % (args.cc, args.bitness)
        cmake_args = ["-DCMAKE_BUILD_TYPE=Release"]
    else:
        cc = args.cc
        target = "x86_64-w64-mingw32" if args.bitness == 64 else "i686-w64-mingw32"
        cmake_args = [
            "-DCMAKE_SYSTEM_NAME=Windows",
            "-DCMAKE_C_COMPILER=" + args.cc,
            "-DCMAKE_RC_COMPILER=" + target + "-windres",
            "-DCMAKE_FIND_ROOT_PATH=/usr/" + target,
            "-DCMAKE_BUILD_TYPE=Release",
        ]

    if not ((prefix / "lib/libevent.dll.a").is_file()
            and (prefix / "lib/libevent.dll").is_file()):
        _run([
            "cmake", "-S", args.libevent, "-B", str(libevent_build),
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            *cmake_args,
            "-DEVENT__DISABLE_OPENSSL=ON",
            "-DEVENT__DISABLE_TESTS=ON",
            "-DEVENT__DISABLE_SAMPLES=ON",
            "-DEVENT__DISABLE_BENCHMARK=ON",
            "-DEVENT__LIBRARY_TYPE=SHARED",
            "-DCMAKE_INSTALL_PREFIX=" + str(prefix),
        ], root, env)
        _run(["cmake", "--build", str(libevent_build), "--parallel", "2"], root, env)
        _run(["cmake", "--install", str(libevent_build)], root, env)

    if args.flavor == "mingw":
        _build_openssl(args, root, prefix, target, env)
        _build_zlib(args, root, prefix, target, env)

    pkgconfig = str(prefix / "lib/pkgconfig")
    env["PKG_CONFIG_PATH"] = pkgconfig + os.pathsep + env.get("PKG_CONFIG_PATH", "")
    if args.flavor == "mingw":
        env["PKG_CONFIG_LIBDIR"] = pkgconfig
        env["CPPFLAGS"] = "-I" + str(prefix / "include")
        env["LDFLAGS"] = "-L" + str(prefix / "lib")
    env["LD_LIBRARY_PATH"] = str(prefix / "lib") + os.pathsep + env.get("LD_LIBRARY_PATH", "")
    env["CC"] = cc
    env["CFLAGS"] = "-O2 -g"
    env["STRIP"] = "true"

    configure = ["./configure"]
    if args.flavor == "mingw":
        configure += ["--build=x86_64-pc-linux-gnu", "--host=" + target,
                      "--disable-tool-name-check"]
        env["AR"] = target + "-ar"
        env["RANLIB"] = target + "-ranlib"
    configure += [
        "--disable-module-relay",
        "--disable-module-dirauth",
        "--disable-asciidoc",
        "--disable-unittests",
        "--with-libevent-dir=" + str(prefix),
    ]
    if args.flavor == "mingw":
        configure += ["--with-openssl-dir=" + str(prefix),
                      "--with-zlib-dir=" + str(prefix)]
    _run(configure, root, env)
    binary = "src/app/tor.exe" if args.flavor == "mingw" else "src/app/tor"
    _run(["make", "-j2", binary], root, env)
    return root / binary


def _build_openssl(args: argparse.Namespace, root: Path, prefix: Path,
                   target: str, env: dict[str, str]) -> None:
    lib_dir = prefix / "lib"
    bin_dir = prefix / "bin"
    if ((lib_dir / "libssl.dll.a").is_file()
            and (lib_dir / "libcrypto.dll.a").is_file()
            and list(bin_dir.glob("libssl-*.dll"))
            and list(bin_dir.glob("libcrypto-*.dll"))):
        return
    if not args.openssl:
        raise ValueError("MinGW Tor build requires the pinned OpenSSL source")
    source = _extract_source(args.openssl, root / "build_tor" / "openssl-source")
    openssl_env = env.copy()
    openssl_env.update({"CC": "gcc", "CXX": "g++", "AR": "ar",
                        "RANLIB": "ranlib", "WINDRES": "windres",
                        "CFLAGS": "-O2 -g"})
    platform = "mingw64" if args.bitness == 64 else "mingw"
    _run(["./Configure", platform,
          "--cross-compile-prefix=" + target + "-", "shared", "no-tests",
          "--prefix=" + str(prefix), "--openssldir=" + str(prefix / "ssl")],
         source, openssl_env)
    try:
        _run(["make", "-j2", "build_libs", "build_programs"], source,
             openssl_env)
    except subprocess.CalledProcessError:
        # OpenSSL 1.1.1 has a parallel dependency-file race; a second make
        # finishes the affected target, matching the corpus OpenSSL recipe.
        _run(["make", "-j2", "build_libs", "build_programs"], source,
             openssl_env)
    _run(["make", "install_sw"], source, openssl_env)
    # Keep only the PE import libraries in the Tor prefix. Otherwise GNU ld
    # can select the static archives first and attribute OpenSSL to Tor.
    for name in ("libssl.a", "libcrypto.a"):
        path = prefix / "lib" / name
        if path.exists():
            path.unlink()


def _build_zlib(args: argparse.Namespace, root: Path, prefix: Path,
                target: str, env: dict[str, str]) -> None:
    if ((prefix / "lib/libz.a").is_file()
            and (prefix / "bin/zlib1.dll").is_file()):
        return
    if not args.zlib:
        raise ValueError("MinGW Tor build requires the pinned zlib source")
    source = _extract_source(args.zlib, root / "build_tor" / "zlib-source")
    zlib_env = env.copy()
    _run(["make", "-f", "win32/Makefile.gcc", "PREFIX=" + target + "-",
          "STRIP=true", "-j2", "zlib1.dll"], source, zlib_env)
    include_dir = prefix / "include"
    lib_dir = prefix / "lib"
    bin_dir = prefix / "bin"
    include_dir.mkdir(parents=True, exist_ok=True)
    lib_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "zlib.h", include_dir / "zlib.h")
    shutil.copy2(source / "zconf.h", include_dir / "zconf.h")
    shutil.copy2(source / "libz.dll.a", lib_dir / "libz.a")
    shutil.copy2(source / "zlib1.dll", bin_dir / "zlib1.dll")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flavor", choices=("linux", "mingw"), required=True)
    parser.add_argument("--arch", choices=("x86", "x64"), required=True)
    parser.add_argument("--bitness", type=int, choices=(32, 64), required=True)
    parser.add_argument("--cc", required=True)
    parser.add_argument("--libevent", required=True)
    parser.add_argument("--openssl")
    parser.add_argument("--zlib")
    args = parser.parse_args()
    result = build(args)
    print("built %s" % result.relative_to(Path.cwd()), flush=True)


if __name__ == "__main__":
    main()

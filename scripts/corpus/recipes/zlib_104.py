"""zlib 1.0.x, the pre-1.2 inflate - draft, docstring written after measuring."""

from ..recipe import Artifact, BuildStep, Recipe, Source

_PPP_URL = "https://github.com/ppp-project/ppp.git"
_PPP_COMMIT = "4fb319056f168bb8379865b91b4fd3e1ada73f1e"

_SOURCES = ("adler32.c compress.c crc32.c deflate.c gzio.c infblock.c "
            "infcodes.c inffast.c inflate.c inftrees.c infutil.c trees.c "
            "uncompr.c zutil.c")

_PPP_MINGW = "{cc} -O2 -shared -Dlocal= -o ppp_zlib.dll common/zlib.c"
_PPP_LINUX = ("{cc} {archflag} -O2 -shared -fPIC -fvisibility=hidden "
              "-Dlocal= -o ppp_zlib.so common/zlib.c")
_Z104_MINGW = "{cc} -O2 -shared -Dlocal= -o zlib1.dll " + _SOURCES
_Z104_LINUX = ("{cc} {archflag} -O2 -shared -nostdlib -fPIC -fvisibility=hidden "
               "-Dlocal= -o libz.so " + _SOURCES)

_Z104_SOURCE = Source(
    url="https://zlib.net/fossils/zlib-1.0.4.tar.gz",
    sha256="e5c260cd3db1370fb3e0c193e9cbd9f127a9bd055d622b3fb55b82747f6e5b24")
_PPP_SOURCE = Source(git_url=_PPP_URL, git_ref=_PPP_COMMIT)


def _r(version, source, command, artifact, toolchains, upstream, flags):
    return Recipe(
        family="libzlib", version=version, upstream=upstream, license="zlib",
        source=source, build=[BuildStep(command)], artifacts=[artifact],
        toolchains=toolchains, build_flags=flags)


RECIPES = {
    "libzlib_1.0.4-ppp2.4.9": _r(
        "1.0.4-ppp2.4.9", _PPP_SOURCE, _PPP_MINGW,
        Artifact(path="ppp_zlib.dll", component="ppp_zlib.dll"),
        ["mingw_x86", "mingw_x64"], "https://github.com/ppp-project/ppp",
        "-O2 -Dlocal="),
    "libzlib_1.0.4-ppp2.4.9_linux": _r(
        "1.0.4-ppp2.4.9", _PPP_SOURCE, _PPP_LINUX,
        Artifact(path="ppp_zlib.so", component="ppp_zlib.so"),
        ["linux_x86", "linux_x64"], "https://github.com/ppp-project/ppp",
        "-O2 -Dlocal="),
    "libzlib_1.0.4": _r(
        "1.0.4", _Z104_SOURCE, _Z104_MINGW,
        Artifact(path="zlib1.dll", component="zlib1.dll"),
        ["mingw_x86", "mingw_x64"], "https://github.com/madler/zlib",
        "-O2 -Dlocal="),
    "libzlib_1.0.4_linux": _r(
        "1.0.4", _Z104_SOURCE, _Z104_LINUX,
        Artifact(path="libz.so", component="libz.so"),
        ["linux_x86", "linux_x64"], "https://github.com/madler/zlib",
        "-O2 -Dlocal="),
}

"""The zlib that UltraVNC and TightVNC link statically, as a name pattern.

Both programs build zlib from a vendored or vcpkg source tree and link it into
the executable, so its functions are in the image under the program's family
and are PicHash-identical to data/libzlib. That is what `validate --deep`
reports as leakage: a hash under TightVNC, UltraVNC and libzlib at once, one
symbol name for all three. Recipe.exclude_functions removes them by name.

A pattern is built from a recipe's own tuple of exact zlib identifiers, not
from a prefix such as ``^(de|in)flate``, because three other vendored
libraries in these images reuse zlib's internal names for different code: the
Info-ZIP sources of UltraVNC 1.2.1.x (``crc32``, ``get_crc_table``,
``fill_window``, ``build_tree``, ``compress_block``, ``copy_block`` ...) and
liblzma's ``fill_window`` in 1.8.x. The tuples contain only identifiers for
which every function of that name in the recipe's images is zlib's:

  * a function of 10 or more instructions whose PicHash is in data/libzlib
    (PicHash confirmation), or a function of fewer than 10 instructions whose
    PicHash is that of a libzlib function of the same name, or
  * a function of the same exact name and architecture whose opcode sequence
    (frame-pointer set-up and padding dropped) is at least 80% similar to the
    same-named function of some libzlib image, in a recipe where another
    function of that name IS confirmed by PicHash. These are zlib compiled
    with other flags: the x86 libzlib images keep frame pointers, vcpkg's do
    not, so the hash differs for code that is zlib's.

An identifier that fails either test for any of its functions is left out of
the tuple and stays in the image under the program's family, however
zlib-like its name is; each recipe's docstring lists them.

The pattern accepts a leading underscore (x86 symbol decoration: `_deflate`,
`__tr_init`) and GCC's ``.constprop.N`` suffix, nothing else, and is anchored,
so C++ methods and mangled names never match.
"""


def zlib_functions(names):
    """One anchored regular expression over exact zlib function names."""
    return r"^_?(?:%s)(?:\.constprop\.\d+)?$" % "|".join(sorted(set(names)))

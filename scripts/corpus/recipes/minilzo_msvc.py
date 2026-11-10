"""miniLZO as its own family, MSVC: see minilzo.py for why.

The same minilzo-2.10 tarball and the same cl and link lines as the lzo
family's lzo_minilzo_2.10_msvc recipe (lzo_msvc.py). An image whose PicHash
set is identical to that artefact is not committed; the measurement is in the
notes.
"""

import dataclasses

from .lzo_msvc import RECIPES as _LZO

RECIPES = {
    "miniLZO_2.10_msvc": dataclasses.replace(
        _LZO["lzo_minilzo_2.10_msvc"], family="miniLZO", version="2.10",
        notes="miniLZO 2.10, the lzo1x subset vendored byte-identically in "
              "UltraVNC (minilzo.c 213674 bytes), built from the "
              "minilzo-2.10 tarball as its own family per tracker #59, with "
              "the lzo family's lzo_minilzo_2.10_msvc command lines. "
              "Upstream is unpatched; exports are generated from the "
              "compiled object. Built against the DLL runtime."),
}

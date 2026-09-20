"""Declarative description of a reference build.

A recipe says where upstream source comes from, how to turn it into PE/ELF
binaries, and how the resulting artefacts should be labelled in the corpus.
Recipes carry no logic of their own so that every project goes through the
exact same fetch/build/disassemble/export code path.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Source:
    """Where the unmodified upstream source comes from.

    Exactly one of ``url`` (release tarball/zip) or ``git_url`` is used. A
    tarball is pinned by ``sha256``; a clone is pinned by ``git_ref``, which
    must be a tag or a full commit hash so the checkout is reproducible.
    """

    url: Optional[str] = None
    sha256: Optional[str] = None
    git_url: Optional[str] = None
    git_ref: Optional[str] = None
    # Directory inside the archive that holds the source, if it is not the
    # single top level directory the archive unpacks to.
    strip_prefix: Optional[str] = None


@dataclass
class BuildStep:
    """One shell command, run inside the unpacked source tree.

    ``cwd`` is relative to the source root. ``env`` is merged on top of the
    toolchain environment. Placeholders of the form ``{cc}``, ``{cxx}``,
    ``{prefix}``, ``{bitness}``, ``{arch}``, ``{cflags}``, ``{out}`` are
    substituted from the toolchain and the artefact directory.
    """

    command: str
    cwd: str = "."
    env: Dict[str, str] = field(default_factory=dict)
    # A step may legitimately fail (e.g. an optional "make clean" on a tree
    # that was never built). Everything else aborts the recipe.
    allow_failure: bool = False


@dataclass
class Artifact:
    """A binary the build is expected to produce, and how to label it.

    ``path`` is relative to the source root. ``component`` mirrors the SMDA
    metadata field used throughout the corpus to distinguish several binaries
    belonging to the same project/version.
    """

    path: str
    component: str = ""
    # Overrides the recipe-level family, for projects that vendor a second
    # upstream project whose code should not be attributed to the host family.
    family: Optional[str] = None
    is_library: bool = True
    # A position-independent code blob rather than a PE/ELF image. Raw bytes
    # carry no container header, so the bitness has to be stated and the base
    # address is arbitrary; SMDA disassembles it as a buffer, which is the
    # same route the aPLib reports in this repository took.
    is_blob: bool = False
    bitness: Optional[int] = None
    base_addr: int = 0x400000
    # Overrides the recipe-level build_flags, for a recipe whose artefacts
    # were not all produced the same way - donut ships both a GCC-built
    # generator and MSVC-compiled loader blobs.
    build_flags: Optional[str] = None


@dataclass
class Recipe:
    """A project/version/toolchain combination to add to the corpus."""

    # Corpus family name; also the data/<family>/ directory.
    family: str
    version: str
    source: Source
    build: List[BuildStep]
    artifacts: List[Artifact]
    # Toolchain ids from corpus.toolchain, e.g. ["mingw13_x86", "mingw13_x64"].
    toolchains: List[str]
    # Additional pinned sources a build needs, as {placeholder: Source}. Each
    # is fetched and verified like the main source, and the placeholder
    # expands to the downloaded archive (or checkout) path inside build steps.
    # Dependencies that are statically linked into the artefact have to come
    # through here, or their version and digest go unrecorded.
    extra_sources: Dict[str, Source] = field(default_factory=dict)
    # Free-form provenance recorded next to the generated data.
    upstream: str = ""
    license: str = ""
    notes: str = ""
    # Packages of this build that must be installed on the host, checked up
    # front so a recipe fails before spending time on a download.
    requires: List[str] = field(default_factory=list)
    # Drop MinGW C runtime glue that every DLL links in, so it is not
    # mis-attributed to this family. See corpus.baseline.
    drop_crt_glue: bool = True
    # Minimum share of functions that must carry a recovered symbol before the
    # build is accepted. Lower it only for projects that genuinely cannot keep
    # symbols; 0 disables the check.
    min_named_ratio: float = 0.5
    # What actually governs optimization for this build, recorded as
    # provenance: most upstream build systems set their own flags and ignore
    # the CFLAGS this tooling exports.
    build_flags: str = "upstream default"

    def slug(self, toolchain_id, artifact, arch=None):
        """Corpus filename stem, following the data/libzlib naming scheme:

        ``<family>_<version>_<toolchain>_<arch>_<component>``

        ``arch`` comes from the disassembled binary rather than the toolchain,
        because a build system can drive both cross compilers itself and emit
        32- and 64-bit output from a single run.
        """
        from .toolchain import get_toolchain

        toolchain = get_toolchain(toolchain_id)
        # A blob was compiled by whoever committed it upstream. Naming it after
        # the toolchain that merely ran the extraction would be a lie baked
        # into the filename, so those are labelled by their real compiler.
        producer = "msvc" if artifact.is_blob else toolchain.short_id
        parts = [self.family, self.version, producer, arch or toolchain.arch]
        component = artifact.component or _basename_component(artifact.path)
        parts.append(component)
        return "_".join(p for p in parts if p)


def _basename_component(path):
    import os

    return os.path.basename(path)

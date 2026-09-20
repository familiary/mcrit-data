"""Shared infrastructure for generating MCRIT reference data from upstream source.

The pipeline mirrors the one described in the repository README, with the
IDA Pro / lib2smda stage replaced by a direct SMDA pass over PE/ELF binaries:

    fetch  -> build -> smdaify -> export -> package -> validate

Every stage is deliberately fail-loud: a build that produces no artefact, a
disassembly that recovers no functions, or an export whose configuration
hashes do not match the existing corpus aborts the run instead of silently
committing unusable data.
"""

from .recipe import Artifact, BuildStep, Recipe, Source

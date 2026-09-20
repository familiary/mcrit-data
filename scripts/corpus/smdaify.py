"""Turn built binaries into SMDA reports carrying corpus provenance.

This replaces the lib2smda/IDA Pro stage of the README pipeline for inputs
that are PE or ELF images. MinGW writes a COFF symbol table into unstripped
output, which SMDA reads, so the resulting reports carry function symbols of
a quality comparable to the IDA-with-symbols path; static .LIB/.A archives
still need IDA and remain out of reach here.
"""

import logging
import os

from . import config
from .baseline import is_glue


LOGGER = logging.getLogger(__name__)


class DisassemblyError(RuntimeError):
    pass


def disassemble(path):
    from smda.Disassembler import Disassembler
    from smda.SmdaConfig import SmdaConfig

    smda_config = SmdaConfig()
    smda_config.CALCULATE_SCC = True
    smda_config.CALCULATE_NESTING = True
    return Disassembler(smda_config).disassembleFile(path)


def disassemble_blob(path, bitness, base_addr):
    """Disassemble position-independent code that has no container header.

    Shellcode carries no PE/ELF header to read the architecture and bitness
    from, so both have to be supplied. This is the same route the aPLib
    reports in this repository came through, and their metadata records it
    with ``is_buffer: true``.
    """
    from smda.Disassembler import Disassembler
    from smda.SmdaConfig import SmdaConfig

    with open(path, "rb") as handle:
        content = handle.read()
    smda_config = SmdaConfig()
    smda_config.CALCULATE_SCC = True
    smda_config.CALCULATE_NESTING = True
    # oep=0 tells SMDA the blob is entered at its first byte, which is how
    # shellcode is invoked. Without it the recursive pass starts elsewhere and
    # recovers a fraction of the code (79 of ~750 instructions on sRDI x64).
    return Disassembler(smda_config).disassembleBuffer(
        content, base_addr, bitness=bitness, architecture="intel", oep=0)


def _recompute_statistics(report):
    """Recompute the statistics block after functions have been removed.

    The counts end up in the .mcrit sample entry, so leaving them describing a
    function set that is no longer in the report would ship metadata that does
    not match its own data. Cross-function counts are re-derived against the
    retained set only, which is why the instruction map is built first.
    """
    from smda.DisassemblyStatistics import DisassemblyStatistics

    functions = list(report.getFunctions())
    retained_instructions = set()
    for function in functions:
        for block in function.blocks.values():
            for instruction in block:
                retained_instructions.add(instruction.offset)

    statistics = DisassemblyStatistics()
    statistics.num_functions = len(functions)
    statistics.num_basic_blocks = sum(f.num_blocks for f in functions)
    statistics.num_instructions = sum(f.num_instructions for f in functions)
    statistics.num_api_calls = sum(len(f.apirefs) for f in functions)
    # SMDA counts every reference to a function start, without regard to where
    # it came from. Filtering to surviving callers would be defensible on its
    # own terms but would stop this field meaning the same thing it means in
    # every report already in the corpus, so SMDA's definition is kept.
    statistics.num_function_calls = sum(len(f.inrefs) for f in functions)
    statistics.num_recursive_functions = len(
        [f for f in functions
         if any(f.offset in targets for targets in f.outrefs.values())]
    )
    statistics.num_leaf_functions = len([f for f in functions if f.num_outrefs == 0])
    statistics.num_thunk_functions = len([f for f in functions if f.isApiThunk()])
    # Failures are properties of the disassembly pass itself; the pass ran over
    # the whole binary regardless of what was retained afterwards.
    previous = report.statistics
    statistics.num_failed_functions = previous.num_failed_functions if previous else 0
    statistics.num_failed_instructions = previous.num_failed_instructions if previous else 0
    report.statistics = statistics

    # binweight and the cached block/instruction totals are computed once at
    # construction and would otherwise keep describing the pre-removal set;
    # binweight in particular is copied straight into the .mcrit sample entry.
    report.binweight = sum(f.binweight for f in functions)
    report._num_blocks = statistics.num_basic_blocks
    report._num_instructions = statistics.num_instructions


def _drop_crt_glue(report, toolchain_id):
    """Remove compiler runtime functions so they keep the MinGW family.

    A function is glue only when its symbol name and its PicHash both match a
    baseline measured from an otherwise empty DLL built with the same
    toolchain, so a project that provides its own version of a runtime symbol
    keeps it.
    """
    removed = []
    for offset, function in list(report.xcfg.items()):
        if is_glue(function, toolchain_id):
            removed.append(function.function_name)
            del report.xcfg[offset]
    # getFunctions() memoises its sorted list, so it has to be dropped or
    # everything downstream keeps seeing the functions just removed.
    report._sorted_functions = None
    if removed:
        _recompute_statistics(report)
        LOGGER.info("dropped %d MinGW runtime functions: %s", len(removed), ", ".join(sorted(removed)))
    return removed


def smdaify(binary_path, family, version, component, is_library=True,
            toolchain_id=None, drop_crt_glue=True, filename=None,
            min_named_ratio=0.5, is_blob=False, bitness=None,
            base_addr=0x400000):
    """Disassemble ``binary_path`` and label it the way the corpus expects."""
    if is_blob:
        if bitness not in (32, 64):
            raise DisassemblyError(
                "%s: a raw code blob has no header to read bitness from, so the "
                "recipe must state it" % binary_path)
        report = disassemble_blob(binary_path, bitness, base_addr)
        # Nothing in a stripped shellcode blob carries a symbol, and no
        # compiler runtime was linked in, so neither pass applies.
        min_named_ratio = 0
        drop_crt_glue = False
    else:
        report = disassemble(binary_path)
    if report.status != "ok":
        raise DisassemblyError("SMDA did not finish cleanly for %s: %s"
                               % (binary_path, report.message))

    removed = []
    if drop_crt_glue and toolchain_id:
        removed = _drop_crt_glue(report, toolchain_id)

    # MinGW writes a COFF symbol table unless the build strips it, and those
    # symbols are what makes this data comparable to the IDA-with-symbols
    # reports already in the corpus. A build system that strips by default
    # (zlib's win32/Makefile.gcc does) would otherwise quietly yield anonymous
    # reference data, so treat a symbol-poor report as a build failure.
    named = len([f for f in report.getFunctions() if f.function_name])
    if min_named_ratio and report.num_functions:
        ratio = named / report.num_functions
        if ratio < min_named_ratio:
            raise DisassemblyError(
                "%s: only %d of %d functions carry symbols (%.0f%%); the build "
                "most likely stripped them - pass STRIP=true to the build system"
                % (binary_path, named, report.num_functions, 100 * ratio))

    if is_blob:
        recovered = report.statistics.num_instructions if report.statistics else 0
        if recovered < config.MIN_USEFUL_BLOB_INSTRUCTIONS:
            raise DisassemblyError(
                "%s yielded only %d instructions, which is too little to be "
                "useful reference data" % (binary_path, recovered))
    elif report.num_functions < config.MIN_USEFUL_FUNCTIONS:
        raise DisassemblyError(
            "%s yielded only %d functions, which is too little to be useful reference data"
            % (binary_path, report.num_functions))

    report.family = family
    report.version = version
    report.component = component or ""
    report.is_library = is_library
    report.filename = filename or os.path.basename(binary_path)
    if is_blob:
        # Records how the report was produced, matching the aPLib entries.
        report.is_buffer = True
    return report, removed

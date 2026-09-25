"""Convert SMDA reports into ready-to-import .mcrit files.

The repository README describes submitting reports to a vanilla MCRIT
instance and using its export. The same MinHashIndex is used here against the
in-memory storage backend, which produces byte-identical export structures
without needing a MongoDB deployment.
"""

import json
import os

from . import config


class ExportError(RuntimeError):
    pass


def _fresh_index():
    # Imported lazily so `build_corpus.py list` and `validate` stay usable
    # without the analysis dependencies installed.
    from mcrit.config.McritConfig import McritConfig
    from mcrit.storage.StorageFactory import StorageFactory
    from mcrit.index.MinHashIndex import MinHashIndex

    mcrit_config = McritConfig()
    mcrit_config.STORAGE_CONFIG.STORAGE_METHOD = StorageFactory.STORAGE_METHOD_MEMORY
    mcrit_config.QUEUE_CONFIG.QUEUE_METHOD = "fake"
    return MinHashIndex(mcrit_config)


def export_reports(reports, output_path):
    """Index ``reports`` in a throwaway MCRIT and write the export.

    Each call uses a fresh index so sample ids stay deterministic and no state
    can leak between unrelated projects.
    """
    index = _fresh_index()
    for report in reports:
        index.addReportJson(report.toDict())

    export = index.getExportData(compress_data=True)
    _assert_compatible(export)

    if export["content"]["num_samples"] != len(reports):
        raise ExportError("expected %d samples in export, got %d"
                          % (len(reports), export["content"]["num_samples"]))
    if export["content"]["num_functions"] == 0:
        raise ExportError("export contains no functions")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(export, handle)
    return export


def _assert_compatible(export):
    """Refuse to write an export MCRIT could not reuse minhashes from.

    Every .mcrit file already in this repository carries the same two config
    hashes; an export that disagrees would import but never match against the
    rest of the corpus, which is worse than no data at all.
    """
    minhash = export["config"]["minhash"]
    shingler = export["config"]["shingler"]
    if minhash != config.EXPECTED_MINHASH_CONFIG:
        raise ExportError("minhash config hash %s does not match the corpus (%s)"
                          % (minhash, config.EXPECTED_MINHASH_CONFIG))
    if shingler != config.EXPECTED_SHINGLER_CONFIG:
        raise ExportError("shingler config hash %s does not match the corpus (%s)"
                          % (shingler, config.EXPECTED_SHINGLER_CONFIG))

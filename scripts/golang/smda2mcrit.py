# convert SMDA reports into a .mcrit export using in-memory storage (no MCRIT server or database involved)
# usage: smda2mcrit.py <output.mcrit> <report.smda> [<report.smda> ...]
import sys
import json

from mcrit.config.McritConfig import McritConfig
from mcrit.storage.StorageFactory import StorageFactory
from mcrit.queue.QueueFactory import QueueFactory
from mcrit.index.MinHashIndex import MinHashIndex

out, reports = sys.argv[1], sys.argv[2:]
config = McritConfig()
config.STORAGE_CONFIG.STORAGE_METHOD = StorageFactory.STORAGE_METHOD_MEMORY
config.QUEUE_CONFIG.QUEUE_METHOD = QueueFactory.QUEUE_METHOD_FAKE
# the indexing pool forks per CPU and multiplies the memory footprint of large reports
config.MINHASH_CONFIG.MINHASH_POOL_INDEXING = False
index = MinHashIndex(config)
for report_path in reports:
    with open(report_path) as fin:
        report_json = json.load(fin)
    index.addReportJson(report_json, calculate_hashes=True, calculate_matches=False)
    del report_json
    print(report_path, "added")
export = index.getExportData(compress_data=True)
with open(out, "w") as fout:
    json.dump(export, fout)
print(out, export["config"], export["content"])

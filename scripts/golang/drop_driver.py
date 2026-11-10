# Remove the coverage driver's own main.* functions from an SMDA report, the
# step the default 1.27.3 references record as "only main.* coverage-driver
# functions are removed", and recompute the statistics block over what is left
# with the corpus pipeline's own routine.
# usage: drop_driver.py <in.smda> <out.smda>
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from smda.common.SmdaReport import SmdaReport
from corpus.smdaify import _recompute_statistics

src, dst = sys.argv[1:3]
with open(src) as fin:
    report = SmdaReport.fromDict(json.load(fin))
removed = []
for offset, function in list(report.xcfg.items()):
    name = function.function_name or ""
    if name.startswith("main."):
        removed.append((name, function.num_instructions, function.pic_hash))
        del report.xcfg[offset]
_recompute_statistics(report)
with open(dst, "w") as fout:
    json.dump(report.toDict(), fout)
print("removed %d driver function(s): %s" % (len(removed), removed))
print("kept %d" % report.num_functions)

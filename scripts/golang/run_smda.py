# disassemble a Golang reference binary with SMDA and label it as library code
# usage: run_smda.py <binary> <output.smda> <version label> <filename label>
import sys
import json
import time

from smda.Disassembler import Disassembler
from smda.SmdaConfig import SmdaConfig

path, out, version, filename = sys.argv[1:5]
start = time.time()
config = SmdaConfig()
# the default of 300s is not enough for ~20k functions
config.TIMEOUT = 3600
report = Disassembler(config).disassembleFile(path)
report_dict = report.toDict()
report_dict["metadata"].update({"family": "Golang", "version": version, "is_library": True, "filename": filename})
with open(out, "w") as fout:
    json.dump(report_dict, fout)
functions = list(report_dict["xcfg"].values())
named = sum(1 for f in functions if f.get("metadata", {}).get("function_name"))
print(out, report_dict["status"], "functions", len(functions), "named", named, "stats", report_dict["statistics"], "time %.1f" % (time.time() - start))

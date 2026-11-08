"""Scratch: crawl every installed old toolset and dump function PicHashes.

Run on the runner after the toolsets were installed. For each toolset and the
leg's architecture it links every shard (crawl_vclib.py), disassembles the
image with the corpus's own smdaify and writes
out/<toolset>_<arch>_<shard>.json with [pic_hash, instruction_count, name]
per function. Nothing here is committed to the corpus.
"""
import json, os, subprocess, sys, time, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
from corpus import crawl_vclib
from corpus.smdaify import smdaify

arch = sys.argv[1]
out = os.path.abspath(sys.argv[2])
only = sys.argv[3:]
os.makedirs(out, exist_ok=True)
toolsets = crawl_vclib.find_toolsets()
print("toolsets found:", ", ".join(sorted(toolsets)) or "none", flush=True)
summary = []
for version in sorted(toolsets):
    if only and version not in only:
        continue
    work = os.path.join(out, "work_" + version)
    os.makedirs(work, exist_ok=True)
    for shard in crawl_vclib.SHARDS:
        t0 = time.time()
        rec = {"toolset": version, "arch": arch, "shard": shard}
        try:
            name = crawl_vclib.crawl(version, toolsets[version], arch, shard, work)
            if name is None:
                rec["status"] = "absent"
                summary.append(rec)
                continue
            dll = os.path.join(work, name + ".dll")
            report, _ = smdaify(dll, "scratch", version, shard, drop_crt_glue=False,
                                min_named_ratio=0, min_functions=1,
                                pdb_path=os.path.join(work, name + ".pdb"), dedupe=True)
            funcs = [[f.pic_hash, f.num_instructions, f.function_name]
                     for f in report.getFunctions()]
            named = sum(1 for f in funcs if f[2])
            inputs = json.load(open(os.path.join(work, name + ".inputs.json")))
            json.dump({"inputs": inputs, "functions": funcs,
                       "image_bytes": os.path.getsize(dll)},
                      open(os.path.join(out, "%s_%s_%s.json" % (version, arch, shard)), "w"))
            rec.update(status="ok", functions=len(funcs), named=named,
                       seconds=round(time.time() - t0))
        except BaseException as e:
            traceback.print_exc()
            rec.update(status="failed", error=str(e)[-1500:])
        print(json.dumps(rec), flush=True)
        summary.append(rec)
        for f in os.listdir(work):
            if f.endswith((".dll", ".pdb")):
                os.remove(os.path.join(work, f))
json.dump(summary, open(os.path.join(out, "summary_%s.json" % arch), "w"), indent=1)

"""Scratch: crawl every installed old toolset and dump function PicHashes.

    measure_oldtoolsets.py <arch> <outdir>            drive every task, 4 at a time
    measure_oldtoolsets.py --one <arch> <outdir> <toolset> <shard>

Each (toolset, shard) task runs in its own process under a hard timeout, so a
pathological image costs one task and not the run. Writes
<outdir>/<toolset>_<arch>_<shard>.json with [pic_hash, instruction_count, name]
per function plus the crawl's inputs record.
"""
import json, os, subprocess, sys, time, traceback
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
from corpus import crawl_vclib

TIMEOUT = int(os.environ.get("TASK_TIMEOUT", "1200"))


def key(v):
    return [int(x) for x in v.split(".")]


def one(arch, out, version, shard):
    from corpus.smdaify import smdaify
    toolsets = crawl_vclib.find_toolsets()
    work = os.path.join(out, "work_%s_%s" % (version, shard))
    os.makedirs(work, exist_ok=True)
    t0 = time.time()
    rec = {"toolset": version, "arch": arch, "shard": shard}
    try:
        name = crawl_vclib.crawl(version, toolsets[version], arch, shard, work)
        if name is None:
            rec["status"] = "absent"
        else:
            dll = os.path.join(work, name + ".dll")
            t1 = time.time()
            report, _ = smdaify(dll, "scratch", version, shard, drop_crt_glue=False,
                                min_named_ratio=0, min_functions=1,
                                pdb_path=os.path.join(work, name + ".pdb"), dedupe=True)
            funcs = [[f.pic_hash, f.num_instructions, f.function_name]
                     for f in report.getFunctions()]
            inputs = json.load(open(os.path.join(work, name + ".inputs.json")))
            json.dump({"inputs": inputs, "functions": funcs,
                       "image_bytes": os.path.getsize(dll)},
                      open(os.path.join(out, "%s_%s_%s.json" % (version, arch, shard)), "w"))
            rec.update(status="ok", functions=len(funcs),
                       named=sum(1 for f in funcs if f[2]),
                       image_bytes=os.path.getsize(dll),
                       link_seconds=round(t1 - t0), seconds=round(time.time() - t0))
    except BaseException as e:
        traceback.print_exc()
        rec.update(status="failed", error=str(e)[-1500:])
    print("RESULT " + json.dumps(rec), flush=True)
    for f in os.listdir(work):
        if f.endswith((".dll", ".pdb")):
            os.remove(os.path.join(work, f))


def drive(arch, out):
    os.makedirs(out, exist_ok=True)
    only = os.environ.get("SHARDS", "").split()
    toolsets = crawl_vclib.find_toolsets()
    print("toolsets found:", ", ".join(sorted(toolsets, key=key)), flush=True)
    tasks = [(v, s) for v in sorted(toolsets, key=key) for s in crawl_vclib.SHARDS
             if not only or s in only]

    def run(task):
        version, shard = task
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", arch,
                                out, version, shard], capture_output=True, text=True,
                               timeout=TIMEOUT, errors="replace")
            text = (p.stdout or "") + (p.stderr or "")
        except subprocess.TimeoutExpired:
            text = "RESULT " + json.dumps({"toolset": version, "arch": arch, "shard": shard,
                                           "status": "timeout", "seconds": TIMEOUT})
        for line in text.splitlines():
            if line.startswith("RESULT "):
                print(line[7:], flush=True)
                return
        print(json.dumps({"toolset": version, "arch": arch, "shard": shard,
                          "status": "crashed", "tail": text[-800:]}), flush=True)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(run, tasks))


if __name__ == "__main__":
    if sys.argv[1] == "--one":
        one(*sys.argv[2:6])
    else:
        drive(sys.argv[1], sys.argv[2])

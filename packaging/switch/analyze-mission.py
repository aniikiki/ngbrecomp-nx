"""Summarize mission-perf.csv; phase and nested timings are not additive."""
import argparse
import csv
from collections import Counter
from math import ceil
from statistics import mean

def summarize(path):
    groups = {"M": [], "D": []}
    fields = {}
    with open(path, encoding="utf8") as f:
        for line in f:
            if line.startswith("# "):
                k, names = line[2:].strip().split(": ", 1)
                fields[k] = names.split(",")
                continue
            kind, *raw = next(csv.reader([line]))
            if kind not in groups or kind not in fields or len(raw) != len(fields[kind]):
                raise ValueError(f"Invalid or incomplete {kind} record")
            groups[kind].append(dict(zip(fields[kind], map(int, raw))))
    rows = groups["M"]
    if not rows:
        raise ValueError("No Mission loop samples")
    def times(label, values):
        vals = sorted(values)
        if vals:
            print(f"{label:22} avg={mean(vals)/1000:7.2f} ms  p95={vals[ceil(.95*len(vals))-1]/1000:7.2f} ms")
    print(f"Mission iterations: {len(rows)}; display samples: {len(groups['D'])}")
    print("Menu state counts:", dict(Counter(r["state"] for r in rows)))
    times("whole iteration", (r["update_us"]+r["draw_us"]+r["wait_call_us"] for r in rows))
    for col in ("update_us","draw_us","wait_call_us","update_cpu_us","draw_cpu_us","wait_cpu_us","strip_us","read_us","upload_us"):
        times(col, (r[col] for r in rows if "_cpu_" not in col or not r["cpu_rc"]))
    for col in ("gl_draws","gl_reads","fb_uploads","vk_draws","vk_presents","guest_flips","thumb_hit","thumb_miss"):
        print(f"{col:22} total={sum(r[col] for r in rows)}")
    # These are independent stage counts. Identical source images may be suppressed.
    if "published" in rows[0]:
        for col in ("published","displayed"):
            print(f"{col:22} total={sum(r[col] for r in rows)}")
    n=sum(r.get("split_reads",0) for r in rows)
    if n:
        print(f"GL split: {n} reads; finish={sum(r['finish_us'] for r in rows)/n/1000:.3f} ms/read; after finish={sum(r['post_finish_read_us'] for r in rows)/n/1000:.3f} ms/read")
    for col in ("acquire_us","blit_overlay_us","end_us"):
        times(col, (r[col] for r in groups["D"]))
    print("Nested strip/GL times and the parallel display thread must not be added to iteration time.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log")
    summarize(parser.parse_args().log)

#!/usr/bin/env python3
"""Summarize a 0.43+ Switch boot.log using the matching nm -nS -C symbols.gz."""
import argparse
import bisect
import gzip
import math
import re
from collections import Counter
from pathlib import Path


def load_symbols(path):
    table = []
    gates = {}
    with gzip.open(path, "rt") as file:
        for line in file:
            match = re.fullmatch(r"(\w+) (\w+) [TtWw] (.+)\n", line)
            if match:
                table.append((int(match[1], 16), int(match[2], 16), match[3]))
            else:
                # The release symbol bundle has address-only gate rows. Each
                # gate uses the same 13 AArch64 instructions (gates.py).
                gate = re.fullmatch(r"(\w+) [Tt] (ngb_gate_\w+)\n", line)
                if gate:
                    gates[int(gate[1], 16)] = gate[2]
    # Only infer the length where the next contiguous gate proves it.
    table.extend((a, 52, label) for a, label in gates.items() if a+52 in gates)
    table.sort()
    starts = [row[0] for row in table]

    def name(address):
        i = bisect.bisect_right(starts, address) - 1
        if i >= 0:
            start, size, label = table[i]
            if address < start + size:
                return label
        return f"0x{address:x}"

    return name


def parse_windows(lines):
    windows = {}
    for line in lines:
        if line.startswith("[PROFILE_WINDOW]"):
            first, last = map(int, re.findall(r"\d+", line))
            window = windows[first, last] = {"cpu": [], "profiles": {}}
        elif line.startswith("[SCHED]") and "skipped_waiters=" in line:
            fields = dict(word.split("=") for word in line.split()[1:])
            if int(fields["first"]) == first:
                window["scheduler"] = tuple(int(fields[key]) for key in
                                            ("frames", "switches", "skipped_waiters"))
        elif line.startswith("[FRAME_CPU]"):
            args = dict(word.split("=") for word in line.split()[1:])
            window["cpu"].append((int(args["frame"]), int(args["wall_us"]),
                                  int(args["guest_cpu_us"]), int(args["rc"], 16),
                                  int(args["draws"]), int(args["entries"]), int(args["polls"])))
        elif line.startswith("[CALLERS]"):
            args = dict(word.split("=") for word in line.split()[1:])
            profile = window["profiles"][args["thread"]] = (args, [])
        elif line.startswith("[STACK]"):
            fields = line.split()[1:]
            frame, worker, scope, wall, cpu = map(int, fields[:5])
            profile[1].append((frame, worker, scope, wall, cpu,
                               [int(pc, 16) for pc in fields[5:]]))
    return windows


def show_stacks(rows, symbol, heading, folded_file):
    if not rows:
        return
    counts, leaves, workers, depths = Counter(), Counter(), Counter(), []
    tasks = Counter()
    for _, worker, _, _, _, pcs in rows:
        stack = [symbol(pc) for pc in pcs]
        depths.append(len(stack))
        workers[worker] += 1
        if not stack:
            leaves["<no saved PC>"] += 1
            continue
        # rc1 has a public trampoline and a private ARM implementation.
        # Keep raw names for inclusive/leaf and folded views.
        logical = [label.removeprefix("ngb_reg_") for label in stack]
        if "sub_0030C8B0" in logical:
            # The XBE task trampoline loads its callback from task + 0xc.
            at = logical.index("sub_0030C8B0")
            if at:
                while at and logical[at - 1] == "ngb_gate_indirect":
                    at -= 1
                if at:
                    tasks[logical[at - 1]] += 1
        leaves[stack[0]] += 1
        counts.update(set(stack))
        if folded_file:
            print(";".join([heading, *reversed(stack)]), 1, file=folded_file)
    print(f"  {heading}: {len(rows)} wall samples, median stack depth "
          f"{sorted(depths)[len(depths)//2]}, leaf-only {depths.count(1)}, workers {dict(workers)}")
    if tasks:
        print(f"    samples with a task caller {sum(tasks.values())}/{len(rows)}:", tasks.most_common(12))
    print("    leaf:     ", leaves.most_common(10))
    print("    inclusive:", counts.most_common(20))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("symbols", type=Path)
    parser.add_argument("--folded", type=argparse.FileType("w"))
    args = parser.parse_args()
    symbol = load_symbols(args.symbols)
    windows = parse_windows(args.log.read_text().splitlines())
    if not any(w["profiles"] for w in windows.values()):
        parser.error("no saved call stacks in this log")
    for (first, last), window in windows.items():
        frames = window["cpu"]
        print(f"Frames {first}-{last}, captured {len(frames)}/{last-first+1}")
        if "scheduler" in window:
            n, switches, skips = window["scheduler"]
            if n:
                print(f"  Xbox fiber switches/frame: {switches/n:.1f}; "
                      f"unready event waiters bypassed/frame: {skips/n:.1f}")
        if frames:
            wall = sorted(row[1] for row in frames)
            print(f"  mean wall {sum(wall)/len(wall)/1000:.2f} ms, "
                  f"P95 {wall[math.ceil(len(wall)*.95)-1]/1000:.2f} ms")
            print("  draws / guest entries / poll checks per frame:",
                  *(round(sum(r[i] for r in frames)/len(frames), 1) for i in (4, 5, 6)))
            valid = [r for r in frames if not r[3]]
            if valid:
                print(f"  mean game CPU {sum(r[2] for r in valid)/len(valid)/1000:.2f} ms, "
                      f"mean off-CPU {sum(r[1]-r[2] for r in valid)/len(valid)/1000:.2f} ms "
                      f"({len(valid)} frames)")
            if len(frames) != len(valid):
                print("  missing game CPU ticks:", Counter(r[3] for r in frames if r[3]))
        for role, (flags, rows) in window["profiles"].items():
            rows = [r for r in rows if first <= r[0] <= last]
            if len(rows) >= 2 and not int(flags["clock_rc"], 16):
                wall_span = rows[-1][3] - rows[0][3]
                cpu_span = rows[-1][4] - rows[0][4]
                if wall_span > 0:
                    print(f"  {role} scheduled {cpu_span/wall_span:.1%} of sampled interval "
                          f"({wall_span/int(flags['tick_hz']):.2f} s)")
            show_stacks(rows, symbol, f"{first}/{role}", args.folded)
            if role == "guest":
                outside = [r for r in rows if r[2] == 0]
                show_stacks(outside, symbol, f"{first}/guest-outside-mesh-and-setters", None)


if __name__ == "__main__":
    main()

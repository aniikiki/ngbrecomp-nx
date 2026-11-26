"""Attribute archived guest PC samples and the frame records captured with them.

Run with the symbols and NRO archived alongside the recorded build. Optional
--objdump disassembles the NRO bytes, not a newly linked or host executable.
The time equivalents are sampling estimates, not instrumented function timings.
"""
import argparse
import bisect
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import statistics as st
import struct
import subprocess
import tempfile


# Guest addresses are deliberately explicit. Do not infer a subsystem from an
# address range, a caller's name alone, or the appearance of a math instruction.
# These labels describe the sampled function, not its unobserved ancestors.
GUEST_GROUPS = {
    "game render preparation": {
        "001CA790", "001CB260", "001D7130", "002216B0", "00222730",
        "00308130", "00308D50", "0030B7E0", "0030BA30", "0030BCA0",
        "0030C1A0", "00314430", "00317540", "00317DC0",
    },
    "collision queries": {
        "0013DD60", "0013DE30", "0013ED30", "0013F960", "00140AF0", "00142910",
    },
    "geometry and matrix math": {
        "00014420", "00037260", "00039030", "00189EB0", "0018A4B0",
        "0018A8F0", "00305950", "00328232", "0036FDB8", "0037A480", "0037A5C5",
    },
    "actor state checks": {"0001CA90", "000299D0", "0002ADC0", "0003B420"},
    "other guest library or dispatch": {"00297860", "0032D49E", "003433F0", "003E11E3"},
}
XDK_NAMES = {
    "003C52A0": "SetRenderState_ShadowFunc", "003C5F60": "D3D state helper",
    "003C7270": "SetViewport", "003C7490": "SetLight", "003C79A0": "SetTexture",
    "003C7DB0": "SetScissors", "003C8710": "SetStreamSource",
    "003CAA10": "BlockOnTime", "003D20A0": "SetStateUP",
}


def load_log(path):
    schemas, rows, lost, partial = {}, defaultdict(list), Counter(), 0
    session = None
    with path.open() as source:
        for fields in csv.reader(source):
            if not fields:
                continue
            kind, *values = fields
            if kind == "#SESSION":
                schemas.clear(); rows.clear(); lost.clear(); partial = 0
                session = values
            elif kind == "#LOST":
                lost[values[0]] += int(values[1])
            elif kind.startswith("#"):
                schemas[kind[1:]] = values
            elif kind in schemas:
                if len(values) != len(schemas[kind]) or not all(v.isdecimal() for v in values):
                    partial += 1
                    continue
                rows[kind].append(dict(zip(schemas[kind], map(int, values))))
    return session, rows, dict(lost), partial


class Symbols:
    def __init__(self, path, text_end):
        by_address = {}
        with gzip.open(path, "rt") as source:
            for line in source:
                parts = line.split()
                if len(parts) not in (3, 4) or parts[-2] not in "TtWw":
                    continue
                address = int(parts[0], 16)
                size = int(parts[1], 16) if len(parts) == 4 else 0
                # Prefer an explicitly sized alias at a shared start address.
                if address not in by_address or size > by_address[address][0]:
                    by_address[address] = size, parts[-1]
        self.starts = sorted(by_address)
        self.entries = []
        for i, address in enumerate(self.starts):
            size, name = by_address[address]
            end = address + size if size else min(
                text_end, self.starts[i + 1] if i + 1 < len(self.starts) else address,
                address + 64)
            self.entries.append((address, end, name, bool(size)))

    def lookup(self, address):
        i = bisect.bisect_right(self.starts, address) - 1
        if i >= 0:
            start, end, name, sized = self.entries[i]
            if start <= address < end:
                return name, start, end, "sized" if sized else "next-symbol bound (<=64 bytes)"
        return "unresolved", address, address, "unresolved"


def guest_address(name):
    match = re.fullmatch(r"(?:ngb_reg_)?(?:sub_|d3d_orig_)([0-9A-F]{8})(?:\.localalias)?", name)
    return match[1] if match else None


def saved_callers(sample, symbols, text_size):
    # The recorder already converted each saved return address to its call site.
    # PC and live LR are separately sampled registers, not saved frames.
    chain = []
    for i in range(min(sample.get("depth", 0), 12)):
        site = sample.get(f"caller{i}")
        if site is None or site >= text_size or site % 4:
            break
        name = symbols.lookup(site)[0]
        chain.append(hex(site) if name == "unresolved" else name)
    return tuple(chain)


def short_name(name):
    recorded = re.search(r"Recorded(\d+)([A-Za-z_].*)", name)
    if recorded:
        return "Recorded::" + recorded[2][:int(recorded[1])]
    if "_Map_base" in name:
        return "header unordered_map::operator[]"
    if "condition_variable10notify_one" in name:
        return "condition_variable::notify_one"
    return name


def branch(word, address):
    if word & 0xfc000000 in (0x94000000, 0x14000000):
        offset = word & 0x3ffffff
        if offset & 0x2000000:
            offset -= 0x4000000
        return ("BL" if word & 0xfc000000 == 0x94000000 else "B"), address + offset * 4
    if word & 0xfffffc1f == 0xd63f0000:
        return "BLR", None
    return "other", None


def call_evidence(nro, symbols, pc, lr):
    leaf, start, end, _ = symbols.lookup(pc)
    if lr < 4 or lr == 0xffffffff or lr > len(nro):
        return "invalid LR", "unresolved", None, ""
    caller = symbols.lookup(lr - 4)[0]
    op, target = branch(struct.unpack_from("<I", nro, lr - 4)[0], lr - 4)
    if caller == leaf and leaf != "unresolved":
        # Non-leaf ARM functions commonly retain their last internal return PC.
        return "LR is inside sampled function; no parent recovered", caller, target, op
    if op == "BL" and start <= target < end and leaf != "unresolved":
        return "direct call target matches sampled function", caller, target, op
    if op == "BLR":
        return "indirect call; target not recorded", caller, None, op
    return "LR alone does not establish parent", caller, target, op


def classify(leaf, caller, evidence):
    address = guest_address(leaf)
    if address in XDK_NAMES:
        return ("BlockOnTime path" if address == "003CAA10" else "XDK state and resource work"), XDK_NAMES[address]
    for group, addresses in GUEST_GROUPS.items():
        if address in addresses:
            return group, address
    if leaf in {"execute_dma", "service_dma", "submit_dma", "direct_state_words", "state_packet_size", "retire_state_packets"}:
        return "NV2A FIFO parsing", leaf
    if "Recorded" in leaf:
        return "draw capture and command recording", short_name(leaf)
    parent_valid = evidence == "direct call target matches sampled function"
    if parent_valid and "Recorded" in caller:
        return "draw capture and command recording", short_name(caller) + " -> " + short_name(leaf)
    if parent_valid and "L4DrawE" in caller:
        return "draw capture and command recording", "HLE Draw -> " + leaf
    if parent_valid and "L6Before" in caller:
        return "XDK state and resource work", "HLE Before -> " + leaf
    if parent_valid and guest_address(caller) == "003CAA10":
        return "BlockOnTime path", "BlockOnTime -> " + leaf
    if parent_valid and guest_address(caller) == "00317DC0":
        return "game render preparation", "00317DC0 -> " + leaf
    if leaf in {"atan", "cos", "sin", "__kernel_cos", "__kernel_sin", "__ieee754_rem_pio2"}:
        return "geometry and matrix math", leaf
    if leaf.startswith("ngb_gate_") or leaf in {
        "ngb_guest_pointer", "ngb_guest_scalar_fallback", "ngb_reg_checkpoint", "ngb_checkpoint",
        "ngb_timers_poll", "ngb_poll_due", "recomp_lookup", "svcArbitrateUnlock", "_free_r",
    }:
        return "runtime, scheduling and host support", leaf
    return "unattributed", leaf


def summary(values):
    if not values:
        return None
    values = sorted(values)
    return {"mean": st.mean(values), "median": st.median(values),
            "p95_nearest_rank": values[(95 * len(values) + 99) // 100 - 1]}


def disassemble(objdump, nro, addresses):
    result = {}
    with tempfile.TemporaryDirectory(prefix="ngb-alma-pc-") as temp:
        fragment = Path(temp) / "instruction.bin"
        for address in sorted(set(addresses)):
            if address < 0 or address + 4 > len(nro):
                continue
            fragment.write_bytes(nro[address:address + 4])
            raw = subprocess.check_output([
                objdump, "-D", "-b", "binary", "-m", "aarch64", f"--adjust-vma={address}", str(fragment)
            ], text=True)
            match = re.search(r"^\s*[0-9a-f]+:\s+[0-9a-f]{8}\s+(.+)$", raw, re.M)
            if not match:
                raise ValueError(f"No instruction decoded at {address:#x}")
            result[address] = match[1].strip()
    return result


def report(args):
    session, rows, lost, partial = load_log(args.log)
    if not rows["G"]:
        raise ValueError("No guest boundaries in the last session")
    origin = rows["G"][0]["time_us"]
    seconds = lambda r: (r["time_us"] - origin) / 1e6
    inside = lambda r: args.start <= seconds(r) < args.end
    pairs = [(a, b) for a, b in zip(rows["G"], rows["G"][1:])
             if inside(a) and inside(b) and a["active"] and b["active"]
             and b["guest_flip"] == a["guest_flip"] + 1]
    if not pairs:
        raise ValueError("No consecutive active guest boundaries in this window")
    valid = [(a, b) for a, b in pairs if 0 < a["cpu_us"] <= b["cpu_us"]]
    cpu = summary([(b["cpu_us"] - a["cpu_us"]) / 1000 for a, b in valid])
    wall = summary([(b["time_us"] - a["time_us"]) / 1000 for a, b in pairs])
    nro = args.nro.read_bytes()
    if nro[16:20] != b"NRO0":
        raise ValueError("Not an NRO")
    text_start, text_size = struct.unpack_from("<II", nro, 32)
    if text_start != 0 or text_size > len(nro):
        raise ValueError("Unsupported NRO text layout")
    symbols = Symbols(args.symbols, text_size)
    samples = [r for r in rows["P"] if inside(r) and not r["renderer"]]
    accepted = [r for r in samples if not r["rc"] and r["pc_offset"] != 0xffffffff]
    if not accepted:
        raise ValueError("No valid guest PC samples in window")
    if any(r["pc_offset"] % 4 or r["pc_offset"] >= text_size for r in accepted):
        raise ValueError("A guest PC falls outside aligned NRO text")
    instructions = disassemble(args.objdump, nro,
                               [a for r in accepted for a in
                                (*range(r["pc_offset"], r["pc_offset"] + 20, 4),
                                 *range(r["lr_offset"] - 20, r["lr_offset"], 4))]) if args.objdump else {}
    details, groups, paths, evidence_counts = [], Counter(), Counter(), Counter()
    chains = Counter()
    instruction_overlay = Counter()
    blocks = defaultdict(Counter)
    for sample in accepted:
        pc, lr = sample["pc_offset"], sample["lr_offset"]
        leaf, _, _, extent = symbols.lookup(pc)
        parents = saved_callers(sample, symbols, text_size)
        if parents:
            chains[(leaf, *parents)] += 1
        evidence, caller, target, op = call_evidence(nro, symbols, pc, lr)
        group, path = classify(leaf, caller, evidence)
        instruction = instructions.get(pc, "")
        overlay = ""
        if leaf.startswith("ngb_reg_") and guest_address(leaf):
            if re.match(r"ldr\s+w\d+, \[x27, x\d+, lsl #2\]$", instruction):
                overlay = "guest page-end table load"
            alias = re.match(r"and\s+([wx])(\d+), \1\2, #0x7fffffff$", instruction)
            if alias:
                reg = alias[2]
                following = [instructions.get(pc + offset, "") for offset in (4, 8, 12, 16)]
                if any(re.search(r"\[x26, w" + reg + r", uxtw\]", ins) or
                       re.fullmatch(r"add\s+x" + reg + r", x26, x" + reg, ins) for ins in following):
                    overlay = "RAM alias mask (nearby x26 access verified)"
        if overlay:
            instruction_overlay[overlay] += 1
        groups[group] += 1; paths[group, path] += 1; evidence_counts[evidence] += 1
        blocks[int((seconds(sample) - args.start) // 5)][group] += 1
        details.append({"seconds": seconds(sample), "pc": hex(pc), "lr": hex(lr),
                        "saved_callers_nearest_first": " | ".join(parents),
                        "pc_symbol": leaf, "symbol_extent": extent, "lr_site_symbol": caller,
                        "lr_site_op": op, "lr_target": hex(target) if target is not None else "",
                        "lr_target_symbol": symbols.lookup(target)[0] if target is not None else "",
                        "call_evidence": evidence, "group": group, "path": path,
                        "pc_instruction": instructions.get(pc, ""), "lr_instruction": instructions.get(lr - 4, ""),
                        "instructions_before_lr_call": " | ".join(instructions.get(lr - i, "") for i in (20, 16, 12, 8)),
                        "instruction_overlay_NOT_additive": overlay,
                        "next_four_instructions": " | ".join(instructions.get(pc + i, "") for i in (4, 8, 12, 16)),
                        "pause_cost_us": sample["pause_cost_us"]})
    renders = [r for r in rows["R"] if inside(r)]
    gpu = defaultdict(list)
    for q in rows["Q"]:
        gpu[q["submit_frame"]].append(q)
    gpu_times = [sum(q["gpu_us"] for q in gpu[r["present"]]) / 1000 for r in renders
                 if gpu[r["present"]] and all(q["valid"] for q in gpu[r["present"]])]
    render_pairs = [(a, b) for a, b in zip(renders, renders[1:]) if b["present"] == a["present"] + 1]
    group_rows = [{"group": group, "samples": n, "fraction": n / len(accepted),
                   "cpu_ms_equivalent_NOT_measured": cpu["mean"] * n / len(accepted) if cpu else None,
                   "five_second_counts": [blocks[i][group] for i in range(len(blocks))]}
                  for group, n in groups.most_common()]
    result = {
        "session": session, "window_seconds": [args.start, args.end], "guest_intervals": len(pairs),
        "guest_cpu_intervals": len(valid), "guest_wall_ms": wall, "guest_cpu_ms": cpu,
        "render_intervals": len(render_pairs),
        "render_cpu_ms": summary([(b["cpu_us"] - a["cpu_us"]) / 1000 for a, b in render_pairs
                                  if 0 < a["cpu_us"] <= b["cpu_us"]]),
        "render_frames": len(renders), "gpu_covered_frames": len(gpu_times), "gpu_ms": summary(gpu_times),
        "render_wait_ms_per_present": st.mean((b["guest_wait_us_total"] - a["guest_wait_us_total"]) / 1000
                                                for a, b in render_pairs) if render_pairs else None,
        "samples": len(accepted), "rejected_samples": len(samples) - len(accepted),
        "sample_pause_us": sum(r["pause_cost_us"] for r in accepted),
        "lost": lost, "partial_records": partial, "call_evidence": dict(evidence_counts),
        "samples_with_saved_callers": sum(chains.values()),
        "recorded_chains": [{"leaf_and_saved_callers": chain, "samples": n}
                            for chain, n in chains.most_common()],
        "instruction_overlay_NOT_additive": dict(instruction_overlay),
        "groups": group_rows, "five_second_sample_totals": [sum(blocks[i].values()) for i in range(len(blocks))],
        "clocks": [dict(zip(("cpu_hz", "gpu_hz", "emc_hz", "cpu_rc", "gpu_rc", "emc_rc"), k), count=n)
                   for k, n in Counter(tuple(r[k] for k in ("cpu_hz", "gpu_hz", "emc_hz", "cpu_rc", "gpu_rc", "emc_rc"))
                                       for r in rows["C"]).items()],
        "nro_build_id": nro[64:96].hex(),
        "inputs": {key: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                   for key, path in (("log", args.log), ("symbols", args.symbols), ("nro", args.nro))},
        "limitations": [
            "Each chain contains the sampled PC and available frame records, nearest first. "
            "Older logs have only PC/LR. Tail calls and functions without frame records can be absent.",
            "Internal LR is not evidence of recursion or of the sampled function's caller.",
            "PC snapshots sample elapsed time, including possible off-CPU time; CPU equivalents assume representative sampling.",
            "Five-second counts expose variability; 82 samples do not establish precise per-function milliseconds.",
            "Log records version, not NRO hash/build ID. The archived version match is not cryptographic provenance.",
            "Game, render and GPU times overlap. Do not add them or attach host replay timings to these paths.",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    with (args.output / "samples.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(details[0])); writer.writeheader(); writer.writerows(details)
    with (args.output / "paths.csv").open("w", newline="") as file:
        writer = csv.writer(file); writer.writerow(["group", "path_or_leaf", "samples"])
        writer.writerows((g, p, n) for (g, p), n in paths.most_common())
    print(f"{len(pairs)} guest intervals; {len(accepted)} PC samples; wall/CPU ms {wall['mean']:.3f}/{cpu['mean']:.3f}" if cpu
          else f"{len(pairs)} guest intervals; CPU clock unavailable")
    for row in group_rows:
        equivalent = row["cpu_ms_equivalent_NOT_measured"]
        print(f"{row['samples']:3} {row['fraction']:6.1%} ~{equivalent:.2f} ms {row['group']} {row['five_second_counts']}" if equivalent is not None
              else f"{row['samples']:3} {row['group']}")
    print("Call evidence:", dict(evidence_counts))
    print("Output:", args.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("symbols", type=Path)
    parser.add_argument("nro", type=Path)
    parser.add_argument("--start", type=float, default=91)
    parser.add_argument("--end", type=float, default=111)
    parser.add_argument("--objdump", help="GNU aarch64 objdump; optional NRO instruction decoding")
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    if options.end <= options.start:
        parser.error("--end must be greater than --start")
    report(options)

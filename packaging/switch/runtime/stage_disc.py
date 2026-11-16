"""Stage real disc bytes used during boot, plus the read-only disc catalog."""
from pathlib import Path
import struct


def stage_disc(root):
    romfs = root / "build/switch-runtime/romfs"
    romfs.mkdir(exist_ok=True)
    # Xbox disc sectors read by the original boot, opening, menu and attract sequences.
    # Adjacent payloads share a range. Keep the whole title music stream.
    sectors = {
        'bgm.afs': [(0, 1), (198808, 5099), (213661, 3143)],
        'boff_cmn.afs': [(0, 1), (933, 59), (1280, 2), (2580, 16)],
        'chr_army.afs': [(0, 1), (1891, 90), (2364, 25), (2398, 31)],
        'chr_cat.afs': [(0, 628)],
        'chr_dino.afs': [(0, 898), (999, 137)],
        'chr_e_ryu.afs': [(0, 1), (3, 2), (11, 1), (14, 1), (16, 1), (2987, 1134), (4991, 314)],
        'chr_genin.afs': [(0, 508), (529, 56), (586, 114)],
        'chr_jonin.afs': [(0, 412)],
        'chr_kage.afs': [(0, 673), (1195, 23), (1229, 41)],
        'chr_m_arm.afs': [(0, 36), (39, 720)],
        'chr_murai.afs': [(0, 826), (1602, 67), (1670, 116)],
        'chr_ryu.afs': [(0, 499)],
        'chr_ryue.afs': [(0, 370)],
        'chr_s_kag.afs': [(0, 416)],
        'chr_swat.afs': [(0, 1), (1074, 17), (1257, 67), (1376, 1), (1379, 2)],
        'cmn.afs': [(0, 1592), (2728, 3273), (9591, 2030), (12334, 795), (13807, 1715), (16342, 2209), (22434, 623), (24277, 73)],
        'rail_12.afs': [(0, 2381)],
        'rail_cmn.afs': [(0, 122), (201, 43), (491, 48), (765, 21), (2078, 24), (2165, 1048), (3269, 36), (3341, 190)],
        'rtm_suiro.afs': [(0, 1), (5527, 422)],
        'rtm_tlna.afs': [(0, 1), (8265, 24)],
        'spr.afs': [(0, 3), (3275, 13), (27226, 44), (27538, 420)],
        'sse.afs': [(0, 2), (5925, 22)],
        'suiro_00.afs': [(0, 2553)],
        'suiro_05.afs': [(0, 263)],
        'suiro_10.afs': [(0, 3526)],
        'suiro_cmn.afs': [(0, 143), (639, 235), (1343, 91), (2487, 212), (2973, 23), (3182, 237), (3499, 50), (3606, 32)],
        'tln_a_05.afs': [(0, 2427)],
        'tln_a_99.afs': [(0, 238)],
        'tln_a_cmn.afs': [(0, 1), (357, 165), (1054, 129), (1963, 214), (2355, 13), (2466, 67), (5078, 245), (5665, 119)],
        'yasik_06.afs': [(0, 2227)],
        'yasik_cmn.afs': [(0, 1), (103, 174), (351, 29), (1150, 68), (1297, 44), (1565, 101), (1783, 1093), (3601, 102)],
    }
    full_files = ['default.xbe', 'demo.afs', 'dsstdfx.bin', 'live00.afs', 'load_img.bin', 'movie/4_VI_STD_B.sfd', 'movie/2_VI_WIDE_B.sfd']
    game = root / "game_files"
    catalog = bytearray()
    payload_changed = False
    for src in sorted(game.rglob("*")):
        rel = src.relative_to(game)
        if any(part.startswith(".") for part in rel.parts):
            continue
        dest = romfs / rel
        if src.is_dir():
            dest.mkdir(exist_ok=True)
            continue
        size = src.stat().st_size
        spans = ([(0, size)] if str(rel) in full_files else
                 [(sector * 2048, count * 2048) for sector, count in sectors.get(str(rel), [])])
        assert len(spans) <= 8 and all(start + length <= size for start, length in spans)
        payload = bytearray()
        with src.open("rb") as handle:
            for start, length in spans:
                handle.seek(start)
                payload.extend(handle.read(length))
        if not dest.is_file() or dest.read_bytes() != payload:
            dest.write_bytes(payload)
            payload_changed = True
        name = rel.as_posix().encode("ascii")
        if len(name) >= 160 or size >= 2**32:
            raise ValueError(f"unrepresentable disc entry {rel}")
        slots = spans + [(0, 0)] * (8-len(spans))
        catalog.extend(struct.pack("<160sII16I", name, size, len(spans),
                                   *(word for span in slots for word in span)))
    manifest = romfs / ".ngb-disc"
    if payload_changed or not manifest.exists() or manifest.read_bytes() != catalog:
        manifest.write_bytes(catalog)


if __name__ == "__main__":
    stage_disc(Path(__file__).resolve().parents[3])

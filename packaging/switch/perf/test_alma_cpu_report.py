"""Guard against inventing call stacks or combining unrelated log sessions."""
import gzip
from pathlib import Path
import runpy
import struct
import tempfile
import unittest

report = runpy.run_path(str(Path(__file__).with_name("alma-cpu-report.py")))


class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        path = self.root / "symbols.gz"
        with gzip.open(path, "wt") as file:
            file.write("00000100 00000020 T parent\n"
                       "00000200 00000020 T child\n"
                       "00000200 T child_alias_without_size\n"
                       "00000300 T tiny\n00000308 00000010 T following\n"
                       "00000400 T unbounded\n")
        self.symbols = report["Symbols"](path, 0x500)
        self.nro = bytearray(0x500)

    def call(self, site, target):
        struct.pack_into("<I", self.nro, site, 0x94000000 | (((target - site) // 4) & 0x3ffffff))

    def test_matching_direct_call_recovers_only_one_edge(self):
        self.call(0x110, 0x200)
        evidence, caller, target, op = report["call_evidence"](self.nro, self.symbols, 0x208, 0x114)
        self.assertEqual((evidence, caller, target, op),
                         ("direct call target matches sampled function", "parent", 0x200, "BL"))

    def test_lr_inside_current_function_is_not_a_recursive_stack(self):
        self.call(0x210, 0x200)
        evidence = report["call_evidence"](self.nro, self.symbols, 0x208, 0x214)[0]
        self.assertIn("no parent recovered", evidence)

    def test_different_target_is_not_attributed_as_direct_caller(self):
        self.call(0x110, 0x300)
        evidence = report["call_evidence"](self.nro, self.symbols, 0x208, 0x114)[0]
        self.assertEqual(evidence, "LR alone does not establish parent")

    def test_indirect_target_cannot_be_recovered_without_registers(self):
        struct.pack_into("<I", self.nro, 0x110, 0xd63f0000)
        self.assertEqual(report["call_evidence"](self.nro, self.symbols, 0x208, 0x114)[0],
                         "indirect call; target not recorded")

    def test_signed_branch_offset(self):
        self.call(0x210, 0x100)
        self.assertEqual(report["branch"](struct.unpack_from("<I", self.nro, 0x210)[0], 0x210), ("BL", 0x100))

    def test_symbols_do_not_cover_gaps_or_overwrite_sized_alias(self):
        self.assertEqual(self.symbols.lookup(0x208)[0], "child")
        self.assertEqual(self.symbols.lookup(0x240)[0], "unresolved")
        self.assertEqual(self.symbols.lookup(0x304)[3], "next-symbol bound (<=64 bytes)")
        self.assertEqual(self.symbols.lookup(0x308)[0], "following")
        self.assertEqual(self.symbols.lookup(0x450)[0], "unresolved")

    def test_host_support_is_not_charged_to_unproven_graphics_parent(self):
        group, _ = report["classify"]("ngb_guest_pointer", "_ZN12_GLOBAL__N_1L6BeforeEi", "LR alone does not establish parent")
        self.assertEqual(group, "runtime, scheduling and host support")

    def test_last_session_only_and_partial_record_rejection(self):
        path = self.root / "trace.csv"
        path.write_text("#SESSION,old\n#G,time_us,cpu_us\nG,1,2\n#LOST,0,5\n"
                        "#SESSION,new\n#G,time_us,cpu_us\nG,3,4\nG,5\nG,6,broken\n")
        session, rows, lost, partial = report["load_log"](path)
        self.assertEqual(session, ["new"])
        self.assertEqual(rows["G"], [{"time_us": 3, "cpu_us": 4}])
        self.assertEqual(lost, {})
        self.assertEqual(partial, 2)


if __name__ == "__main__":
    unittest.main()

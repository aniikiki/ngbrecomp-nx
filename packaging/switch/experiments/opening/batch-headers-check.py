"""Replay ordered header changes across delayed, recycled command batches."""
from pathlib import Path
import subprocess
import tempfile

source = Path('src/d3d/gpu/threaded.cpp').read_text()

def method(name):
    start = source.index('    void ' + name + '(')
    return source[start:source.index('\n    }', start) + 6]

start = source.index('    struct HeaderGroup {')
groups = source[start:source.index('    std::vector<uint8_t> bytes;', start)]
test = """
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <unordered_map>
#include <vector>
using std::size_t;
struct HeaderSend { uint32_t addr, w[5]; int32_t data = -1; };
struct HeaderCopy { uint32_t w[5]{}; const uint8_t* host = nullptr; };
struct Cmd { uint32_t addr, w[5]; int payload; };
struct Batch {
""" + groups + """
    std::vector<uint8_t> bytes;
};
struct Test {
    Batch* cur_;
    std::unordered_map<uint32_t, HeaderCopy> headers_;
    std::vector<uint32_t> hosted_;
""" + method('FlushHeaders') + method('ExecuteBatch') + """
    void Execute(Batch&, const Cmd& c) {
        const auto& h = headers_[c.addr];
        assert(!std::memcmp(c.w, h.w, sizeof(c.w)));
        assert((h.host ? int(*h.host) : -1) == c.payload);
    }
};
int main() {
    std::array<Batch, 3> batches;
    std::array<Cmd, 23> expected{};
    for (unsigned i = 0; i < expected.size(); ++i) expected[i] = {i, {}, -1};
    Test test{};
    unsigned seed = 83471;
    for (unsigned turn = 0; turn < 3000; ++turn) {
        auto& b = batches[turn % batches.size()];
        test.ExecuteBatch(b);
        b.cmds.clear(); b.headers.clear(); b.header_groups.clear(); b.bytes.clear();
        test.cur_ = &b;
        for (unsigned j = 0; j < 39; ++j) {
            seed = 1664525 * seed + 1013904223;
            auto& target = expected[seed % expected.size()];
            HeaderSend h{target.addr, {seed,j,turn,~seed,target.addr}};
            target.payload = -1;
            if (seed & 2) {
                h.data = int(b.bytes.size());
                b.bytes.push_back(uint8_t(seed >> 16));
                target.payload = b.bytes.back();
            }
            std::memcpy(target.w, h.w, sizeof(h.w));
            b.headers.push_back(h);
            if (seed & 8) {
                test.FlushHeaders();
                assert(b.HasHeaderBoundary());
                b.cmds.push_back(target);
                assert(!b.HasHeaderBoundary());
            }
        }
        test.FlushHeaders();
        const auto count = b.CommandCount();
        test.FlushHeaders();
        assert(b.CommandCount() == count && !b.Empty());
        for (auto& target : expected) {
            b.cmds.push_back(target);
            target.payload = -1; // inline bytes expire with their batch
        }
    }
    for (auto& b : batches) test.ExecuteBatch(b);
}
"""
with tempfile.TemporaryDirectory() as directory:
    src = Path(directory) / 'test.cpp'
    exe = src.with_suffix('')
    src.write_text(test)
    subprocess.run(['c++', '-std=c++17', '-O2', str(src), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print('117000 ordered header updates matched, including inline data and delayed batch reuse')

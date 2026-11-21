"""Exercise the actual push parser, including the XDK-owned trailing word.

An optional captured buffer is a private fixture: five header words followed
by Size bytes. Game data stays under build/, never in this test's source.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[4]
source = (root / 'src/d3d/hle.cpp').read_text()
start = source.index('void RunPushBuffer(uint32_t pb,')
parser = source[start:source.index('\n}', start) + 2]
code = r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <vector>
#include "gpu/prepared.h"
#define NGB_DIRECT3D 1
static std::vector<uint8_t> header(20), payload;
static bool ngb_d3d_native_enabled() { return true; }
[[noreturn]] static void ngb_stop(const char* reason, uint32_t) { throw std::runtime_error(reason); }
static void* HostPtr(uint32_t a, size_t n=4) {
    if (a>=0x80001000u && uint64_t(a)+n<=0x80001000ull+header.size()) return header.data()+a-0x80001000u;
    if (a>=0x80002000u && uint64_t(a)+n<=0x80002000ull+payload.size()) return payload.data()+a-0x80002000u;
    throw std::runtime_error("test memory overread");
}
static uint32_t R32(uint32_t a) { uint32_t v; std::memcpy(&v, HostPtr(a), 4); return v; }
static std::vector<uint32_t> draws;
static void Draw(uint32_t prim, uint32_t start, uint32_t count, const uint8_t* data, bool prepared, gpu::CombatEffect effect) {
    if (prepared != (effect == gpu::CombatEffect::Transparent)) throw std::runtime_error("lost effect role");
    draws.insert(draws.end(), {prim,start,count});
    for (unsigned i=0;i<count;++i) { uint16_t v; std::memcpy(&v,data+i*2,2); draws.push_back(v); }
}
''' + parser + r'''
static void setup(const std::vector<uint32_t>& words) {
    payload.resize(words.size()*4); std::memcpy(payload.data(),words.data(),payload.size());
    uint32_t h[]={0x20001,0x80002000,0,uint32_t(payload.size()),uint32_t(payload.size())};
    std::memcpy(header.data(),h,sizeof h); draws.clear();
}
static bool fails(const char* why) {
    try { RunPushBuffer(0x80001000); }
    catch (const std::runtime_error& e) { return std::strcmp(e.what(),why)==0; }
    return false;
}
int main(int argc, char** argv) {
    const std::vector<uint32_t> expected={6,0,5,3,7,11,13,17};
    for (uint32_t footer : {0u,0x3fc38002u,0xffffffffu,0x20000u,0x12340001u}) {
        setup({0x417fc,6,0x40081800,0x00070003,0x000d000b,0x41808,17,0x417fc,0,footer});
        RunPushBuffer(0x80001000,true,gpu::CombatEffect::Transparent); if(draws!=expected)return 1;
        setup({footer}); RunPushBuffer(0x80001000); if(!draws.empty())return 2;
    }
    setup({0x417fc,6,0x40081800,0x00070003,0});
    if(!fails("truncated native index push buffer") || !draws.empty())return 3;
    setup({0x40100,0,0}); if(!fails("unsupported native index push method"))return 4;
    for(uint32_t invalid : {0u,3u,7u}) {
        setup({0,0});std::memcpy(header.data()+12,&invalid,4);
        if(!fails("invalid native push buffer size"))return 5;
    }
    if(argc==2) {
        std::ifstream f(argv[1],std::ios::binary);
        std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(f)),{});
        if(bytes.size()<24)return 6;
        header.assign(bytes.begin(),bytes.begin()+20);payload.assign(bytes.begin()+20,bytes.end());
        uint32_t address=0x80002000;std::memcpy(header.data()+4,&address,4);draws.clear();
        RunPushBuffer(0x80001000);
        if(draws.size()!=7646 || draws[0]!=6 || draws[2]!=7643)return 7;
    }
    std::puts("PASS: complete draws, opaque footer, empty buffer, truncated data, unsupported method, invalid sizes");
}
'''
with tempfile.TemporaryDirectory(prefix='ngb-push-') as temp:
    cpp = Path(temp) / 'test.cpp'; cpp.write_text(code)
    exe = Path(temp) / 'test'
    subprocess.run(['c++', '-std=c++17', '-O2', '-I', str(root/'src/d3d'), str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe), *sys.argv[1:]], check=True)

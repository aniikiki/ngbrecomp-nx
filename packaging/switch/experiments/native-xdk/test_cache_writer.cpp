#include "vk/cache_writer.h"
#include <cassert>
#include <cstring>
#include <future>

struct Record { unsigned producer, sequence; unsigned char payload[120]; };

int main(int argc, char** argv) {
    assert(argc == 2);
    FILE* f = std::fopen(argv[1], "wb");
    assert(f);
    gpu::CacheWriter writer;
    writer.Own(f);
    flockfile(f); // Simulate an SD write which has stopped making progress.
    writer.Start();
    std::vector<std::future<void>> producers;
    for (unsigned p = 0; p < 3; ++p) producers.push_back(std::async(std::launch::async, [&, p] {
        for (unsigned n = 0; n < 1000; ++n) {
            Record record{p, n, {}};
            std::memset(record.payload, (p + n) % 251, sizeof(record.payload));
            assert(writer.Append(f, &record, sizeof(record)));
        }
    }));
    for (auto& p : producers) assert(p.wait_for(std::chrono::seconds(2)) == std::future_status::ready);
    funlockfile(f);
    for (auto& p : producers) p.get();
    writer.Stop();
    assert(!writer.Lost() && !writer.Errors());
    f = std::fopen(argv[1], "rb"); assert(f);
    unsigned counts[3]{};
    Record record;
    while (std::fread(&record, sizeof(record), 1, f)) {
        assert(record.producer < 3 && record.sequence == counts[record.producer]++);
        for (auto b : record.payload) assert(b == (record.producer + record.sequence) % 251);
    }
    std::fclose(f);
    for (auto count : counts) assert(count == 1000);
    f = std::tmpfile(); assert(f);
    gpu::CacheWriter bounded(0); bounded.Own(f); bounded.Start();
    assert(!bounded.Append(f, &record, sizeof(record)) && bounded.Lost() == 1);
    bounded.Stop();
    f = std::fopen("/dev/full", "wb"); assert(f);
    std::setvbuf(f, nullptr, _IONBF, 0);
    gpu::CacheWriter failed; failed.Own(f); failed.Start();
    failed.Append(f, &record, sizeof(record)); failed.Stop();
    assert(failed.Errors());
    std::puts("PASS: blocked I/O leaves producers running; ordered records, joined drain, bounded overflow, write errors");
}

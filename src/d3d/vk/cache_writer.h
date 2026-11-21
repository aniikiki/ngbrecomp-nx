#pragma once

#include <atomic>
#include <cerrno>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cstdio>
#include <deque>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace gpu {

// Some SD filesystems refuse to rename over an existing file. If the game
// stopped between the two renames, the old complete cache is still in .bak.
inline FILE* OpenCacheForRead(const std::string& path) {
    FILE* f = std::fopen(path.c_str(), "rb");
    if (f || errno != ENOENT || std::rename((path + ".bak").c_str(), path.c_str())) return f;
    return std::fopen(path.c_str(), "rb");
}

inline bool ReplaceCacheFile(const std::string& path, const void* data, size_t size) {
    const std::string tmp = path + ".tmp", backup = path + ".bak";
    FILE* f = std::fopen(tmp.c_str(), "wb");
    if (!f) return false;
    bool complete = std::fwrite(data, 1, size, f) == size;
    complete = std::fclose(f) == 0 && complete;
    if (complete && std::rename(tmp.c_str(), path.c_str()) == 0) return true;
    if (complete && (errno == EEXIST || errno == EACCES)) {
        // The existing destination is still intact until the temp is closed.
        // Clear a backup left after a previous successful install only if
        // there is a destination to take its place.
        if (FILE* old = std::fopen(path.c_str(), "rb")) {
            std::fclose(old);
            std::remove(backup.c_str());
            if (std::rename(path.c_str(), backup.c_str()) == 0) {
                if (std::rename(tmp.c_str(), path.c_str()) == 0) {
                    std::remove(backup.c_str());
                    return true;
                }
                std::rename(backup.c_str(), path.c_str());
            }
        }
    }
    std::remove(tmp.c_str());
    return false;
}

// Copy new cache records into a bounded queue. The consumer never holds the
// queue lock while accessing the filesystem, including fflush and fclose.
// Losing a cache record is recoverable; making a frame wait for the SD card is not.
class CacheWriter {
    struct Write { FILE* file; std::vector<unsigned char> bytes; };
    std::mutex mutex_;
    std::condition_variable ready_;
    std::deque<Write> queue_;
    std::vector<FILE*> files_;
    std::thread thread_;
    size_t pending_ = 0;
    const size_t limit_;
    bool stop_ = false;
    std::atomic<uint64_t> lost_{0}, errors_{0};

    void Run() {
        auto flushed = std::chrono::steady_clock::now();
        for (;;) {
            std::deque<Write> batch;
            bool done;
            {
                std::unique_lock<std::mutex> lock(mutex_);
                ready_.wait_for(lock, std::chrono::milliseconds(250), [&] { return stop_ || !queue_.empty(); });
                batch.swap(queue_);
                pending_ = 0;
                done = stop_;
            }
            for (auto& w : batch) {
                // After an I/O error, don't append behind an incomplete record.
                // CacheOpen repairs the tail on the next launch.
                if (errors_ || std::fwrite(w.bytes.data(), 1, w.bytes.size(), w.file) != w.bytes.size()) ++errors_;
            }
            auto now = std::chrono::steady_clock::now();
            if (done || now - flushed >= std::chrono::seconds(1)) {
                for (FILE* f : files_) if (std::fflush(f)) ++errors_;
                flushed = now;
            }
            if (done) break;
        }
    }

public:
    explicit CacheWriter(size_t limit = 32u * 1024 * 1024) : limit_(limit) {}
    ~CacheWriter() { Stop(); }
    // Register/open only before Start. The writer owns these files until Stop.
    void Own(FILE* f) { if (f) files_.push_back(f); }
    void Start() { if (!files_.empty()) thread_ = std::thread([this] { Run(); }); }
    bool Append(FILE* f, const void* data, size_t n) {
        if (!f) return false;
        std::lock_guard<std::mutex> lock(mutex_);
        if (stop_ || n > limit_ || pending_ > limit_ - n) { ++lost_; return false; }
        const auto* p = static_cast<const unsigned char*>(data);
        queue_.push_back({f, {p, p + n}});
        pending_ += n;
        ready_.notify_one();
        return true;
    }
    void Stop() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            stop_ = true;
        }
        ready_.notify_one();
        if (thread_.joinable()) thread_.join();
        for (FILE* f : files_) if (std::fclose(f)) ++errors_;
        files_.clear();
    }
    uint64_t Lost() const { return lost_; }
    uint64_t Errors() const { return errors_; }
};

} // namespace gpu

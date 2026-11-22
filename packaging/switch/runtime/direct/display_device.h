#pragma once
#include "display.h"
#ifdef NGB_GPU_PRESENT
#include <volk.h>
#include <vk_mem_alloc.h>
#include <mutex>

namespace switch_display {
std::mutex& queue_mutex();
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
// Called with queue_mutex held after submitting the write to the shared image.
void note_screen_write(VkImage image, uint32_t frame);
#endif
void attach(VkInstance instance, VkPhysicalDevice physical, VkDevice device,
            VkQueue queue, uint32_t family, const VolkDeviceTable& table, VmaAllocator allocator);
void detach(VkDevice device);
bool active();
void disable();
// The render queue has submitted the write and the transition to TRANSFER_SRC_OPTIMAL.
void publish(VkImage image, uint32_t width, uint32_t height);
}
#endif

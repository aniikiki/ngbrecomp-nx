#pragma once
#include "display.h"
#ifdef NGB_GPU_PRESENT
#include <volk.h>
#include <vk_mem_alloc.h>
#include <mutex>

namespace switch_display {
std::mutex& queue_mutex();
void attach(VkInstance instance, VkPhysicalDevice physical, VkDevice device,
            VkQueue queue, uint32_t family, const VolkDeviceTable& table, VmaAllocator allocator);
void detach(VkDevice device);
bool active();
void disable();
// The render queue has submitted the write and the transition to TRANSFER_SRC_OPTIMAL.
void publish(VkImage image, uint32_t width, uint32_t height);
}
#endif

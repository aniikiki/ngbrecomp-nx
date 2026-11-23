// Test-only interception of actual Vulkan calls. The shipping renderer has no
// dependency on this probe; the contract checks that mid-frame work is queued
// without waiting or resetting resources that earlier submissions still own.
#include <atomic>
#include <cstdint>
#include <volk.h>

namespace {
std::atomic<uint64_t> calls[4]{};
std::atomic<uint64_t> instanced[2]{};
PFN_vkCmdDraw cmd_draw;
PFN_vkCmdDrawIndexed cmd_draw_indexed;
PFN_vkQueueSubmit queue_submit;
PFN_vkWaitForFences wait_fences;
PFN_vkResetCommandBuffer reset_command;
PFN_vkResetDescriptorPool reset_sets;
VkResult VKAPI_PTR Submit(VkQueue queue, uint32_t count, const VkSubmitInfo* info, VkFence fence) {
    VkResult result = queue_submit(queue, count, info, fence);
    if (result == VK_SUCCESS && !fence) ++calls[0];
    return result;
}
VkResult VKAPI_PTR Wait(VkDevice device, uint32_t count, const VkFence* fences, VkBool32 all, uint64_t timeout) {
    ++calls[1];
    return wait_fences(device, count, fences, all, timeout);
}
VkResult VKAPI_PTR Reset(VkCommandBuffer command, VkCommandBufferResetFlags flags) {
    ++calls[2];
    return reset_command(command, flags);
}
VkResult VKAPI_PTR ResetSets(VkDevice device, VkDescriptorPool pool, VkDescriptorPoolResetFlags flags) {
    ++calls[3];
    return reset_sets(device, pool, flags);
}
void VKAPI_PTR Draw(VkCommandBuffer cmd, uint32_t vertices, uint32_t instances, uint32_t first, uint32_t base) {
    if (instances > 1) ++instanced[0];
    cmd_draw(cmd, vertices, instances, first, base);
}
void VKAPI_PTR DrawIndexed(VkCommandBuffer cmd, uint32_t indices, uint32_t instances, uint32_t first,
                           int32_t vertex, uint32_t base) {
    if (instances > 1) ++instanced[1];
    cmd_draw_indexed(cmd, indices, instances, first, vertex, base);
}
}
extern "C" void __real_volkLoadDeviceTable(VolkDeviceTable*, VkDevice);
extern "C" void __wrap_volkLoadDeviceTable(VolkDeviceTable* table, VkDevice device) {
    __real_volkLoadDeviceTable(table, device);
    queue_submit = table->vkQueueSubmit; table->vkQueueSubmit = Submit;
    wait_fences = table->vkWaitForFences; table->vkWaitForFences = Wait;
    reset_command = table->vkResetCommandBuffer; table->vkResetCommandBuffer = Reset;
    reset_sets = table->vkResetDescriptorPool; table->vkResetDescriptorPool = ResetSets;
    cmd_draw = table->vkCmdDraw; table->vkCmdDraw = Draw;
    cmd_draw_indexed = table->vkCmdDrawIndexed; table->vkCmdDrawIndexed = DrawIndexed;
}
extern "C" void ngb_test_submission_counts(uint64_t* output) {
    for (unsigned i = 0; i < 4; ++i) output[i] = calls[i].load();
}
extern "C" uint64_t ngb_test_instanced_draws(bool indexed) { return instanced[indexed].load(); }

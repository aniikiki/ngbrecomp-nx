// The UI owns the NWindow. Rendering and presentation use the same Vulkan device
// and queue, so a paused game picture can be used again without a CPU readback.
#include "scanout.h"
#include "vk/spirv.h"
#include <algorithm>
#include <array>
#include <cstring>
#include <vector>
#ifdef __SWITCH__
#include <vulkan/vulkan_vi.h>
#else
extern "C" VkResult ngb_display_test_surface(VkInstance, void*, VkSurfaceKHR*);
#endif

namespace switch_display {
namespace {
constexpr uint32_t screen_pixels = NGB_SCREEN_W * NGB_SCREEN_H;
constexpr uint32_t movie_pixels = NGB_SCAN_W * NGB_SCAN_H;
struct Slot {
    VkCommandBuffer cmd{};
    VkFence done{};
    VkSemaphore acquired{};
    VkBuffer pixels{};
    VmaAllocation allocation{};
    uint32_t* mapped{};
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
    struct { uint64_t begin_us, generation, lock_us, submit_us, present_us; bool timed; } sample{};
#endif
};
struct WindowImage {
    VkImage image{};
    VkImageView view{};
    VkSemaphore ready{}; // May be reused only after this image is acquired again.
};
struct Window {
    VkSurfaceKHR surface{};
    VkSwapchainKHR chain{};
    VkFormat format{};
    VkCommandPool pool{};
    VkDescriptorSetLayout descriptors{};
    VkPipelineLayout layout{};
    VkPipeline pipeline{};
    std::array<Slot, 2> slots{};
    std::vector<WindowImage> images;
    unsigned next{};
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
    VkQueryPool timestamps{};
    double period_ns{};
    uint64_t tick_mask{};
#endif
};
struct Context {
    VkInstance instance{};
    VkPhysicalDevice physical{};
    VkDevice device{};
    VkQueue queue{};
    uint32_t family{};
    const VolkDeviceTable* d{};
    VmaAllocator allocator{};
    bool attempted{};
    void* window{};
};
Context ctx;
Window win;
std::mutex lifecycle, picture_mutex, submissions;
std::atomic<bool> enabled{};
VkImage picture{};
uint32_t picture_width{}, picture_height{};
struct Picture { VkImage image; uint32_t width, height; };
Picture latest_picture() {
    std::lock_guard lock(picture_mutex);
    return {picture, picture_width, picture_height};
}

bool check(VkResult rc, const char* call) {
    if (rc == VK_SUCCESS) return true;
    char line[144];
    std::snprintf(line, sizeof(line), "720p display: %s returned %d", call, int(rc));
    ngb_kernel_log(line);
    return false;
}
#define DISPLAY_VK(call) check((call), #call)

#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
void create_window_timer() {
    uint32_t count = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(ctx.physical, &count, nullptr);
    if (ctx.family >= count) return;
    std::vector<VkQueueFamilyProperties> families(count);
    vkGetPhysicalDeviceQueueFamilyProperties(ctx.physical, &count, families.data());
    const unsigned bits = families[ctx.family].timestampValidBits;
    if (!bits) return;
    VkPhysicalDeviceProperties props;
    vkGetPhysicalDeviceProperties(ctx.physical, &props);
    win.period_ns = props.limits.timestampPeriod;
    win.tick_mask = UINT64_MAX >> (64 - bits);
    VkQueryPoolCreateInfo ci{VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO};
    ci.queryType = VK_QUERY_TYPE_TIMESTAMP;
    ci.queryCount = 2 * win.slots.size();
    VkQueryPool pool{};
    if (ctx.d->vkCreateQueryPool(ctx.device, &ci, nullptr, &pool) == VK_SUCCESS) win.timestamps = pool;
}

void read_window_sample(Slot& slot, unsigned first) {
    const auto& s = slot.sample;
    uint64_t t[2];
    const bool valid = s.timed && ctx.d->vkGetQueryPoolResults(ctx.device, win.timestamps, first, 2,
        sizeof(t), t, sizeof(uint64_t), VK_QUERY_RESULT_64_BIT) == VK_SUCCESS;
    const uint64_t ns = valid ? uint64_t(double((t[1] - t[0]) & win.tick_mask) * win.period_ns) : 0;
    uint64_t values[]{s.begin_us, s.generation, s.lock_us, s.submit_us, s.present_us, ns, valid};
    ngb_combat_row('Y', values, 7);
    slot.sample = {};
}
#endif

void release_window() {
    disable();
    if (!ctx.device) return;
    const auto& d = *ctx.d;
    if (win.chain) {
        std::lock_guard queue_lock(submissions);
        d.vkQueueWaitIdle(ctx.queue);
    }
    for (auto& slot : win.slots) {
        if (slot.done) d.vkDestroyFence(ctx.device, slot.done, nullptr);
        if (slot.acquired) d.vkDestroySemaphore(ctx.device, slot.acquired, nullptr);
        if (slot.pixels) vmaDestroyBuffer(ctx.allocator, slot.pixels, slot.allocation);
    }
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
    if (win.timestamps) d.vkDestroyQueryPool(ctx.device, win.timestamps, nullptr);
#endif
    if (win.pipeline) d.vkDestroyPipeline(ctx.device, win.pipeline, nullptr);
    if (win.layout) d.vkDestroyPipelineLayout(ctx.device, win.layout, nullptr);
    if (win.descriptors) d.vkDestroyDescriptorSetLayout(ctx.device, win.descriptors, nullptr);
    if (win.pool) d.vkDestroyCommandPool(ctx.device, win.pool, nullptr);
    for (auto& image : win.images) {
        if (image.ready) d.vkDestroySemaphore(ctx.device, image.ready, nullptr);
        if (image.view) d.vkDestroyImageView(ctx.device, image.view, nullptr);
    }
    if (win.chain) d.vkDestroySwapchainKHR(ctx.device, win.chain, nullptr);
    if (win.surface) vkDestroySurfaceKHR(ctx.instance, win.surface, nullptr);
    win = {};
}

bool create_pipeline() {
    const auto& d = *ctx.d;
    VkDescriptorSetLayoutBinding binding{0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 1, VK_SHADER_STAGE_FRAGMENT_BIT, nullptr};
    VkDescriptorSetLayoutCreateInfo dl{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
    dl.flags = VK_DESCRIPTOR_SET_LAYOUT_CREATE_PUSH_DESCRIPTOR_BIT_KHR;
    dl.bindingCount = 1; dl.pBindings = &binding;
    if (!DISPLAY_VK(d.vkCreateDescriptorSetLayout(ctx.device, &dl, nullptr, &win.descriptors))) return false;
    VkPushConstantRange range{VK_SHADER_STAGE_FRAGMENT_BIT, 0, 3 * sizeof(uint32_t)};
    VkPipelineLayoutCreateInfo pl{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
    pl.setLayoutCount = 1; pl.pSetLayouts = &win.descriptors;
    pl.pushConstantRangeCount = 1; pl.pPushConstantRanges = &range;
    if (!DISPLAY_VK(d.vkCreatePipelineLayout(ctx.device, &pl, nullptr, &win.layout))) return false;

    const char* shader[] = {
        R"(float4 main(uint id : SV_VertexID) : SV_Position {
             float2 p = float2((id << 1) & 2, id & 2);
             return float4(p * 2.0 - 1.0, 0.0, 1.0);
           })",
        R"([[vk::binding(0,0)]] StructuredBuffer<uint> pixels;
           [[vk::push_constant]] cbuffer Screen { uint movie; uint left; uint width; };
           float4 main(float4 position : SV_Position) : SV_Target {
             uint2 p = uint2(position.xy);
             uint i = movie != 0 ? 1280*720 + (p.y*480/720)*720 + (p.x-left)*720/width : p.y*1280 + p.x;
             uint v = pixels[i];
             float4 c = float4(v & 255, (v>>8) & 255, (v>>16) & 255, v>>24) / 255.0;
             return movie != 0 ? float4(c.bgr, 1.0) : c;
           })"
    };
    VkPipelineShaderStageCreateInfo stages[2]{};
    auto destroy_modules = [&] {
        for (auto& s : stages) if (s.module) d.vkDestroyShaderModule(ctx.device, s.module, nullptr);
    };
    for (unsigned i = 0; i < 2; ++i) {
        std::vector<uint32_t> code;
        std::string log;
        if (!vkr::Compile(shader[i], i == 0, code, &log)) {
            ngb_kernel_log(log.c_str()); destroy_modules(); return false;
        }
        VkShaderModuleCreateInfo sm{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
        sm.codeSize = code.size() * sizeof(uint32_t); sm.pCode = code.data();
        auto& stage = stages[i];
        stage.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        stage.stage = i ? VK_SHADER_STAGE_FRAGMENT_BIT : VK_SHADER_STAGE_VERTEX_BIT;
        stage.pName = "main";
        if (!DISPLAY_VK(d.vkCreateShaderModule(ctx.device, &sm, nullptr, &stage.module))) {
            destroy_modules(); return false;
        }
    }
    VkPipelineVertexInputStateCreateInfo vi{VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO};
    VkPipelineInputAssemblyStateCreateInfo ia{VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO};
    ia.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    VkPipelineViewportStateCreateInfo vp{VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO};
    vp.viewportCount = vp.scissorCount = 1;
    VkPipelineRasterizationStateCreateInfo rs{VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO};
    rs.lineWidth = 1.0f;
    VkPipelineMultisampleStateCreateInfo ms{VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO};
    ms.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;
    VkPipelineColorBlendAttachmentState blend{};
    blend.blendEnable = VK_TRUE;
    blend.srcColorBlendFactor = blend.srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
    blend.dstColorBlendFactor = blend.dstAlphaBlendFactor = VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
    blend.colorWriteMask = 15;
    VkPipelineColorBlendStateCreateInfo bs{VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO};
    bs.attachmentCount = 1; bs.pAttachments = &blend;
    VkDynamicState dyn[] = {VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR};
    VkPipelineDynamicStateCreateInfo ds{VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO};
    ds.dynamicStateCount = 2; ds.pDynamicStates = dyn;
    VkPipelineRenderingCreateInfo rendering{VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO};
    rendering.colorAttachmentCount = 1; rendering.pColorAttachmentFormats = &win.format;
    VkGraphicsPipelineCreateInfo pipe{VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO};
    pipe.pNext = &rendering; pipe.layout = win.layout; pipe.stageCount = 2; pipe.pStages = stages;
    pipe.pVertexInputState = &vi; pipe.pInputAssemblyState = &ia; pipe.pViewportState = &vp;
    pipe.pRasterizationState = &rs; pipe.pMultisampleState = &ms; pipe.pColorBlendState = &bs;
    pipe.pDynamicState = &ds;
    bool ok = DISPLAY_VK(d.vkCreateGraphicsPipelines(ctx.device, VK_NULL_HANDLE, 1, &pipe, nullptr, &win.pipeline));
    destroy_modules();
    return ok;
}

bool create_window(void* window) {
    const auto& d = *ctx.d;
#ifdef __SWITCH__
    auto* native = static_cast<NWindow*>(window);
    uint32_t width = 0, height = 0;
    if (R_FAILED(nwindowGetDimensions(native, &width, &height)) ||
        width != NGB_SCREEN_W || height != NGB_SCREEN_H) {
        if (R_FAILED(nwindowSetDimensions(native, NGB_SCREEN_W, NGB_SCREEN_H))) return false;
    }
    auto create = reinterpret_cast<PFN_vkCreateViSurfaceNN>(vkGetInstanceProcAddr(ctx.instance, "vkCreateViSurfaceNN"));
    VkViSurfaceCreateInfoNN vi{VK_STRUCTURE_TYPE_VI_SURFACE_CREATE_INFO_NN};
    vi.window = window;
    if (!create || !DISPLAY_VK(create(ctx.instance, &vi, nullptr, &win.surface))) return false;
#else
    if (!DISPLAY_VK(ngb_display_test_surface(ctx.instance, window, &win.surface))) return false;
#endif
    VkBool32 supported{};
    if (!DISPLAY_VK(vkGetPhysicalDeviceSurfaceSupportKHR(ctx.physical, ctx.family, win.surface, &supported)) || !supported)
        return false;
    VkSurfaceCapabilitiesKHR caps{};
    if (!DISPLAY_VK(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(ctx.physical, win.surface, &caps))) return false;
    const VkExtent2D extent{NGB_SCREEN_W, NGB_SCREEN_H};
    const VkImageUsageFlags usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT;
    if ((caps.supportedUsageFlags & usage) != usage ||
        (caps.currentExtent.width != UINT32_MAX && (caps.currentExtent.width != extent.width || caps.currentExtent.height != extent.height)) ||
        extent.width < caps.minImageExtent.width || extent.width > caps.maxImageExtent.width ||
        extent.height < caps.minImageExtent.height || extent.height > caps.maxImageExtent.height) return false;
    uint32_t count = 0;
    if (!DISPLAY_VK(vkGetPhysicalDeviceSurfaceFormatsKHR(ctx.physical, win.surface, &count, nullptr)) || !count) return false;
    std::vector<VkSurfaceFormatKHR> formats(count);
    if (!DISPLAY_VK(vkGetPhysicalDeviceSurfaceFormatsKHR(ctx.physical, win.surface, &count, formats.data()))) return false;
    VkSurfaceFormatKHR format{};
    for (auto wanted : {VK_FORMAT_R8G8B8A8_UNORM, VK_FORMAT_B8G8R8A8_UNORM}) {
        auto found = std::find_if(formats.begin(), formats.end(), [&](auto f) {
            return (f.format == wanted || f.format == VK_FORMAT_UNDEFINED) && f.colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR;
        });
        if (found != formats.end()) { format = {wanted, found->colorSpace}; break; }
    }
    if (!format.format) return false;
    VkFormatProperties features{};
    vkGetPhysicalDeviceFormatProperties(ctx.physical, format.format, &features);
    if (!(features.optimalTilingFeatures & VK_FORMAT_FEATURE_BLIT_DST_BIT)) return false;
    win.format = format.format;
    VkSwapchainCreateInfoKHR info{VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR};
    info.surface = win.surface; info.minImageCount = std::max(3u, caps.minImageCount);
    if (caps.maxImageCount) info.minImageCount = std::min(info.minImageCount, caps.maxImageCount);
    info.imageFormat = format.format; info.imageColorSpace = format.colorSpace;
    info.imageExtent = extent; info.imageArrayLayers = 1; info.imageUsage = usage;
    info.preTransform = caps.currentTransform;
    info.compositeAlpha = static_cast<VkCompositeAlphaFlagBitsKHR>(caps.supportedCompositeAlpha & -caps.supportedCompositeAlpha);
    info.presentMode = VK_PRESENT_MODE_FIFO_KHR; info.clipped = VK_TRUE;
    if (!DISPLAY_VK(d.vkCreateSwapchainKHR(ctx.device, &info, nullptr, &win.chain))) return false;
    if (!DISPLAY_VK(d.vkGetSwapchainImagesKHR(ctx.device, win.chain, &count, nullptr)) || !count) return false;
    std::vector<VkImage> images(count);
    if (!DISPLAY_VK(d.vkGetSwapchainImagesKHR(ctx.device, win.chain, &count, images.data()))) return false;
    win.images.resize(count);
    VkSemaphoreCreateInfo sem{VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
    for (unsigned i = 0; i < count; ++i) {
        auto& image = win.images[i];
        image.image = images[i];
        VkImageViewCreateInfo view{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
        view.image = image.image; view.viewType = VK_IMAGE_VIEW_TYPE_2D; view.format = format.format;
        view.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        if (!DISPLAY_VK(d.vkCreateImageView(ctx.device, &view, nullptr, &image.view)) ||
            !DISPLAY_VK(d.vkCreateSemaphore(ctx.device, &sem, nullptr, &image.ready))) return false;
    }
    VkCommandPoolCreateInfo pool{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
    pool.queueFamilyIndex = ctx.family; pool.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    if (!DISPLAY_VK(d.vkCreateCommandPool(ctx.device, &pool, nullptr, &win.pool))) return false;
    for (auto& slot : win.slots) {
        VkCommandBufferAllocateInfo cmd{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
        cmd.commandPool = win.pool; cmd.commandBufferCount = 1; cmd.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        VkFenceCreateInfo fence{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
        fence.flags = VK_FENCE_CREATE_SIGNALED_BIT;
        if (!DISPLAY_VK(d.vkAllocateCommandBuffers(ctx.device, &cmd, &slot.cmd)) ||
            !DISPLAY_VK(d.vkCreateFence(ctx.device, &fence, nullptr, &slot.done)) ||
            !DISPLAY_VK(d.vkCreateSemaphore(ctx.device, &sem, nullptr, &slot.acquired))) return false;
        VkBufferCreateInfo buf{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        buf.size = (screen_pixels + movie_pixels) * sizeof(uint32_t);
        buf.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
        VmaAllocationCreateInfo mem{};
        mem.usage = VMA_MEMORY_USAGE_AUTO;
        mem.flags = VMA_ALLOCATION_CREATE_HOST_ACCESS_SEQUENTIAL_WRITE_BIT | VMA_ALLOCATION_CREATE_MAPPED_BIT;
        VmaAllocationInfo alloc{};
        if (!DISPLAY_VK(vmaCreateBuffer(ctx.allocator, &buf, &mem, &slot.pixels, &slot.allocation, &alloc))) return false;
        slot.mapped = static_cast<uint32_t*>(alloc.pMappedData);
    }
    return create_pipeline();
}

void transition(VkCommandBuffer cmd, VkImage image, VkImageLayout from, VkImageLayout to) {
    auto stage = [](VkImageLayout l) -> VkPipelineStageFlags2 {
        if (l == VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL) return VK_PIPELINE_STAGE_2_ALL_TRANSFER_BIT;
        if (l == VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL) return VK_PIPELINE_STAGE_2_COLOR_ATTACHMENT_OUTPUT_BIT;
        return VK_PIPELINE_STAGE_2_NONE;
    };
    auto access = [](VkImageLayout l) -> VkAccessFlags2 {
        if (l == VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL) return VK_ACCESS_2_TRANSFER_WRITE_BIT;
        if (l == VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL) return VK_ACCESS_2_COLOR_ATTACHMENT_READ_BIT | VK_ACCESS_2_COLOR_ATTACHMENT_WRITE_BIT;
        return VK_ACCESS_2_NONE;
    };
    VkImageMemoryBarrier2 bar{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER_2};
    bar.image = image; bar.oldLayout = from; bar.newLayout = to;
    bar.srcStageMask = stage(from); bar.srcAccessMask = access(from);
    bar.dstStageMask = stage(to); bar.dstAccessMask = access(to);
    bar.srcQueueFamilyIndex = bar.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    bar.subresourceRange = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
    VkDependencyInfo dep{VK_STRUCTURE_TYPE_DEPENDENCY_INFO};
    dep.imageMemoryBarrierCount = 1; dep.pImageMemoryBarriers = &bar;
    ctx.d->vkCmdPipelineBarrier2(cmd, &dep);
}

bool upload_layers(const NgbScreenFrame& frame, Slot& slot, bool software) {
    if (software) {
        std::memcpy(slot.mapped + screen_pixels, frame.cpu_bgra, movie_pixels * 4);
        if (!DISPLAY_VK(vmaFlushAllocation(ctx.allocator, slot.allocation, screen_pixels * 4, movie_pixels * 4))) return false;
    }
    for (unsigned i = 0; i < frame.count; ++i) {
        const auto& rect = frame.rects[i];
        uint32_t at = rect.y * NGB_SCREEN_W + rect.x;
        for (unsigned y = 0; y < rect.h; ++y, at += NGB_SCREEN_W)
            std::memcpy(slot.mapped + at, frame.overlay_rgba + at, rect.w * 4);
        uint32_t first = rect.y * NGB_SCREEN_W + rect.x;
        uint32_t span = (rect.h - 1) * NGB_SCREEN_W + rect.w;
        if (!DISPLAY_VK(vmaFlushAllocation(ctx.allocator, slot.allocation, first * 4, span * 4))) return false;
    }
    return true;
}

bool record(const NgbScreenFrame& frame, Slot& slot, WindowImage& dst, Picture game) {
    const auto& d = *ctx.d;
    const bool gpu = frame.gpu && game.image && !frame.blank;
    const bool software = !frame.gpu && frame.cpu_bgra && !frame.blank;
    const uint32_t left = frame.standard ? 160u : 0u, width = NGB_SCREEN_W - 2 * left;
    if (!upload_layers(frame, slot, software)) return false;
    VkCommandBuffer cmd = slot.cmd;
    if (!DISPLAY_VK(d.vkResetCommandBuffer(cmd, 0))) return false;
    VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (!DISPLAY_VK(d.vkBeginCommandBuffer(cmd, &begin))) return false;
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
    const unsigned first = 2 * (win.next % win.slots.size());
    if (slot.sample.timed) {
        d.vkCmdResetQueryPool(cmd, win.timestamps, first, 2);
        d.vkCmdWriteTimestamp(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, win.timestamps, first);
    }
#endif
    VkImageLayout current = VK_IMAGE_LAYOUT_UNDEFINED;
    if (gpu) {
        transition(cmd, dst.image, current, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
        current = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
        VkImageBlit b{};
        b.srcSubresource = b.dstSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1};
        b.srcOffsets[1] = {int32_t(game.width), int32_t(game.height), 1};
        b.dstOffsets[0].x = int32_t(left);
        b.dstOffsets[1] = {int32_t(left + width), NGB_SCREEN_H, 1};
        d.vkCmdBlitImage(cmd, game.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, dst.image, current,
                         1, &b, VK_FILTER_NEAREST);
    }
    if (!gpu || left || frame.count) {
        transition(cmd, dst.image, current, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL);
        current = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
        VkRenderingAttachmentInfo color{VK_STRUCTURE_TYPE_RENDERING_ATTACHMENT_INFO};
        color.imageView = dst.view; color.imageLayout = current;
        color.loadOp = gpu ? VK_ATTACHMENT_LOAD_OP_LOAD : VK_ATTACHMENT_LOAD_OP_CLEAR;
        color.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
        color.clearValue.color.float32[3] = 1;
        VkRenderingInfo render{VK_STRUCTURE_TYPE_RENDERING_INFO};
        render.renderArea.extent = {NGB_SCREEN_W, NGB_SCREEN_H}; render.layerCount = 1;
        render.colorAttachmentCount = 1; render.pColorAttachments = &color;
        d.vkCmdBeginRendering(cmd, &render);
        if (gpu && left) {
            VkClearAttachment black{};
            black.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT; black.clearValue.color.float32[3] = 1;
            VkClearRect bars[] = {{{{0,0}, {left,NGB_SCREEN_H}}, 0, 1},
                                  {{{int32_t(left + width),0}, {left,NGB_SCREEN_H}}, 0, 1}};
            d.vkCmdClearAttachments(cmd, 1, &black, 2, bars);
        }
        if (software || frame.count) {
            d.vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, win.pipeline);
            VkDescriptorBufferInfo buffer{slot.pixels, 0, VK_WHOLE_SIZE};
            VkWriteDescriptorSet write{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
            write.descriptorCount = 1; write.descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            write.pBufferInfo = &buffer;
            d.vkCmdPushDescriptorSetKHR(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, win.layout, 0, 1, &write);
            VkViewport vp{0, 0, float(NGB_SCREEN_W), float(NGB_SCREEN_H), 0, 1};
            d.vkCmdSetViewport(cmd, 0, 1, &vp);
            auto draw = [&](bool movie, VkRect2D rect) {
                uint32_t pc[] = {uint32_t(movie), left, width};
                d.vkCmdPushConstants(cmd, win.layout, VK_SHADER_STAGE_FRAGMENT_BIT, 0, sizeof(pc), pc);
                d.vkCmdSetScissor(cmd, 0, 1, &rect);
                d.vkCmdDraw(cmd, 3, 1, 0, 0);
            };
            if (software) draw(true, {{int32_t(left), 0}, {width, NGB_SCREEN_H}});
            for (unsigned i = 0; i < frame.count; ++i) {
                const auto& r = frame.rects[i];
                draw(false, {{int32_t(r.x), int32_t(r.y)}, {r.w, r.h}});
            }
        }
        d.vkCmdEndRendering(cmd);
    }
    transition(cmd, dst.image, current, VK_IMAGE_LAYOUT_PRESENT_SRC_KHR);
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
    if (slot.sample.timed)
        d.vkCmdWriteTimestamp(cmd, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, win.timestamps, first + 1);
#endif
    return DISPLAY_VK(d.vkEndCommandBuffer(cmd));
}

bool start(void* window) {
    ctx.window = window;
    ctx.attempted = true;
    if (!create_window(window)) {
        release_window();
        ngb_kernel_log("3D scene 720p display unavailable; using software framebuffer");
        return false;
    }
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
    if (ngb_combat_enabled) create_window_timer();
#endif
    enabled.store(true);
    ngb_kernel_log("3D scene 720p display active: Vulkan swapchain 1280x720");
    return true;
}
int rebuild() {
    release_window();
    return start(ctx.window) ? 0 : -1;
}

int present(const NgbScreenFrame& frame, uint64_t* times) {
    if (!enabled.load()) return -1;
    const auto& d = *ctx.d;
    auto& slot = win.slots[win.next % win.slots.size()];
    uint64_t begin = times ? ngb_elapsed_ns() : 0;
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
    const bool trace = times && frame.gpu && !frame.blank && ngb_combat_enabled && ngb_combat_active();
    const unsigned generation = trace ? ngb_scanout_generation() : 0;
    auto log_wait = [&](uint64_t slot_end, uint64_t image_end, bool reusable, bool acquired) {
        uint64_t values[] = {begin / 1000, generation, ngb_scanout_generation(),
                             (slot_end - begin) / 1000, (image_end - slot_end) / 1000,
                             uint64_t(reusable), uint64_t(acquired)};
        ngb_combat_row('H', values, 7);
    };
#endif
    VkResult fence = d.vkWaitForFences(ctx.device, 1, &slot.done, VK_TRUE, 20000000);
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
    const uint64_t slot_end = trace ? ngb_elapsed_ns() : 0;
    if (trace && fence != VK_SUCCESS) log_wait(slot_end, slot_end, false, false);
#endif
    if (fence == VK_TIMEOUT) return 0;
    if (!check(fence, "display slot fence")) return -1;
    uint32_t index;
    VkResult acq = d.vkAcquireNextImageKHR(ctx.device, win.chain, 20000000, slot.acquired, VK_NULL_HANDLE, &index);
    uint64_t acquired = times ? ngb_elapsed_ns() : 0;
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
    if (trace) log_wait(slot_end, acquired, true, acq == VK_SUCCESS || acq == VK_SUBOPTIMAL_KHR);
    // Retire the old sample after both waits have been measured.
    if (slot.sample.begin_us) read_window_sample(slot, 2 * (win.next % win.slots.size()));
#endif
    if (acq == VK_ERROR_OUT_OF_DATE_KHR) return rebuild();
    if (acq == VK_TIMEOUT || acq == VK_NOT_READY) return 0;
    if (acq != VK_SUBOPTIMAL_KHR && !check(acq, "acquire window image")) return -1;
    auto& image = win.images[index];
    const auto game = latest_picture();
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
    const bool sample = trace && game.image && (win.next % 8 == 0);
    if (sample) {
        slot.sample.generation = ngb_scanout_generation();
        slot.sample.timed = win.timestamps != VK_NULL_HANDLE;
    }
#endif
    if (!record(frame, slot, image, game)) return -1;
    uint64_t recorded = times ? ngb_elapsed_ns() : 0;
    VkPipelineStageFlags wait_at = VK_PIPELINE_STAGE_ALL_COMMANDS_BIT;
    VkSubmitInfo sub{VK_STRUCTURE_TYPE_SUBMIT_INFO};
    sub.waitSemaphoreCount = 1; sub.pWaitSemaphores = &slot.acquired; sub.pWaitDstStageMask = &wait_at;
    sub.commandBufferCount = 1; sub.pCommandBuffers = &slot.cmd;
    sub.signalSemaphoreCount = 1; sub.pSignalSemaphores = &image.ready;
    VkPresentInfoKHR out{VK_STRUCTURE_TYPE_PRESENT_INFO_KHR};
    out.waitSemaphoreCount = 1; out.pWaitSemaphores = &image.ready;
    out.swapchainCount = 1; out.pSwapchains = &win.chain; out.pImageIndices = &index;
    if (!DISPLAY_VK(d.vkResetFences(ctx.device, 1, &slot.done))) return -1;
    VkResult shown;
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
    const uint64_t locking = sample ? ngb_elapsed_ns() : 0;
    uint64_t locked = 0, submitted = 0, presented = 0;
#endif
    {
        std::lock_guard queue_lock(submissions);
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
        if (sample) locked = ngb_elapsed_ns();
#endif
        if (!DISPLAY_VK(d.vkQueueSubmit(ctx.queue, 1, &sub, slot.done))) return -1;
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
        if (sample) submitted = ngb_elapsed_ns();
#endif
        shown = d.vkQueuePresentKHR(ctx.queue, &out);
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
        if (sample) presented = ngb_elapsed_ns();
#endif
    }
#if defined(NGB_COMBAT_PERF) && defined(NGB_NATIVE_DIAG)
    if (sample) {
        slot.sample.begin_us = begin / 1000;
        slot.sample.lock_us = (locked - locking) / 1000;
        slot.sample.submit_us = (submitted - locked) / 1000;
        slot.sample.present_us = (presented - submitted) / 1000;
    }
#endif
    ++win.next;
    if (times) {
        times[0] = (acquired - begin) / 1000;
        times[1] = (recorded - acquired) / 1000;
        times[2] = (ngb_elapsed_ns() - recorded) / 1000;
    }
    if (shown == VK_ERROR_OUT_OF_DATE_KHR) return rebuild();
    // A suboptimal image is still displayed at the requested extent.
    return shown == VK_SUBOPTIMAL_KHR || check(shown, "present window image") ? 1 : -1;
}
#undef DISPLAY_VK
} // namespace

std::mutex& queue_mutex() { return submissions; }
void attach(VkInstance instance, VkPhysicalDevice physical, VkDevice device, VkQueue queue,
            uint32_t family, const VolkDeviceTable& d, VmaAllocator allocator) {
    std::lock_guard lock(lifecycle);
    ctx = {instance, physical, device, queue, family, &d, allocator};
}
void detach(VkDevice device) {
    std::lock_guard lock(lifecycle);
    if (!device || ctx.device != device) return;
    release_window();
    { std::lock_guard picture_lock(picture_mutex); picture = VK_NULL_HANDLE; }
    ctx = {};
}
bool active() { return enabled.load(); }
void disable() {
    std::lock_guard lock(picture_mutex);
    enabled.store(false);
}
void publish(VkImage image, uint32_t w, uint32_t h) {
    std::lock_guard lock(picture_mutex);
    if (!enabled.load()) return;
    picture = image; picture_width = w; picture_height = h;
    ngb_scanout_publish_gpu();
}
} // namespace switch_display

extern "C" int ngb_display_pending() {
    using namespace switch_display;
    std::lock_guard lock(lifecycle);
    return ctx.device && !ctx.attempted;
}
extern "C" int ngb_display_open(void* window) {
    using namespace switch_display;
    std::lock_guard lock(lifecycle);
    return ctx.device && !ctx.attempted && start(window);
}
extern "C" void ngb_display_close() {
    using namespace switch_display;
    std::lock_guard lock(lifecycle);
    release_window();
}
extern "C" int ngb_display_present(const NgbScreenFrame* frame, uint64_t times[3]) {
    using namespace switch_display;
    std::lock_guard lock(lifecycle);
    return present(*frame, times);
}

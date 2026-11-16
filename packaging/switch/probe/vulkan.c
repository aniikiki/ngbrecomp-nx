/* Uses the pinned NXVK validation harness, supplied on the include path. */
#include "nvk_harness.h"

int main(void)
{
    consoleInit(NULL);
    padConfigureInput(1, HidNpadStyleSet_NpadStandard);
    PadState pad;
    padInitializeDefault(&pad);
    nvk_log_open("sdmc:/ngb_vk_caps.log");
    LOG("=== NGB Vulkan capability probe 0.1.0 ===");
    LOG("Checks device creation and entrypoints, not full game rendering.");

    /* The minimum feature set used by src/d3d/vk/backend.cpp. */
    VkPhysicalDeviceVulkan13Features f13 = {
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES,
        .dynamicRendering = VK_TRUE,
        .synchronization2 = VK_TRUE,
    };
    VkPhysicalDeviceFeatures2 f2 = {
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2,
        .pNext = &f13,
        .features.samplerAnisotropy = VK_TRUE,
    };
    g_nvk_dev_pnext = &f2;
    const char *inst_exts[] = {VK_KHR_SURFACE_EXTENSION_NAME, "VK_NN_vi_surface"};
    const char *dev_exts[] = {VK_KHR_SWAPCHAIN_EXTENSION_NAME, VK_KHR_PUSH_DESCRIPTOR_EXTENSION_NAME};
    struct nvk_ctx c;
    bool ok = false;
    VkResult result = nvk_bringup_ex(&c, inst_exts, 2, dev_exts, 2);
    if (result != VK_SUCCESS) {
        LOG("FAIL: required-feature device creation: VkResult=%d", result);
        goto done;
    }
    LOAD_INST(&c, GetPhysicalDeviceFeatures2);
    LOAD_INST(&c, GetPhysicalDeviceFormatProperties);
    if (!GetPhysicalDeviceFeatures2 || !GetPhysicalDeviceFormatProperties) {
        LOG("FAIL: missing feature/format query entrypoint");
        goto done;
    }
    GetPhysicalDeviceFeatures2(c.phys, &f2);
    LOG("dynamicRendering=%u synchronization2=%u samplerAnisotropy=%u",
        f13.dynamicRendering, f13.synchronization2, f2.features.samplerAnisotropy);
    LOG("Optional: BC=%u nonSolid=%u wideLines=%u largePoints=%u",
        f2.features.textureCompressionBC, f2.features.fillModeNonSolid,
        f2.features.wideLines, f2.features.largePoints);
    LOG("Limits: maxImageDimension2D=%u maxPushConstantsSize=%u maxSamplerAnisotropy=%.1f",
        c.props.limits.maxImageDimension2D, c.props.limits.maxPushConstantsSize,
        c.props.limits.maxSamplerAnisotropy);

    ok = c.props.apiVersion >= VK_API_VERSION_1_3 && f13.dynamicRendering &&
         f13.synchronization2 && f2.features.samplerAnisotropy;
    const char *functions[] = {
        "vkCmdBeginRendering", "vkCmdEndRendering", "vkCmdPipelineBarrier2",
        "vkQueueSubmit2", "vkCmdPushDescriptorSetKHR", "vkCreateSwapchainKHR",
        "vkQueuePresentKHR",
    };
    for (unsigned i = 0; i < sizeof(functions) / sizeof(functions[0]); ++i) {
        bool found = c.GetDeviceProcAddr(c.dev, functions[i]) != NULL;
        LOG("%s: %s", functions[i], found ? "present" : "MISSING");
        ok = ok && found;
    }
    const VkFormat formats[] = {
        VK_FORMAT_R8G8B8A8_UNORM, VK_FORMAT_B8G8R8A8_UNORM,
        VK_FORMAT_D24_UNORM_S8_UINT, VK_FORMAT_D32_SFLOAT_S8_UINT,
        VK_FORMAT_BC1_RGBA_UNORM_BLOCK, VK_FORMAT_BC3_UNORM_BLOCK,
    };
    for (unsigned i = 0; i < sizeof(formats) / sizeof(formats[0]); ++i) {
        VkFormatProperties properties;
        GetPhysicalDeviceFormatProperties(c.phys, formats[i], &properties);
        LOG("format=%d optimalFeatures=0x%x", formats[i], properties.optimalTilingFeatures);
    }
done:
    nvk_teardown(&c);
    LOG("=== ngb_vk_caps %s ===", ok ? "PASSED" : "FAILED");
    LOG("Log: sdmc:/ngb_vk_caps.log (driver: sdmc:/nvk_mesa.log)");
    LOG("Press PLUS to exit. A pass is NOT a game compatibility verdict.");
    while (appletMainLoop()) {
        padUpdate(&pad);
        if (padGetButtonsDown(&pad) & HidNpadButton_Plus) break;
        consoleUpdate(NULL);
    }
    if (g_nvk_log) fclose(g_nvk_log);
    consoleExit(NULL);
    return ok ? 0 : 1;
}

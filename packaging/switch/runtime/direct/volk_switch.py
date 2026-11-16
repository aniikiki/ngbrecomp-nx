"""Use nxvk's statically linked ICD instead of volk's dlopen path on Horizon."""
from pathlib import Path
import sys

src, dest = map(Path, sys.argv[1:])
code = src.read_text()
start = code.index("VkResult volkInitialize(void)")
end = code.index("void volkInitializeCustom(", start)
code = code[:start] + """extern PFN_vkVoidFunction vk_icdGetInstanceProcAddr(VkInstance, const char*);
VkResult volkInitialize(void)
{
    volkInitializeCustom(vk_icdGetInstanceProcAddr);
    return VK_SUCCESS;
}

""" + code[end:]
code = code.replace("#\tinclude <dlfcn.h>", "").replace("dlclose(loadedModule);", "(void)loadedModule;")
dest.write_text(code)

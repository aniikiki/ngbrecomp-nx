# Switch 最小验证程序

目标：初代 Nintendo Switch / Lite / OLED，Horizon 原生 homebrew `.nro`。
这套程序不包含、不读取 NGB 游戏数据，不访问游戏存档。

## 安装和运行

将测试包里的 `switch` 文件夹合并复制到 SD 卡根目录。
从 **Application 模式**的 hbmenu 启动测试（通常按住 R 启动一个已安装游戏进入）；
NXVK 测试按 Application 模式构建，不要从相册的 Applet 模式运行。

按下表顺序逐个运行。前三个无画面的 NXVK 测试可能很快返回 hbmenu，
是否通过以日志为准。某项失败或卡住时先保留日志，不必继续后面的项目。

| 程序 | 操作和预期 | SD 卡日志 |
|---|---|---|
| `ngb-basic-probe.nro` | 屏幕出现 SD / Heap PASS；heartbeat 持续增长；按键和摇杆数值变化。A 重测 SD，B 重测内存，X 将摇杆值记入日志，+ 退出 | `/switch/ngb-probe/logs/basic-*.log` |
| `ngb_vk_caps.nro` | 创建启用 dynamic rendering、synchronization2、各向异性采样及 push descriptors 的设备，显示 PASSED；+ 退出 | `/switch/ngb-probe/logs/ngb_vk_caps.log` |
| `nvk_smoke.nro` | GPU 填充缓冲区并回读比对，自动退出，日志含 PASSED | `/switch/ngb-probe/logs/nvk_smoke.log` |
| `nvk_tri.nro` | 离屏渲染三角形并验证，自动退出，日志含 PASSED | `/switch/ngb-probe/logs/nvk_tri.log` |
| `nvk_textures.nro` | 离屏纹理测试，自动退出，日志含 PASSED | `/switch/ngb-probe/logs/nvk_textures.log` |
| `nvk_vi_swapchain.nro` | 应出现随时间变色的画面，运行最多 300 帧后退出，日志含 PASSED；还需人工确认画面显示正常 | `/switch/ngb-probe/logs/nvk_vi_swapchain.log` |

NXVK 的驱动日志统一为 `/switch/ngb-probe/logs/nvk_mesa.log`，每次图形测试会覆盖它；
失败时请在下一次测试前复制这份日志。各 NXVK 程序的同名日志也会被重跑覆盖。
基础测试每次使用独立日志文件，只创建并删除自己的临时读写测试文件。

请反馈：

- 机型、系统版本、掌机/底座模式、hbmenu 是否为 Application 模式。
- 基础程序屏幕照片，按 + 后是否能回到 hbmenu，以及对应 `basic-*.log`。
- 每个图形程序的日志；失败时的 `nvk_mesa.log`、现象和系统错误码。
- `nvk_vi_swapchain` 是否显示变色画面、是否正常返回。

## 清理空间

所有测试程序、日志和临时文件均位于 SD 卡的 `/switch/ngb-probe/` 内。
磁盘着色器缓存已关闭；SD 读写测试创建的 `.io` 文件在测试完成时删除，
异常中断若留下该文件，也只会留在此目录中。

- 保留程序、只清日志：退出测试程序后删除 `/switch/ngb-probe/logs/`，下次运行会重建。
- 全部卸载：先保存需要反馈的日志，然后删除 `/switch/ngb-probe/` 整个文件夹。
- 如出现系统崩溃，Atmosphère 自己生成的系统崩溃报告由系统管理，不属于测试程序写入的文件。

程序不安装系统组件，不创建游戏存档，不修改系统配置。测试包仅上传解压后的程序，
不需要把 ZIP、源码或游戏镜像复制到 Switch。

## 验证范围

基础程序验证 8 MiB 堆内存的实际读写、SD 文件读写、输入及普通 libnx 线程的运行和退出。
它**没有验证** Xbox 的 4 GiB 虚拟地址窗口、别名映射、MMIO 异常、优先级调度或游戏 fiber。
Vulkan 功能程序验证设备创建和入口存在；实际 GPU 执行由另外四个 NXVK 测试补充。
这些结果不能替代 NGB 渲染器集成测试，也不能预测游戏帧率。

## 2026-11-10 真机结果

6 项测试全部通过，日志已通过 DBI FTP 下载到本机
`build/switch-probe/device-logs/20261110-174603/`，该目录包含原始日志及 `results.json`。

- 基础：SD 与 8 MiB 堆内存检查通过，输入有记录，后台线程正常增长，按 + 后线程回收和退出成功。
- Vulkan 功能：设备报告 NVIDIA Tegra X1 / Vulkan 1.4.354；请求的功能启用和设备创建通过。
- GPU：缓冲区回读、三角形像素检查、sRGB/mipmap/BC1 纹理测试通过。
- 呈现：1280×720，300/300 帧提交呈现；用户确认看到了多种变色。

这证明本套独立测试通过，不代表 NGB 已可运行；客体内存映射、Xbox 调度、MMIO 和游戏渲染集成仍需验证。

## 在 Mac 上重新构建

在仓库根目录执行：

```sh
bash packaging/switch/build-probe.sh
bash packaging/switch/build-nxvk.sh
```

基础产物位于 `build/switch-probe/ngb-basic-probe.nro`，图形产物位于
`build/switch-probe/nxvk/`。两个脚本都使用 Docker，不需要在 macOS 安装 devkitPro。

基础镜像固定到 `devkitpro/devkita64:20260219` 对应的 manifest digest
`sha256:1fc388c3a0d34bd2045a6dadcb1020e069d5f876a187fd705de14b4440c00282`。
NXVK 固定到 `c3abea1efde44027b7e3e20b48eb55beeecd5ab4`，默认源码位于仓库的同级
`nxvk` 目录，可用 `NXVK_DIR` 指定已有路径。

`Dockerfile.nxvk` 基于该 revision 自带 Dockerfile，固定基础镜像并限制 Cargo 并发；
构建脚本限制 Ninja 默认使用两个任务，容器最多使用 6 GiB 内存。
镜像内的部分包仍由上游软件仓库解析，因此这些 pin 不代表逐字节可复现。
测试源码在构建目录暂存后重定向日志路径并停用上游 chainloader；NXVK 原始源码不修改。
构建记录保存在 `build/switch-probe`，游戏镜像和生成代码均不参与测试包打包。

## 上游来源

- [devkitPro Docker 镜像源码](https://github.com/devkitPro/docker)
- [NXVK 固定版本](https://github.com/PalindromicBreadLoaf/nxvk/tree/c3abea1efde44027b7e3e20b48eb55beeecd5ab4)
- [NXVK 验证程序](https://github.com/PalindromicBreadLoaf/nxvk/blob/c3abea1efde44027b7e3e20b48eb55beeecd5ab4/switch/smoke/README.md)

图形测试链接 NXVK/Mesa，继承对应上游许可；本地新增的功能检测源码位于
`packaging/switch/probe/vulkan.c`，基础测试源码位于 `packaging/switch/probe/main.c`。

## 游戏启动接入（0.13.0）

`packaging/switch/runtime/` 是独立的游戏启动适配器。它不再跑图形样例，而是加载用户
镜像中的 `default.xbe`，执行重新编译的 `xbe_entry_point`。这只是运行时接入的第一段，
尚无标题画面、可玩场景、音频或完整 Xbox 内核/线程调度；文件系统仅覆盖启动所需的同步操作。

当前路径：16 个 XBE section → 64 MiB 客体内存 → 145 个内核导入 → 游戏入口
`0x0032b385` → 首线程 trampoline `0x003298ad` → XAPI 初始化 `0x0032b311`。
初始化 TIB/TLS，支持单个客体线程的递归临界区，并沿用上游的零 section 内核兼容页和
零售机硬件/内核版本字段。线程创建目前仅支持第一次同步交接，不代表完整调度已完成。
未实现的内核调用、缺失的间接调用目标和未映射的设备地址会停止并记日志。

0.4.0 真机已完成缓存格式化与挂载，见
`build/switch-runtime/device-logs/20261111-095244/results.json`。
0.5.0 真机已查询光驱链接，并到达第一笔连续内存申请。0.6.0 真机通过两笔连续内存的读写校验。
0.7.0 真机已创建记忆卡设备并访问 8 KiB 缓冲区。0.8.0 真机已初始化 USB 中断对象。0.9.0 真机进入 Direct3D 设备创建并访问 NV2A。0.10.0 真机已读出 NV2A 配置，并尝试连接 GPU 中断线 3。

日常推进在仓库根目录执行下面的本地验证。它构建与 Switch 共用的运行时，重跑启动、
旧版数据和 USB 定时器在显存清零期间触发的场景。日志保存在 `build/switch-runtime/`。

```sh
bash packaging/switch/build-runtime.sh check
```

需要检查画面呈现、手柄输入或调查仅在真机发生的差异时，使用
`bash packaging/switch/build-runtime.sh switch` 构建 NRO。

可加第二个参数 `--generate` 强制重新分析/生成。首次会从项目 `disc/` 下 ISO 提取
`game_files/`，可通过 `NGB_ISO` 指定其他绝对路径。构建固定 devkitPro 镜像 digest、
限制 6 GiB 内存和两个编译任务。生成代码放在被 Git 忽略的 `build/switch-runtime/`，
正常桌面版本生成代码不使用此处的地址检查和启动追踪插桩。

产物为 `build/switch-runtime/switch/ngb-startup.nro`，内含用户 XBE 的私有 RomFS，
仅用于自己的设备，不提交游戏文件或生成代码到仓库。暂不需要把整个约 6 GB 游戏资源
复制到 Switch。验证脚本运行真实启动路径，并检查改动、截断和缺失的 XBE 被拒绝。
记录保存在 `build/switch-runtime/verification.json` 和 `verify-*.log`。

Switch 只需 `/switch/ngb-runtime/ngb-startup.nro` 这一个入口。使用按住 R 启动已安装
游戏的方式进入 hbmenu，给程序完整内存。打开 **NGB Startup** 后会自动运行并显示
`STOPPED (status 1)` 和上述服务名；这属于当前预期结果，无需一直等待。按 **+** 退出。
然后进入 DBI FTP，即可取回 `/switch/ngb-runtime/logs/boot.log`。FTP 只用于读写文件，
不能代替在主机上启动程序，也不能在 DBI 已退出后继续读取实时日志。

日志每次覆盖同一个文件，普通日志限制为 1024 行，另保留停止状态和最后的调用记录。
生成代码的基本块加入取消和约 10 秒启动预算检查；这是诊断用插桩，不能用于预测性能。
运行时自身只在 `/switch/ngb-runtime/` 写日志和启动元数据。数据位于 `data/`，普通文件
单个上限 1 MiB、总内容上限 8 MiB、文件数上限 128；0.4.0 电脑启动生成 5 个文件，
内容合计 137,280 字节，SD 实际占用另含簇和目录开销。重复启动复用这些文件，不增加副本。
删除 `data/` 可重置虚拟磁盘；删除整个 `ngb-runtime/` 可清理程序、日志及数据。主机系统若崩溃，Atmosphère 的报告由系统另行管理。

### 2026-11-10 游戏启动适配器真机结果

用户运行 0.1.0 后重新打开 DBI FTP，已下载 `boot.log` 到
`build/switch-runtime/device-logs/20261110-182832/`，同目录 `results.json` 保存检查结果。
真机日志与电脑 ARM64/Linux 的 `verify-startup.log` 内容一致：16 个 section 和 145 个
内核导入加载完成，TLS 初始化完成，执行游戏入口并交接到首线程，临界区进入/退出完成。
最后在 `HalRegisterShutdownNotification`（47）主动停止，输出完整 `[RESULT] status=1`。
本轮启动接入验证通过；这不代表完整 Xbox 调度、游戏资源读取或游戏画面已经运行。

### 0.2.0 内核接入及电脑验证

- 直接编译并链接上游 `kernel_xbox.c` 的主机设置读取和 `kernel_rtl.c` 的状态码转换；
  未用函数由链接器删除，无需引入完整桌面平台层。未知 EEPROM 索引仍停止并记录。
- 按上游客体布局初始化 DPC 和定时器。定时器在生成代码的轮询点协作调度，支持单次、
  周期、重设与取消；到期设置客体信号状态，并用独立栈/SEH 链执行原始游戏 DPC，返回后
  恢复寄存器。这还不是完整的线程、事件等待或中断优先级调度器。
- `NtAllocateVirtualMemory`、`NtFreeVirtualMemory` 和 `NtQueryVirtualMemory` 接入独立
  页状态表：预留、提交、取消提交、释放、查询、冲突拒绝与空间重用。地址区域是
  `0x01000000..0x03e00000`，只有读写页受支持，仍受现有 64 MiB 客体映射限制；
  不声称支持整个 4 GiB 虚拟空间。取消提交后重提交得到零页。
- 关机通知保存注册项；回到 hbmenu 是退出宿主程序，不触发 Xbox 系统关机回调。
  文件打开目前仅解码并记录路径，不返回虚假句柄。

实际启动达到 23 次生成函数入口、13 次间接调用：注册 6 小时闲置定时器，预留 1 MiB
游戏堆并提交首个 4 KiB 页面，随后请求上述硬盘目录。这些步骤在电脑 ARM64/Linux
通过；0.2.0 真机结果见下节。

`ctest` 的三项检查通过：客体页生命周期/边界、定时器生命周期、内核桥调用约定及
原始游戏 DPC 的寄存器/栈恢复。内存和定时器模块另通过 macOS ASan/UBSan 检查。
完整启动以及损坏、截断、缺失 XBE 的四项集成检查也通过。测试程序只在电脑构建，
Switch 仍只有同一个 `ngb-startup.nro`；没有上传游戏资源或新增测试入口。

### 2026-11-10 0.2.0 真机结果

设备日志已保存到 `build/switch-runtime/device-logs/20261110-185312/boot.log`，
同目录 `results.json` 的全部 11 项检查通过，完整日志与电脑启动日志一致。
确认了设置读取、6 小时定时器注册、1 MiB 堆预留及首个 4 KiB 页面提交，最终按预期
停在打开 `\Device\Harddisk0\partition1\` 的 `NtOpenFile`，有完整 `[RESULT] status=1`。
这次短暂启动没有等到定时器到期，不构成真机 DPC 回调触发验证；回调执行与寄存器恢复
目前由电脑端独立集成测试覆盖。此版本无需重复运行，下一步是虚拟磁盘与文件句柄。


### 0.3.0 虚拟磁盘与文件接入

- `D:` / `\Device\CdRom0` 映射到只读 RomFS；Xbox 硬盘分区映射到本程序的 `data/hdd/`。
  支持大小写无关路径、相对目录句柄和客体盘符链接；拒绝越界路径和宿主符号链接。
- 提供有生命周期和共享检查的 32 位客体句柄，支持同步打开/创建目录与普通文件、读写、
  关闭、位置设置、文件信息及卷信息查询。按上游给出 16 KiB FATX 簇几何。
  目前不支持异步完成、文件删除/截断、原始磁盘写入；遇到这些服务明确停止。
- 游戏原始启动创建 `TDATA` / `UDATA` 和标题目录 `5443000d`，写入 `TitleMeta.xbx`
  （64 字节）、`TitleImage.xbx`（10,240 字节）、`SaveImage.xbx`（4,096 字节），建立 `T:` / `U:`。
  上述私有内容来自用户 XBE，不提交到 Git。
- `partition0` 仅有内存中的 4 KiB 模拟头部及上游零售分区表，支持受限读取与几何查询。
  `HalDiskCachePartitionCount` 是值为 3 的数据导出。不存在 GB 级稀疏磁盘文件，
  也不会对 SD 卡发出原始磁盘读写。
- `RtlEqualString` 复用上游实现，客体字符串先校验并转换；XBE section 加载/卸载跟踪
  已加载区段的引用计数，启动适配器保留所有区段，不据此宣称完成动态换入换出。

电脑检查：四项 CTest 通过；文件模块通过 macOS ASan/UBSan。真实启动、重复启动、
三个元数据文件的内容与大小一致性、改动/截断/缺失 XBE 拒绝检查通过。
桥接测试通过客体的 `NtOpenFile` / `NtReadFile` / `NtQueryInformationFile` / `NtClose`
读取真实 XBE，检查栈清理、IOSB 字段边界和失效句柄，测试结束删除自有临时目录。
主机 CLI 必须显式指定独立数据目录：`ngb-startup default.xbe scratch-data-directory`。
Switch 0.3.0 真机未通过，原因与修复见下节。


### 2026-11-10 0.3.0 真机差异与 0.3.1 修复

真机资料保存于 `build/switch-runtime/device-logs/20261110-192729/`，包含原始日志、
文件清单、下载的数据及 `results.json`。0.3.0 成功完成目录创建和卷查询，但新建
`TitleMeta.xbx` 后的 `NtQueryInformationFile`（class 34）返回 `c0000001`；游戏进入
错误处理路径，最后在 `MmAllocateContiguousMemory` 停止。这不是预期的缓存盘停止点，
因此本轮不能记为通过。设备实际只有 0 字节的 `TitleMeta.xbx`，日志 9,999 字节，
并未产生预期的两个图标文件。

原实现对已打开的普通文件使用 `stat(path)`。固定版本的
[libnx fs_dev.c](https://github.com/switchbrew/libnx/blob/v4.12.0/nx/source/runtime/devices/fs_dev.c#L1038)
显示该调用会另开读句柄，可能与现有写句柄冲突；0.3.0 日志未记录原生错误码，
这一具体冲突原因尚需修复版真机结果确认。0.3.1 改用 `fstat(fileno(file))` 查询现有
文件对象，目录继续按路径查询，并在文件信息失败时保留原生 errno 方便后续定位。

新增回归检查：打开的文件即使改名，客体信息查询仍返回同一个文件对象的信息；
集成检查重建真机遗留的空 `TitleMeta.xbx`，确认可以补写完整元数据，无需先删数据。
0.3.1 保持同一个程序入口、数据目录和容量限制，预期仍在缓存盘原始写入处停止；
真机结果已通过，见下节。


### 2026-11-10 0.3.1 真机结果

设备资料保存在 `build/switch-runtime/device-logs/20261110-193159/`，含 `logs/boot.log`、
`inventory.json`、三个下载的元数据文件及 `results.json`。全部 18 项检查通过，
完整日志与电脑端首次启动及空文件恢复的日志一致。

上次遗留的空 `TitleMeta.xbx` 已补写为 64 字节，`TitleImage.xbx` 为 10,240 字节，
`SaveImage.xbx` 为 4,096 字节；三个文件内容均与电脑端一致，两个图标文件也与用户
XBE 的对应 section 逐字节一致。文件信息查询三次均成功，证明改用现有句柄后已越过
0.3.0 的真机失败点。此前缺少原生错误码，因此不额外声称已捕获具体的系统冲突代码。

真机随后成功读取模拟分区头部 512 字节，最终在向 `partition0` 偏移 2048 写入
512 字节时按预期主动停止，结果为 `unsupported file operation: 0x000000ec`。
尚未接入的下一阶段仍是缓存盘头部写入与初始化，并不代表游戏画面或可玩场景已运行。

本轮设备目录仅有同一个 NRO、12,060 字节日志和三个合计 14,400 字节的数据文件；
没有额外大型磁盘镜像。以上是文件内容大小，不含 SD 簇和目录开销。所有资料已本地
备份，本轮未删除或修改设备数据。真机重复启动不在本轮检查范围内，电脑端已覆盖。


### 0.4.0 缓存初始化（仅本地编译，待真机）

- 模拟 `partition0` 的 4 KiB 头部保存为 `data/hdd/partition0-header.bin`。
  记录客体实际写入并在下一次启动读回，写入前检查边界和共享容量，不扩展成整盘镜像。
  长度不正确的既有头部会使初始化失败，不静默丢弃状态。
- 区分没有尾部分隔符的原始缓存设备 `Partition3..5` 与带分隔符的文件系统根目录。
  原始设备支持磁盘几何、分区长度查询及前 1 MiB 范围内的受限读写，按需增长普通文件；
  模型外读取停止，超容量写入拒绝。分区长度沿用上游零售缓存几何 750 MiB，仅是客体
  逻辑几何；不会创建对应大小的文件。缓存文件系统访问仍通过宿主目录和 8 MiB 共享额度，
  并未实现通用 FATX 文件系统驱动或任意原始磁盘访问。
- 接入 `KeQuerySystemTime`，返回真实时钟的 NT 100 ns 时间值，供原始游戏生成卷标识。
  游戏自身写入 FATX 头、分配表和空根目录；本版实际选择分区 5，保存为
  `data/hdd/cache-partition5.bin`，大小 118,784 字节。
- 接入本阶段用到的 `NtFsControlFile(0x90020)`：刷新缓存设备并停止该句柄继续读写。
  随后的目录挂载检查 FATX 头字段和完成格式化所需的长度，不把空或截断分区当成已格式化。
  在中途退出后重启，游戏会重新格式化不完整缓存，之后建立 `Z:` 链接。
- 新停止点是 `NtOpenSymbolicLinkObject`（203）。这说明本阶段的缓存初始化已在电脑端
  越过，不代表所有文件系统接口或完整启动运行时已完成。

本地四项 CTest 和文件模块 macOS ASan/UBSan 通过；十项集成结果包含首次启动、重复
启动、大小与内容校验、遗留空文件恢复、0.3.1 数据升级、中断格式化恢复、错误缓存头恢复，
以及三种错误 XBE 拒绝。重复启动不再次格式化，五个文件的内容和总大小保持不变。
格式化的卷标识来自当前系统时间，不同新建运行之间只在该字段允许差异。

普通三个元数据文件仍共 14,400 字节；新增两个缓存状态文件共 122,880 字节，总内容
137,280 字节（约 134 KiB）。全部位于 `ngb-runtime/data`，之后可整体删除重建。
0.4.0 真机日志与电脑端从 0.3.1 升级的启动日志一致，缓存头、FATX 信息及三个标题文件均已核对。

### 0.5.0 盘符链接与启动计时

运行时通过 Xbox 内核序号 203、215、187 打开、查询和关闭盘符链接。查询返回创建该链接时
记录的设备目标，并检查输出缓冲区长度与句柄类型。启动日志显示游戏查询 `D:`，目标为
`\Device\CdRom0`。链接对象使用内存中的句柄表。

`KeTickCount` 读取游戏启动以来的单调时钟毫秒数，`HalBootSMCVideoMode` 使用上游的冷启动值。
在电脑端使用 0.4.0 真机数据副本运行时，五个数据文件均保持原有内容，随后游戏申请
38,215,680 字节的连续内存，在该服务入口停止。0.5.0 真机日志已确认同一请求，见
`build/switch-runtime/device-logs/20261111-100610/results.json`。

### 0.6.0 连续内存与记忆卡设备初始化

启动适配器沿用桌面端物理地址窗口，把普通连续分配放在物理偏移 64–128 MiB 内。
每笔分配使用独立、清零的内存，支持页对齐、地址范围限制、地址查询和释放。
当前支持启动路径请求的读写保护值 4。进入与离开 DPC 优先级时会更新客体
`fs:[0x24]`，在优先级降低后继续投递到期的定时器。输入驱动使用的物理第零页单独映射。

游戏按顺序申请 38,215,680 字节和 2,097,152 字节。适配器在交给游戏前分别验证首尾写入、
读回与恢复，日志出现两次 `[MEMORY] readback passed`。这些操作只占运行内存。
随后游戏调用 `IoCreateDevice` 请求创建 `\Device\MU_0`。主机端使用上一版真机数据
和本版 RomFS 启动，五个数据文件保持逐字节一致。0.6.0 真机日志已确认两次读回和同一设备请求，与主机端升级日志逐字节一致。
真机数据目录仍为五个文件，共 137,280 字节，内容与 0.5.0 完全一致。
记录见 `build/switch-runtime/device-logs/20261111-101904/results.json`。

### 0.7.0 记忆卡设备对象与 USB 启动缓冲区

`IoCreateDevice` 在已提交的客体内存中创建记忆卡设备对象，初始化内嵌队列和事件，
为设备扩展保留独立空间。游戏取得 `\Device\MU_0` 的对象地址后，自行写入其 368 字节扩展。
设备对象随启动进程释放。[Xbox 设备对象字段定义](https://github.com/XboxDev/nxdk/blob/master/lib/xboxkrnl/xboxkrnl.h)

输入驱动随后申请并锁定 8,192 字节连续内存，取物理地址，用客体指令清零并填入数据。
适配器按页记录锁定次数，检查整段地址并阻止释放仍有锁的块。本版真机核对点依次为
`created device name=\Device\MU_0`、`lock pages va=86672000 bytes=8192`、
`first guest access va=86672000` 和 `HalGetInterruptVector: 0x0000002c`。
主机端基于 0.6.0 真机数据副本重跑后，五个文件合计 137,280 字节且内容一致。

0.7.0 真机已确认设备创建、缓冲区锁定和客体访问，随后停在中断向量查询。
五个数据文件与 0.6.0 真机数据逐字节一致。记录见
`build/switch-runtime/device-logs/20261111-102541/results.json`。

### 0.8.0 USB 控制器启动及中断对象

游戏查询 IRQ 1，得到向量 `0x31` 和 IRQL 26。五个启动例程通过读写接口访问首个 OHCI
控制器的寄存器。主机日志记录了读取版本、软件复位、写入 HCCA 物理地址 `0x06672000`，
以及设置控制端点队列的过程。此处实现了启动所需的寄存器操作，USB 传输、手柄枚举与
中断投递有待接入。[中断向量定义](https://github.com/Cxbx-Reloaded/Cxbx-Reloaded/blob/master/src/core/kernel/init/CxbxKrnl.h)

游戏随后调用 `KeInitializeInterrupt`，填写客体中断对象，服务例程地址为 `0x003dfe3d`。
本版预期停在 `KeConnectInterrupt`（98）。0.7.0 真机数据副本的五个文件在主机测试后逐字节一致。

0.8.0 真机已确认 USB 控制器复位、缓冲区配置和中断对象初始化，随后停在连接中断的调用。
五个数据文件与 0.7.0 真机数据逐字节一致。记录见
`build/switch-runtime/device-logs/20261111-103536/results.json`。

### 0.9.0 USB 中断投递与 Direct3D 设备创建

Switch 端采样 libnx 的手柄连接状态，主机端测试使用一个已连接手柄。Xbox 根集线器开放端口变化
中断后，运行时把连接状态变化交给 IRQ 1。游戏自己的 ISR（`003dfe3d`）返回已处理并排入
DPC（`003e0511`）。游戏降低 IRQL 后执行 DPC，确认端口状态变化并重新开启中断。
本轮验证覆盖设备连接事件。USB 报告传输与游戏内按键输入仍需后续接入。

主机端日志随后出现 `[D3D] Direct3D_CreateDevice entry=003cc310`。游戏申请 1 MiB
写合并缓冲区后读取 NV2A 的 PCI 命令/状态寄存器，停在 `0xfd001804`。启动适配器使用
CPU 内存模拟这块可读写缓冲区并记录客体保护属性。图形设备创建和首帧呈现仍待实现。
主机端的 0.8.0 真机数据副本保持五个文件、共 137,280 字节。

0.9.0 真机日志确认中断处理和 DPC 返回，随后进入 `Direct3D_CreateDevice`，在读取
NV2A PCI 命令/状态寄存器 `0xfd001804` 时停止。五个数据文件与 0.8.0 真机数据逐字节一致。
记录见 `build/switch-runtime/device-logs/20261111-104508/results.json`。

### 0.10.0 NV2A 设备探测

游戏在 `003cf055` 读取 PCI 命令寄存器并写入 `4`，随后关闭 PCRTC 和 PTIMER 中断。
在 `003cf080`，游戏读到设备标识 `02a010de`、类别及修订号 `030000a1`。
PFB 报告当前客体物理地址空间大小 128 MiB。该数值来自移植运行时的内存配置。

主机日志随后记录 GPU 中断向量 `0x33`、处理函数 `003cf980`，并在
`KeConnectInterrupt` 报告 `unsupported interrupt line: 0x00000003`。
真机日志已确认该停点，见 `build/switch-runtime/device-logs/20261111-113016/results.json`。

### 0.11.0 GPU 中断连接

USB 和 GPU 中断对象分别注册到第 1、3 号线。GPU 启动适配器按 60 Hz 采样垂直消隐，
在 PCRTC 和 PMC 中断使能且客体 IRQL 允许时，通过客体中断栈投递事件。
这个阶段使用启动时钟，尚未接入游戏画面的显示同步。

主机运行原始启动流程时，游戏连接第 3 号线，注册关机通知，写入 PCI 配置，
随后在 `003d2c43` 读取 `NV_PMC_ENABLE` 时停下。此时游戏尚未开启显示中断。
真机的预期停点为 `unsupported NV2A read: 0xfd000200`。

独立主机测试设置驱动就绪标志并打开垂直消隐中断，用重编译的游戏处理函数
`003cf980` 验证 IRQL 屏蔽、关闭主中断和 DPC 入队。完整启动流程达到上述停点时，
显示中断仍处于关闭状态。

0.11.0 真机已连接 IRQ 3，在读取 `NV_PMC_ENABLE` 时停止，见
`build/switch-runtime/device-logs/20261111-114043/results.json`。

### 0.12.0 GPU 时钟与定时器

游戏向 `NV_PMC_ENABLE` 写入全 1，随后以 32 位及 8 位两种宽度读取内存、视频和核心 PLL 系数。
本版沿用仓库桌面 NV2A 后端的启动系数。游戏把 PTIMER 的分子设为 `0xde86`、分母设为
`0x1dcd`，并写入 alarm 比较值。独立主机测试覆盖引擎屏蔽、计时器匹配中断及清除。

主机完整启动随后进入 `MmClaimGpuInstanceMemory`，请求 `0x5000` 字节。当前预期停点为
`MmClaimGpuInstanceMemory: 0x000000a8`，末尾数值是内核导出序号 168。

0.12.0 真机已确认这笔 20 KiB 申请，见 `build/switch-runtime/device-logs/20261111-121516/results.json`。

### 0.13.0 GPU 实例内存与 FIFO 表

在当前 128 MiB 客体布局下，`MmClaimGpuInstanceMemory` 返回上界 `0x87ff0000` 和
64 KiB 填充。游戏自行减去申请量，得到 CPU 起址 `0x87feb000`。
PRAMIN 与 CPU 端共享内存，以 64 字节为单位反向寻址。启动日志记录 RAMHT、RAMFC
的寄存器写入及清零范围首尾。主机测试先把 20 KiB 填成非零值，运行游戏初始化函数，
再从 CPU 映射逐字节检查。真机预期停在显示控制器的索引寄存器 `0xfd6013d4`。

0.13.0 真机取得了实例内存，并写入 RAMHT、RAMFC 和 PRAMIN 首字。清零期间 USB 定时器
触发，游戏向 `0xfed00054` 写入端口复位命令时停止。原始日志位于
`build/switch-runtime/device-logs/20261111-130834/logs/boot.log`。

0.13.1 将端口复位和禁用操作接入 OHCI 总线，按有效位处理端口命令。主机时序测试在第一次
PRAMIN 写入后让真实的 USB 定时器到期，再检查端口复位、复位完成确认、PRAMIN 最末写入和
显示控制器停点 `0xfd6013d4` 的先后顺序。

### 0.14.0-dev：首批游戏 GPU 命令（主机回放）

在本地运行 `bash packaging/switch/build-runtime.sh check`。普通启动、历史真机数据副本以及
PRAMIN 清零期间插入 USB 复位的回放均检查同一批命令。本阶段无需每改一个寄存器就上机测试。

游戏完成 PGRAPH 启动配置，镜像八组内存分块配置，建立 PFIFO DMA 通道。第一次提交后，
运行时从游戏写入的 DMA 描述符找到物理页零，执行其中的跳转。游戏从 USER 寄存器读回
GET 为 `06675000` 后才继续。它随后分配 2,949,120 和 1,474,560 字节的图形内存，
写入并读回分块配置，再查询 AV pack 并把 PUT 推到 `06675280`。

两指针之间 640 字节包含 32 个方法包、128 个参数字。只读解码从游戏自己的 RAMHT
解析出前五次对象绑定对应的类：97、39、9f、62、44（十六进制）。此处 GET 仍为
`06675000`：第一条 SET_OBJECT 尚未分派给图形引擎。这是接入命令执行的测试输入；
没有执行绘制、设置显示模式或产生标题画面。回放日志为
`build/switch-runtime/verify-startup.log` 和 `build/switch-runtime/verify-usb-reset-during-instance-clear.log`。

### 0.15.0-dev：Direct3D 设备创建成功（主机回放）

第一次绑定图形对象会触发 PGRAPH 上下文切换。运行时保留尚待执行的参数，游戏的 GPU
中断处理函数及 DPC 装入通道零的上下文并重新开放 FIFO，之后才绑定五个子通道对象。
首批 32 个包全部执行，向物理地址 `06674000` 写回信号量 5，GET 与 PUT 均为
`06675280`。游戏调用方随后收到 `Direct3D_CreateDevice` 返回的 HRESULT 0。

`build-runtime.sh check`（见上文）也验证分段提交时的 GET、GPU 对常量的写入及 RDI
读回，检查信号量两侧的内存没有被修改，并在信号量完成后主动插入一次垂直消隐。
在该回放中，游戏处理 vblank，设置事件，随后同样成功返回。详见
`build/switch-runtime/verify-vblank-after-startup-semaphore.log`。

游戏接着提交 2,132 字节、200 个包。主机测试工具只读扫描了这段内存，展开递增方法后看到了
两条 CLEAR_SURFACE（掩码 03、f3）。此时实际执行仍停在第一个设置顶点属性的方法
（Kelvin 类 97，方法 194c）。两条清除指令尚未执行，也没有画面或真机验证。
包头及清除请求记录在 `build/switch-runtime/verify-graphics-command-trace.log`。

### 0.16.0：从游戏清屏到 Switch 显示（待真机确认）

主机回放中，第二批 200 个命令包（333 个参数）全部执行。游戏清除 720×480
的 Z24S8 和 A8R8G8B8 表面，然后在 AvSetDisplayMode 选择物理地址 06778000，
并把同一地址写入 PCRTC。该表面每行 3072 字节，读出的可见像素均为黑色。
此处保留第一帧；随后的 TV 编码器选项 0x0f 仍会停止游戏。尚无标题图像。

主机测试以彩色输入检查清屏掩码、裁剪、行尾填充、通道顺序及 4:3 缩放；
在释放游戏内存后仍能读取所保存的首帧。运行时仅在内存中保存画面，不写截图。
Switch 测试：在 hbmenu 启动 NGB Startup；若出现灰蓝色背景上的黑色矩形，
说明首帧已经送到屏幕。B 返回详情，A 重看，+ 退出。若只显示文字或全屏黑色，
保留该现象并查看原有 logs/boot.log。画面提交给 libnx 后日志会有一行
“first guest scanout queued to Switch framebuffer”；日志不能代替肉眼确认显示。

0.16.0 真机只显示了启动文字。USB 枚举定时器在显存实例初始化期间到期，手柄驱动写
HcCommandStatus（0xfed00008）时停住，尚无可显示的首帧。设备日志备份在
`build/switch-runtime/device-logs/0.16.0-text/logs/boot.log`。

0.16.1 接入了 USB 控制传输的提交、描述符响应和完成中断。主机回归在 PRAMIN
写入期间触发端口复位及枚举定时器，并放慢写入以覆盖多次 USB 帧。检查顺序包括
读取设备描述符、分配地址、读取配置、选择配置、读取 XID 描述符以及首帧捕获。
对应日志为 `build/switch-runtime/verify-usb-enumeration-before-first-frame.log`。

0.16.1 真机确认：屏幕出现灰边里的黑色矩形。对应日志有 720×480 首帧、
nonblack=0 和 Switch framebuffer 提交记录。随后游戏停在编码器选项 0x0f。
记录在 `build/switch-runtime/device-logs/0.16.1-first-frame/logs/boot.log`。

0.17.0-dev 主机回放根据垂直消隐时钟向游戏返回奇偶场，并处理解除消隐及冷启动 AV
数据地址。游戏随后从光盘读取 load_img.bin 的全部 37596 字节，查询内核池分配大小，
走到声音处理器前端控制寄存器 0xfe801100。日志在 `build/switch-runtime/verify-startup.log`。

### 0.18.0 启动警告页

主机回放中，原版 XBE 初始化 AC’97 和 APU，在静音模式下提交音效程序，启动工作线程并切换 XAPI fiber。游戏从自己的 AFS 读取字库和图像，向 NV2A 提交纹理四边形。CPU 渲染路径处理本页用到的离屏缩放、A8 纹理、索引色字形及透明度混合。显示线程在垂直消隐时取得游戏当前帧缓冲，可见英文 Warnings 和版权正文。此里程碑覆盖启动警告页，标题菜单仍待验证。

私有 RomFS 保存光盘目录、原始文件长度和启动实际读取的区段。读取未打包的区段会报告文件操作停点。SD 卡沿用原入口和数据目录，进入这一阶段会在模拟缓存分区产生一个 212 字节的 `instinfo.ins`。主机测试将写入限制在临时目录，并检查重复启动及从历史版本升级后的文件。真机验收时从 hbmenu 打开 NGB Startup，等待黑底警告文字淡入，按 + 退出后再打开 DBI FTP 读取 `logs/boot.log`。

0.18.0 真机已目视确认 Warnings 标题。真机帧缓冲从 4,061 个非黑像素增加到 44,448 个，随后停在 NtReadFile。主机用同版 RomFS 复现了相同的客体函数、栈指针和通用寄存器，失败请求为读取 `live00.afs` 偏移 55,296 处的 28,672 字节。

### 0.19.0 开场影片与 Start 输入

主机用打包的游戏资源执行原 XBE。游戏在 `0x84095900` 请求对 1,273,856 字节设置写合并，随后以 64 KiB 为单位把完整的 `demo.afs` 安装到 Xbox 的 Z 盘。测试比对缓存和光盘原件，并通过 OHCI 周期中断端点把 Start 交给游戏。警告页淡出后，游戏读取 `movie/4_VI_STD_B.sfd`，用 Sofdec 解码开场海浪。可见帧从实际翻转的 720×480 显示缓冲读取。

从 hbmenu 打开 NGB Startup。待 Warnings 文字清晰后，轻按并松开 +。海浪和远处亮起来的天空可以用来确认开场影片首帧。真机测试时可另外记录海浪是否在动。游戏画面中 + 对应 Start，按 B 可回诊断页，再按 + 退出。随后可用 DBI FTP 读取 `/switch/ngb-runtime/logs/boot.log`。`First Start report delivered` 表示游戏手柄驱动收到 Start，`First decoded movie frame drawn` 表示首个影片矩形已经绘制。

退出 NRO 后可以删除 `/switch/ngb-runtime/data/hdd/partition5/`，同时清掉 10,481,664 字节的影片相关缓存 `demo.afs` 和安装记录 `instinfo.ins`。游戏下次启动时会重建缓存。每次运行都会覆盖同一个 `logs/boot.log`。

### 0.20.0 警告页淡入和单次 Start

原版游戏的等待线程现在只在所有游戏线程都阻塞时让宿主休眠。使用同一份真机缓存，主机回放从亮度 12 到 167 都经过 17 档，耗时从约 10.8 秒降到约 0.52 秒。真机每次运行会在原有 boot.log 中记录 `Warning fade steps`、`elapsed_ms` 和实测峰值，可直接比较。

从 hbmenu 打开 NGB Startup，看到 Warnings 开始淡入时轻按一次 +。程序记住这次按键，直到游戏载入警告页资源并开始接受输入。读取下一场景资源时停止补发。主机回放已在空缓存和已有缓存下看到开场海浪首帧。测试可在首帧出现后按 B 回诊断页，再按 + 退出。

### 0.21.0 真机输入与显示线程

0.20.0 的真机日志记录到警告页前 17 档亮度耗时 4050 毫秒，随后没有 Start 交付记录。0.21.0 使用独立线程每 4 毫秒采样控制器，用三个缓冲区交接输入和画面。可用核心允许时，将游戏运行线程放到另一个核心。画面静止时仍然采样输入，显示线程只提交变化的画面。

查看同一个 boot.log 中的 `[THREADS]` 和 `[INPUT] dedicated_sampler` 可确认实机采用的线程配置。`[INPUT] Plus=1` 和 `B=1` 记录实体按键，`Buffered warning Start on guest flip` 及 `First Start report delivered` 分别记录警告页的按键补发和手柄报告交付。按 B 切回诊断页会记录 `[DISPLAY] diagnostics opened`。主机回放中前 17 档亮度的完整画面哈希与 0.20.0 逐档一致。

### 0.22.0 开场影片连续画面

0.21.0 真机记录到 Warnings 前 17 档亮度耗时 1099 毫秒、Start 报告交付及影片首帧。画面停住后，B 已打开诊断页；随后客体在 0x00346e80 读取了空指针加 0x48 的地址。

回放时，游戏反复绘制海浪的同一张纹理。影片使用的 DirectSound 循环缓冲已经启动，但静音 APU 没有更新其当前位置。0.22.0 按 48 kHz 的采样时钟更新循环缓冲的播放位置，处理音高、暂停、缓冲回绕和停止通知。B 由诊断页独占。程序仍为静音模式。

主机测试从实际翻转的 720×480 客体画面取样，验证冷启动和已有缓存下各有至少 120 个内容各异的完整画面。真机日志在影片纹理内容变化 30 次和 120 次时记录 `Movie content changes=`。本机延长回放读到了 4_VI_STD_B.sfd 最后一段数据，影片收尾时的下一个停点是 APU 方法 0x010c，标题尚待验证。

### 0.23.0 开场影片帧率

0.22.0 真机日志中，画面内容变化 120 次期间游戏提交了 2471 次影片绘制。0.23.0 在原游戏选中 `4_VI_STD_B.sfd` 并进入播放状态时，直接从 NRO 内置原盘影片流式读取 MPEG-1 视频。ARM 版 libavcodec 解码，显示线程按原片的 30000/1001 帧率接收画面。读到影片结束包并排空解码器后，播放状态返回游戏的片尾处理分支。当前影片静音，测试无需额外的 SD 卡影片、转码缓存或截图。

`Opening movie EOF` 记录解码帧数、播放时长、显示线程提交次数和迟到至少一帧的次数。B 打开诊断页，随后按 + 可退出。主机回放中原片共 600 帧，用时 20.02 秒。片尾之后的音频处理仍需补齐。

### 0.24.0 按键到海浪首帧

0.23.0 真机在 20.02 秒内提交了全部 600 帧，迟到一个帧周期的帧数为零。原生播放之前，适配层还等 Xbox 的 Sofdec 解码器从准备状态进入播放状态。0.24.0 在游戏已选定该开场影片并首次报告准备状态时启动原生播放。读到 EOF 并排空解码器后仍由游戏处理片尾。若无法打开影片，游戏可继续使用原解码路径。

在主机容器限制为 0.3 个 CPU、同一份缓存、警告页资源就绪后同一时刻轻按 Start 的对照中，旧路径的按键到首帧为 2403 和 4299 毫秒，新路径两次为 1402 毫秒。新路径从游戏选定影片到首帧均为 8 毫秒。真机每次启动的 `boot.log` 会记录 `start_to_frame_ms` 和 `select_to_frame_ms`。这些时间截止于影片首帧提交给显示线程。独立回归测试在 Warnings 刚开始淡入时按键，已有缓存耗时 1285 毫秒，首次建立缓存耗时 10553 毫秒。

此路径在本地越过影片收尾，执行了保存数据签名使用的 SHA-1 调用。主机与 Switch 均使用桌面移植的 SHA 实现及虚拟主机密钥。标题画面仍待验证。

### 0.25.0 标题画面与主菜单

原游戏在开场影片结束后读取虚拟 EEPROM，用 XAPI 签名并写出 1,360 字节的 `T:\system.dat`。该文件保存在应用自己的 `data` 目录中。RomFS 按游戏实际读取的光盘扇区提供标题、菜单和这两个界面的音乐数据。音频设备推进播放位置并向 DirectSound 通知缓冲区完成，当前版本仍为静音。

本地主机运行原始 XBE，从海浪片尾继续渲染龙隼背景、标题标志和 `PRESS START BUTTON`。在标题输入 Start 后，游戏绘制金色 `MAIN MENU` 标题和菜单项。回归测试对两幅画面的固定区域取样，再通过虚拟手柄发送方向键，并核对游戏自己的光标索引发生变化。

Switch 上打开同一个 NGB Startup，在 Warnings 按 +，等海浪片尾的标题画面出现后再按一次 +，用方向键检查菜单高亮。按 B 回到诊断页，再按 + 退出。设备日志中的 `Main menu cursor=` 会记录菜单绘制和选中项变化。当前验证范围到主菜单。

### 0.26.0 主菜单帧率与方向键

0.25.0 真机日志记录了影片显示 600 帧和主菜单光标 0 → 3。当时日志未记录方向键时间。按同一组上下键、本地独立数据和相同的 7.5 秒采样窗口回放原游戏，0.25.0 刷新 192 帧，0.26.0 刷新 450 帧。软件绘制每帧平均耗时从 31.7 毫秒降至 8.7 毫秒。优化保留 720×480 的游戏画面，对相同的背景绘制复用结果，并为旋转、滚动的透明纹理只插值透明度。播放完的音效会向 DirectSound 报告空闲，原驱动可以立即回收声部。

真机复测在主菜单轻点方向键。日志中的 `Main menu direction_to_flip_ms` 计量方向键采样到游戏提交光标变化帧的时间。`Main menu flips` 与 `elapsed_ms` 记录约三秒内游戏提交的帧数与实际时长。日志仍写入同一个 boot.log。上述对比数字来自主机回放。

### 0.27.0 主菜单透明图层的 GPU 合成

0.26.0 的 Switch 日志在三个连续窗口内记录了 79 次菜单翻页，共 9.099 秒，平均 8.7 FPS。四次方向键从采样到游戏提交光标变化帧分别用了 168、171、277 和 133 毫秒。

0.27.0 通过独立的 OpenGL ES 离屏缓冲合成原版 720×480 菜单的透明图层。纹理来自游戏内存。图层连续绘制，后续指令读取目标区域或 FIFO 提交结束时，结果回写到游戏的帧缓冲。进入主菜单后才创建图形上下文，初始化失败时使用软件绘制。每次启动把渲染器、图层绘制次数和回读耗时写入同一份 boot.log。

主机的 Mesa 离屏回放验证了标题、菜单和四次方向切换；稳定菜单的每帧 26 次透明绘制合并成一次回读。对前 80 批真实菜单图层逐像素比较 GPU 和原软件路径，RGB 各通道平均偏差 0.18/255，最大偏差 4/255。硬件帧率以本版 Switch 日志为准。

### 0.28.0 标题按键与主菜单淡入

0.27.0 的第二次真机运行启用了 NV120，主菜单在 24.146 秒内提交 699 帧，约 29 FPS。方向键到翻页为 39～70 毫秒。首次运行返回 hbmenu 的日志已被第二次启动覆盖，具体原因尚未确认。

标题和菜单的大幅背景在淡入时使用相同的纹理、调色板和几何坐标，仅改变透明度。0.28.0 复用过滤后的不透明背景，保留游戏每一步混合及其原有顺序。回放核对了 156 次实际背景绘制，每次都与原软件路径的输出逐像素相同。离屏着色器在片尾收尾时预热。设备日志中的 `Main menu entry first_30_flips_ms` 从首次绘制菜单计时到第 30 次菜单翻页。

开场影片收尾后解除启动时间限制，玩家可以在标题画面停留。游戏画面上的 + 交给原游戏。若运行时已经停止，这次按键会显示诊断页；在诊断页重新按 + 才会退出。应用目录 logs 下保留 boot.log 与 boot.previous.log，退出应用后均可删除。

### 0.29.0 标题待机演示

原版在 `PRESS START BUTTON` 页静置时进入实时绘制的战斗演示。主机在 `MAIN MENU` 上用打包资源和原盘各静置超过两分钟，两次都停留在菜单。两页的计时与输入均由游戏控制。

第一次索引绘制会启用来自 xemu `478b4f4` 的 NV2A OpenGL 渲染器。PGRAPH 与重编译代码共享物理内存，着色器缓存只在内存中保留。0.29.0 的主机回放看到了石殿和铁路战斗，演示中按 Start 可回到标题。驱动和真机帧率需在 Switch 上验证。

主机测试可在独立的临时数据目录运行。将环境变量 `NGB_TEST_IDLE_SCENE` 设为 `skip` 或 `natural`，以 `ngb-runtime-test --start-button <光盘目录> <临时数据目录>` 启动。测试对实际显示缓冲区采样，确认画面发生变化后，分别测试 Start 返回和无输入返回。

### 0.29.1 演示后续切场

按原游戏的光盘读取记录补入五段战斗用到的资源。一次无按键主机回放从标题经过全部五段并回到标题。为加快这项长回放，主机每 24 个翻页渲染一帧，保留游戏时钟。将这次记录的 871 个不同读取范围与原盘逐字节对照，覆盖 35 个文件。NRO 中的 248 个 RomFS 条目也与打包输入逐项核对。

演示后段的资源查询会读取低地址页。运行时沿用桌面移植默认的零初始化页，并保留 `RECOMP_TRAP_NULL` 调试选项。正常渲染的主机测试另行验证了标题静置触发和演示中按 Start 返回。真机上可从 `logs/boot.log` 的 `3D scene flips=` 读取渲染翻页数、绘制次数和经过的毫秒数。

### 0.30.0 实时战斗演示的渲染开销

0.29.1 的 Switch 日志记录到石殿演示前 120 次翻页耗时 95.119 秒。0.30.0 在显存页可能发生改写时才重传顶点和核对纹理，按实际读取范围同步渲染目标。普通平滑着色的实心三角形使用硬件插值窗口深度，仍应用游戏的深度偏移、裁剪和量化。

同一套 Docker 离屏回放使用四个 llvmpipe 工作线程、包内光盘数据和独立的临时存档，逐帧绘制原演示。前 120 次翻页耗时从 25.798 秒降到 13.406 秒，同期 GPU 回读从 1,673 次降到 239 次，缓冲区更新从 909 MB 降到 29 MB。第 4 到 119 帧各取一张 360×240 的显示采样，逐帧比较的 RGB 平均绝对偏差中位数为 0.12/255。

另一次完整渲染回放中，前 600 次翻页共提交 259,307 次绘制，用时 44.615 秒。两次独立测试分别确认了演示中按 Start 回到标题，以及持续无输入时演示自然播放完并回到标题。

真机复测可直接等标题自动进入战斗。原有的 boot.log 在第 30、120 和 600 次翻页记录累计时间及绘制次数，同一位置新增累计回读次数、回读 MiB 和顶点上传 MiB。新版的真机帧率待测。

### 0.31.0 实机帧时间验证

0.30.0 的 Switch 复测中，3D 演示的前 30 次翻页用时 12.849 秒，前 120 次用时 41.847 秒。第 31 至 120 次共用时 28.998 秒，平均每帧 322.2 毫秒。正常游玩的验收目标是实机可操作的战斗持续达到 60 FPS，每帧约 16.67 毫秒。标题演示用于复现同一段绘制负载。

0.31.0 将连续的顶点着色器程序、常量和数组设置批量提交，缓存顶点属性与索引范围，对可表示的索引使用 16 位存储。普通已映射的游戏内存页直接访问，跨页、设备与时钟访问继续使用原地址转换。对匹配当前显示格式的线性彩色渲染目标，显示路径使用两个像素传输缓冲区，读取已完成的屏幕图像。游戏自己读取该显存时仍同步最新内容。

真机标题页静置到演示出现。日志按第 30 次、每 120 次翻页或经过 5 秒后的下一次翻页输出。每段记录游戏翻页数、Switch 显示提交数、超出 16.67 毫秒的帧数和帧间隔 P95。同期的 FIFO、绘制准备、绘制提交和同步回读是可能互相包含的 CPU 墙钟时间。GPU 时间戳仅覆盖抽样绘制，另有异步显示的排队与实际发布计数。

0.31.0 真机运行记录到第 321 次翻页，耗时 83.086 秒。前 120 次翻页用时 32.367 秒，平均 3.71 FPS，上一版同一段为 2.87 FPS。第 31 至 120 次翻页平均每帧 243.8 毫秒。前 120 帧的 FIFO 处理累计 16.111 秒，其中绘制准备 12.022 秒。同期像素同步回读累计 0.364 秒，异步显示发布 119 张画面。全部 321 个帧间隔均超过 16.67 毫秒。第 229 至 236 帧中有一帧耗时 3.32 秒。游戏运行到用户主动退出。

## 0.33.0 标题演示的 Vulkan 渲染

从原版标题进入 3D 演示后，游戏的 Direct3D 调用通过 Vulkan 提交给 GPU。Switch 包链接同级 `nxvk` 工作树中交叉编译的 NVK 驱动。编译入口是 `bash packaging/switch/build-runtime.sh switch`，可用 `NGB_NXVK_ROOT` 指定已有构建的 nxvk 目录。

本地用 `bash packaging/switch/build-runtime.sh host` 编译。Linux 容器中可用下面的命令运行前 120 帧，数据写入临时目录，着色器缓存保留在本机。测试命中预期停点时返回 1，日志末行包含 `verified 120 original demo frames`。

```sh
out=build/switch-runtime
mkdir -p "$out/shader-cache"
data=$(mktemp -d)
NGB_D3D_CACHE="$PWD/$out/shader-cache" NGB_TEST_IDLE_SCENE=benchmark \
    "$out/host/ngb-runtime-test" --start-button "$out/romfs" "$data"
rm -rf "$data"
```

构建脚本会将已有的 `shader-cache/spirv.bin` 打入 RomFS，GPU 在运行时创建当前设备的图形管线。0.33.0 的测试包包含本地演示收集到的 93 个着色器。真机日志中的 `draws` 和 `submitted` 记录 Direct3D 绘制调用，`scanouts` 记录发布给前端的画面数，`screen_submits` 记录 Switch 前端实际提交的画面数。累计的 `queue_ms`、`fence_wait_ms` 和 `publish_ms` 分别记录 CPU 在驱动提交、等待 GPU 及把已完成画面发布给前端时的耗时。

### 离线比较重战斗的主线程时间（0.45.0）

用同一个 ARM Linux 主机构建、相同的着色器缓存和临时存档目录运行
`NGB_TEST_IDLE_SCENE=combat ngb-runtime-test --start-button <romfs> <临时目录>`。
它经过开场和标题进入原版演示，检查画面运动，并在第 1920 帧停止。
两行 `[OFFLINE]` 分别覆盖 1681–1800、1801–1920 帧；`guest_ms` 是
120 帧合计的游戏线程 CPU 时间，除以 120 才是每帧值。它不包含渲染线程
及游戏线程被调度出去的时间，不能取倒数当作 Switch FPS。先核对绘制数：
自然演示的敌人和镜头时序会有变化，不能假设固定帧号就有完全相同的工作量。

若需细分模型提交，在同一个容器内运行：

```sh
python3 packaging/switch/profile-model-calls.py build/switch-runtime/host /tmp/ngb-model
NGB_TEST_IDLE_SCENE=combat /tmp/ngb-model/model-replay --start-button "$romfs" "$scratch"
```

此工具另行链接测试程序，不改 Switch 包。按约 1/32 的比例抽取整个模型提交，
在同一次调用中测各子调用的线程 CPU 时间。`sites.txt` 是调用点表，
`[MODEL]` 的 31 号是整个模型提交的包容时间，不能与子项相加。
时钟读取本身也有成本；先用这些数字选目标，再用未插桩的整帧做对照。

同一工具的 `--chains` 模式不计调用耗时，改为统计模型状态指令链。
它只观察普通 RAM，最多探查 32 个节点，用入口、节点地址、类型和 0xFE 节点的显式回调地址
估计下次能否沿用同一种解析顺序。`repeat` 是 4096 项直接映射表中的指纹命中，
并不表示材质参数值、回调副作用或绘制结果也能复用。

0.46.0 的 combat 回放还输出每个窗口的函数入口次数 `entries` 和轮询次数
`polls`，用于检查两个版本执行的游戏逻辑是否可比。函数多并不等于函数入口
本身耗时；不应把次数换算成帧率。

需要细查游戏内存时，容器中运行
`python3 packaging/switch/profile-guest-memory.py build/switch-runtime/host /tmp/ngb-mem`，
再按 combat 回放参数启动 `/tmp/ngb-mem/memory`。只在 1801–1920 帧统计指定
函数中动态标量地址的求值次数，排除编译时常量、SIMD 和已有批量路径。
`columns.txt` 标明函数和各列。`near-ESP` 与地址分区列重合；
它指距离当前客体栈指针不到约 2 KiB，不能据此假定地址永远映射有效。

### 0.47.0：等待事件的线程和离线整帧对照

改动在 Xbox 内核的线程选择上。原先每次轮转都可能恢复一个没有等到事件的线程，检查后再切走。现在只有事件就绪、句柄失效、超时或必须检查异常状态时才恢复该等待者。内存事件由游戏直接写入，调度器检查当前映射；不缓存可能失效的指针。所有线程都在等待时仍有线程处理时钟和中断。进入游戏后，命名事件的正常等待也不再受三分钟启动预算限制。

四项主机回归通过；调度测试覆盖直接写入事件、命名事件置位/清除、句柄失效、定时唤醒、当前线程退出、未提交内存和启动预算结束后的有限等待。独立回放使用 NRO 的 49 个游戏代码目标文件，主机运行时和 Vulkan 驱动仍由 Linux 提供。重战斗段同场相邻帧对照，旧/新调度策略分别为 6.488/6.088 ms 游戏线程 CPU，同期绘制 679.4/678.7 次每帧。单独的计数回放在 120 帧内分别切换 329145/12423 次；这不是帧率提升比例。真机将在原有日志中按窗口写一行 `[SCHED]`，给出实际切换和略过未就绪等待者的次数；没有额外 SD 文件。

主机复现、训练和同场试验入口见 [离线回放说明](../packaging/switch/perf/README.md)。`[OFFLINE] end=120` 覆盖第 31–120 帧；后两条各覆盖 120 帧。

复测重战斗 6.086→5.696 ms；无输入回归经过第 9240 次翻页，自然回到原版标题。详见[整帧对照和任务分账](performance/switch-0.47.md)。

The startup package's embedded disc is deliberately partial. For local story-mode
testing, the runtime also accepts a complete extracted copy of the matching
retail disc at `sdmc:/switch/ngb-runtime/disc/`, with `default.xbe` immediately
inside that directory. When present it replaces the entire guest DVD mount;
the boot log identifies the source, and the normal executable fingerprint check
still applies. This mount is read-only and creates no second copy. Removing the
directory restores the embedded demo data. Saves remain under `data/`.

0.48.0 已在离线环境从新游戏进入第一章，并通过两轮角色输入验证。
见[验证方法和重战斗任务依赖](performance/switch-0.48.md)。

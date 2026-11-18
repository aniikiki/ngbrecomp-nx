# 0.56.25 Alma 真机游戏线程拆分

这份记录支持优先检查**游戏线程上的绘制准备和状态处理，以及碰撞/几何路径**。
它没有显示游戏线程主要在等待 Vulkan。下面的分项来自 82 个 PC/LR 快照，
不是逐函数计时，也不是一份完整调用栈剖析。

## 数据与计时边界

输入是 `build/switch-runtime/reports/alma-perf-0.56.25/hardware.csv`，最后一个 SESSION。
沿用已讨论的相对首条 G 记录第 **91 ≤ t < 111 秒**，没有根据采样命中的函数挑选窗口。
取两端均在窗口内、active 为真且 guest_flip 连续的 1043 个区间；渲染记录 1044 条。
该窗口避开了最初加载和随后的死亡画面，但仍包含少量首次编译，不宣称完全预热。

|实测量|平均|P95（最近秩）|
|---|---:|---:|
|游戏帧间隔|19.153 ms|21.071 ms|
|游戏线程 CPU|18.873 ms|20.917 ms|
|渲染线程 CPU，两次相邻 Present 之间|11.809 ms|13.093 ms|
|GPU 命令缓冲时间，按提交帧聚合|5.630 ms|6.650 ms|
|游戏线程显式等待 Recorded 工作线程|0.083 ms/Present|—|

线程与 GPU 并行，以上不能相加。游戏线程每区间墙钟减 CPU 平均约 0.280 ms；
CPU 占窗口墙钟约 98.5%。这不排除忙等，因为忙等也是 CPU 时间。
GPU 查询覆盖这 1044 条渲染记录；不把它解释成全设备 GPU 利用率。
帧间隔的倒数约为 52.2 Hz，也不是独立测得的显示器上屏帧率。

全部 25 次频率读取均成功：CPU 1785000000、GPU 921600000、EMC 1600000000 Hz。
最后一个 SESSION 没有上报丢失记录或半行。窗口内游戏线程 82 次采样均成功，
记录的暂停/取上下文/恢复成本合计 573 µs；这不是全部诊断开销。

符号取自 `history/0.56.25/symbols.gz`，指令直接读取同目录 NRO。
不使用旧 ELF、宿主 ELF 或离线回放的时间代替真机数据。
日志只写了版本号，未写 Build ID 或文件哈希，因此归档版本对应不是密码学意义上的构建证明。

## 约 19 ms 分布在哪里

下表按**采样时所在位置**互斥分组，每个快照只算一次。为了显示量级，最后一列为
`18.872696 ms × 本组样本数 / 82`，四舍五入到 0.1 ms。
这要求墙钟采样近似代表游戏线程 CPU 分布，只能用来排优先级。
单个样本已经相当于约 0.23 ms，不能据此承诺某个函数可省多少时间。

|范围|样本|占比|CPU 量级估算，非分段实测|
|---|---:|---:|---:|
|原游戏模型、材质、渲染列表及绘制准备|14|17.1%|约 3.2 ms|
|HLE Draw、状态差分及绘制命令记录|11|13.4%|约 2.5 ms|
|原 XDK 状态与资源处理|9|11.0%|约 2.1 ms|
|对象几何、矩阵与数学函数|18|22.0%|约 4.1 ms|
|碰撞候选、空间判定及结果整理|8|9.8%|约 1.8 ms|
|重编译运行时、调度及宿主支持|9|11.0%|约 2.1 ms|
|NV2A FIFO 命令解析|4|4.9%|约 0.9 ms|
|角色状态及条件检查|4|4.9%|约 0.9 ms|
|其他原游戏库函数、堆管理或回调分派|4|4.9%|约 0.9 ms|
|可识别的 BlockOnTime 路径|1|1.2%|约 0.2 ms|
|总计|82|100%|18.873 ms（各行舍入前）|

前三项合计 **34/82，41.5%，约 7.8 ms 的量级**；几何与碰撞合计
**26/82，31.7%，约 6.0 ms 的量级**。这两项不是两段已经测得的连续调用范围。
通用矩阵函数缺少上层栈，不能全部算到碰撞或全部算到渲染。

分成四个连续五秒区间，样本量为 20、21、20、21。绘制三组合计为
6、8、9、11；几何加碰撞为 7、9、3、7。其中碰撞自身为 5、2、1、0。
既有战斗负载变化，也有稀疏采样误差；不能拿整段比例预测每一帧或给出很窄的误差区间。

## 已经对应到具体调用点的工作

只把 NRO 中 LR−4 确为 `BL`、且其目标落在采样 PC 所属函数内的关系标成直接调用。
共 **22 个样本**符合。下列是其中与绘制记录最相关的部分：

|真实 LR 调用点 → 被采到的函数|样本|核查结果|
|---|---:|---|
|`HLE Draw → memcmp`|2|调用点 `0x53b9fc`、`0x53bab0`；后者 x2 明确为 1024 字节|
|`HLE Draw → memcpy`|1|调用点 `0x53b890`，x2 为 296 字节；对应 74 个延迟渲染状态|
|`Recorded::SendState → memcmp`|3|`0x4f96bc` 比较 1336 字节状态区；另外两个点在变化区间扫描中|
|`Recorded::SendHeader → unordered_map::operator[]`|2|两个样本来自同一调用点 `0x4f90d8`，正在查资源头缓存|
|`Recorded::Draw → memcmp`|1|调用点 `0x4faf34`；另有一个样本停在 Recorded::Draw 自身|
|`Recorded::Submit → condition_variable::notify_one`|1|调用点 `0x4fc080`，唤醒消费者；不是睡眠等待|

这些合计为表中 11 个绘制记录样本。源码入口为
[`hle.cpp` 的 SyncDeferred/Draw](../../src/d3d/hle.cpp) 与
[`threaded.cpp` 的 SendState/SendHeader/Draw](../../src/d3d/gpu/threaded.cpp)。

296 = `(kRsMax 166 − kRsDeferredFirst 92) × 4`；1024 对应顶点常量的八个
128 字节块。SyncDeferred 已内联到这个构建的 HLE Draw 中，不能因为 PC 的符号名
是 Draw 就将其理解为实际 Vulkan 绘图耗时。SendState 的 1336 字节检查来自
以 rs 起始的固定状态区；后续扫描可继续比较较小的变化块。
这些是所采到调用点的操作，不是每帧调用次数或每帧比较字节总数。

## 原游戏侧的具体路径

以下连接从生成代码中的直接调用恢复，用于决定下一轮计时边界。
**它们是静态路径，不是把不同时间的样本拼成一条真实堆栈。**

模型路径有以下可核对的片段：

```text
001CA790 → 00308CE0 / 00308D50 → 间接模型回调（本日志没有记录目标）

001CB260 → 003078B0 → 0030BCA0
                         ├→ 0030B7E0 → SetStreamSource / SetVertexShader / 状态设置
                         ├→ 0030BA30 → SetTexture
                         └→ DrawIndexedVertices

001D7130 → SetTexture / 顶点与像素着色器 / 常量设置
00314430 → SetTexture / SetScissors / 状态设置 / DrawVerticesUP 等
```

14 个绘制准备叶样本中，00314430 为 2 个；001CA790、001CB260、001D7130、
002216B0、00222730、00308130、00308D50、0030B7E0、0030BA30、0030BCA0、
0030C1A0、00317540 各 1 个。
原 XDK 的 9 个叶样本则是 SetTexture 2 个，SetLight、SetStreamSource、
SetViewport、SetScissors、SetStateUP、SetRenderState_ShadowFunc 和 003C5F60 状态辅助函数各 1 个。
因此不能把全部 XDK 开销归咎于 SetTexture，也没有足够证据只优化一个 setter。

碰撞/空间路径：

```text
0013ED30 → 0013F960
00140AF0 → 00142910
0013DC10 → 0013DD60；另有 0013DE30 的结果整理

00189EB0 → 0018A4B0 / 0018A8F0
0018A8F0 → 00328232（矩阵乘法）/ 0036FDB8（浮点转整数）等
00037260 → 00039030（线段空间计算）/ 00328232 等
```

碰撞组的 8 个叶样本：0013ED30 3 个，0013F960、00140AF0、00142910、
0013DD60、0013DE30 各 1 个。
几何/数学组的 18 个包括 0037A5C5 3 个，0036FDB8 与 00039030 各 2 个，
其余对象变换、矩阵转置/复制/乘法及 atan/cos 辅助函数各 1 个。
不能从这些地址断言“Alma AI 占了多少毫秒”。

## 函数名里面还藏着重编译成本

对 82 个 PC 的原 NRO 指令逐个解码：

- **10 个**恰好停在 `ldr wN, [x27, xM, lsl #2]`。本构建的私有 ABI 中，
  x27 是客体页末地址表 `reg_ends`；这些不是在读角色/顶点数据。
- **3 个**停在清除地址最高位的 `and ..., #0x7fffffff`，紧邻的指令确认结果
  用于 x26 RAM 基址访问，分别在 0003B420、00014420、001CA790。
- 另有 **3 个**直接停在 `ngb_reg_checkpoint`，其 LR 分别指向 0030B7E0、000C2AF0、0003AE90。
  **2 个**停在 `ngb_guest_pointer`；其中一个的 LR 指向 HLE Before 内调用 HostPtr 的位置，
  不是直接调用 ngb_guest_pointer，所以保守归到运行时，不强行分给绘制。

前两项已经包含在各自游戏/XDK 函数组里，不能再加到 18.873 ms 上。
命中某条访存指令不是硬件缓存未命中计数，也不说明可以直接省去等比例时间。
它说明仅按“矩阵”“碰撞”函数名归类会高估纯算法成本；应在保留语义的前提下
考察完整循环的访存、状态保存与计算，而不能从一个函数名决定只换 SIMD。

## 本日志无法补出的调用栈

58/82 个 LR 在当前采样函数内部，通常是最近一次内部调用留下的返回位置；
这既不证明递归，也没有提供父调用者。另有 2 个 LR 调用的目标与 PC 所属函数不同：
`00317DC0 → cos` 时 PC 在 `__kernel_cos`，以及 `Before → HostPtr` 时 PC 在
`ngb_guest_pointer`。源码/指令支持尾调用解释，但本报告没有把它们认定为直接边。

因此，不能从这份 CSV 求出 001CA790、001CB9A0 或某个 Boss 更新入口的完整包含子调用耗时。
现有主运行时已经有 `capture_callers()`，支持宿主栈和客体 fiber 栈；Alma 的
`combat_pc()` 没有调用它。下一轮如果需要完整归属，应在 Alma 采样时使用同一套有边界的
frame-pointer 遍历，并记录 frame、scope、worker ID 与 NRO Build ID。
采样密度也需高于当前约 4 次游戏线程快照/秒，同时单独记录探针成本。
若需要各阶段的毫秒实测，则按 fiber 切换保存计费范围、将中断服务单列，不能直接累加嵌套函数墙钟。

按当前证据，优先把完整的“模型提交 → 状态同步 → XDK/命令记录”路径作为下一轮对象，
并对碰撞和几何循环分别计时。BlockOnTime 只出现一个样本，FIFO 只有四个；
离线软件 Vulkan 中约 38.6% 的 BlockOnTime 比例不适用于这段真机记录。

本次只增加分析脚本、验证和本文，没有改运行时代码、生成 NRO 或部署。

## 复算与产物

脚本为 [`alma-cpu-report.py`](../../packaging/switch/perf/alma-cpu-report.py)，只依赖 Python 标准库；
解码原 NRO 指令时另外需要 GNU AArch64 objdump。可在现有交叉工具链容器执行：

```sh
python3 packaging/switch/perf/alma-cpu-report.py \
  build/switch-runtime/reports/alma-perf-0.56.25/hardware.csv \
  build/switch-runtime/history/0.56.25/symbols.gz \
  build/switch-runtime/history/0.56.25/ngb-startup.nro \
  --start 91 --end 111 \
  --objdump /opt/devkitpro/devkitA64/bin/aarch64-none-elf-objdump \
  --output build/switch-runtime/reports/alma-perf-0.56.25/cpu-breakdown
```

输出 `summary.json`（计时、互斥分组、采样质量、输入哈希），`samples.csv`
（逐 PC/LR、调用指令、证据等级及附近指令），`paths.csv`（路径/叶函数计数）。
无 objdump 时仍可用 Python 核查 BL 的直接目标，但不输出指令层的页表/地址转换分类。
未收录游戏代码或二进制到版本控制。

输入 SHA-256：

```text
hardware.csv  0956cdab56de3e78c609ce6fc902b057cd48f011cce4c2fce9a5f192cd81f4db
symbols.gz    4e6bd48d723444a2c96e9b5ee927b8b2d3e44bf02441cd282eb6350898b67819
NRO           f7364dea3a97eca05045f8de0ac0d27157ba1861f19c5e4fd24a9be4cd2c4458
```

验证：8 个独立用例覆盖内部 LR、错误目标、间接调用、负偏移 BL、符号空洞/别名、
不确定父函数的保守归属和跨 SESSION/半行处理。真机窗口 82 个样本全部闭合到互斥组；
全部 1043 个游戏区间有 CPU 时钟，1044 个渲染帧有有效 GPU 查询。

# Ninja Gaiden Black · Nintendo Switch 版

这是原版 Xbox《忍者龙剑传 Black》的非官方 Switch 移植版，基于 [Ninja Gaiden Black Recompiled](https://github.com/gamboozino/ngbrecomp)。游戏通过 Switch 的 Homebrew Menu 启动。

**当前版本：0.56.24。** 游戏音效和过场动画使用 48 kHz 双声道输出，音量由 Switch 系统控制。

## 首次安装

准备好 Switch 版程序 `ngb-startup.nro`，以及你自己的原版 Xbox **美版零售版（NTSC-U）** 游戏镜像。仓库不包含游戏数据。

1. 在电脑上用 Chrome 或 Edge 打开 [XISO Tool](https://xiso.antangelo.com/)，选择 **Unpack**，选中游戏 ISO，再选一个空文件夹作为输出目录。解包在本机完成，无需上传镜像。如果已经有包含 `default.xbe` 的完整游戏目录，可以跳过这一步。
2. 在 SD 卡上创建 `/switch/ngb-runtime/disc/`，将解包目录**里面的全部内容**复制进去，保留子目录。即使 ISO 超过 4 GiB，也不必分卷：只把解包后的文件放到 SD 卡上。
3. 将 `ngb-startup.nro` 放到 `/switch/ngb-runtime/`。把 SD 卡放回 Switch，打开 Homebrew Menu，选择 **Ninja Gaiden Black**。

安装后的目录结构如下（仅列出部分游戏文件）：

```text
SD 卡/
└── switch/
    └── ngb-runtime/
        ├── ngb-startup.nro
        └── disc/
            ├── default.xbe
            ├── movie/
            └── …
```

如果启动时提示缺少 `default.xbe`，请检查它是否**直接**位于 `disc/` 下。例如，`disc/Ninja Gaiden Black/default.xbe` 就多了一层目录。

## 操作与设置

新开游戏或读档后，推动**右摇杆**即可转动第三人称镜头；按下右摇杆（**R3**）可以切换视角。在主菜单打开 **Recomp Settings → Controls**，可以调整按键、镜头灵敏度，以及第一、第三人称各自的横纵轴反转。喜欢默认用第一人称观察的玩家，可以关闭 **Start in third person**。

暂停时切到 **Exit**，按 **A** 选择返回游戏、返回主菜单或退出程序。后两项需要再次确认，不会自动存档。

## 更新与存档

退出游戏后，替换 SD 卡上的 `/switch/ngb-runtime/ngb-startup.nro` 即可更新，不需要重新解包。请保留同目录下的 `data/`（包含存档）和 `recomp-settings.ini`（移植版设置）。如需备份进度，先退出游戏，再复制整个 `data/` 目录。

## Mission 选关性能记录（可选）

日常游玩默认关闭。要排查选关卡顿，在 SD 卡创建空文件 `/switch/ngb-runtime/mission-perf.flag` 后重启游戏；无需开启全局诊断。进入 Mission 后先静止，再翻动任务列表、进入难度选择。返回主菜单后，记录保存在 `/switch/ngb-runtime/logs/mission-perf.csv`。删除 flag 并重启即可关闭。下次启用并采集时会覆盖旧记录。

每次启动最多保留 2400 次选关循环和 2400 次显示采样，先存在内存里，离开选关或正常退出时写盘。`M` 行区分更新、绘制、交给调度器三个阶段的实际耗时和线程 CPU 时间；`cpu_rc` 为 0 才能使用 CPU 时间。GL 读回、上传等是阶段内的明细，不能与阶段耗时相加。`vk_draws`、`vk_presents` 是发往 Vulkan 后端的调用次数。`D` 行独立记录显示线程取缓冲、缩放与叠加、提交上屏的耗时，序号表示开始取缓冲时所在的选关循环，不是像素来源。耗时单位为微秒。

如果还需定位到 ARM 函数，同时创建 `mission-pc.flag`。只在选关循环内短暂停住游戏线程读取 PC 和 LR，采样有开销；测正常帧率时请关闭此选项。退出选关后将 `logs/mission-pc.csv` 与同一次构建的 `symbols.gz` 交给 `python3 packaging/switch/mission-pc-report.py mission-pc.csv symbols.gz`。PC 样本也可能落在等待上，需结合阶段 CPU 时间判断。

要区分 GL 读回时是在等前面的绘制，还是在传像素，可以另外创建 `mission-gl-sync.flag`（也需要 `mission-perf.flag`）。每 61 次读回取一次样，`finish_us` 是等此前 GL 工作完成的时间，`post_finish_read_us` 是随后读取像素的调用时间；两者只用于这部分样本。删除诊断 flag 后重启恢复日常模式。

## 致谢与许可

感谢 [ngbrecomp 上游项目及其贡献者](https://github.com/gamboozino/ngbrecomp#credits)。项目代码按 [GPL-3.0-or-later](LICENSE) 授权，第三方组件遵循[各自的许可](THIRD_PARTY.md)。本项目与 Koei Tecmo 或 Team Ninja 没有关联，也未获其背书。

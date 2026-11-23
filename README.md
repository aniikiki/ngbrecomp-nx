# Ninja Gaiden Black · Nintendo Switch 版

这是原版 Xbox《忍者龙剑传 Black》的非官方 Switch 移植版，基于 [Ninja Gaiden Black Recompiled](https://github.com/gamboozino/ngbrecomp)。游戏通过 Switch 的 Homebrew Menu 启动。

**当前版本为 0.57.56。** 游戏音效和过场动画使用 48 kHz 双声道输出，音量由 Switch 系统控制。

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

同一美版零售游戏的 `default.xbe` 即使因重新打包而改变了签名、证书、填充或分段的文件偏移，也可以加载。启动时会检查入口地址和分段边界。文件无法读取、已截断或地址布局不兼容时，启动画面会显示具体原因。

## 操作与设置

新开游戏或读档后，推动**右摇杆**即可转动第三人称镜头；按下右摇杆（**R3**）可以切换视角。在主菜单打开 **Recomp Settings → Controls**，可以调整按键、镜头灵敏度，以及第一、第三人称各自的横纵轴反转。喜欢默认用第一人称观察的玩家，可以关闭 **Start in third person**。

暂停时切到 **Exit**，按 **A** 或 **Y** 选择返回游戏、返回主菜单或退出程序。后两项默认选中 **No**。选择 **Yes** 后，**Return to Main Menu** 会回到含 **New Game**、**Load Game** 等选项的主菜单，**Quit Game** 会关闭程序。请先保存想要保留的进度。

## 更新与存档

退出游戏后，替换 SD 卡上的 `/switch/ngb-runtime/ngb-startup.nro` 即可更新，不需要重新解包。请保留同目录下的 `data/`（包含存档）和 `recomp-settings.ini`（移植版设置）。如需备份进度，先退出游戏，再复制整个 `data/` 目录。

## 致谢与许可

感谢 [ngbrecomp 上游项目及其贡献者](https://github.com/gamboozino/ngbrecomp#credits)，以及提供渲染实现与优化参考的 [black-pc](https://github.com/Spark198rus/black-pc) 和 [ngb-pc-native-port](https://github.com/akirahayabusa/ngb-pc-native-port) 项目及其贡献者。

项目代码按 [GPL-3.0-or-later](LICENSE) 授权，第三方组件遵循[各自的许可](THIRD_PARTY.md)。本项目与 Koei Tecmo 或 Team Ninja 没有关联，也未获其背书。

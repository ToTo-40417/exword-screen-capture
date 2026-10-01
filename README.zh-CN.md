# EX-word Screen Capture

[日本語](README.md) · [English](README.en.md) · 简体中文 · [繁體中文](README.zh-TW.md)

通过CASIO EX-word的“投影仪连接”功能，在PC上显示、保存和录制设备画面。

版本：v1.0.0

![应用界面](docs/images/capture-ui-window.png)

※图片使用展示用测试图案。

## 功能

- PNG截图、默认无音频的H.264 / MP4录像，可选无损FFV1 / MKV。
- 以实际接收分辨率为基准，按x1至x10整数倍放大。
- 全部／上屏／下屏切换，保持整数倍的全屏显示。
- 保存位置设置、灰度与反色滤镜。
- 日语、英语、简体中文和繁体中文界面。

## 设备

已实机确认的型号、OS及功能：

- CASIO EX-word XD-N6500（DATAPLUS 7）：Linux（画面显示、截图保存、录像）
- CASIO EX-word XD-K8700（DATAPLUS 9）：macOS（画面显示、录像）
- CASIO EX-word XD-Y4900（DATAPLUS 10）：Linux（画面显示、截图保存、录像）；Windows（画面显示）

以下系列的官方资料记载了投影仪连接功能。候选范围仅限具备该功能的型号，
除上述已确认型号外，其他型号**未使用本软件进行实机确认**：

- EX-word：XD-N、XD-K、XD-Y、XD-SX系列。
- 图形计算器：fx-9860G系列（含GII、GIII）、fx-9750G系列。
- 彩色图形计算器：fx-CG10／20／50系列、GRAPH90+ E。

投影功能本身不保证兼容性。fx-CG候选设备需使用 `ScreenR(XP)` 模式。
参见[依据与连接条件](docs/COMPATIBILITY.md)。

## 环境

- PC GUI：Windows x64、macOS arm64、Linux x86_64。[OS要求](docs/SETUP.md)。
- Linux CLI：无界面的截图与录像。[安装与操作](docs/SETUP.md#headless-cli--軽量環境向けcli)。
- Brainux：Brain上的独立显示应用。[与PC版的区别及安装方法](docs/BRAINUX.md)。

### 推荐配置估算

以528×432、10 fps录像为基准的计算估算，并非实测最低要求或性能保证。

| 用途 | CPU选型参考 | RAM | 存储 |
| --- | --- | --- | --- |
| 显示、PNG保存、x1至x2录像 | 64位，2核以上 | 4 GiB以上 | 推荐SSD |
| x10录像（5280×4320） | 64位，4核以上 | 8 GiB以上 | SSD，足够的可用空间 |

优先满足OS要求。不需要独立GPU，负载取决于分辨率与画面内容。[计算依据](docs/RESOURCE_ESTIMATES.md)。

## 安装

### 使用可执行文件

从[Releases](https://github.com/ToTo-40417/exword-screen-capture/releases)下载适合自己OS的GUI程序。Windows x64直接运行 `EXwordScreenCapture.exe`；macOS解压ZIP后打开 `.app`；Linux解压ZIP后运行其中的 `EXwordScreenCapture`，并保留整个文件夹。
GUI发行包包含Python、Qt、libusb和录像用FFmpeg，无需另外安装库。
Windows首次连接前必须为目标USB设备分配**WinUSB驱动程序**，内置libusb不能替代此设置。参阅[Windows连接准备（日／英）](docs/WINDOWS_USB.md)。Linux USB访问权限及Mac未公证应用的首次运行许可仍属于OS侧条件。详见[安装说明](docs/SETUP.md)。
修改Windows USB驱动程序可能影响CASIO传输软件。

### 从源代码启动

Python依赖、源代码启动与构建方法见[安装说明](docs/SETUP.md)。

## GUI操作

### 连接

1. 通过USB将电子词典连接到PC，点击PC应用的“连接”。
2. 在确认窗口中点击“连接”。应用显示“等待中”。
3. 在电子词典上选择“投影仪连接”。PC按钮变为“断开”时，连接完成。

停止接收时，点击PC应用的“断开”。

如果词典等待连接超时，请保持PC应用等待，再次选择投影仪连接。Windows持续等待时，请检查[USB驱动设置](docs/WINDOWS_USB.md)。

### 截图与录像

在“设置”中选择录制格式与倍率（x1至x10），默认H.264/MP4、x1。
录制倍率独立于显示与PNG倍率。超高分辨率视频可能无法在部分播放器中播放。

| 操作 | PC应用中的控件 | 快捷键 |
| --- | --- | --- |
| 保存图片 | 截图 (F8) | F8 |
| 开始／停止录像 | 录制 (F9) | F9 |
| 切换全屏 | 全屏 (F11) | F11 |
| 退出全屏 | 按Esc | Esc |

默认保存到 `Pictures/EX-word Captures`，可在“设置”中修改。
每次创建带时间的独立文件，不覆盖已有文件。

### 显示与设置

- **显示范围**：“全部画面”包含完整接收图像。支持的组合画面可选择上屏或下屏。
- **倍率**：通过“分辨率 x1”选择x1至x10，改变窗口显示与PNG保存倍率；放不下的部分可滚动查看。
- **全屏**：以x1至x10中能容纳图像的最大倍率居中显示，可能出现黑边。显示器小于原图时会裁切部分画面。保存倍率不变。
- **滤镜**：在“设置”中选择无、灰度或反色，同时作用于显示、保存与录像。
- **语言**：在全屏旁的“语言 / Language”中修改。

语言、保存位置、倍率与滤镜设置会保留到下次启动。

## 注意事项

- 使用投影仪连接，不要使用普通USB传输模式。不要同时运行其他USB传输软件，仅连接一台词典。
- 运行自制应用（追加内容）时，可能无法捕获画面。
- 录像为10 fps、无音频，设备未发送新图像时重复上一帧；不保证设备以10 fps发送画面。
- 编码跟不上时会报错停止。
- 使用或公开捕获内容前，请自行确认所需权利。

## 许可与技术资料

原创源代码采用[MIT License](LICENSE)，依赖库保留各自的许可与版权。
本项目参考Cahute公开规范独立实现，不包含Cahute代码、CASIO词典或固件，并非CASIO官方产品。

- [安装与打包](docs/SETUP.md)
- [通信协议与安全性](docs/PROTOCOL.md)
- [许可与二进制分发检查事项](docs/LICENSING.md)
- [第三方许可声明](THIRD_PARTY_NOTICES.md)

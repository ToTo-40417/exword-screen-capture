# EX-word Screen Capture

[日本語](README.md) · [English](README.en.md) · [简体中文](README.zh-CN.md) · 繁體中文

透過CASIO EX-word的「投影機連線」功能，在PC上顯示、儲存及錄製裝置畫面。

版本：v1.0.0

![應用程式介面](docs/images/capture-ui-window.png)

※圖片使用展示用測試圖案。

## 功能

- PNG螢幕截圖、預設無音訊的H.264 / MP4錄影，可選無損FFV1 / MKV。
- 以實際接收解析度為基準，以x1至x10整數倍放大。
- 全部／上螢幕／下螢幕切換，保持整數倍的全螢幕顯示。
- 儲存位置設定、灰階與色彩反轉濾鏡。
- 日語、英語、簡體中文與繁體中文介面。

## 裝置

已實機確認的型號、OS及功能：

- CASIO EX-word XD-N6500（DATAPLUS 7）：Linux（畫面顯示、截圖儲存、錄影）
- CASIO EX-word XD-K8700（DATAPLUS 9）：macOS（畫面顯示、錄影）
- CASIO EX-word XD-Y4900（DATAPLUS 10）：Linux（畫面顯示、截圖儲存、錄影）；Windows（畫面顯示）

以下系列的官方資料記載了投影機連線功能。候選範圍僅限具備該功能的型號，
除上述已確認型號外，其他型號**未使用本軟體進行實機確認**：

- EX-word：XD-N、XD-K、XD-Y、XD-SX系列。
- 圖形計算機：fx-9860G系列（含GII、GIII）、fx-9750G系列。
- 彩色圖形計算機：fx-CG10／20／50系列、GRAPH90+ E。

投影功能本身不保證相容性。fx-CG候選裝置需使用 `ScreenR(XP)` 模式。
請參閱[依據與連線條件](docs/COMPATIBILITY.md)。

## 環境

- PC GUI：Windows x64、macOS arm64、Linux x86_64。[OS需求](docs/SETUP.md)。
- Linux CLI：無介面的截圖與錄影。[安裝與操作](docs/SETUP.md#headless-cli--軽量環境向けcli)。
- Brainux：Brain上的獨立顯示應用程式。[與PC版的差異及安裝方法](docs/BRAINUX.md)。

### 建議規格估算

以528×432、10 fps錄影為基準的計算估算，並非實測最低需求或效能保證。

| 用途 | CPU選型參考 | RAM | 儲存 |
| --- | --- | --- | --- |
| 顯示、PNG儲存、x1至x2錄影 | 64位元，2核心以上 | 4 GiB以上 | 建議SSD |
| x10錄影（5280×4320） | 64位元，4核心以上 | 8 GiB以上 | SSD，足夠的可用空間 |

優先滿足OS需求。不需要獨立GPU，負載取決於解析度與畫面內容。[計算依據](docs/RESOURCE_ESTIMATES.md)。

## 安裝

### 使用執行檔

從[Releases](https://github.com/ToTo-40417/exword-screen-capture/releases)下載適合自己OS的GUI程式。Windows x64直接執行 `EXwordScreenCapture.exe`；macOS解壓縮ZIP後開啟 `.app`；Linux解壓縮ZIP後執行其中的 `EXwordScreenCapture`，並保留整個資料夾。
GUI發行包包含Python、Qt、libusb及錄影用FFmpeg，不需另外安裝函式庫。
Windows首次連線前必須為目標USB裝置指派**WinUSB驅動程式**，內建libusb不能替代此設定。請參閱[Windows連線準備（日／英）](docs/WINDOWS_USB.md)。Linux USB存取權限及Mac未公證應用程式的首次執行許可仍屬於OS側條件。請參閱[安裝說明](docs/SETUP.md)。
變更Windows USB驅動程式可能影響CASIO傳輸軟體。

### 從原始碼啟動

Python相依元件、原始碼啟動與建置方法請參閱[安裝說明](docs/SETUP.md)。

## GUI操作

### 連線

1. 透過USB將電子辭典連接至PC，按下PC應用程式的「連線」。
2. 在確認視窗中按下「連線」。應用程式顯示「等待中」。
3. 在電子辭典上選擇「投影機連線」。PC按鈕變為「中斷連線」時，連線完成。

停止接收時，按下PC應用程式的「中斷連線」。

若辭典等待連線逾時，請保持PC應用程式等待，再次選擇投影機連線。Windows持續等待時，請檢查[USB驅動設定](docs/WINDOWS_USB.md)。

### 截圖與錄影

在「設定」中選擇錄製格式與倍率（x1至x10），預設H.264/MP4、x1。
錄製倍率獨立於顯示與PNG倍率。超高解析度影片可能無法在部分播放器中播放。

| 操作 | PC應用程式中的控制項 | 快捷鍵 |
| --- | --- | --- |
| 儲存圖片 | 螢幕截圖 (F8) | F8 |
| 開始／停止錄影 | 錄製 (F9) | F9 |
| 切換全螢幕 | 全螢幕 (F11) | F11 |
| 離開全螢幕 | 按Esc | Esc |

預設儲存至 `Pictures/EX-word Captures`，可在「設定」中變更。
每次建立含有時間的獨立檔案，不覆寫既有檔案。

### 顯示與設定

- **顯示範圍**：「全部畫面」包含完整接收影像。支援的組合畫面可選擇上螢幕或下螢幕。
- **倍率**：透過「解析度 x1」選擇x1至x10，變更視窗顯示與PNG儲存倍率；放不下的部分可捲動查看。
- **全螢幕**：以x1至x10中能容納影像的最大倍率置中顯示，可能出現黑邊。顯示器小於原圖時會裁切部分畫面。儲存倍率不變。
- **濾鏡**：在「設定」中選擇無、灰階或色彩反轉，同時套用於顯示、儲存與錄影。
- **語言**：在全螢幕旁的「語言 / Language」中變更。

語言、儲存位置、倍率與濾鏡設定會保留到下次啟動。

## 注意事項

- 使用投影機連線，不要使用一般USB傳輸模式。不要同時執行其他USB傳輸軟體，僅連接一台辭典。
- 執行自製應用程式（追加內容）時，可能無法擷取畫面。
- 錄影為10 fps、無音訊，裝置未傳送新影像時重複上一張畫面；不保證裝置以10 fps傳送畫面。
- 編碼跟不上時會回報錯誤並停止。
- 使用或公開擷取內容前，請自行確認所需權利。

## 授權與技術資料

原創原始碼採用[MIT License](LICENSE)，相依函式庫保留各自的授權與著作權。
本專案參考Cahute公開規範獨立實作，不包含Cahute程式碼、CASIO辭典或韌體，並非CASIO官方產品。

- [安裝與封裝](docs/SETUP.md)
- [通訊協定與安全性](docs/PROTOCOL.md)
- [授權與二進位散布檢查事項](docs/LICENSING.md)
- [第三方授權聲明](THIRD_PARTY_NOTICES.md)

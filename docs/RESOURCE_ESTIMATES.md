# リソース見積もり / Resource estimates

推奨スペックは、現行ソフトの処理方式と画素量を基にした選定目安です。
ベンチマークに基づく最低動作要件ではありません。

## 前提

- 上下を含む528×432ピクセルの受信画像。
- 受信形式RGB565、内部受け渡しRGB24。
- 最大10倍の整数拡大、録画10 fps。
- FFmpegのnearest-neighbor拡大。標準録画はH.264 / MP4（yuv420p）、任意選択の無劣化録画はFFV1 / MKV（level 3、bgr0）。
- 拡大前のRGBをFFmpegへ渡し、PNGは行単位で拡大・圧縮する。
- 録画入力は直近画像を保持し、全フレームの無制限キューは作らない。

## 画素量

倍率s、幅W、高さHとすると、32-bit画素面は `W × H × s² × 4` bytesです。
以下はFFV1のbgr0出力を基準とした計画用の値であり、標準H.264録画の
出力画素形式・実際のメモリ使用量・ファイル容量を表すものではありません。
H.264ではyuv420pへ変換し、必要なら右端・下端を黒で補って偶数サイズにします。

| 倍率 | 出力サイズ | 32-bit画素面／枚 | 10 fpsの非圧縮換算 |
| --- | --- | --- | --- |
| x1 | 528×432 | 912,384 bytes（0.870 MiB） | 9.124 MB/s |
| x2 | 1056×864 | 3,649,536 bytes（3.480 MiB） | 36.495 MB/s |
| x10 | 5280×4320 | 91,238,400 bytes（87.012 MiB） | 912.384 MB/s |

MBは10⁶ bytes、MiBは2²⁰ bytes。
x10はx1に比べ100倍の画素をエンコードします。

内部の元画像RGB24は684,288 bytes（0.653 MiB）、RGB565受信ペイロードは456,192 bytesです。
受信・元画像の保持量は拡大倍率に比例して増えませんが、エンコーダー側の作業量は増えます。

## CPU・RAMの選定

READMEの2コア／4 GiB、4コア／8 GiBは、次の余裕を取った推奨目安です。

- 通常利用：OS・Python・GUI・USB受信・エンコーダーの常駐分を含めて2 GiB、
  追加のOS負荷・キャッシュ等に2 GiBの余裕を取り、4 GiBを選定目安とする。
  軽量Linuxのみなら2 GiBも予算案となるが、共通推奨値にはしない。
- 高倍率録画：仮にx10の画素面16枚相当を作業領域として予算化すると約1.36 GiB。
  OS・GUI等に2 GiB、その他のコピー・エンコーダー作業領域・キャッシュの余裕を加え、
  総RAMを8 GiBとする。16枚は実測値や実装上のバッファ枚数ではなく、見積もり上の仮定。
- CPU：現行FFmpeg指定は2スレッド。GUIと受信処理の余裕を考え、通常2コア、高倍率4コアを選定目安とする。
  コア数から圧縮速度を導けるわけではなく、4コアでもx10録画の成功を保証しない。
- 専用GPUは必須ではない。録画はソフトウェアエンコードであり、GPU性能をCPU要件の代わりにはしない。

OS・画面内容・フィルター・Python/Qt/FFmpegの版によって常駐量と速度は変わります。
周波数、CPU型番、最低RAM、録画速度を計算だけから確定することはできません。
OS自体の要件は別に満たす必要があります。例えば[Windows 11の公式要件](https://www.microsoft.com/en-us/windows/windows-11-specifications)
では4 GB以上のRAMが必要です。OS側が本ソフトの目安を上回る場合はOS側を優先してください。

## 保存先

x10・10 fpsの非圧縮換算は1分あたり約54.743 GBです。
実際のH.264・FFV1ファイルは画面内容と圧縮設定に依存するため、この値を必要なSSD書込速度や
必ず消費する空き容量と解釈しないでください。高倍率録画はSSDと十分な空き容量を推奨します。

## English summary

Planning recommendations—not measured minimums—are 2 CPU cores / 4 GiB RAM for
preview, PNG and x1–x2 recording, and 4 cores / 8 GiB for x10 recording.
At 528×432 and 10×, a bgr0 pixel plane is 91,238,400 bytes; 10 fps corresponds
to 912.384 MB/s of uncompressed pixel processing, not disk writes. Encoding speed
and compressed file size depend on content and the environment. No dedicated GPU
is required. These estimates do not guarantee sustained recording at the selected scale.

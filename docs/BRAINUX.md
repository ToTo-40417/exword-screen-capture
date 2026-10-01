# Brainux版

SHARP Brain上のBrainuxで、EX-wordのプロジェクター接続画面を表示する軽量版です。
Brainを受信側、EX-wordを送信側として使います。
動作確認済みの組合せはPW-SH3（Brainux）とXD-Y4900です。
Windows CE向けアプリではありません。

ソースは [packaging/brain-preview](../packaging/brain-preview/) にあります。
PC用GUIやCLIコマンドとは別の表示アプリで、共通の通信パーサーを使用します。
CLIパッケージのインストールだけでは、このアプリは追加されません。

## PC用GUIとの違い

| 項目 | PC用GUI | Brainux版 |
|---|---|---|
| 表示ライブラリ | Qt / PySide6 | GTK3 / GdkPixbuf / GLib |
| 色変換 | PC版のデコーダー | C共有ライブラリによるRGB565変換 |
| 表示倍率 | 整数1〜10倍 | 等倍。表示領域に収まらない場合は最近傍で縮小 |
| 表示位置 | 中央 | 中央 |
| 上・下画面の選択 | あり | 受信した全体画像を表示 |
| スクリーンショット保存 | あり | なし |
| 録画 | H.264/MP4、FFV1/MKV | なし |
| 専用の全画面切替 | あり | なし |
| 言語選択 | 日本語・英語・簡体字・繁体字 | なし。UIは英語 |

Brainux版はQt、Pillow、Python GI、FFmpegを使用しません。
Pythonからctypesで既存のGTK系ライブラリを呼び出します。
USB受信と色変換は別スレッドで行い、変換待ちの画像は最新1件だけ保持します。
色変換の開始とUI更新の間隔は100msです。これは実測10fpsを保証する値ではありません。

## 必要な環境

Brainux側には、Python 3、PyUSB、libusb、GTK3、GdkPixbuf、GLibが必要です。
PC用GUIの実行ファイルやQtは使用しません。
共通パッケージ `exword_capture` とPyUSBは `/opt/exword-capture/lib` に配置します。

開発用Linux機には、Python 3、PyUSB、ホスト用GCC、ARM用の
`arm-linux-gnueabi-gcc` と `arm-linux-gnueabi-readelf` が必要です。
ARMライブラリは開発機で作成し、Brain側へ転送します。

## ビルド

リポジトリのルートで実行します。

```sh
sh packaging/brain-preview/build-brain-pixels.sh
```

全65,536通りのRGB565変換、不正な画像長の拒否、最新フレーム保持のテストを行い、
ARMv5TE EABI soft-floatの `libbrain_pixels.so` を生成します。
このライブラリに動的ライブラリ依存はありません。
`libbrain_pixels-test.so` は開発機用のテスト生成物で、Brainへは配置しません。

Python環境などを明示する場合は `PYTHON`、`HOST_CC`、`ARM_CC`、
`ARM_READELF` を指定できます。別の共通パッケージを使う場合は
`EXWORD_SOURCE` にそのソースルートを指定します。

## 配置と起動

開発用Linux機で、Brain用にPyUSB（純Python）を準備します。
`vendor` が既にある場合は、新しい空の作業ディレクトリで実行してください。

```sh
python3 -m pip install --no-deps --target packaging/brain-preview/vendor pyusb==1.3.1
```

リポジトリのソース、生成した `libbrain_pixels.so` と `vendor` をBrainへ転送します。
Brainux側にPython 3、libusb、GTK3、GdkPixbuf、GLibがあることを確認してください。
次のコマンドはBrainux側のリポジトリのルートから実行します。

```sh
sudo install -d /opt/exword-capture/lib /usr/local/bin /usr/share/applications
sudo cp -R exword_capture /opt/exword-capture/lib/
sudo cp -R packaging/brain-preview/vendor/. /opt/exword-capture/lib/
cd packaging/brain-preview
sudo install -m 644 exword-capture-preview.py brain_usb_source.py \
  brain_pixels.py libbrain_pixels.so LICENSE /opt/exword-capture/
sudo install -m 755 exword-live /usr/local/bin/exword-live
sudo install -m 644 exword-live.desktop /usr/share/applications/exword-live.desktop
DISPLAY=:0 /usr/local/bin/exword-live
```

起動後、EX-word側でプロジェクター接続を選びます。
アプリ一覧の名称は `EX-word Live` です。ウィンドウを閉じると受信を終了します。
USBアクセス権の設定は [Linuxの接続手順](SETUP.md#linux) を参照してください。
プレビューとCLIなど、複数の受信アプリで同じUSB機器を同時に使用しないでください。

状態ログは `~/.local/state/exword-capture/live.log` に保存します。
ログには受信数・変換数・エラー情報を記録し、画像そのものは保存しません。
切断後にも最後の画像が残るため、画像が表示されていることだけでは接続継続を判断できません。

アダプターのソースは本リポジトリと同じMITライセンスです。
GTKなどのシステムライブラリはこのアダプターに同梱しません。

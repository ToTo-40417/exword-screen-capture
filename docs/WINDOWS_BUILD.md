# Windowsでビルドする

Windows x64上で実行します。MacやLinuxでWindows実行ファイルを生成する手順ではありません。
以下はビルド担当者向けです。完成したEXEの利用者はこの作業を行いません。
Python 3.12 x64と、Windows OpenSSHの `ssh` / `scp` が必要です。
ネイティブ補助ライブラリのビルドには無料のMSYS2 UCRT64も使用します。
MSYS2のUCRT64シェルで以下の開発ツールを用意してください：

```sh
pacman -S --needed mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-python make diffutils sed
```

これはビルドするPCだけの要件です。完成したGUIパッケージの利用者にPython・MSYS2・
Qt・libusb・FFmpegの追加導入は必要ありません。USBドライバーは別のOS側条件です。
スクリプトはUSBドライバーを変更しません。

共通ソースにはWindowsで確認したビルド修正を統合しています。
古いWindows専用ソースZIPではなく、同梱資料・Brainuxソース・権利表示を更新した
下記の共通ソースZIPを使用してください。Pythonが使用するOpenSSLの版に合った
公式ライセンスと帰属もビルド時に取得し、検査します。

## E130経由の手順

1. E130に `EXwordScreenCapture-source-v1.0.0.zip` と同名の `.sha256`、
   `build-windows.ps1`、`EXwordScreenCapture-dependency-sources-v1.0.0.zip` とその `.sha256` を置きます。
2. Windowsへスクリプトを取得します。接続先とディレクトリは自分の環境の値に置き換えてください。
3. スクリプトを実行します。

```powershell
scp user@e130:/path/to/handoff/build-windows.ps1 .
powershell -NoProfile -File .\build-windows.ps1 -E130 user@e130 -RemoteRoot /path/to/handoff
```

このスクリプトは、一時フォルダにソースを取得してSHA-256を確認し、
専用venvへ依存関係を導入します。自動テスト、パッケージ化、個人情報検査、
軽量FFmpeg/libusbのビルドと対応ソース同梱、USBを使わないGUI／PNG／録画の起動確認を行い、成功時のみ成果物を
E130の `windows-return/` に返送します。
ソース、venv、キャッシュ、ビルドログは返送しません。

出力は単体EXE `EXwordScreenCapture-v1.0.0-windows-x86_64.exe`、
差し替え可能なフォルダ版ZIP、検査レポート・SHA-256です。
単体EXEを通常の配布候補とし、フォルダ版はライブラリ差し替え用にも保持します。
フォルダ版のexeだけを取り出すとQt等を参照できません。

今回のビルドはH.264/MP4（標準）とFFV1/MKVの両形式について、
録画終了後の全フレーム復号まで検査します。標準録画倍率はx1で、表示倍率とは独立です。
アプリ用アイコンはソースZIPの `assets/` に同梱されています。
フォルダ版・単体EXEともICOを埋め込み、GUIも同じPNGを使用します。
画像生成やMac専用のアイコン変換をWindowsで再実行する必要はありません。
オフライン起動検査ではアイコンが読み込めることも確認します。
FFmpeg/libx264はGPL-2.0-or-later、Qt等は従来通りLGPLです。対応ソースも同梱します。

MinGWの非ASCIIパス問題を避けるため、作業先は既定の `C:\EXwordBuild`、
MSYS2は `C:\msys64` など英数字のパスを使用してください。
書込権限がある別ドライブへ変更する場合は `-BuildRoot D:\EXwordBuild` を指定します。
GCCの検索経路と一時フォルダにも同じ規則を適用します。

Windows実機のUSB接続確認、コード署名、SmartScreenの評価は別工程です。
USBを使わない起動テストの合格だけでは、Windowsでの実機接続確認済みとは扱いません。
実機確認では、EX-wordでプロジェクター接続を選び、GUIの接続、
スクリーンショット保存、録画開始・停止を確認してください。
辞書画面を含む画像・動画は検査用の非公開資料として扱い、返送用ZIPへ混ぜないでください。
MSYS2が標準以外の場所にある場合は `-MSYS2Root D:\msys64` のように指定します。
配布前には[ライセンス資料](LICENSING.md)も確認してください。

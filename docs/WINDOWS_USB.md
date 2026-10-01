# Windowsの接続準備

[English](#english)

Windows x64版は `EXwordScreenCapture.exe` を起動します。Python・Qt・libusb・
FFmpegは内蔵されていますが、**対象USBにWinUSBを割り当てる作業は別途必要**です。
アプリはドライバーを自動で変更しません。

## 初回の準備

1. CASIOの転送ソフトや別のキャプチャアプリを終了し、電子辞書を1台だけ接続します。
2. 本体で「プロジェクター接続」を選び、Windowsのデバイスマネージャーで対応する機器を探します。
   接続待ちが終了した場合は本体で選び直します。
3. 機器の「プロパティ」→「詳細」→「ハードウェアID」を確認します。
   本アプリの対象は `USB\VID_07CF&PID_6101` です。表示名だけで判断せず、
   USBの抜き差しで対象が増減することも確認してください。
4. 元のドライバー名・提供元・バージョンとハードウェアIDを記録します。
   既存のドライバーを変更するとCASIOの転送ソフトが使えなくなる場合があります。
5. 対象がWinUSBでなければ、[libusbの公式導入案内](https://github.com/libusb/libusb/wiki/Windows#driver-installation)
   に沿ってWinUSBを割り当てます。同案内が推奨するツールは[Zadig](https://zadig.akeo.ie/)です。
   Zadigでは必要に応じて **Options → List All Devices** を開き、対象のUSB IDが
   **07CF / 6101** であることを確認し、右側で **WinUSB** を選んで導入します。
   管理者の許可が必要です。IDや対象インターフェイスを確認できない場合は中止してください。
6. デバイスマネージャーの警告が消えていることを確認し、以下の順番で接続します。

キーボード・マウス・USBメモリなど、対象以外のドライバーを変更しないでください。
署名検証を無効化したり、出所不明のドライバーパッケージを入れたりする必要はありません。

## 起動・接続の順番

1. PCで `EXwordScreenCapture.exe` を起動します。
2. 「接続」→確認画面の「接続する」を押し、「待機中」にします。
3. 本体で「プロジェクター接続」を選びます。
4. PCのボタンが「切断」に変わり、実画面が表示されたら接続完了です。

本体が接続待ちを終了した場合は、PCを待機状態にして本体側の操作を繰り返します。
終了時は録画を止め、PCの「切断」を押します。

## 接続できない場合

| 症状 | 確認すること |
| --- | --- |
| GUIは起動するが「待機中」のまま | 対象USBへのWinUSB割り当て、プロジェクター接続の選び直し、他の転送アプリの終了 |
| デバイスマネージャーにコード28 | ドライバー未導入です。対象IDを確認して導入手順へ戻ります |
| 対象機器がデバイスマネージャーに現れない | データ通信可能なUSBケーブル、本体の接続モード、USBポート |
| 通常のCASIO転送ソフトが使えなくなった | 記録した元のドライバーに戻します。以下を参照してください |

「libusbを読み込めた」ことと「対象USBを使える」ことは別です。
待機表示だけではドライバーが正しいとは判断できません。
コード28の意味は[Microsoftの説明](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/cm-prob-failed-install)も参照できます。

## 元のドライバーへ戻す

キャプチャアプリを終了し、デバイスマネージャーで記録済みの対象機器を選びます。
「ドライバーを元に戻す」が使える場合は、その機能を使います。
使えない場合は、メーカーの正規ドライバー・転送ソフトの導入手順に沿って元の割り当てを復元します。
戻した後はUSBを再接続し、通常の転送を確認してください。
無関係な機器やWindows標準のドライバーファイルを削除しないでください。

## English

Run the Windows x64 `EXwordScreenCapture.exe`. Python, Qt, libusb and FFmpeg are
included, but **the target USB device must also use WinUSB**. The application
does not install or replace a device driver automatically.

Before changing a driver, close other transfer/capture applications, connect one
dictionary, select projector mode, and identify it in Device Manager by hardware
ID `USB\VID_07CF&PID_6101`. Record its original driver/provider/version and confirm
that unplugging it removes that entry. A matching display name alone is insufficient.

Follow [libusb's official Windows driver instructions](https://github.com/libusb/libusb/wiki/Windows#driver-installation).
They recommend [Zadig](https://zadig.akeo.ie/): enable **Options → List All Devices**
if needed, confirm the target ID **07CF / 6101**, select **WinUSB**, and install
with administrator approval. Stop if the device/interface is uncertain. Never
replace a keyboard, mouse or storage device driver or disable driver-signature enforcement.

Start the PC app, click **Connect**, confirm, and wait. Then select projector
connection on the dictionary. Retry that selection if the device times out.
The button changes to **Disconnect** and the actual screen appears on connection.
Persistent waiting can mean a missing/incompatible driver, not just an absent device.
[Device Manager code 28](https://learn.microsoft.com/en-us/windows-hardware/drivers/install/cm-prob-failed-install)
means the driver is not installed.

Changing the driver may affect CASIO transfer software. To restore it, close the
capture app, select the recorded device and use **Roll Back Driver** if available;
otherwise restore the manufacturer's original driver using its official installation
instructions. Reconnect and test ordinary transfers. Do not delete unrelated drivers.

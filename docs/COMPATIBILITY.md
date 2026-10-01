# 対応候補の根拠 / Compatibility basis

## 実機で確認した端末

PC版で画面受信を確認した組合せは次の通りです。

- XD-N6500（DATAPLUS 7）とLinux：画面表示・静止画保存・録画。
- XD-K8700（DATAPLUS 9）とmacOS：画面表示・録画。
- XD-Y4900（DATAPLUS 10）とLinux：画面表示・静止画保存・録画。
- XD-Y4900とWindows：画面表示。

その他の機種・OSの組合せは確認済みとして扱いません。
確認済みの1機種をもって、同シリーズの全機種への対応を保証するものではありません。

## EX-word

以下の公式資料で投影機能を確認できます。実機で確認した通信と
同系統である可能性を候補選定の根拠としていますが、公式資料はパケット形式や
USB識別子の同一性を保証していません。

| READMEの候補シリーズ | 投影機能を確認できる公式資料の例 |
| --- | --- |
| XD-Nシリーズ | [XD-N10000取扱説明書](https://support.casio.jp/pdf/003/XD-N10000_WA.pdf) |
| XD-Kシリーズ | [XD-K9800取扱説明書](https://www.casio.com/content/dam/casio/global/support/manuals/exword/pdf/003-ja/xd-k/XD-K9800_WB_JA.pdf) |
| XD-Yシリーズ | [XD-Y7100取扱説明書](https://www.casio.com/content/dam/casio/global/support/manuals/exword/pdf/003-ja/xd-y/XD-Y7100_WA_JA.pdf) |
| XD-SXシリーズ | [公式プロジェクター接続FAQ](https://www.casio.com/jp/support/exword/faq/article/00/12/68/88/) |

READMEはシリーズ単位で記載しています。対象は各シリーズのうち取扱説明書に
プロジェクター接続機能が記載されている機種であり、全機種への互換性を主張するものではありません。

## グラフ関数電卓

Cahuteの[Protocol 7.00 Screenstreaming資料](https://cahute.org/topics/protocols/seven-ohp.html)は、
fx-9860G互換機とfx-CG互換機の画面転送を説明しています。
[CASIO Screen Receiver説明書](https://www.casio.com/content/dam/casio/global/support/manuals/calculators/pdf/004-en/s/Screen_Receiver_EN.pdf)
と[fx-9860GII説明書](https://www.casio.com/content/dam/casio/global/support/manuals/calculators/pdf/004-en/f/fx-9860GII_Soft_v211_EN.pdf)
にも対応シリーズと画面送信機能が記載されています。

READMEの候補：fx-9860Gシリーズ（GII・GIIIを含む）、fx-9750Gシリーズ、
fx-CG10／20／50シリーズ、GRAPH90+ E。
各機種の取扱説明書に投影・画面送信機能が記載されていることが前提です。
fx-9750G系の公式資料で確認できる例はfx-9750GIIIです。

ただし、アプリケーション層のパケットが同系統でもUSBの転送方式は一致しない場合があります。
fx-CG系では `ScreenR(XP)` がUSB bulk経路、通常の `ScreenRecv` / `Projector` はUSBストレージ経路です。
本ソフトは前者のみを候補とし、USBストレージの拡張コマンドを実装していません。
詳細はCahuteの[USB transport資料](https://cahute.org/topics/protocols/transport.html)を参照してください。

現在の受信実装は `07cf:6101` のvendor-specificインターフェイスとbulk端点を使用します。
対応する接続モード・USB識別子・パケット形式が揃うことが必要です。
資料にある公式Screen Receiverの対応機種すべてを、本ソフトの対応機種と読み替えることはできません。

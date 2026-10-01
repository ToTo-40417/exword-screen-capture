# Protocol and safety / 通信と安全性

Reference: Cahute's [Protocol 7.00 screenstreaming](https://cahute.org/topics/protocols/seven-ohp/packet-format.html).

Physically observed projector-mode frames:

| Device | Generation | Received frame | Payload bytes | Format |
| --- | --- | --- | --- | --- |
| XD-N6500 | DATAPLUS 7 | 528×432 combined | 456192 | TYPZ2 / 1RC2 |
| XD-Y4900 | DATAPLUS 10 | 528×320 single | 337920 | TYPZ2 / 1RC2 |

The XD-Y4900 was received by the same live receiver without protocol changes.

XD-N6500 handshake observations:

| Item | Observed value |
| --- | --- |
| USB | `07cf:6101`, vendor interface, one bulk IN and one bulk OUT |
| Enable | Control transfer `41 01`, value/index 0, no payload |
| Check | `16 44 49 43 30 30 44 30` (`DIC00`) |
| ACK | `06 30 32 30 30 31 30 44` |
| Frame | `TYPZ2`, `1RC2` big-endian RGB565 |
| Combined screen | 528×432; upper main panel 528×320, lower panel includes black padding |

Endpoint addresses are discovered, not fixed. Only valid checksums and documented
supported frame layouts are decoded. Incomplete packets survive bulk-read boundaries.
Unknown frame subtypes stop interpretation rather than guessing lengths or accidentally
acknowledging bytes inside image data. Payloads are bounded at 2 MiB.

The app does not mount storage, write models, read NAND, reset USB devices, change
USB configurations, detach drivers, or inject keys. The enable request and ACK are
the only intentional outbound protocol messages. Input remains on the dictionary.
Only projector mode is in scope; shared USB IDs do not prove that another mode is safe.

USB reception, GUI painting and encoding are separate. The receiver holds one latest
frame; the recorder also holds one latest native RGB frame. Upscaling happens on the
PC, never on the EX-word. Disconnects retain the last image and wait for reconnection.

日本語：実機から確認した通信・画像形式のみを上表に記載しています。本体ストレージの書換えや遠隔キー操作は行いません。
上下分割は確認済みの528×432配置に限定し、未確認サイズでは全体表示を使います。

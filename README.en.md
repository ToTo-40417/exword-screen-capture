# EX-word Screen Capture

[日本語](README.md) · English · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md)

Display, save and record CASIO EX-word screens on a PC using the device's projector connection.

Version: v1.0.0

![Application preview](docs/images/capture-ui-window.png)

*An illustrative test pattern is used in this image.*

## Features

- PNG screenshots and silent H.264/MP4 recording by default; optional lossless FFV1/MKV.
- Exact x1–x10 integer scaling based on the received native resolution.
- Whole/upper/lower views and integer-scaled fullscreen display.
- Output folder selection and optional grayscale/invert filters.
- Japanese, English, Simplified Chinese and Traditional Chinese UI.

## Devices

Physically verified model/OS combinations and functions:

- CASIO EX-word XD-N6500 (DATAPLUS 7): Linux (display, snapshots and recording)
- CASIO EX-word XD-K8700 (DATAPLUS 9): macOS (display and recording)
- CASIO EX-word XD-Y4900 (DATAPLUS 10): Linux (display, snapshots and recording); Windows (display)

The following families have projector connection documented in official materials.
Only models with that feature are candidates. Models other than those listed above are **not physically verified with this app**:

- EX-word: XD-N, XD-K, XD-Y and XD-SX series.
- Graphing calculators: fx-9860G series (including GII/GIII) and fx-9750G series.
- Color graphing calculators: fx-CG10/20/50 series and GRAPH90+ E.

Projector support alone does not guarantee compatibility. fx-CG candidates require `ScreenR(XP)`.
See [compatibility sources and connection requirements](docs/COMPATIBILITY.md).

## Environment

- PC GUI: Windows x64, macOS arm64 and Linux x86_64. See [OS prerequisites](docs/SETUP.md).
- Linux CLI: headless capture and recording. See [CLI setup and usage](docs/SETUP.md#headless-cli--軽量環境向けcli).
- Brainux: a separate preview application on Brain. See [differences and setup](docs/BRAINUX.md).

### Recommended planning specifications

Calculated planning estimates for a 528×432 source at 10 fps—not measured minimums or performance guarantees.

| Use | CPU selection guideline | RAM | Storage |
| --- | --- | --- | --- |
| Preview, PNG and x1–x2 recording | 64-bit, 2+ cores | 4+ GiB | SSD recommended |
| x10 recording (5280×4320) | 64-bit, 4+ cores | 8+ GiB | SSD with sufficient free space |

OS requirements take precedence. A dedicated GPU is not required; workload depends on resolution and content.
See [calculations and assumptions](docs/RESOURCE_ESTIMATES.md).

## Installation

### Executable download

Download the GUI package for your OS from [Releases](https://github.com/ToTo-40417/exword-screen-capture/releases).

- **Windows x64:** run `EXwordScreenCapture.exe`. Assign **WinUSB to the target USB device before the first connection**; follow [Windows USB setup](docs/WINDOWS_USB.md#english).
- **macOS:** extract the ZIP and open the `.app`. Initial permission to open an unnotarized app may be required.
- **Linux:** extract the ZIP and run `EXwordScreenCapture` inside it. Keep the entire folder. USB access permissions may need configuration.

Python, Qt, libusb and recording FFmpeg are bundled. Bundling libusb does not
replace Windows USB driver setup. Changing the driver may affect CASIO transfer
software; identify the target device and record its original driver first.
See [setup](docs/SETUP.md).

### Run from source

See [setup](docs/SETUP.md) for Python dependencies, source execution and build instructions.

## GUI usage

### Connect

1. Connect the dictionary to your PC via USB and click **Connect** in the PC app.
2. Click **Connect** in the confirmation dialog. The app shows **Waiting**.
3. Select projector connection on the dictionary. The PC button becomes **Disconnect** when connected.

Click **Disconnect** in the PC app to stop reception.

If the dictionary times out, select projector connection again while the PC app
is waiting. On Windows, persistent waiting may indicate a missing or incompatible
USB driver; see [Windows USB setup](docs/WINDOWS_USB.md#english).

### Capture and record

Settings selects the recording format and scale (x1–x10), independently of display/PNG scale.
The defaults are H.264/MP4 and x1. Very large videos may exceed a player’s capabilities.

| Action | PC app control | Key |
| --- | --- | --- |
| Save an image | Screenshot (F8) | F8 |
| Start/stop recording | Recording (F9) | F9 |
| Toggle fullscreen | Fullscreen (F11) | F11 |
| Exit fullscreen | Press Esc | Esc |

The default folder is `Pictures/EX-word Captures`; change it in **Settings**.
Each capture creates a timestamped file without overwriting existing files.

### Display and settings

- **View:** All screens includes the complete received frame. Upper/lower selection is available for supported combined frames.
- **Scale:** Resolution x1 selects x1–x10 for windowed display and PNG export. Scroll to see parts that do not fit.
- **Fullscreen:** The image is centered at the largest fitting scale from 1x to 10x, possibly with black margins. A screen smaller than the source clips the image. Export scale does not change.
- **Filter:** Settings offers None, Grayscale and Invert colors, applied to preview, screenshots and recording.
- **Language:** Use the menu next to Fullscreen.

Language, folder, scale and filter preferences persist.

## Notes

- Use projector connection, not normal USB transfer mode. Do not run another USB transfer tool simultaneously; connect only one dictionary.
- Screens may not be captured while homebrew applications (additional content) are running.
- Recording is silent at 10 fps, repeating the latest image during idle periods. This does not guarantee a 10 fps device transmission rate.
- An encoder that falls behind stops with an error.
- Users must check the rights required to use or publish captured content.

## License and technical documents

Original source is [MIT-licensed](LICENSE). Dependencies retain their respective
licenses and copyrights. This independent implementation references public Cahute
specifications; no Cahute code, CASIO dictionary or firmware is included.
This is not an official CASIO product.

- [Installation and packaging](docs/SETUP.md)
- [Protocol and safety](docs/PROTOCOL.md)
- [Licensing and binary distribution checklist](docs/LICENSING.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

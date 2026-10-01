# Brainux preview adapter

GTK-based EX-word live preview for Brainux. This is separate from the PC GUI
and the CLI command. It shares the core protocol parser and uses native
RGB565 conversion on ARM.

Features, differences and setup: [Brainux版の補足資料](../../docs/BRAINUX.md).

Adapter source: MIT, as specified in [LICENSE](LICENSE).
Build `libbrain_pixels.so` on the Linux development host; do not deploy the
host-test library `libbrain_pixels-test.so`. Built libraries and private
device captures are not part of the source export.

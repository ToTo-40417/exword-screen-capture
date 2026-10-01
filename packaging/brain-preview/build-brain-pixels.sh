#!/bin/sh
set -eu
cd "$(dirname "$0")"
SOURCE_ROOT=${EXWORD_SOURCE:-$(CDPATH= cd ../.. && pwd)}
HOST_CC=${HOST_CC:-gcc}
ARM_CC=${ARM_CC:-arm-linux-gnueabi-gcc}
ARM_READELF=${ARM_READELF:-arm-linux-gnueabi-readelf}
PYTHON=${PYTHON:-python3}
"$HOST_CC" -O3 -fPIC -shared -Wall -Wextra -Werror brain_pixels.c -o libbrain_pixels-test.so
export BRAIN_PIXELS_LIBRARY="$PWD/libbrain_pixels-test.so"
export PYTHONPATH="$SOURCE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON" test_brain_pixels.py
"$PYTHON" test_brain_receiver.py
"$ARM_CC" -O3 -march=armv5te -mfloat-abi=soft -fPIC -shared \
    -nostdlib -Wall -Wextra -Werror -Wl,--no-undefined \
    brain_pixels.c -o libbrain_pixels.so
"$ARM_READELF" -h -A -d libbrain_pixels.so
"$PYTHON" -m py_compile brain_pixels.py brain_usb_source.py exword-capture-preview.py

#!/usr/bin/env bash
# Keep all build tool search paths on the caller's project-only ASCII alias.
set -eu
root=${EXWORD_NATIVE_ROOT:?Set EXWORD_NATIVE_ROOT to the ASCII MSYS2 root}
compiler="$root/ucrt64/bin/gcc.exe"
version=$("$compiler" -dumpversion)
machine=$("$compiler" -dumpmachine)
export TMPDIR=${EXWORD_NATIVE_TEMP:?Set EXWORD_NATIVE_TEMP to the ASCII project temp directory}
export TMP="$TMPDIR" TEMP="$TMPDIR"
export MSYS2_ENV_CONV_EXCL='TMPDIR;TMP;TEMP'
exec "$compiler" "--sysroot=$root/ucrt64" \
    -B "$root/ucrt64/bin/" -B "$root/ucrt64/lib/" \
    -B "$root/ucrt64/lib/gcc/$machine/$version/" "$@"

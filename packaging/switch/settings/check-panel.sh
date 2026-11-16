#!/bin/sh
# macOS host fixture. Use a fresh SD tree and the local, read-only extracted disc.
set -eu
cd "$(dirname "$0")/../../.."
repo=$PWD
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/sdmc:/switch/ngb-runtime"
cc -O2 -ffunction-sections -fdata-sections -I. -Isrc -Ibuild/switch-runtime/gen \
  -Ipackaging/switch/runtime -Ixboxrecomp/src -Ixboxrecomp/src/kernel \
  $(sdl2-config --cflags) packaging/switch/settings/test-panel.c src/quick_ui.c \
  -Wl,-dead_strip -o "$tmp/test"
cd "$tmp"
./test "$repo/game_files"

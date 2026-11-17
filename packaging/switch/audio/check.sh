#!/bin/sh
set -eu
cd "$(dirname "$0")/../../.."
docker run --rm -v "$PWD:/work:ro" -w /work ngb-switch-host:direct0331 sh -ec '
cc -std=c11 -O2 -Ipackaging/switch/runtime -Ixboxrecomp/src packaging/switch/audio/check.c \
    -lavcodec -lavutil -lm -o /tmp/check
/tmp/check game_files/movie/2_VI_WIDE_B.sfd game_files/movie/ninja_gaiden.sfd game_files/movie/pre_movie1.sfd
cc -std=c11 -O2 -Ipackaging/switch/runtime -Ixboxrecomp/src packaging/switch/audio/trace.c \
    -lavcodec -lavutil -lm -o /tmp/trace
/tmp/trace >/tmp/pcm.trace
echo "74968711227aa7236fe917960d6076e192c20395b281c23315998f92fc294ac1  /tmp/pcm.trace" | sha256sum -c -'

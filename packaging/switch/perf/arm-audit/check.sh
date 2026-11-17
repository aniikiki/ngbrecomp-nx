set -eu
python3 /audit/spans.py
c++ /audit/check.cpp $(/usr/lib/llvm-15/bin/llvm-config --cxxflags --ldflags --libs --system-libs) -O2 -o /audit/check
/audit/check build/switch-runtime/history/0.56.23/ngb-startup.nro

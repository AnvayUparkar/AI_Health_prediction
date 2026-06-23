#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🔍 Locating native system dependencies in lib/..."
# Find all directories containing shared libraries (.so files) under lib
SO_DIRS=$(find "$(pwd)/lib" -name "*.so*" -exec dirname {} \; 2>/dev/null | sort -u | tr '\n' ':')

if [ -n "$SO_DIRS" ]; then
  export LD_LIBRARY_PATH="${SO_DIRS}${LD_LIBRARY_PATH}"
  echo "✅ Set LD_LIBRARY_PATH to: $LD_LIBRARY_PATH"
else
  echo "⚠️ No extracted .so libraries found in lib/"
fi

echo "🚀 Starting Python server..."
python server.py

#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting workspace build..."
cd project
bash build.sh
cd ..
echo "🎉 Root workspace build finished!"

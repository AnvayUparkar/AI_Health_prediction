#!/usr/bin/env bash
# exit on error
set -o errexit

echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🔧 Installing native system dependencies (libgl1, libglib2.0-0)..."
mkdir -p lib
cd lib

# Download native package binaries
echo "Downloading packages..."
apt-get update -qy || true
apt-get download -q libgl1 libglib2.0-0 || true

# Extract downloaded .deb archives
for deb in *.deb; do
  if [ -f "$deb" ]; then
    echo "Extracting $deb..."
    dpkg -x "$deb" .
  fi
done

# Clean up .deb files to save space
rm -f *.deb

echo "✅ Build script finished successfully!"

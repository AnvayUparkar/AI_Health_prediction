#!/usr/bin/env bash
# exit on error
set -o errexit

echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "🔧 Installing native system dependencies (libgl1, libglib2.0-0)..."
mkdir -p lib
cd lib

# We will try a standard download first, and if that fails, we use a user-space apt configuration
if apt-get download -q libgl1 libglib2.0-0 libgles2 libegl1 libgthread-2.0-0 2>/dev/null; then
  echo "Standard apt download succeeded."
else
  echo "Standard apt download failed. Trying user-space apt-get..."
  mkdir -p apt/lists/partial
  mkdir -p apt/cache/archives/partial
  mkdir -p apt/etc/apt/preferences.d
  mkdir -p apt/etc/apt/sources.list.d

  # Create user-space apt config
  cat <<EOF > apt/apt.conf
Dir "$(pwd)/apt";
Dir::State "$(pwd)/apt";
Dir::State::status "$(pwd)/apt/status";
Dir::Cache "$(pwd)/apt/cache";
Dir::Etc "$(pwd)/apt/etc";
EOF

  if [ -f /etc/apt/sources.list ]; then
    cp /etc/apt/sources.list apt/etc/apt/sources.list
  else
    echo "deb http://deb.debian.org/debian bookworm main" > apt/etc/apt/sources.list
  fi
  touch apt/status

  apt-get -c apt/apt.conf update -qy || true
  apt-get -c apt/apt.conf download -q libgl1 libglib2.0-0 libgles2 libegl1 libgthread-2.0-0 || true
fi

# Extract downloaded .deb archives
for deb in *.deb; do
  if [ -f "$deb" ]; then
    echo "Extracting $deb..."
    dpkg -x "$deb" .
  fi
done

# Clean up .deb files and custom apt directory to save space
rm -f *.deb
rm -rf apt

echo "✅ Build script finished successfully!"

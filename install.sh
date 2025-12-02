#!/usr/bin/env bash
set -e

echo ""
echo "==============================================="
echo "   BlackBox OSINT Appliance – Upgrade Install"
echo "==============================================="
echo ""

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# -------------------------
# 1. SYSTEM REQUIREMENTS
# -------------------------
echo "[*] Updating system packages..."
sudo apt-get update -y

echo "[*] Installing OS dependencies (Python, build tools, WeasyPrint deps, libpcap)..."
sudo apt-get install -y \
    python3 \
    python3-venv \
    python3-dev \
    python3-pip \
    build-essential \
    libffi-dev \
    libssl-dev \
    libxml2 \
    libxml2-dev \
    libxslt1-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libcairo2-dev \
    libgdk-pixbuf2.0-0 \
    libgdk-pixbuf2.0-dev \
    libmagic1 \
    fonts-liberation \
    libjpeg-dev \
    zlib1g-dev \
    libpcap-dev \
    git \
    curl

echo ""
echo "[*] System dependencies installed."
echo ""

# -------------------------
# 2. PYTHON VIRTUAL ENV
# -------------------------
if [ ! -d ".venv" ]; then
    echo "[*] Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "[*] Virtual environment already exists. Skipping creation."
fi

echo "[*] Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[*] Upgrading pip/setuptools/wheel..."
pip install --upgrade pip setuptools wheel

# -------------------------
# 3. PYTHON DEPENDENCIES
# -------------------------
if [ -f "requirements.txt" ]; then
    echo "[*] requirements.txt found – installing from file..."
    pip install -r requirements.txt
else
    echo "[*] requirements.txt not found – installing baseline Python packages..."
    pip install \
        requests \
        PyYAML \
        Jinja2 \
        python-docx \
        weasyprint \
        markdown \
        beautifulsoup4 \
        python-dotenv \
        tqdm
fi

echo ""
echo "[*] Python dependencies installed."
echo ""

# -------------------------
# 4. GO + PROJECTDISCOVERY TOOLS + AMASS
# -------------------------

# 4.1 Install Go if missing
if ! command -v go >/dev/null 2>&1; then
    echo "[*] Go not found – installing golang-go..."
    sudo apt-get install -y golang-go
else
    echo "[*] Go already installed."
fi

# Ensure GOPATH/bin is on PATH for this session
if [ -z "$GOPATH" ]; then
    export GOPATH="$HOME/go"
fi
export PATH="$PATH:$GOPATH/bin"

# Also persist GOPATH/bin to shell profile (for future sessions)
if ! grep -q 'export GOPATH=' "$HOME/.bashrc" 2>/dev/null; then
    echo 'export GOPATH="$HOME/go"' >> "$HOME/.bashrc"
fi
if ! grep -q 'export PATH=.*$GOPATH/bin' "$HOME/.bashrc" 2>/dev/null; then
    echo 'export PATH="$PATH:$GOPATH/bin"' >> "$HOME/.bashrc"
fi

echo ""
echo "[*] Installing ProjectDiscovery tools and Amass via Go..."
echo "    (this may take a while on first run)"

# Subfinder
echo "  - Installing subfinder..."
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest || true

# Naabu
echo "  - Installing naabu..."
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest || true

# httpx
echo "  - Installing httpx..."
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest || true

# Nuclei
echo "  - Installing nuclei..."
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest || true

# Amass (v5+)
echo "  - Installing amass..."
go install -v github.com/owasp-amass/amass/v5/cmd/amass@main || true

# Symlink to /usr/local/bin if binaries exist
echo ""
echo "[*] Linking binaries into /usr/local/bin (requires sudo)..."

for bin in subfinder naabu httpx nuclei amass; do
    if [ -f "$GOPATH/bin/$bin" ]; then
        echo "  - Linking $bin -> /usr/local/bin/$bin"
        sudo ln -sf "$GOPATH/bin/$bin" "/usr/local/bin/$bin"
    else
        echo "  [!] $bin not found in $GOPATH/bin (install may have failed)."
    fi
done

# 4.2 Nuclei templates
if command -v nuclei >/dev/null 2>&1; then
    echo ""
    echo "[*] Updating nuclei templates (optional but recommended)..."
    nuclei -update-templates || true
else
    echo "[!] nuclei not on PATH – skipping template update."
fi

echo ""
echo "[*] Tool installation complete."
echo ""

# -------------------------
# 5. DIRECTORY STRUCTURE CHECK
# -------------------------
echo "[*] Checking directory structure..."

for dir in config data modules reporting reporting/templates config/targets; do
    if [ ! -d "$dir" ]; then
        echo "    [!] Missing directory: $dir – creating it."
        mkdir -p "$dir"
    fi
done

echo "[*] Directory structure OK."
echo ""

# -------------------------
# 6. FINAL MESSAGE
# -------------------------
echo "==============================================="
echo " Installation complete!"
echo "==============================================="
echo ""
echo "Next steps (from repo root):"
echo ""
echo "  source .venv/bin/activate"
echo "  python main.py --target acme"
echo ""
echo "Generate reports:"
echo "  python reporting/generate_report.py --target acme"
echo "  python reporting/generate_docx.py --target acme"
echo "  python reporting/generate_pdf.py --target acme"
echo ""
echo "Tools installed (expected on PATH):"
echo "  - amass"
echo "  - subfinder"
echo "  - naabu"
echo "  - httpx"
echo "  - nuclei  (templates in ~/.local/nuclei-templates or similar)"
echo ""
echo "BlackBox Pentesters – Raising Standards in Cybersecurity Testing"
echo ""

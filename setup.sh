#!/usr/bin/env bash
#
# setup.sh – Ubuntu 2 bootstrap for Reachy_Local_08.4.2 (web app only)
# - Ensures ./venv exists
# - Activates it
# - Installs apps/web/requirements.txt
# - Prints a short status summary

set -euo pipefail

# Figure out project root (directory containing this script)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_ROOT}/venv"
REQ_FILE="${PROJECT_ROOT}/apps/web/requirements.txt"

echo "=== Reachy_Local_08.4.2 setup (Ubuntu 2) ==="
echo "Project root : ${PROJECT_ROOT}"
echo "Venv dir     : ${VENV_DIR}"
echo "Req file     : ${REQ_FILE}"
echo

# 1) Create venv if it doesn't exist
if [[ ! -d "${VENV_DIR}" ]]; then
  echo "[1/4] Creating virtual environment in ./venv ..."
  python3 -m venv "${VENV_DIR}"
else
  echo "[1/4] Virtual environment already exists at ./venv"
fi

# 2) Activate venv
echo "[2/4] Activating virtual environment ..."
# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"

# 3) Install web requirements
if [[ ! -f "${REQ_FILE}" ]]; then
  echo "ERROR: requirements file not found at:"
  echo "  ${REQ_FILE}"
  echo "Aborting."
  exit 1
fi

echo "[3/4] Upgrading pip and installing web dependencies ..."
python -m pip install --upgrade pip
pip install -r "${REQ_FILE}"

# 4) Print status
echo "[4/4] Environment status:"
python --version

# Try to print versions of key packages (best-effort)
python - << 'EOF'
import importlib

pkgs = ["streamlit", "requests", "lumaai", "python_dotenv", "pydantic"]
for name in pkgs:
    try:
        m = importlib.import_module(name.replace("-", "_"))
        ver = getattr(m, "__version__", "unknown")
        print(f"  {name}: {ver}")
    except Exception as e:
        print(f"  {name}: NOT INSTALLED ({e.__class__.__name__})")
EOF

echo
echo "✅ Setup complete for Ubuntu 2 web stack."
echo "Next steps:"
echo "  source venv/bin/activate"
echo "  cd apps/web"
echo "  streamlit run landing_page.py"


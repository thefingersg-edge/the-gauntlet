#!/usr/bin/env bash
# One-time environment setup for macOS.
#
# Why a virtual environment rather than `pip install pandas`:
#
# Recent macOS Pythons -- both Apple's /usr/bin/python3 and Homebrew's -- ship
# marked "externally managed" (PEP 668). pip refuses to install into them to
# stop you breaking the system or Homebrew's own Python. The error looks like:
#
#     error: externally-managed-environment
#     × This environment is externally managed
#
# The usual workaround people reach for is --break-system-packages, which does
# what the name says. A virtual environment is the same amount of typing, needs
# no admin rights, touches nothing outside this folder, and can be deleted by
# removing one directory.
#
# Run:  bash setup_mac.sh

set -euo pipefail

cd "$(dirname "$0")"
VENV=".venv"

echo "=================================================="
echo "  pineport environment setup"
echo "=================================================="
echo

# ---- find a usable python3 ------------------------------------------------
PYTHON=""
for candidate in \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    "$(command -v python3 || true)" \
    /usr/bin/python3
do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
        version="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "0.0")"
        major="${version%%.*}"; minor="${version##*.}"
        if [ "$major" -eq 3 ] && [ "$minor" -ge 9 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "No Python 3.9+ found."
    echo "Install one with:  brew install python3"
    echo "(or from python.org if you do not use Homebrew)"
    exit 1
fi

echo "Using: $PYTHON  ($("$PYTHON" -c 'import sys; print(sys.version.split()[0])'))"
echo

# ---- create the virtual environment ---------------------------------------
if [ -d "$VENV" ]; then
    echo "Virtual environment already exists at $VENV -- reusing it."
else
    echo "Creating virtual environment in $VENV ..."
    "$PYTHON" -m venv "$VENV"
fi

VPY="$VENV/bin/python"

echo "Upgrading pip ..."
"$VPY" -m pip install --quiet --upgrade pip

echo "Installing packages ..."
"$VPY" -m pip install --quiet pandas numpy yfinance
echo "  core packages installed"

# pyarrow speeds up the data cache but has no wheel on some Python versions;
# it is genuinely optional, so a failure here must not stop the setup.
if "$VPY" -m pip install --quiet pyarrow 2>/dev/null; then
    echo "  pyarrow installed (faster data cache)"
else
    echo "  pyarrow skipped -- optional, everything works without it"
fi

# ---- verify ---------------------------------------------------------------
echo
echo "Verifying ..."
"$VPY" check_env.py || true

echo
echo "Running the offline test suites ..."
"$VPY" test_port.py    2>&1 | tail -1
"$VPY" dukascopy.py --self-test 2>&1 | tail -1
"$VPY" fetch_data.py --self-test 2>&1 | tail -1

# ---- what to do next ------------------------------------------------------
FULL_VPY="$(cd "$(dirname "$VPY")" && pwd)/$(basename "$VPY")"

cat <<EOF

==================================================
  Setup complete
==================================================

From the Terminal, use the venv's python:

    cd $(pwd)
    $VPY dukascopy.py --probe --year 2024 --month 6
    $VPY dukascopy.py --start 2006 --out xauusd_1h.csv

Or activate it once and just use 'python':

    source $VENV/bin/activate
    python dukascopy.py --probe --year 2024 --month 6

From RStudio, point reticulate at the same interpreter BEFORE any other
Python call (restart R first if you have already touched Python this
session -- Session -> Restart R):

    library(reticulate)
    use_python("$FULL_VPY", required = TRUE)
    source("pineport.R")
    pineport_env()

pineport.R will find this venv automatically if you source it in a fresh
session.

EOF

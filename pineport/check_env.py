#!/usr/bin/env python3
"""Diagnose the Python environment and print the exact command to fix it.

Standard library only, deliberately -- this has to run in the interpreter that
is missing packages, so it cannot import any of them.

    python3 check_env.py

The problem this exists for: a Mac typically has several Pythons (the system
one, Homebrew's, pyenv's, conda's, and whatever reticulate binds to). Installing
with a bare `pip install` targets whichever pip happens to be first on PATH,
which is frequently not the interpreter you then run the script with. The result
is "I definitely installed pandas" followed by ModuleNotFoundError.

Running `<interpreter> -m pip install ...` removes the ambiguity, because pip is
invoked *by* the interpreter that needs the package.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig

REQUIRED = ["pandas", "numpy"]
OPTIONAL = ["yfinance", "pyarrow", "optuna", "sklearn"]


def probe(module: str) -> tuple[bool, str]:
    try:
        mod = __import__(module)
    except ImportError:
        return False, ""
    return True, getattr(mod, "__version__", "?")


def is_externally_managed() -> bool:
    """PEP 668 marker -- Homebrew and recent system Pythons set this.

    When present, pip refuses to install into the interpreter without either a
    virtual environment or an explicit override flag.
    """
    stdlib = sysconfig.get_paths().get("stdlib", "")
    return os.path.exists(os.path.join(stdlib, "EXTERNALLY-MANAGED"))


def in_virtualenv() -> bool:
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def find_other_pythons() -> list[str]:
    seen, found = set(), []
    for name in ("python3", "python3.13", "python3.12", "python3.11",
                 "python3.10", "python3.9", "python"):
        path = shutil.which(name)
        if not path:
            continue
        real = os.path.realpath(path)
        if real in seen:
            continue
        seen.add(real)
        found.append(real)
    return found


def has_pandas(python: str) -> str:
    try:
        out = subprocess.run(
            [python, "-c", "import pandas; print(pandas.__version__)"],
            capture_output=True, text=True, timeout=20)
        return out.stdout.strip() if out.returncode == 0 else "-"
    except Exception:                                   # noqa: BLE001
        return "?"


def main() -> int:
    print("Interpreter")
    print("-" * 68)
    print(f"  executable   {sys.executable}")
    print(f"  version      {sys.version.split()[0]}")
    print(f"  virtualenv   {'yes' if in_virtualenv() else 'no'}")
    print(f"  PEP 668      {'externally managed' if is_externally_managed() else 'installable'}")

    print("\nPackages in THIS interpreter")
    print("-" * 68)
    missing = []
    for group, mods in (("required", REQUIRED), ("optional", OPTIONAL)):
        print(f"  {group}:")
        for m in mods:
            ok, ver = probe(m)
            print(f"    {m:<12} {'yes  ' + ver if ok else 'MISSING'}")
            if not ok and group == "required":
                missing.append(m)

    others = find_other_pythons()
    if len(others) > 1:
        print("\nOther Pythons on PATH")
        print("-" * 68)
        print("  (pandas column shows which ones already have it)")
        for p in others:
            marker = "  <-- you are here" if os.path.realpath(sys.executable) == p else ""
            print(f"    {p:<52} {has_pandas(p):>8}{marker}")

    print("\n" + "=" * 68)
    if not missing:
        print("Everything required is present. You are good to go:")
        print("  python3 dukascopy.py --probe --year 2024 --month 6")
        return 0

    print(f"MISSING: {', '.join(missing)}")
    print("\nFix -- run exactly this, using the interpreter you will run the")
    print("script with, so pip and python cannot disagree:\n")

    pkgs = " ".join(REQUIRED + ["yfinance"])
    if in_virtualenv():
        print(f'  "{sys.executable}" -m pip install {pkgs}')
    elif is_externally_managed():
        print("  This interpreter is marked externally-managed (PEP 668), so pip")
        print("  will refuse a plain install. Two options.\n")
        print("  A virtual environment (recommended -- keeps things isolated):")
        print(f'    "{sys.executable}" -m venv ~/.venvs/pineport')
        print(f"    ~/.venvs/pineport/bin/python -m pip install {pkgs}")
        print("    ~/.venvs/pineport/bin/python dukascopy.py --probe --year 2024 --month 6")
        print("\n  Or install into it anyway:")
        print(f'    "{sys.executable}" -m pip install --break-system-packages {pkgs}')
    else:
        print(f'  "{sys.executable}" -m pip install {pkgs}')

    print("\nIf you are calling this from RStudio instead, reticulate may be")
    print("bound to a DIFFERENT interpreter than the one above. Check with:")
    print("    source('pineport.R'); pineport_env()")
    print("and install there with:")
    print("    reticulate::py_install(c('pandas','numpy','yfinance'), pip = TRUE)")
    return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Check the environment and folder layout before running anything else.

    python setup_check.py

Run it with the SAME interpreter you intend to use for the real scripts:

    .venv/bin/python setup_check.py

That last point is the whole reason this file exists. "pandas is not
recognised" almost always means the script was launched with a different
Python than the one pandas was installed into -- not that pandas is missing.
This prints exactly which interpreter is running and what it can see.
"""

from __future__ import annotations

import importlib
import os
import sys

REQUIRED = {
    "numpy":   ("1.24", "arrays"),
    "pandas":  ("2.0",  "all data handling; 2.0+ needed for to_datetime(format='mixed')"),
}
OPTIONAL = {
    "sklearn": ("1.1", "logistic meta-model in silver_mr.py -- NOT needed for data pulling"),
}

# files that must be co-located, because one imports the other
COLOCATED = [("dukascopy.py", "dukascopy_intraday.py")]


def vtuple(s: str):
    out = []
    for part in s.split("."):
        digits = "".join(c for c in part if c.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out)


def main() -> int:
    problems, warnings = [], []

    print("=" * 70)
    print("INTERPRETER")
    print("=" * 70)
    print(f"  executable : {sys.executable}")
    print(f"  version    : {sys.version.split()[0]}")
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    print(f"  virtualenv : {'YES -> ' + sys.prefix if in_venv else 'NO (system Python)'}")

    if sys.version_info < (3, 9):
        problems.append(f"Python {sys.version.split()[0]} is too old; these "
                        f"scripts use 3.9+ syntax (X | None type hints)")

    if not in_venv:
        warnings.append(
            "Not running inside a virtualenv. If you installed pandas into a\n"
            "     venv, this interpreter cannot see it. Use .venv/bin/python "
            "explicitly.")

    print("\n" + "=" * 70)
    print("PACKAGES")
    print("=" * 70)

    for name, (minv, why) in {**REQUIRED, **OPTIONAL}.items():
        optional = name in OPTIONAL
        try:
            mod = importlib.import_module(name)
            got = getattr(mod, "__version__", "?")
            ok = got == "?" or vtuple(got) >= vtuple(minv)
            mark = "ok " if ok else "OLD"
            print(f"  [{mark}] {name:10s} {got:12s} (need >= {minv})")
            if not ok:
                (warnings if optional else problems).append(
                    f"{name} {got} is below {minv} -- {why}")
        except ImportError:
            print(f"  [--] {name:10s} NOT INSTALLED   ({'optional' if optional else 'required'})")
            msg = f"{name} missing -- {why}"
            (warnings if optional else problems).append(msg)

    print("\n" + "=" * 70)
    print("FOLDER LAYOUT")
    print("=" * 70)
    here = os.path.dirname(os.path.abspath(__file__))
    print(f"  checking: {here}")
    present = set(os.listdir(here))

    for a, b in COLOCATED:
        if b in present and a not in present:
            problems.append(
                f"{b} needs {a} in the SAME folder (it does `import dukascopy`). "
                f"Copy {a} here.")
        elif a in present and b in present:
            print(f"  [ok ] {a} and {b} are co-located")

    for f in ("dukascopy.py", "dukascopy_intraday.py", "silver_mr.py"):
        if f not in present:
            warnings.append(f"{f} not in this folder")

    csvs = sorted(f for f in present if f.endswith(".csv"))
    if csvs:
        print(f"  [ok ] {len(csvs)} csv(s) here: {', '.join(csvs[:6])}")
        need = ["xagusd", "xauusd"]
        missing = [n for n in need if not any(n in c.lower() for c in csvs)]
        if missing:
            warnings.append(
                f"no {'/'.join(missing)} csv here. The strategy regresses silver "
                f"on gold;\n     silver alone will not run.")
    else:
        print("  [--] no csv files yet (expected before the first pull)")

    print("\n" + "=" * 70)
    if problems:
        print(f"{len(problems)} PROBLEM(S) -- fix before running:")
        for p in problems:
            print(f"  *  {p}")
    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  -  {w}")
    if not problems and not warnings:
        print("All clear. Next:")
        print("  python dukascopy_intraday.py --self-test")
        print("  python dukascopy_intraday.py --instrument XAGUSD --verify "
              "--year 2024 --month 6")

    if problems:
        print("\n" + "-" * 70)
        print("If packages are missing, install into THIS interpreter:")
        print(f"  {sys.executable} -m pip install pandas numpy scikit-learn")
        print("-" * 70)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

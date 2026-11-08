#!/usr/bin/env python3
"""
registry.py — one index of every pre-registered test across every project.

WHY THIS IS GENERATED AND NOT WRITTEN BY HAND
---------------------------------------------
`Claude/README.md` used to describe silver15 — one project out of five, and
not even the one it sat above. An agent reading it concluded the whole tree
was the silver project and never found `fastbot/`, which cost a day of work
and produced a programme summary that omitted four real findings.

A hand-maintained index is exactly what failed. This one is rebuilt by
scanning, so it cannot drift from the files it describes. Re-run it after
any new pre-registration or result:

    python3 registry.py            # rewrite REGISTRY.csv and REGISTRY.md
    python3 registry.py --audit    # exit non-zero if the audit finds problems
    python3 registry.py --self-test

WHAT IT AUDITS
    open      a pre-registration with no matching result   (a test still running)
    ORPHAN    a result with no pre-registration            (investigate)
    SPLIT     one topic, two projects, different verdicts  (read both)
"""
import argparse, csv, os, re, sys, subprocess
from datetime import datetime, timezone

ROOT  = os.path.dirname(os.path.abspath(__file__))
SKIP  = {".git", "venv", ".venv", "__pycache__", "node_modules", "data",
         "charts", "final_charts", "logs_r4"}
KINDS = ("PREREGISTRATION", "RESULT", "FINDINGS")

# Topics that are the same subject under different names across projects.
# Only collapse what is genuinely the same question.
ALIASES = {
    "REVERSALS": "PATTERNS", "ZOO": "PATTERNS", "ZOO_H1": "PATTERNS",
    "WEDGE": "PATTERNS", "CANDLESPACE": "PATTERNS", "CANDLEINFO": "PATTERNS",
    "IVSIZE": "VRP", "IVSIZE_REPLICATION": "VRP", "VRP_BUDGET": "VRP",
    "PREANN": "PREANNOUNCEMENT", "KUROV": "PREANNOUNCEMENT",
    "TRACKA": "PREANNOUNCEMENT", "TRACKA_D2": "PREANNOUNCEMENT",
    "TRACKA_D3": "PREANNOUNCEMENT",
    "FXCARRY": "CARRY", "FXCARRY_P0": "CARRY", "CARRYDISPERSION": "CARRY",
    "VIXCARRY": "CARRY", "VIXCURVE": "VIXTERM", "VIXDAILY": "VIXTERM",
    "KRAKENBASIS": "BASIS", "KRAKENBASIS_LINEAR": "BASIS",
    "KRAKENBASIS_V7": "BASIS",
}

DATE_RE = re.compile(
    r"^\s*(?:RUN|WRITTEN|FROZEN|EXECUTED|DATE|STARTED)\s*:?\s*(\d{4}-\d{2}-\d{2})",
    re.I | re.M)
DATE_PROSE = re.compile(r"(?:^|\s)(?:Run|Executed|Frozen(?: on)?)\s+(\d{4}-\d{2}-\d{2})",
                        re.I)
VERDICT_LINE = re.compile(r"^\s*VERDICT\s*:?\s*(.+?)\s*$", re.I | re.M)
VERDICT_BOLD = re.compile(
    r"\*\*\s*(?:VERDICT\s*:\s*)?((?:FAIL|PASS|DEAD|WITHDRAWN|PROCEED|NO PROMISE)[^*]*)\*\*",
    re.I)
SPEC_RE = re.compile(r"^\s*SPEC[S]?\s*:?\s*(.+?)\s*$", re.I | re.M)
PREREG_REF = re.compile(r"PREREGISTRATION[_ ]?(v?[A-Za-z0-9_]+(?:\.[0-9]+)*)")
STATUS_RE = re.compile(r"^\s*STATUS\s*:?\s*(.+?)\s*$", re.I | re.M)


BARE_V = re.compile(r"\bv([0-9]+(?:\.[0-9]+)?)\b")


def _refs(text: str) -> set:
    """Every pre-registration this document names.

    A spec line reads "PREREGISTRATION_v11 (two arms), v12 (their window),
    v13 (2016-2026)" -- only the first carries the prefix, so once a line
    names one pre-registration every bare vN on that line is also a reference.
    """
    out = {r.upper() for r in PREREG_REF.findall(text)}
    for line in text.splitlines():
        if "PREREGISTRATION" in line.upper():
            out |= {f"V{m.group(1)}".upper() for m in BARE_V.finditer(line)}
    return out


def first(*vals):
    for v in vals:
        if v:
            return v.strip()
    return ""


def squash(s: str, n: int = 110) -> str:
    s = re.sub(r"\s+", " ", re.sub(r"[`*_]", "", s or "")).strip(" .-—")
    return s if len(s) <= n else s[: n - 1] + "…"


def walk():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP and not d.startswith(".")
                       and not d.startswith("data")]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            up = fn.upper()
            for k in KINDS:
                if up.startswith(k):
                    yield k, os.path.join(dirpath, fn)
                    break


def _class(name: str, head: str) -> str:
    """test | measurement | derived.

    Only a `test` needs a pre-registration. A `measurement` declares its
    thresholds frozen and simulates no strategy (fastbot Rule 1 -- measuring
    beats backtesting). A `derived` document restates or corrects others.
    """
    u = name.upper()
    if u in ("FINDINGS.MD", "CONCLUSION.MD") or any(
            k in u for k in ("CORRECTED", "AUDIT", "CONCLUSION", "ASSESSMENT")):
        return "derived"
    h = head.upper()
    if "MEASUREMENT ONLY" in h or "SIZING ONLY" in h or "NO STRATEGY" in h:
        return "measurement"
    return "test"


def slug_of(fn: str, kind: str) -> str:
    s = os.path.basename(fn)[:-3]
    s = s[len(kind):].lstrip("_- ").upper()
    return s or "(base)"


def topic_of(slug: str) -> str:
    base = re.sub(r"^V[\d.]+$", "", slug)          # fastbot's versioned preregs
    return ALIASES.get(slug, base or slug)


VERSION_ONLY = re.compile(r"^(V[\d.]+|\(base\))$")
TABLE_ROW = re.compile(r"^\|\s*v(\d+(?:\.\d+)?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")


def readme_results(preregs: list[dict]) -> list[dict]:
    """Results a project records as a table row in its README, not a file.

    silver15 reports v1-v7 in one table in README.md ("| v2 | cross-metal
    residual basket | rejected, all 9 pairs negative |"), so a scan that only
    reads RESULT_*/FINDINGS_* files listed six finished tests as open. A row
    counts only if the SAME directory holds the pre-registration it names, so
    a stray "| v3 |" in some other table cannot close anything.
    """
    have = {(r["project"], r["slug"]) for r in preregs}
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP and not d.startswith(".")
                       and not d.startswith("data")]
        if "README.md" not in filenames:
            continue
        path = os.path.join(dirpath, "README.md")
        proj = os.path.relpath(dirpath, ROOT)
        for line in open(path, encoding="utf-8", errors="replace"):
            m = TABLE_ROW.match(line)
            if not m:
                continue
            v, subject, verdict = m.groups()
            slug = f"V{v}".upper()
            if (proj, slug) not in have and v == "1" and (proj, "(base)") in have:
                slug = "(base)"                  # PREREGISTRATION.md is v1
            if (proj, slug) not in have:
                continue
            out.append(dict(
                project=proj, kind="RESULT", slug=slug, topic=topic_of(slug),
                date="", verdict=squash(verdict), status="", spec="",
                refs=slug, cls="test",
                lead=squash(f"README table: {subject}", 70),
                file=os.path.relpath(path, ROOT),
                mtime=datetime.fromtimestamp(os.path.getmtime(path),
                                             timezone.utc).strftime("%Y-%m-%d"),
            ))
    return out


def scan() -> list[dict]:
    rows = []
    for kind, path in walk():
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        head = text[:2500]
        slug = slug_of(path, kind)
        m = DATE_RE.search(head) or DATE_PROSE.search(head) \
            or DATE_RE.search(text) or DATE_PROSE.search(text)
        vm = VERDICT_LINE.search(head) or VERDICT_BOLD.search(text) \
            or VERDICT_LINE.search(text)
        sm = SPEC_RE.search(head)
        rows.append(dict(
            project=os.path.relpath(os.path.dirname(path), ROOT),
            kind=kind,
            slug=slug,
            topic=topic_of(slug),
            date=m.group(1) if m else "",
            verdict=squash(vm.group(1)) if vm else "",
            status=squash(STATUS_RE.search(head).group(1)) if STATUS_RE.search(head) else "",
            spec=squash(sm.group(1), 60) if sm else "",
            refs="|".join(sorted(_refs(text))),
            cls=_class(os.path.basename(path), head),
            lead=squash(first(*(l for l in head.splitlines()
                                if re.match(r"\s*(METHOD|SPEC|SUBJECT)\s*:", l, re.I))), 70),
            file=os.path.relpath(path, ROOT),
            mtime=datetime.fromtimestamp(os.path.getmtime(path),
                                         timezone.utc).strftime("%Y-%m-%d"),
        ))
    rows += readme_results([r for r in rows if r["kind"] == "PREREGISTRATION"])
    rows.sort(key=lambda r: (r["project"], r["topic"], r["kind"], r["slug"]))
    return rows


def audit(rows: list[dict]) -> dict:
    """Link results to pre-registrations.

    fastbot names its spec in a METHOD:, SPEC: or VERDICT: line and versions its
    pre-registrations (v10, v25); pineport matches on slug (KALMAN <-> KALMAN);
    silver15 has one FINDINGS.md covering seven. All three have to resolve, so
    the link is taken from ANY PREREGISTRATION reference anywhere in the result,
    plus the slug and topic fallbacks. An amendment claims its base too --
    v10.1 is a result for v10.
    """
    preregs = [r for r in rows if r["kind"] == "PREREGISTRATION"]
    results = [r for r in rows if r["kind"] != "PREREGISTRATION"]

    def variants(ref: str) -> set:
        v = {ref}
        if "." in ref:
            v.add(ref.split(".")[0])          # V10.1 -> V10
        return v

    claimed, links = set(), {}
    for r in results:
        got = set()
        for ref in (r["refs"].split("|") if r["refs"] else []):
            got |= variants(ref)
        got |= {r["slug"]}
        for g in got:
            claimed.add((r["project"], g))
        links[r["file"]] = got

    prereg_keys = {(p["project"], p["slug"]) for p in preregs}

    def is_claimed(p) -> bool:
        if (p["project"], p["slug"]) in claimed:
            return True
        base = p["slug"].split(".")[0]           # V24.1 -> V24
        return base != p["slug"] and (p["project"], base) in claimed

    open_tests = [p for p in preregs if not is_claimed(p)]

    unlinked = []
    for r in results:
        hit = any((r["project"], g) in prereg_keys for g in links[r["file"]])
        if not hit:
            hit = any(p["project"] == r["project"] and p["topic"] == r["topic"]
                      for p in preregs)
        if not hit and r["cls"] == "test":
            unlinked.append(r)

    by_topic: dict[str, list] = {}
    for r in results:
        if r["verdict"]:
            by_topic.setdefault(r["topic"], []).append(r)
    # A version number is not a subject: fastbot's v2 and silver15's v2 are
    # unrelated tests, so version-only topics never count as a cross-project split.
    splits = {t: v for t, v in by_topic.items()
              if not VERSION_ONLY.match(t)
              and len({x["project"].split("/")[0] for x in v}) > 1}
    return dict(open_tests=open_tests, orphans=unlinked, splits=splits,
                n_prereg=len(preregs), n_result=len(results))


def render(rows: list[dict], a: dict) -> str:
    out = [
        "# REGISTRY — every pre-registered test, every project",
        "",
        f"Generated by `registry.py` on {datetime.now(timezone.utc):%Y-%m-%d}. "
        "**Do not edit by hand** — re-run the script.",
        "",
        f"    pre-registrations  {a['n_prereg']}",
        f"    results/findings   {a['n_result']}",
        f"    open (no result)   {len(a['open_tests'])}",
        f"    unlinked results   {len(a['orphans'])}",
        f"    split topics       {len(a['splits'])}",
        "",
    ]
    if a["splits"]:
        out += ["## Topics investigated in more than one project", "",
                "Read both before citing either — these are where a "
                "programme-level summary goes wrong.", ""]
        for t, v in sorted(a["splits"].items()):
            out.append(f"**{t}**")
            for r in sorted(v, key=lambda x: x["project"]):
                out.append(f"- `{r['project']}` — {r['verdict'] or '(no verdict line)'}  "
                           f"[{r['file']}]({r['file']})")
            out.append("")
    if a["open_tests"]:
        out += ["## Open — pre-registered, no result yet", ""]
        for p in a["open_tests"]:
            out.append(f"- `{p['project']}` **{p['slug']}** "
                       f"{p['date'] or p['mtime']} {p['status']} [{p['file']}]({p['file']})")
        out.append("")
    if a["orphans"]:
        out += ["## Results not linked to a pre-registration", "",
                "Some are declared measurements rather than backtests (fastbot Rule 1), "
                "which is a different category — the lead line says which. "
                "Anything here that is a backtest wants checking.", ""]
        for r in a["orphans"]:
            out.append(f"- `{r['project']}` **{r['slug']}** — {r['lead'] or '(no method line)'} "
                       f"[{r['file']}]({r['file']})")
        out.append("")

    out += ["## Full record", "",
            "| project | kind | slug | date | verdict | file |",
            "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['project']} | {r['kind'][:6]} | {r['slug']} | "
                   f"{r['date'] or r['mtime']} | {r['verdict']} | "
                   f"[{os.path.basename(r['file'])}]({r['file']}) |")
    return "\n".join(out) + "\n"


def self_test() -> int:
    ok = True
    def check(name, cond, extra=""):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name} {extra}")
        ok = ok and bool(cond)
    check("slug strips the kind prefix", slug_of("x/FINDINGS_KALMAN.md", "FINDINGS") == "KALMAN")
    check("versioned prereg keeps its slug", slug_of("x/PREREGISTRATION_v25.1.md", "PREREGISTRATION") == "V25.1")
    check("alias collapses pattern work", topic_of("WEDGE") == topic_of("ZOO") == "PATTERNS")
    check("fenced VERDICT parses",
          VERDICT_LINE.search("```\nRUN: 2026-09-03\nVERDICT:  FAIL  (Gate E)\n```").group(1).startswith("FAIL"))
    check("bold verdict parses",
          bool(VERDICT_BOLD.search("## Verdict\n\n**FAIL. Kill condition MET.**")))
    check("date from prose", DATE_PROSE.search("Run 2026-09-19 against").group(1) == "2026-09-19")
    check("spec ref extracted", PREREG_REF.findall("PREREGISTRATION_v10.1, frozen") == ["v10.1"])
    check("data dirs are skipped", "data" in SKIP)
    m = TABLE_ROW.match("| v2 | cross-metal residual basket | rejected, all 9 pairs negative |")
    check("README table row parses", bool(m) and m.group(1) == "2" and m.group(3).startswith("rejected"))
    check("unnumbered table row ignored", TABLE_ROW.match("| — | crypto funding | closed below cash |") is None)
    check("version slugs are not topics", bool(VERSION_ONLY.match("V3")) and not VERSION_ONLY.match("VRP"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", action="store_true", help="exit non-zero on findings")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        sys.exit(self_test())

    rows = scan()
    a = audit(rows)
    with open(os.path.join(ROOT, "REGISTRY.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    open(os.path.join(ROOT, "REGISTRY.md"), "w").write(render(rows, a))
    print(f"{a['n_prereg']} pre-registrations, {a['n_result']} results  ->  REGISTRY.md / REGISTRY.csv")
    print(f"  open {len(a['open_tests'])}   unlinked {len(a['orphans'])}   split topics {len(a['splits'])}")
    if args.audit and (a["orphans"] or a["splits"]):
        sys.exit(1)

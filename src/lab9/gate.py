"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item
from lab9.graders import GRADERS


def _loosened(current: dict, protected: dict) -> bool:
    """A removed bound or a weaker bound is a ratchet violation."""
    for key in ("min", "max", "max_increase"):
        if key not in protected:
            continue
        if key not in current:
            return True
        if key == "min" and current[key] < protected[key]:
            return True
        if key != "min" and current[key] > protected[key]:
            return True
    return bool(protected.get("no_significant_drop") and not current.get("no_significant_drop"))


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems: list[str] = []
    pm, bm = pr.get("manifest", {}), base.get("manifest", {})
    for name, report in (("PR", pr), ("baseline", base)):
        manifest = report.get("manifest", {})
        rows = report.get("rows", [])
        seeds = manifest.get("seeds", [])
        if not isinstance(rows, list) or not isinstance(seeds, list) or not isinstance(manifest.get("items"), int):
            problems.append(f"{name}: malformed rows or manifest")
            continue
        if len(seeds) != len(set(seeds)) or len(rows) != manifest["items"] * len(seeds):
            problems.append(f"{name}: row count or seed list differs from manifest")
        pairs = [(r.get("item_id"), r.get("seed")) for r in rows]
        if len(pairs) != len(set(pairs)):
            problems.append(f"{name}: duplicate item/seed rows")
        if len({r.get("item_id") for r in rows}) != manifest["items"]:
            problems.append(f"{name}: item count differs from manifest")
        if any(r.get("seed") not in seeds for r in rows):
            problems.append(f"{name}: row has unlisted seed")
        if report.get("evaluator_failures"):
            problems.append(f"{name}: evaluator failures present")
        for metric, value in report.get("metrics", {}).items():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                problems.append(f"{name}: {metric} is missing or non-finite")
        graded = [m["id"] for m in spec["metrics"] if m["id"] in GRADERS]
        for row in rows:
            for mid in graded:
                if type(row.get(mid)) is not bool:
                    problems.append(f"{name}: {row.get('item_id')}@{row.get('seed')} has invalid {mid}")
                    break
            if "cost_per_success" in report.get("metrics", {}) and (
                not isinstance(row.get("cost"), (int, float))
                or not math.isfinite(row["cost"]) or row["cost"] < 0
            ):
                problems.append(f"{name}: row cost invalid")
        # The summary must be derived from exactly these rows, not typed over by hand.
        if rows and not any(f"{name}:" in p for p in problems):
            recomputed = aggregate([{**row, "cost": row.get("cost", 0)} for row in rows],
                                   graded, k_values=spec.get("pass_k", []))
            reported = report.get("metrics", {})
            required = {m["id"] for m in spec["metrics"]}
            for mid, value in recomputed.items():
                if mid not in reported and mid not in required:
                    continue
                actual = reported.get(mid)
                if actual is None or (value is None) != (actual is None) or (
                    value is not None and abs(value - actual) > 1e-6
                ):
                    problems.append(f"{name}: summary {mid} disagrees with rows")
    if pm.get("items") != bm.get("items") or pm.get("seeds") != bm.get("seeds"):
        problems.append("PR manifest item count or seeds differ from baseline")
    pr_rows = {(r.get("item_id"), r.get("seed")): r for r in pr.get("rows", [])}
    base_rows = {(r.get("item_id"), r.get("seed")): r for r in base.get("rows", [])}
    if set(pr_rows) != set(base_rows):
        problems.append("PR item/seed set differs from baseline")
    for pair in set(pr_rows) & set(base_rows):
        if pr_rows[pair].get("slices", []) != base_rows[pair].get("slices", []):
            problems.append(f"{pair}: slice tags differ from baseline")
    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        old_metrics = {m["id"]: m for m in base_spec.get("metrics", [])}
        new_metrics = {m["id"]: m for m in spec.get("metrics", [])}
        for mid, old in old_metrics.items():
            new = new_metrics.get(mid)
            if new is None or (old.get("blocking") and not new.get("blocking")) or (
                new is not None and _loosened(new.get("threshold", {}), old.get("threshold", {}))
            ):
                problems.append(f"ratchet: metric {mid} loosened or removed")
        old_slices = {s["name"]: s for s in base_spec.get("slices", [])}
        new_slices = {s["name"]: s for s in spec.get("slices", [])}
        for name, old in old_slices.items():
            new = new_slices.get(name)
            if new is None or new.get("metric") != old.get("metric") or (
                old.get("blocking") and not new.get("blocking")
            ) or _loosened(new, old):
                problems.append(f"ratchet: slice {name} loosened or removed")
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for slice_spec in spec.get("slices", []):
        name, metric = slice_spec["name"], slice_spec["metric"]
        sid = f"slice:{name}/{metric}"
        current = per_item(pr, metric, slice_name=name)
        previous = per_item(base, metric, slice_name=name)
        keys = sorted(set(current) & set(previous))
        if not keys or set(current) != set(previous):
            failed, value, note = True, None, "missing or mismatched slice items"
        else:
            value = sum(current[k] for k in keys) / len(keys)
            failed = "min" in slice_spec and value < slice_spec["min"]
            note = f"n={len(keys)}"
            if slice_spec.get("no_significant_drop"):
                diff, lo, hi = stats.paired_bootstrap(
                    [current[k] for k in keys], [previous[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027)
                )
                note += f" Δ {diff:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                failed |= hi < 0
        if failed and slice_spec.get("blocking"):
            blocked.append(sid)
        lines.append(f"  {sid:<36} {value!s:<8} min={slice_spec.get('min')} {note} "
                     f"{'BLOCK' if failed and slice_spec.get('blocking') else 'warn' if failed else 'ok'}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

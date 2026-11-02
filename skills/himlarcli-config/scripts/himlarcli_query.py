#!/usr/bin/env python3
"""Query static/declared NREC cloud config from the himlarcli repo (config/ YAML).

Read-only. Resolves the repo root from its own location (repo/skills/himlarcli-config/scripts/),
so it works from any clone location and any agent harness. Does NOT read config.ini
(credentials) and does NOT contact the cloud — dynamic queries belong to himlarcli itself.

Requires: python3 + PyYAML.
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit(
        "ERROR: PyYAML is required. Run inside the himlarcli virtualenv "
        "(source bin/activate) or: pip install pyyaml"
    )

REPO = Path(__file__).resolve().parents[3]
CFG = REPO / "config"


def emit(data, as_json):
    if as_json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(yaml.safe_dump(data, sort_keys=False, default_flow_style=False, width=120))


def load(path):
    try:
        with open(path) as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        return {"__parse_error__": str(exc)}


def regions():
    """Known regions: compute_resources.yaml keys + config/nodes file stems, minus 'default'."""
    regs = set(load(CFG / "compute_resources.yaml").keys())
    regs |= {p.stem for p in (CFG / "nodes").glob("*.yaml")}
    return sorted(regs - {"default", "__parse_error__"})


def walk_scalars(data, path=""):
    if isinstance(data, dict):
        for k, v in data.items():
            yield from walk_scalars(v, f"{path}/{k}" if path else str(k))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            yield from walk_scalars(v, f"{path}[{i}]")
    else:
        yield path, str(data)


def parse_flavors():
    """Return {family: {"base": data, "overrides": {region: data}}} for config/flavors/*.yaml."""
    regs = regions()
    out = {}
    for f in sorted((CFG / "flavors").glob("*.yaml")):
        stem = f.stem
        fam, region = stem, None
        for r in sorted(regs, key=len, reverse=True):
            if stem.endswith("-" + r) and (CFG / "flavors" / f"{stem[:-len(r)-1]}.yaml").is_file():
                fam, region = stem[: -len(r) - 1], r
                break
        entry = out.setdefault(fam, {"base": None, "overrides": {}})
        if region:
            entry["overrides"][region] = load(f)
        else:
            entry["base"] = load(f)
    return out


def flavor_key(data, fam):
    """The top-level hash key holding the sizes (not 'public'/'properties')."""
    if fam in data:
        return fam
    for k in data:
        if k not in ("public", "properties", "__parse_error__"):
            return k
    return fam


def merged_flavor(entry, region):
    """Merge base + region override the way flavor.py does; region=None uses base only."""
    base = entry["base"] or {}
    ov = entry["overrides"].get(region, {}) if region else {}
    fam_key = flavor_key(base or ov, next(
        (k for k in (base or ov) if k not in ("public", "properties", "__parse_error__")), ""))
    props = dict(base.get("properties") or {})
    props.update(ov.get("properties") or {})
    sizes = dict(base.get(fam_key) or {})
    sizes.update(ov.get(fam_key) or {})
    if entry["base"] and entry["overrides"]:
        scope = f"all regions; overridden in: {', '.join(sorted(entry['overrides']))}"
    elif entry["base"]:
        scope = "all regions"
    else:
        scope = f"region-only: {', '.join(sorted(entry['overrides']))}"
    return {
        "name": fam_key,
        "scope": scope,
        "public": ov.get("public", base.get("public", False)),
        "properties": props,
        "sizes": sizes,
    }


def cmd_regions(args):
    emit({"regions": regions()}, args.json)


def cmd_flavors(args):
    fams = parse_flavors()
    out = []
    for fam, entry in sorted(fams.items()):
        if args.match and not re.search(args.match, fam, re.I):
            continue
        regs = [args.region] if args.region else (
            [""] + sorted(entry["overrides"]))  # "" = base scope, then each override
        for r in regs:
            m = merged_flavor(entry, r or None)
            sizes = {name: f"{s.get('vcpus')}vcpu/{s.get('ram')}MB/{s.get('disk')}GB"
                     for name, s in m["sizes"].items()}
            key_props = {k: v for k, v in m["properties"].items()
                         if k.startswith(("trait:", "resources:", "mdev")) or "aggregate" in k}
            out.append({"flavor": fam, "region": r or "all", "public": m["public"],
                        "sizes": sizes, "scheduler_props": key_props})
    emit(out, args.json)


def cmd_flavor(args):
    fams = parse_flavors()
    entry = fams.get(args.name)
    if not entry:
        sys.exit(f"ERROR: flavor family '{args.name}' not found. Try: flavors --match {args.name[:4]}")
    regs = [args.region] if args.region else ([""] + sorted(entry["overrides"]))
    emit([merged_flavor(entry, r or None) for r in regs], args.json)


def cmd_images(args):
    out = {}
    for f in sorted((CFG / "images").glob("*.yaml")):
        data = load(f)
        itype = data.get("type", f.stem)
        if args.type and args.type != itype:
            continue
        rows = []
        for key, img in (data.get("images") or {}).items():
            if args.name and not re.search(args.name, str(key), re.I):
                continue
            rows.append({"key": key, "name": img.get("name"), "latest": img.get("latest"),
                         "deprecated": img.get("depricated"),  # spelling is in the config itself
                         "visibility": img.get("visibility"), "owner": img.get("owner")})
        if rows:
            out[itype] = rows
    emit(out, args.json)


def cmd_golden_images(args):
    emit(load(CFG / "golden_images.yaml"), args.json)


def cmd_quotas(args):
    files = [CFG / "quotas" / f"{args.template}.yaml"] if args.template \
        else sorted((CFG / "quotas").glob("*.yaml"))
    out = {f.stem: load(f) for f in files if f.is_file()}
    if not out:
        sys.exit("ERROR: no quota templates found under config/quotas/")
    emit(out, args.json)


def cmd_quota_types(args):
    emit({"project_quota": load(CFG / "quota.yaml"), "project_types": load(CFG / "type.yaml")},
         args.json)


def cmd_nodes(args):
    regs = [args.region] if args.region else regions()
    out = {}
    for r in regs:
        f = CFG / "nodes" / f"{r}.yaml"
        if not f.is_file():
            continue
        rows = []
        for name, spec in (load(f).get("nodes") or {}).items():
            if args.name and not re.search(args.name, name, re.I):
                continue
            rows.append({"name": name, "compute_profile": spec.get("compute_profile"),
                         "compute_resource": spec.get("compute_resource"),
                         "hostgroup": spec.get("hostgroup"), "environment": spec.get("environment")})
        out[r] = rows
    emit(out, args.json)


def cmd_search(args):
    pat = re.compile(args.pattern, re.I)
    hits = []
    for f in sorted(CFG.rglob("*.yaml")):
        data = load(f)
        for key, val in walk_scalars(data):
            if pat.search(key) or pat.search(val):
                hits.append({"file": str(f.relative_to(REPO)), "key": key, "value": val[:100]})
                if len(hits) >= args.limit:
                    break
        if len(hits) >= args.limit:
            break
    emit({"pattern": args.pattern, "count": len(hits), "hits": hits}, args.json)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", help="override repo root (default: derived from script location)")
    ap.add_argument("--json", action="store_true", help="machine-readable JSON output")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("regions", help="known regions")
    p = sub.add_parser("flavors", help="flavor summary per family/region")
    p.add_argument("--region"); p.add_argument("--match", help="regex on flavor name")
    p = sub.add_parser("flavor", help="full merged flavor definition")
    p.add_argument("name"); p.add_argument("--region")
    p = sub.add_parser("images", help="declared image sets by type")
    p.add_argument("--type"); p.add_argument("--name", help="regex on image key")
    sub.add_parser("golden-images", help="golden_images.yaml")
    p = sub.add_parser("quotas", help="quota templates (config/quotas)")
    p.add_argument("--template")
    sub.add_parser("quota-types", help="project quota tiers + valid project types")
    p = sub.add_parser("nodes", help="per-region foreman host mapping")
    p.add_argument("--region"); p.add_argument("--name", help="regex on node name")
    p = sub.add_parser("search", help="regex over all config YAML keys+values")
    p.add_argument("pattern"); p.add_argument("--limit", type=int, default=50)

    args = ap.parse_args()
    if args.repo:
        global REPO, CFG
        REPO = Path(args.repo).resolve()
        CFG = REPO / "config"
    if not CFG.is_dir():
        sys.exit(f"ERROR: no config/ under {REPO}. Run from inside a himlarcli clone "
                 "or pass --repo /path/to/himlarcli")
    {"regions": cmd_regions, "flavors": cmd_flavors, "flavor": cmd_flavor, "images": cmd_images,
     "golden-images": cmd_golden_images, "quotas": cmd_quotas, "quota-types": cmd_quota_types,
     "nodes": cmd_nodes, "search": cmd_search}[args.cmd](args)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:  # output piped through head/less by a harness
        sys.exit(0)

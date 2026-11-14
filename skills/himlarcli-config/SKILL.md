---
name: himlarcli-config
description: Query static/declared NREC cloud config from the himlarcli repo - flavor definitions and sizes per region, image sets, quota templates, project quota tiers and types, foreman node mappings, regions list, and config search. Read-only, no cloud access, no config.ini. Use when asked what flavors/images/quotas are DEFINED (not what is running).
compatibility: Requires python3 with PyYAML (the himlarcli venv has it: source bin/activate). No network, no credentials. Repo root is resolved from the script location; pass --repo to override.
license: Apache-2.0
metadata:
  author: NREC
  version: "1.0"
---

# himlarcli config

Answer questions about the *declared* config in himlarcli's `config/` YAML.
This is the static half of himlarcli; dynamic state (live flavors, usage,
hypervisors) still requires the real scripts (`flavor.py list` etc.) against
the cloud.

All queries go through one script (run from anywhere):

```bash
python3 skills/himlarcli-config/scripts/himlarcli_query.py <subcommand> [options]
```

Add `--json` for machine-readable output; `--repo PATH` to point at another clone.

## Subcommands

- `regions` — known regions (from compute_resources.yaml + config/nodes)
- `flavors [--region R] [--match REGEX]` — every flavor family: scope
  (all-regions vs region-only, which regions override), sizes
  (vcpus/ram/disk), and scheduler-relevant properties (trait:, resources:,
  aggregate_instance_extra_specs:)
- `flavor <family> [--region R]` — full merged definition; base and region
  files are merged properties-wise and sizes-wise, region file wins — same
  rule flavor.py applies
- `images [--type T] [--name REGEX]` — declared image sets (cirros, uio, uib,
  vgpu, windows, retired*); shows deprecated/visibility/owner per image
- `golden-images` — golden_images.yaml (upstream image sources)
- `quotas [--template T]` — quota templates from config/quotas
  (default/small/medium/large/vgpu/vgpu_l40s/...)
- `quota-types` — project quota tiers (quota.yaml) + valid project types (type.yaml)
- `nodes [--region R] [--name REGEX]` — foreman host mapping: profile,
  compute_resource (hypervisor host), hostgroup, environment per control node
- `search <REGEX>` — regex over all config YAML keys and values; escape hatch

## Examples

```bash
Q=skills/himlarcli-config/scripts/himlarcli_query.py
python3 $Q flavors --region osl --match L40S     # L40S flavors in osl + traits
python3 $Q flavor shpc.c1a --region bgo          # exact sizes/props declared
python3 $Q quotas --template vgpu_l40s           # what quota a vGPU project gets
python3 $Q images --type vgpu                    # vGPU-compatible image set
python3 $Q nodes --region osl --name identity    # where does identity-01 run?
python3 $Q search 'CUSTOM_NREC_VGPU_L40S_24G'    # every config mentioning a trait
```

## Interpretation notes

- A flavor defined without a region suffix exists in ALL regions; region-suffixed
  files exist ONLY in that region (config/flavors/README.md).
- `depricated` is the actual key spelling in the image configs — keep it when grepping.
- Neutron quotas in templates are set via puppet (himlar repo), not pushable
  here; see himlar's common/modules/neutron.yaml.

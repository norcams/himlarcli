# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`himlarcli` is the command-line toolset for operating the Himlar / NREC OpenStack cloud. Each executable `*.py` at the repo root is a standalone admin command (e.g. `flavor.py`, `project.py`, `hypervisor.py`, `security_group.py`). The `himlarcli/` package holds the reusable library (OpenStack service wrappers, argument parsing, output formatting). YAML under `config/` drives both the CLI definitions and the cloud resource definitions.

## Environment & commands

Scripts refuse to run outside a virtualenv (`himlarcli/tests.py:is_virtual_env()` is imported early and calls `sys.exit(1)`), so **always activate first**:

```bash
source bin/activate            # from repo root; virtualenv lives in the repo
./flavor.py -h                 # every script supports -h and subcommand -h
./flavor.py list --region osl
```

- Python 3.11 (tested on el8/el9/Ubuntu 22.04). System deps for `python-ldap`: `openldap-devel`/`python3.11-devel` (el9) or `libldap-dev libsasl2-dev build-essential` (Ubuntu).
- Install: `pip install -r requirements.txt`.
- **Lint / tests** (this is the full CI check — there is no unit-test suite):
  ```bash
  ./test.sh                     # runs: pylint -E on every root *.py except setup.py
  pylint <script>.py            # check a single file; .pylintrc is authoritative
  ```
  Suppress false positives with `# pylint: disable=<message>` at line or block level.
- Config discovery: scripts take `-c <config.ini>`. Without it they look for `config.ini` in the repo root, then `/etc/himlarcli/config.ini`. See `config.ini.example` for required sections (`[openstack]`, `[foreman]`, `[ldap]`, `[state]`, etc.). A `config.ini` in the repo root is picked up automatically.

## Architecture

**Service client layer** (`himlarcli/*.py`). `himlarcli/client.py` defines the abstract `Client` base: it loads `config.ini`, builds a Keystone v3 auth session, sets up logging, and holds `dry_run`. Every OpenStack service wrapper subclasses it — `Keystone`, `Nova`, `Cinder`, `Neutron`, `Glance`, `Designate`, `Placement`, `Gnocchi` — plus non-OpenStack integrations (`Foreman`, `LdapClient`, `Sensu`/`SensuGo`, `MQClient`, `Slack`/`Slack2`, `Twitter`, `StatsdClient`, `Mail`, `State`/`GlobalState`). Subclasses implement `get_client()` returning the underlying SDK client.

- **Region awareness**: a client sets `USE_REGION = True` (e.g. `Nova`) when its resources are per-region. `Client._get_client()` and `utils.get_client()` propagate the region only to such clients. Commands that span regions loop over `kc.find_regions()` / `utils.get_regions()` and build a fresh client per region.
- **Dry-run**: `set_dry_run(True)` is threaded through from the `--dry-run` flag; write operations check `self.dry_run` and log via `log_dry_run()` instead of mutating.

**Argument parsing** (`himlarcli/parser.py`). Root scripts do `parser = Parser()` with no args; `Parser` infers the script name and **autoloads `config/parser/<script>.yaml`**, which declares `desc`, `actions` (subcommands), and `opt_args`. So to add or change a command's flags/subcommands you usually edit the YAML, not the Python. Key `opt_args` fields: `sub` (limit an arg to specific subcommands), `dest`, `default`, `weight` (ordering), `action`. `-c`, `--debug`, `--dry-run`, `--format` are added automatically. (`utils.py` also contains an older `get_*_options()` argparse style used by a few legacy scripts — prefer `Parser` for new work.)

**Action dispatch pattern.** Root scripts define `action_<name>()` functions and dispatch with:
```python
action = locals().get('action_' + options.action.replace('-', '_'))
```
A subcommand named `list-access` maps to `action_list_access()`. This is the consistent shape across nearly all commands — mirror it when adding scripts.

**Output** (`himlarcli/printer.py`). Instantiate `Printer(options.format)` and emit via `output_dict()` / `output_msg()` / `output_list_dicts()`. Supported `--format` values: `text`, `table`, `json`, `csv`. Do not `print()` structured results directly — go through `Printer` so all formats work.

**Config & helpers** (`himlarcli/utils.py`, imported as `himutils`). Central helpers: `load_config()` (YAML), `load_region_config()` (region-specific file with fallback to a default), `get_abs_path()` (resolves relative paths against `$VIRTUAL_ENV` or `/opt/himlarcli`), `get_client()`, `get_regions()`, `confirm_action()` (yes/no prompt — use before destructive ops), and the colored `info/warning/error/fatal` message helpers.

**Resource config** (`config/`). YAML definitions the commands read/apply: `flavors/` (one file per flavor class, with `-<region>` overrides, e.g. `m1.yaml` vs `m1a-osl.yaml`), `quotas/`, `security_group/`, `nodes/`, `images/`, `sensu/`, `checks/`, plus `compute_profiles.yaml`, `compute_resources.yaml`, `golden_images.yaml`. Region-specific files override the default via the `load_region_config` / `flavor.py:get_flavor_config` fallback convention.

**Automation** (`bin/`). Shell wrappers that invoke the Python commands non-interactively for cron (enddate handling, image updates, stats, expired-demo cleanup, etc.).

## Conventions

- Paths in code are relative to the repo root and resolved with `utils.get_abs_path()`; deployed installs live at `/opt/himlarcli`, so avoid hardcoding absolute paths — a few existing scripts hardcode `/opt/himlarcli/...` (e.g. `flavor.py:action_available_flavors`), which only works when deployed.
- Destructive actions gate on `himutils.confirm_action()` and honor `--dry-run`.
- Logging config is in `logging.yaml`; `--debug` adds a verbose console handler on top of the file log.

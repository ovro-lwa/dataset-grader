# Dataset grader

Collaborative web app for grading datasets by **day**, **LST**, and **frequency**. Each reviewer signs in from a configured name list, assigns `pass`, `fail`, or `retry` per cell, and sees a consensus grid with hover details for all reviewers.

## Quick start

```bash
cd /Users/claw/code/dataset-grader
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

export GRADER_MANIFEST="$(pwd)/example/manifest.csv"
./scripts/serve.sh
```

If `GRADER_MANIFEST` is unset, the app uses `example/manifest.csv` when that file exists.

**Open the app at** `http://127.0.0.1:8765/app` (not the site root). The path `/app` comes from the filename `app.py`.

`scripts/serve.sh` binds port **8765** by default so it does not clash with other Panel apps that often use port 5006 (for example the OVRO-LWA dashboard). If you see a 404 at `http://localhost:5006/app`, another service is probably already on 5006 — use 8765 or whatever URL `panel serve` prints when you start dataset-grader.

Manual serve (any port):

```bash
panel serve src/dataset_grader/app.py --port 8765 --autoreload --show
# then open http://127.0.0.1:8765/app
```

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `GRADER_DB_PATH` | `./data/grader.sqlite` | SQLite database file |
| `GRADER_MANIFEST` | (example manifest if present) | CSV catalog path |
| `GRADER_USERS_FILE` | `./config/users.json` | Reviewer names (JSON or text) |
| `GRADER_DATA_ROOT` | unset | Root for directory discovery |
| `GRADER_DISCOVERY` | `manifest` | `manifest` or `directory` |
| `GRADER_HOST` | `127.0.0.1` | Bind host for `panel serve` |
| `GRADER_PORT` | `8765` | Documented port for deploy scripts |

### Manifest CSV

Columns: `day` (`YYYY-MM-DD`), `lst` (`08h`), `frequency` (`74MHz` or numeric MHz).

See [example/manifest.csv](example/manifest.csv).

### Reviewer names

Edit [config/users.json](config/users.json) (or set `GRADER_USERS_FILE`) to list who may sign in. Formats:

- **JSON:** `["alice", "bob"]` or `{"users": ["alice", "bob"]}`
- **Text:** one name per line (`#` for comments)

The app shows a dropdown of these names; free-text names are not accepted.

### Catalog summary plot

The app shows a **Catalog summary** heatmap above the grading grids: cell color is the
number of datasets (subbands) for each day × LST pair. Hover a cell to see the
subband names (frequencies) available that day.

### Grading

Click a cell in your grid to cycle: **unset → pass → fail → retry → unset**. Choosing unset removes your grade for that cell from the database.

### Refresh catalog

**Refresh catalog** re-scans `GRADER_MANIFEST` (or `GRADER_DATA_ROOT` in directory mode) and inserts any new (day, LST, frequency) combinations into the database. It does **not** remove datasets that disappeared from the manifest, and it does **not** delete existing grades. Use it after you add rows to the manifest or new files under the data root.

### Exopipe phase2 auto-discovery (script)

Scan the lustre phase2 layout and write a manifest CSV:

```bash
python scripts/discover_exopipe_phase2.py \
  --root /lustre/pipeline/exopipe/phase2 \
  --output data/phase2_manifest.csv

export GRADER_MANIFEST="$(pwd)/data/phase2_manifest.csv"
./scripts/serve.sh
```

Path pattern: `{root}/??h/*/Science_*/??MHz`

| Segment | Meaning | Example |
|---------|---------|---------|
| `??h` | LST | `08h` |
| `*` | Day (`YYYY-MM-DD`) | `2025-01-11` |
| `Science_*` | Science run dir (presence marks cell) | `Science_20260527_173819` |
| `??MHz` | Frequency subband | `55MHz` |

Use `--dry-run` to print CSV to stdout without writing a file.

You can also set `GRADER_DISCOVERY=exopipe_phase2` (optional `GRADER_DATA_ROOT` overrides the default `/lustre/pipeline/exopipe/phase2`) so **Refresh catalog** scans lustre directly.

### Directory discovery

Set `GRADER_DISCOVERY=directory` and `GRADER_DATA_ROOT` to a tree:

```
{root}/{YYYY-MM-DD}/{LST}/{frequency}.*
```

Example: `data/2024-12-28/08h/74MHz.png`

## Consensus colors

| Condition | Color |
|-----------|-------|
| No grades | Grey |
| Any `fail` | Red |
| Any `retry` (no fail) | Orange |
| At least one grade, all `pass` | Green |

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## macOS service (optional)

Install a launchd agent that serves on a fixed local port:

```bash
# Optional hostname
echo "127.0.0.1 dataset-grader.local" | sudo tee -a /etc/hosts

cp deploy/com.claw.dataset-grader.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.claw.dataset-grader.plist
```

Access: `http://127.0.0.1:8765/` (or `http://dataset-grader.local:8765/` if you added the hosts entry).

Unload:

```bash
launchctl unload ~/Library/LaunchAgents/com.claw.dataset-grader.plist
```

## Security note

v1 has no authentication. Use only on trusted internal networks.

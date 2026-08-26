# Installing Plasma Column Neutralizer Simulation

For detailed installation instructions, see [docs/installation.md](docs/installation.md).

## Quickstart

```bash
# 1. Clone repository
git clone https://github.com/cspark7701/plasma-column.git
cd plasma-column

# 2. Run automated setup script
bash scripts/install.sh

# 3. Verify installation
pytest
python scripts/run_case.py --case cases/baseline_h2.yaml --dry_run
```

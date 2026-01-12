# FlowTask (Python)

A dependency-aware task manager you can run from the terminal.

**Why this project?** It touches multiple CS fundamentals:
- CLI design (argparse)
- Data modeling + persistence (SQLite)
- Graph algorithms (cycle detection + topological sorting)
- Testing + clean structure

## Install (local dev)

```bash
python -m venv .venv
# mac/linux:
source .venv/bin/activate
# windows:
# .venv\Scripts\activate

python -m pip install -U pip
python -m pip install -e ".[dev]"
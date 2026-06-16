#!/usr/bin/env sh
# Convenience launcher (macOS/Linux): run without installing — sets PYTHONPATH to bundled src.
# Usage: ./cost-audit.sh <repo-path> --plan max5x [more flags]   (or: sh cost-audit.sh ...)
# Install properly instead:  pip install .   then use the `cost-audit` command.
# Override the interpreter by setting COST_AUDIT_PY to a python path.
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT/src"
PY="${COST_AUDIT_PY:-}"
if [ -z "$PY" ]; then
  for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
  done
fi
if [ -z "$PY" ]; then
  echo "Python 3.10+ not found on PATH. Install it, set COST_AUDIT_PY, or: pip install . && cost-audit ..." >&2
  exit 1
fi
if ! "$PY" -c "import yaml" >/dev/null 2>&1; then
  echo "PyYAML is required but not installed. Run:  $PY -m pip install pyyaml" >&2
  exit 1
fi
exec "$PY" -m cost_audit.cli "$@"

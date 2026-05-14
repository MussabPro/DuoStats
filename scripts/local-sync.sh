#!/usr/bin/env bash
set -euo pipefail

if [[ -f .env ]]; then
	set -a
	# shellcheck disable=SC1091
	source .env
	set +a
fi

python3 main.py

mkdir -p web/data
cp data/duolingo-progress.json data/profile.json data/statistics.json web/data/

echo "Local sync complete."

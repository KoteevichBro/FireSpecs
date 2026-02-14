#!/bin/bash
cd "$(dirname "$(readlink -f "$0")")"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export PATH="$HOME/.local/bin:$PATH"
python3 firespecs.py

#!/usr/bin/env bash
cd "$(dirname "$0")/app"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip && pip install -q -r requirements.txt
python app.py

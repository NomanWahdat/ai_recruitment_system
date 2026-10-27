#!/usr/bin/env bash
set -euo pipefail
pip install -r requirements.txt -c requirements.lock.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

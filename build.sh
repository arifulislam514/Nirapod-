#!/usr/bin/env bash
# Render.com runs this script every time you deploy

set -o errexit  # stop if any command fails

pip install -r requirements.txt

python manage.py collectstatic --no-input

python manage.py migrate

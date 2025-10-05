#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate


if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput || true
fi

if [ -n "$LOAD_QUESTIONS_ON_DEPLOY" ]; then
  python manage.py load_questions data/questions.json --replace|| true
fi

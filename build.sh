#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate


if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput || true
fi

if [ -n "$LOAD_QUESTIONS_ON_DEPLOY" ]; then
  python manage.py load_questions data/questions.json || true
fi

if [ -n "$APPLY_CIVIL_RUBRIC" ]; then
  python manage.py apply_rubric --spec=civil --file=data/practice/rubrics/civil_v1.json --max=75 || true
fi

if [ -n "$APPLY_CRIMINAL_RUBRIC" ]; then
  python manage.py apply_rubric --spec=criminal --file=data/practice/rubrics/criminal_v1.json --max=75 || true
fi

if [ -n "$INGEST_DECISIONS_ON_DEPLOY" ]; then
  python manage.py ingest_decisions || true
fi

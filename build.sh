#!/usr/bin/env bash
set -o errexit
set -x 

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --noinput

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput
fi

echo "INFO: LOAD_QUESTIONS_ON_DEPLOY=${LOAD_QUESTIONS_ON_DEPLOY:-<unset>}"

if [ -n "$LOAD_QUESTIONS_ON_DEPLOY" ]; then
  echo "INFO: starting questions import..."

  python manage.py load_questions data/questions.json --replace --batch-size=1000

  echo "INFO: verifying questions count in DB..."
  python manage.py shell -c "from your_app.models import Question; from django.db import connection; print('DB:', connection.settings_dict['ENGINE'], connection.settings_dict['NAME']); print('Questions:', Question.objects.count())"
else
  echo "INFO: LOAD_QUESTIONS_ON_DEPLOY is not set → skipping import."
fi

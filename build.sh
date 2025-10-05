set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --noinput

# 1) Очищаємо БД від усіх даних (але не видаляємо структуру)
python manage.py flush --no-input

# 2) Пересоздаємо суперюзера (бо flush його видалив)
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput || true
fi

# 3) Заливка питань із JSON
python manage.py load_questions data/questions.json

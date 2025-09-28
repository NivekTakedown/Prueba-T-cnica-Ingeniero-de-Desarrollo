FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=rios_desierto_sac.settings

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
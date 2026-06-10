# NIFTY100-AI

Django dashboard for browsing Nifty 100 companies, sectors, financial facts, and AI-style health score summaries.

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver 127.0.0.1:8000
```

Open `http://127.0.0.1:8000/`.

## Hosting Checklist

Set environment variables from `.env.example` on the hosting platform before starting the app.

Required production variables:

```text
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<long-random-secret>
DJANGO_ALLOWED_HOSTS=<your-domain>
DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-domain>
```

Run these release commands:

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

Start command:

```bash
gunicorn nifty_intel.wsgi:application
```

For MySQL hosting, set `DATABASE_ENGINE=mysql` and fill the `MYSQL_*` variables from `.env.example`.

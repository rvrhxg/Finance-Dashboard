FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && useradd --create-home --uid 1000 ledger
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
COPY public ./public
USER ledger
EXPOSE 8002
HEALTHCHECK --interval=20s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/api/ready',timeout=3)"
CMD ["uvicorn", "app.main:create_app", "--factory", "--no-access-log", "--host", "0.0.0.0", "--port", "8002"]

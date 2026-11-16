# Ledger — Finance Dashboard

Самостоятельный Python-проект портфолио: учёт доходов и расходов, категории, импорт CSV и аналитика. Планируемый стек FastAPI, SQLAlchemy, PostgreSQL, pandas, pytest; JavaScript-интерфейс. Платные банковские интеграции не используются.

Реализованы FastAPI REST API, SQLAlchemy, авторизация, операции и категории, месячные бюджеты, pandas-аналитика, атомарный CSV-импорт и адаптивный JavaScript-интерфейс. Деньги хранятся целыми копейками, API принимает десятичные суммы строками. Данные аккаунтов изолированы.

## Локальный запуск

Python 3.14, отдельное окружение, `pip install -r requirements.lock`.

```sh
python -m app.seed --email demo@example.test
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8002
```

Откройте http://localhost:8002. Пароль демо-аккаунта вводится через getpass; все 66 операций вымышленные. Существующий аккаунт скрипт не изменяет. Можно зарегистрировать новый аккаунт без демоданных.

## Docker и PostgreSQL

Создайте `.env` с POSTGRES_PASSWORD и случайным паролем из букв/цифр; файл исключён из Git. `docker compose up --build -d`, затем `docker compose exec dashboard python -m app.seed --email demo@example.test`. PostgreSQL хранится в именованном томе, панель доступна только на localhost:8002. Для HTTPS нужны TLS proxy, ENVIRONMENT=production и точный APP_ORIGIN.

## Возможности и проверки

Доходы/расходы, разница периода, доля сбережений, графики по месяцам и категориям, операции с удалением, лимиты расходов и CSV-импорт. CSV: external_id,date,kind,category,amount,note; одинаковые повторы пропускаются, конфликтующие ID отклоняются, ошибочный импорт откатывается целиком.

`pytest -q`: семь тестов домена, pandas, CSV, HTTP-прав и демоданных. [CI 43872604052](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43872604052) подтвердил тесты, Docker build/runtime с PostgreSQL, сохранение операции и аналитики после перезапуска, Chromium вход/операцию/импорт/бюджет. Desktop и mobile 390 px проверены визуально после исправления переполнения.

## Ограничения

Сервис не предоставляет инвестиционных рекомендаций и не является банковским продуктом. Только RUB, без банковских подключений и конвертации. Разница периода — не банковский остаток. До 500 последних операций в списке, аналитика читает весь выбранный период в память. Нет миграций, восстановления пароля и общего распределённого limiter. Портфолио v1 не означает production-готовность.

[Архитектура](docs/ARCHITECTURE.md) · [REST API](docs/API.md).

## Скриншоты

![Ledger desktop](docs/screenshots/dashboard-desktop.png)

[Мобильный экран 390 px](docs/screenshots/dashboard-mobile.png) · [Фактические проверки](docs/ACCEPTANCE.md)

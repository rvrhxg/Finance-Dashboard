# REST API

Swagger /docs, схема /openapi.json. Изменяющие запросы требуют JSON и Origin=APP_ORIGIN (локально http://localhost:8002), даже DELETE без тела. Cookie session: HttpOnly/SameSite=Strict, Secure в production. Тело до 256KiB, CSV до 200KB и 1000 строк.

| Метод | Путь | Назначение |
|---|---|---|
| POST | /api/auth/register | email, password, name |
| POST | /api/auth/login | email, password |
| POST | /api/auth/logout | Отзыв сессии |
| GET | /api/auth/me | Профиль |
| GET/POST | /api/categories | Создание: name, kind income/expense |
| GET/POST | /api/transactions | Создание: category_id, occurred_on YYYY-MM-DD, amount строкой, note? |
| DELETE | /api/transactions/:id | Удаление своей операции |
| GET | /api/analytics?start=YYYY-MM-DD&end=YYYY-MM-DD | Итоги, monthly, categories, count |
| POST | /api/import | content: CSV текст |
| GET/POST | /api/budgets | Установка: category_id, month YYYY-MM, amount строкой |
| GET | /api/health | HTTP liveness |

CSV: external_id,date,kind,category,amount,note. Повтор совпадающего ID возвращает skipped; другой payload — ошибка. Только свои категории/операции/бюджеты. Суммы ответа указаны в копейках. Бюджет обновляется для той же пары месяц/категория. Нет внешней синхронизации с банками.


Новые GET /api/analytics/compare и /api/analytics/monthly.csv принимают start/end и требуют сессию. Сравнение возвращает current/previous/changes; CSV содержит месячные агрегаты. [REPORTS.md](REPORTS.md).

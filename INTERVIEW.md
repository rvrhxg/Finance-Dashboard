# Ledger Finance — разбор для собеседования

Сверено 20 ноября 2026 с app/main.py, models.py, analytics.py, import_csv.py, database.py, security.py, миграциями, Dockerfile и compose.yaml. Ключевые main/models/analytics/import_csv сверены с GitHub. Это существующий учебный MVP. В примерах сохранены исходные строки; номера привязаны к состоянию на дату проверки.

## Архитектура и выполнение запроса

Один процесс FastAPI обслуживает REST API и статические HTML/CSS/JavaScript. Браузер обращается к тому же origin; отдельного frontend-сервера, очереди и микросервисов нет. `app/main.py` собирает приложение фабрикой create_app, валидирует вход через Pydantic и вызывает прикладные функции. SQLAlchemy Session создаётся на запрос/операцию. Engine управляет соединениями; `pool_pre_ping=True` проверяет их перед использованием. Локально по умолчанию SQLite, в compose — PostgreSQL 17 через psycopg.

`app/models.py` описывает SQLAlchemy2 declarative-модели: Base — общий metadata, Mapped[T] — тип атрибута, mapped_column — конфигурация колонки. Типы не заменяют ограничения БД. Связи реализованы ForeignKey и явными SELECT/JOIN: relationship/back_populates и автоматическая загрузка коллекций не объявлены. Наличие FK на пользователя и категорию само по себе не проверяет совпадение владельцев: это делает приложение.

## Авторизация и безопасность

Это серверные opaque-сессии, не JWT. Пароль проверяется scrypt с индивидуальной солью; сравнение через hmac.compare_digest. Токен — secrets.token_hex(32), в БД хранится SHA256 токена, не его исходное значение. Cookie HttpOnly, SameSite=Strict, Secure включается при ENVIRONMENT=production; срок сессии 24 часа проверяется сервером. Logout удаляет строку сессии. identity извлекает пользователя из cookie; фильтр user_id применяется отдельно в запросах к данным.

Middleware ограничивает размер тела и для изменяющих запросов требует JSON и точный Origin. Устанавливаются security headers, для статических страниц — CSP. Это защита браузерных запросов, не замена авторизации. Регистрация нормализует email и не позволяет запросом назначить расширенные права. Ограничитель входа хранится в памяти процесса и не распределён между workers. Нет MFA, восстановления пароля, подтверждения email и централизованного управления сессиями. Синхронный scrypt вызывается из auth handler: подтверждённых нагрузочных гарантий нет.

## Alembic и жизненный цикл БД

Схема обновляется миграциями, а не Base.metadata.create_all в обычном запуске. `app/database.py` передаёт существующее соединение Alembic через config.attributes. По умолчанию create_app вызывает database с initialize=True, поэтому демо-процесс выполняет upgrade head при старте. Для развёртывания нескольких workers миграции лучше выполнять отдельным шагом до запуска. `expire_on_commit=False` оставляет загруженные атрибуты доступными после commit, но не делает их автоматически свежими. SQLite-соединения получают PRAGMA foreign_keys=ON; в Commerce дополнительно регистрируется Unicode lower.

`session.begin()` коммитит при нормальном выходе и откатывает при исключении. `flush()` отправляет SQL и выдаёт ID/ошибки ограничений, но не завершает транзакцию. Если ошибка перехвачена снаружи context manager, изменения уже откатились. `with sessions()` без begin закрывает Session; записывающие операции должны иметь явную транзакцию.

## Docker и эксплуатация

Dockerfile использует python:3.14-slim и requirements.lock; приложение запускается не от root, UID 1000. Копируются app, public и миграции, стартует uvicorn с --no-access-log. Healthcheck обращается к /api/ready; /api/health — liveness. Readiness проверяет соединение и наличие версии схемы, но не весь бизнес-процесс и не точное совпадение head.

Compose поднимает PostgreSQL 17, сохраняет данные в именованном томе и ждёт pg_isready. Пароль задаётся через POSTGRES_PASSWORD, не встроен в образ. Порт приложения привязан к 127.0.0.1; TLS proxy в compose нет. down -v удаляет данные тома. Нужны отдельные настройки HTTPS/APP_ORIGIN и секретов. Конфигурация демонстрационная: высокая доступность, нагрузочное тестирование и аварийные RPO/RTO не подтверждены. Backup/restore и их ограничения описаны в docs/OPERATIONS.md; резервные копии не публикуются.

## Модели и связи

| Модель | Назначение и ограничения |
|---|---|
| User | Уникальный email, имя, hash пароля; административной роли здесь нет |
| LoginSession | PK token_hash, FK user_id, срок действия сессии |
| Category | FK user_id, name/kind, UNIQUE(user_id,name,kind), CHECK kind income/expense |
| Transaction | FK user_id/category_id, дата Date, положительная сумма BigInteger в копейках, note, nullable external_id |
| Budget | FK user_id/category_id, month, положительный limit_kopecks BigInteger, UNIQUE(user_id,category_id,month) |

User имеет несколько категорий/операций/бюджетов/сессий. Category используется несколькими операциями и бюджетами. relationship не объявлены: доступ через запросы. Отдельные FK не гарантируют, что категория принадлежит владельцу операции; own_category и фильтры запросов обеспечивают эту проверку в API. Доход/расход задаёт kind категории, суммы хранятся положительными; баланс рассчитывается как доходы минус расходы. external_id уникален в пределах пользователя, NULL позволяет ручные операции без внешнего идентификатора.

Миграции: 0001 исходная схема; 0002 индекс transactions(user_id,occurred_on). Alembic upgrade/downgrade/check тестируются. Stamp старой базы требует сверки структуры по docs/MIGRATIONS.md, не заменяет миграцию.

## Отчёты, импорт и транзакции

Операции создаются и удаляются в sessions.begin с проверкой владельца категории/строки. CSV endpoint также открывает одну транзакцию вокруг import_csv. До записи валидируются все строки (колонки, размер, количество, даты, суммы, категории и дубли ID). Затем повтор external_id сравнивается с прежним содержимым: совпадение пропускается, различие отменяет импорт. Категории и операции, созданные до позднего конфликта, откатываются вместе. Flush не коммитит. Уникальные ограничения БД защищают данные при гонке, но отдельного универсального retry конкурентного импорта нет.

analytics выполняет GROUP BY/SUM/COUNT в БД и загружает агрегаты, а не всю историю операций. Суммы преобразуются к int, проценты — представление, не денежный тип. compare_periods сравнивает равные по числу включённых дней интервалы; предыдущий заканчивается за день до текущего. При нулевой базе percent=null, иначе знаменатель — модуль предыдущего значения. Несколько запросов отчёта не гарантируют единый snapshot при стандартной изоляции.

GET /api/transactions возвращает страницы limit1..100 (по умолчанию50), offset и X-Total-Count владельца. Порядок: дата DESC, затем ID DESC. Отчёт учитывает выбранный период, список операций — все даты. Изменения между offset-страницами могут сдвигать записи. pandas применяется к CSV-экспорту месячных агрегатов, не к загрузке всей истории для SQL-отчёта.

## Три участка кода: построчный разбор

### [app/analytics.py:14](app/analytics.py#L14)

```python
    grouped = session.execute(select(month, Category.kind, func.sum(Transaction.amount_kopecks), func.count())
                              .join(Category, Category.id == Transaction.category_id)
                              .where(*conditions).group_by(month, Category.kind).order_by(month, Category.kind)).all()
```

| Строка | Объяснение |
|---|---|
| 14 | SELECT формирует месяц, kind, сумму и число операций. month построен через CAST даты и SUBSTR. |
| 15 | JOIN связывает категории с операциями по category_id. |
| 16 | WHERE ограничивает владельцев и даты, GROUP BY агрегирует, ORDER BY задаёт стабильный порядок; all загружает агрегированные строки. |

### [app/import_csv.py:38](app/import_csv.py#L38)

```python
        previous=session.scalar(select(Transaction).where(Transaction.user_id==user_id,Transaction.external_id==external))
        if previous:
            old_category=session.get(Category,previous.category_id)
            if (previous.occurred_on,old_category.kind,old_category.name,previous.amount_kopecks,previous.note)!=(occurred,kind,name,amount,note):
                raise ValidationError("external_id already used with different contents")
            skipped+=1
            continue
```

| Строка | Объяснение |
|---|---|
| 38 | Ищет external_id только среди операций текущего владельца. |
| 39 | Ветвь повтора уже импортированной операции. |
| 40 | Загружает категорию прежней операции для сравнения kind/name. |
| 41 | Сравнивает дату, категорию, сумму и примечание с новым содержимым. |
| 42 | Несовпадение — доменная ошибка; внешняя транзакция откатывает весь импорт. |
| 43 | Совпавшая операция учитывается как пропущенная. |
| 44 | Переходит к следующей строке, не создавая дубликат. |

### [app/main.py:253](app/main.py#L253)

```python
            with sessions.begin() as session:
                user=identity(request,session)
                return import_csv(session,user.id,data.content)
```

| Строка | Объяснение |
|---|---|
| 253 | Открывает границу атомарной записи: commit при успехе, rollback при исключении. |
| 254 | Проверяет сессию и получает владельца для импорта. |
| 255 | Передаёт импорт в ту же Session; return не отменяет выход из контекста и commit. |

## Ограничения и что реально проверено

Только RUB, нет банковской синхронизации, обменных курсов, оплаты и инвестиционных рекомендаций. Баланс отчёта не равен подтверждённому банковскому остатку. Нет единого snapshot нескольких SQL-запросов отчёта; offset может сдвигаться при изменении истории. Не реализованы восстановление пароля, MFA, распределённый limiter, нагрузочные гарантии и аварийный recovery с RPO/RTO. Схема не имеет составного FK, который на уровне БД запрещает категорию другого пользователя: API проверяет её владельца.

Тесты: tests/test_api.py (владельцы/отчёты/бюджеты/импорт), test_pagination.py (505 операций/границы/изоляция), тесты аналитики и periods (точные суммы/даты/сравнение), migrations (upgrade/downgrade/check/данные), PostgreSQL (BigInteger/владельцы), backup/readiness/logging. Реальная БД проверяется только при TEST_POSTGRES_URL; локальный skip нельзя выдавать за PostgreSQL-pass.

Предыдущий подтверждённый [CI 44513836347](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/44513836347) на c0a08031: Python3.12–3.14 с PostgreSQL, Docker/runtime, Chromium, CSV и демо. Это результаты конкретного коммита. Поздние визуальные правки проверялись локально headless Chrome; новый полный CI этих правок не утверждается. Новый локальный pytest-прогон фиксируется ниже. Ruff E9/F — app/tests/scripts; strict mypy — 4 модуля из pyproject.toml, не весь backend.

Короткий ответ: «Денежные суммы хранятся целыми копейками, отчёт считает агрегаты в SQL. Импорт сначала валидирует строки, затем пишет всё в одной транзакции. external_id защищает повтор импорта, а владельцы проверяются отдельно в API и запросах отчёта».

## Локальный прогон 20 ноября 2026

Python 3.14, `python -m pytest -q`: **15 passed, 2 skipped**. Пропуски связаны с отсутствующим TEST_POSTGRES_URL. Это не новый локальный PostgreSQL/Docker/Chromium-прогон и не повтор всей матрицы Python. Есть предупреждение Starlette о deprecated интеграции TestClient/httpx; тесты завершились успешно. Для временных файлов использован отдельный basetemp внутри рабочей папки.

В этой задаче изменён только INTERVIEW.md; бизнес-код, миграции и конфигурация не редактировались.

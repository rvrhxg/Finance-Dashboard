# Приёмка портфолио MVP

[CI 43872604052](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43872604052) на 67c716d: 7 тестов, Docker build, реальный контейнер с PostgreSQL, создание операции, перезапуск и проверка сохранности данных и точной аналитики, непривилегированный UID, Chromium сценарий входа/операции/CSV/бюджета. Скриншоты получены из этого CI; desktop и mobile 390 px просмотрены, переполнения страницы нет. [CI 43907520742](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43907520742) на 7e16fc7 подтвердил тесты Python 3.12, 3.13 и 3.14 и повторно Docker/PostgreSQL/Chromium.

Данные вымышлены. Нет банковской интеграции, восстановления пароля, production-наблюдаемости и проверки восстановления backup. Docker локально не установлен: контейнерные проверки выполнены в CI. Локально Python 3.14: pytest 7 passed. Это самостоятельный учебный MVP портфолио, не коммерческий production-сервис.

[Финальный CI 43909831110](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43909831110) на 9edf48f: все три версии Python и Docker/PostgreSQL/Chromium успешны.


## SQL-отчёты, сравнение и версии схемы

[CI 43923986565](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43923986565) на 569144a: все job успешны. PostgreSQL-сценарий миграций, BigInteger, владельцев и группировки проверен на Python3.12,3.13,3.14. Локально Python3.14: 10 passed, 1 skipped (PostgreSQL отсутствует); в матрице выполняется и PostgreSQL-тест. RuffE9/F app/tests/scripts и strict mypy app/periods.py успешны. Docker build/runtime подтвердили запуск с миграциями и сохранность после перезапуска. Chromium проверил сравнение периодов и скачивание CSV-отчёта вместе с прежними CRUD/import/budget сценариями. Скриншоты1440/390px из артефакта14254129822 просмотрены визуально, горизонтального переполнения страницы нет. Старой базе требуется сверка и stamp0001 по MIGRATIONS.md. Общая snapshot-гарантия многозапросного отчёта и аварийное backup/restore не заявляются.


## Readiness, безопасные HTTP-логи и backup/restore

[CI 43930004510](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43930004510) на 5d63c21: все job успешны на Python3.12/3.13/3.14. Проверены200/503 readiness, реальная недоступность БД/структуры, request_id и отсутствие URL/query/cookie/тела/секрета в JSON-событиях, общий500 без внутреннего текста, SQLite WAL-snapshot/restore, запрет перезаписи и повреждённый источник. PostgreSQL-матрица выполнила pg_dump/pg_restore между двумя временными базами с BigInteger/внешним ключом, проверила непустую цель и новый файл. Использовался клиент postgres17 в Docker. Docker build/runtime/readiness/persistence и Chromium успешны. Локально: 14 passed, 2 skipped; PostgreSQL локально не установлен. Strict mypy охватывает новые эксплуатационные модули и ранее указанный типизированный модуль, RuffE9/F — app/tests/scripts. Шифрование/ротация/offsite/PITR и аварийные RPO/RTO не проверены; это остаётся MVP. [Инструкции](OPERATIONS.md).


## Recorded demonstration

CI 43939463321 passed. The published WebM is 22.17 seconds at 1280x888, without audio, with explicitly documented 3x playback slowdown. File SHA256 matches metadata; six-frame contact sheet was visually reviewed. This is a Chromium recording with fictional data. It does not establish production readiness or real Telegram delivery.

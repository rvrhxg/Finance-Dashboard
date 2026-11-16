# Приёмка портфолио MVP

[CI 43872604052](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43872604052) на 67c716d: 7 тестов, Docker build, реальный контейнер с PostgreSQL, создание операции, перезапуск и проверка сохранности данных и точной аналитики, непривилегированный UID, Chromium сценарий входа/операции/CSV/бюджета. Скриншоты получены из этого CI; desktop и mobile 390 px просмотрены, переполнения страницы нет. [CI 43907520742](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43907520742) на 7e16fc7 подтвердил тесты Python 3.12, 3.13 и 3.14 и повторно Docker/PostgreSQL/Chromium.

Данные вымышлены. Нет банковской интеграции, восстановления пароля, production-наблюдаемости и проверки восстановления backup. Docker локально не установлен: контейнерные проверки выполнены в CI. Локально Python 3.14: pytest 7 passed. Это самостоятельный учебный MVP портфолио, не коммерческий production-сервис.

[Финальный CI 43909831110](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43909831110) на 9edf48f: все три версии Python и Docker/PostgreSQL/Chromium успешны.


## SQL-отчёты, сравнение и версии схемы

[CI 43923986565](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43923986565) на 569144a: все job успешны. PostgreSQL-сценарий миграций, BigInteger, владельцев и группировки проверен на Python3.12,3.13,3.14. Локально Python3.14: 10 passed, 1 skipped (PostgreSQL отсутствует); в матрице выполняется и PostgreSQL-тест. RuffE9/F app/tests/scripts и strict mypy app/periods.py успешны. Docker build/runtime подтвердили запуск с миграциями и сохранность после перезапуска. Chromium проверил сравнение периодов и скачивание CSV-отчёта вместе с прежними CRUD/import/budget сценариями. Скриншоты1440/390px из артефакта14254129822 просмотрены визуально, горизонтального переполнения страницы нет. Старой базе требуется сверка и stamp0001 по MIGRATIONS.md. Общая snapshot-гарантия многозапросного отчёта и аварийное backup/restore не заявляются.

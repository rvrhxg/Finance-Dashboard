# Приёмка портфолио MVP

[CI 43872604052](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43872604052) на 67c716d: 7 тестов, Docker build, реальный контейнер с PostgreSQL, создание операции, перезапуск и проверка сохранности данных и точной аналитики, непривилегированный UID, Chromium сценарий входа/операции/CSV/бюджета. Скриншоты получены из этого CI; desktop и mobile 390 px просмотрены, переполнения страницы нет. [CI 43907520742](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43907520742) на 7e16fc7 подтвердил тесты Python 3.12, 3.13 и 3.14 и повторно Docker/PostgreSQL/Chromium.

Данные вымышлены. Нет банковской интеграции, восстановления пароля, production-наблюдаемости и проверки восстановления backup. Docker локально не установлен: контейнерные проверки выполнены в CI. Локально Python 3.14: pytest 7 passed. Это самостоятельный учебный MVP портфолио, не коммерческий production-сервис.

[Финальный CI 43909831110](https://github.com/rvrhxg/Finance-Dashboard/actions/runs/43909831110) на 9edf48f: все три версии Python и Docker/PostgreSQL/Chromium успешны.

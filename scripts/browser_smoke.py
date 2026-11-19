from scripts.recording import recording_enabled, recording_options, pause, finish_recording
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import date
from pathlib import Path
from playwright.sync_api import sync_playwright
from app.database import database
from app.seed import seed_demo

with tempfile.TemporaryDirectory(prefix="ledger-browser-") as temporary:
    url="sqlite:///"+str(Path(temporary)/"browser.sqlite").replace("\\","/")
    engine,sessions=database(url)
    password="isolated-browser-password"
    with sessions.begin() as session:
        seed_demo(session,"demo@example.test",password)
    engine.dispose()
    server=subprocess.Popen([sys.executable,"-m","uvicorn","app.main:create_app","--factory","--no-access-log","--host","127.0.0.1","--port","8002"],env={**os.environ,"DATABASE_URL":url,"APP_ORIGIN":"http://127.0.0.1:8002"})
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen("http://127.0.0.1:8002/api/health",timeout=1)
                break
            except OSError:
                time.sleep(.25)
        else:
            raise RuntimeError("Dashboard not ready")
        Path("screenshots").mkdir(exist_ok=True)
        with sync_playwright() as p:
            browser=p.chromium.launch(slow_mo=200 if recording_enabled() else 0)
            page=browser.new_page(viewport={"width":1440,"height":1000}, **recording_options())
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.goto("http://127.0.0.1:8002")
            page.get_by_label("Email",exact=True).fill("demo@example.test")
            page.get_by_label("Пароль",exact=True).fill(password)
            page.get_by_role("button",name="Продолжить →",exact=True).click()
            page.locator("#dashboard").wait_for(state="visible")
            page.locator("#monthly .month").first.wait_for()
            page.locator('#comparison').get_by_role('heading',name='Сравнение с предыдущим периодом',exact=True).wait_for()
            with page.expect_download() as download_info:
                page.locator('#export-report').click()
            assert download_info.value.suggested_filename=='ledger-monthly.csv'
            pause(page)
            if not recording_enabled():
                page.screenshot(path="screenshots/dashboard-desktop.png",full_page=True)
            page.get_by_role("button",name="+ Операция",exact=True).click()
            dialog=page.locator("#editor")
            dialog.get_by_label("Сумма, ₽",exact=True).fill("1234.56")
            dialog.get_by_label("Описание",exact=True).fill("Браузерная проверка")
            dialog.get_by_role("button",name="Сохранить",exact=True).click()
            dialog.wait_for(state="hidden")
            page.locator("#transactions").get_by_text("Браузерная проверка",exact=True).wait_for()
            page.get_by_role("button",name="↑ Импорт CSV",exact=True).click()
            source=f"external_id,date,kind,category,amount,note\nbrowser-1,{date.today().year}-01-03,expense,Тест импорта,99.99,Импорт из браузера\n"
            dialog.get_by_label("Содержимое CSV",exact=True).fill(source)
            dialog.get_by_role("button",name="Сохранить",exact=True).click()
            dialog.wait_for(state="hidden")
            page.get_by_role("button",name="Показать ещё операции",exact=True).click()
            page.get_by_text("Импорт из браузера",exact=True).wait_for()
            page.get_by_role("button",name="+ Лимит",exact=True).click()
            dialog.get_by_label("Лимит, ₽",exact=True).fill("30000")
            dialog.get_by_role("button",name="Сохранить",exact=True).click()
            dialog.wait_for(state="hidden")
            if not recording_enabled():
                page.set_viewport_size({"width":390,"height":844})
            pause(page)
            if not recording_enabled():
                page.screenshot(path="screenshots/dashboard-mobile.png",full_page=True)
            assert not errors,errors
            finish_recording(page,'ledger')
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()

# -*- coding: utf-8 -*-
"""Задание 9: замер времени отклика /my-books до и после индексов"""
import sqlite3, time, urllib.request, http.cookiejar, urllib.parse, subprocess, sys

DB = "library.db"
URL = "http://127.0.0.1:5000/my-books"
LOGIN = "http://127.0.0.1:5000/login"

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_loans_user ON loans(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_loans_active_partial ON loans(user_id, due) WHERE returned_at IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_users_lower_email ON users(lower(email))",
    "CREATE INDEX IF NOT EXISTS idx_loans_covering ON loans(user_id, returned_at, book_id, due)",
]

def drop_indexes():
    con = sqlite3.connect(DB)
    for name in ["idx_loans_user", "idx_loans_active_partial",
                 "idx_users_lower_email", "idx_loans_covering"]:
        con.execute(f"DROP INDEX IF EXISTS {name}")
    con.commit()
    con.close()

def create_indexes():
    con = sqlite3.connect(DB)
    for sql in INDEXES:
        con.execute(sql)
    con.commit()
    con.close()

def bench(url, n=5):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    # логин
    data = urllib.parse.urlencode({"username": "demo", "password": "demo123"}).encode()
    opener.open(LOGIN, data)
    # прогрев
    opener.open(url).read()
    times = []
    for i in range(n):
        t0 = time.perf_counter()
        opener.open(url).read()
        dt = (time.perf_counter() - t0) * 1000
        times.append(dt)
        print(f"  замер {i+1}: {dt:.1f} мс")
    return times

def avg(lst):
    return round(sum(lst) / len(lst), 2)

if __name__ == "__main__":
    print("=" * 55)
    print("ЗАДАНИЕ 9. ЗАМЕР ВРЕМЕНИ ОТКЛИКА /my-books")
    print("=" * 55)

    # 1. Убираем индексы
    print("\n[1/4] Удаляю индексы...")
    drop_indexes()
    print("      Готово. Индексы удалены.")

    # 2. Замеряем БЕЗ индексов
    print("\n[2/4] Замеряю /my-books БЕЗ индексов:")
    try:
        before = bench(URL, n=5)
    except Exception as e:
        print(f"  ОШИБКА: {e}")
        print("  Убедись, что 'python app.py' запущен в другом терминале!")
        sys.exit(1)
    print(f"  Среднее ДО: {avg(before)} мс")

    # 3. Создаём индексы
    print("\n[3/4] Создаю индексы...")
    create_indexes()
    print("      Готово. Индексы созданы.")

    # 4. Замеряем С индексами
    print("\n[4/4] Замеряю /my-books С индексами:")
    after = bench(URL, n=5)
    print(f"  Среднее ПОСЛЕ: {avg(after)} мс")

    # Итог
    print("\n" + "=" * 55)
    print("ИТОГ")
    print("=" * 55)
    print(f"  До индексов:    {avg(before)} мс")
    print(f"  После индексов: {avg(after)} мс")
    if avg(after) > 0:
        print(f"  Ускорение:      {avg(before) / avg(after):.2f}x")
    print("\nСкопируй эти цифры в таблицу отчёта для Задания 9.")
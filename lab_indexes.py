# -*- coding: utf-8 -*-
"""Лабораторная работа: индексирование в SQLite на БД library.db"""
import sqlite3, time

DB = "library.db"

def q(sql, params=()):
    con = sqlite3.connect(DB)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()

def exec_sql(sql):
    con = sqlite3.connect(DB)
    con.execute(sql)
    con.commit()
    con.close()

def plan(sql, params=()):
    con = sqlite3.connect(DB)
    rows = con.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
    con.close()
    return [r[3] for r in rows]

def bench(sql, params=(), n=200):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(sql, params).fetchall()      # прогрев
    t0 = time.perf_counter()
    for _ in range(n):
        cur.execute(sql, params).fetchall()
    dt = (time.perf_counter() - t0) / n * 1000
    con.close()
    return round(dt, 4)

def hr(t):
    print("\n" + "=" * 60)
    print(t)
    print("=" * 60)

# ============ ПОДГОТОВКА: инвентаризация БД ============
hr("ИНВЕНТАРИЗАЦИЯ БАЗЫ")

print("\nТаблицы и количество строк:")
for name, in q("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
    cnt = q(f"SELECT COUNT(*) FROM {name}")[0][0]
    print(f"  {name:<12} — {cnt} строк")

print("\nСуществующие индексы:")
for name, tbl, sql in q("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index'"):
    print(f"  {name:<35} на {tbl}")
    if sql:
        print(f"      {sql}")

# ============ ЗАДАНИЕ 1: список запросов ============
hr("ЗАДАНИЕ 1. ЗАПРОСЫ ДЛЯ ОПТИМИЗАЦИИ")

QUERIES = [
    ("Q1 login",        "SELECT * FROM users WHERE username = ?",                          ("demo",)),
    ("Q2 my-books",     "SELECT * FROM loans WHERE user_id = ? AND returned_at IS NULL ORDER BY due", (2,)),
    ("Q3 read-books",   "SELECT book_id FROM loans WHERE user_id = ? AND returned_at IS NOT NULL",   (2,)),
    ("Q4 borrow check", "SELECT * FROM loans WHERE user_id = ? AND book_id = ? AND returned_at IS NULL", (2, 5)),
    ("Q5 fav",          "SELECT * FROM favorites WHERE user_id = ? AND kind = ?",          (2, "book")),
    ("Q6 messages",     "SELECT * FROM messages ORDER BY id DESC LIMIT 5",                 ()),
]

for name, sql, params in QUERIES:
    print(f"\n{name}:\n  {sql}\n  параметры: {params}")
    for line in plan(sql, params):
        print(f"  → {line}")
        
# ============ ЗАДАНИЕ 2: B-tree индекс ============
hr("ЗАДАНИЕ 2. B-TREE ИНДЕКС НА user_id (таблица loans)")

sql = "SELECT * FROM loans WHERE user_id = ?"
params = (2,)

exec_sql("DROP INDEX IF EXISTS idx_loans_user")
print("\nДО индекса:")
for line in plan(sql, params): print("  " + line)
t_before = bench(sql, params)
print(f"  время: {t_before} мс")

exec_sql("CREATE INDEX idx_loans_user ON loans(user_id)")
print("\nПОСЛЕ индекса:")
for line in plan(sql, params): print("  " + line)
t_after = bench(sql, params)
print(f"  время: {t_after} мс")
print(f"  ускорение: {t_before / t_after:.2f}x")

# ============ ЗАДАНИЕ 3: HASH — не поддерживается ============
hr("ЗАДАНИЕ 3. HASH-ИНДЕКС")
print("SQLite не поддерживает HASH-индексы.")
print("Используется только B-tree.")
print("В PostgreSQL HASH компактнее B-tree, но только для оператора =.")

# ============ ЗАДАНИЕ 4: частичный индекс ============
hr("ЗАДАНИЕ 4. ЧАСТИЧНЫЙ ИНДЕКС ПОД АКТИВНЫЕ ВЫДАЧИ")

sql = "SELECT * FROM loans WHERE user_id = ? AND returned_at IS NULL ORDER BY due"
params = (2,)

exec_sql("DROP INDEX IF EXISTS idx_loans_active_partial")
exec_sql("DROP INDEX IF EXISTS idx_loans_user_due_full")

exec_sql("CREATE INDEX idx_loans_user_due_full ON loans(user_id, due)")
size_full = q("SELECT SUM(pgsize) FROM dbstat WHERE name='idx_loans_user_due_full'") \
    if False else None  # dbstat нужен виртуальный модуль; считаем иначе
print("\nПолный индекс idx_loans_user_due_full создан.")
print("ДО (полный индекс):")
for line in plan(sql, params): print("  " + line)
t_full = bench(sql, params)
print(f"  время: {t_full} мс")

exec_sql("DROP INDEX idx_loans_user_due_full")
exec_sql("CREATE INDEX idx_loans_active_partial ON loans(user_id, due) WHERE returned_at IS NULL")
print("\nПОСЛЕ (частичный индекс):")
for line in plan(sql, params): print("  " + line)
t_partial = bench(sql, params)
print(f"  время: {t_partial} мс")

# ============ ЗАДАНИЕ 5: индекс по выражению ============
hr("ЗАДАНИЕ 5. ИНДЕКС ПО ВЫРАЖЕНИЮ lower(email)")

sql = "SELECT * FROM users WHERE lower(email) = ?"
params = ("demo@example.com",)

exec_sql("DROP INDEX IF EXISTS idx_users_lower_email")
print("\nДО индекса:")
for line in plan(sql, params): print("  " + line)
t_before = bench(sql, params)
print(f"  время: {t_before} мс")

exec_sql("CREATE INDEX idx_users_lower_email ON users(lower(email))")
print("\nПОСЛЕ индекса:")
for line in plan(sql, params): print("  " + line)
t_after = bench(sql, params)
print(f"  время: {t_after} мс")
print(f"  ускорение: {t_before / t_after:.2f}x" if t_after else "—")

# ============ ЗАДАНИЕ 6: GIN ============
hr("ЗАДАНИЕ 6. GIN-ИНДЕКС")
print("В БД нет столбцов jsonb / text[] / tsvector.")
print("GIN был бы полезен, если бы хранили теги книг как массив или JSON-настроения.")

# ============ ЗАДАНИЕ 7: BRIN ============
hr("ЗАДАНИЕ 7. BRIN-ИНДЕКС")
print("SQLite не поддерживает BRIN. В таблице loans столбец taken — временной ряд,")
print("по нему в PostgreSQL BRIN был бы компактным и эффективным.")

# ============ ЗАДАНИЕ 8: покрывающий индекс ============
hr("ЗАДАНИЕ 8. ПОКРЫВАЮЩИЙ ИНДЕКС (аналог INCLUDE)")

sql = "SELECT book_id, due FROM loans WHERE user_id = ? AND returned_at IS NULL"
params = (2,)

exec_sql("DROP INDEX IF EXISTS idx_loans_covering")
print("\nДО индекса:")
for line in plan(sql, params): print("  " + line)
t_before = bench(sql, params)
print(f"  время: {t_before} мс")

exec_sql("CREATE INDEX idx_loans_covering ON loans(user_id, returned_at, book_id, due)")
print("\nПОСЛЕ индекса:")
for line in plan(sql, params): print("  " + line)
t_after = bench(sql, params)
print(f"  время: {t_after} мс")

# ============ ЗАДАНИЕ 9: замер на приложении ============
hr("ЗАДАНИЕ 9. ЭФФЕКТ НА ПРИЛОЖЕНИИ")
print("Запусти 'python app.py' и замерь время открытия /my-books")
print("через DevTools браузера (Network → Response Time).")
print("Повтори замер 5 раз до и после создания индексов, возьми среднее.")

# ============ ЗАДАНИЕ 10: итоговые рекомендации ============
hr("ЗАДАНИЕ 10. ИТОГОВЫЕ ИНДЕКСЫ")

for name, tbl, sql in q("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index'"):
    if name.startswith("sqlite_autoindex"): continue
    print(f"\n  {name}  (таблица {tbl})")
    if sql: print(f"    {sql}")
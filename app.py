# -*- coding: utf-8 -*-
"""Сфера Мысли — сайт областной библиотеки (Flask + SQLite).

Запуск:
    pip install -r requirements.txt
    python app.py
Демо-аккаунт: demo / demo123
"""
import os
import random
import re
import secrets
import sqlite3
from collections import Counter
from datetime import date, timedelta
from functools import wraps

from flask import (Flask, Response, abort, flash, g, get_flashed_messages,
                   jsonify, redirect, render_template, request, send_from_directory,
                   session)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "library.db")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_HTTPONLY=True,
)
app.json.ensure_ascii = False

# аватарки хранятся файлами в папке uploads/avatars
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "avatars")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024   # запрос целиком не больше 3 МБ
AVATAR_MAX = 2 * 1024 * 1024                         # сама аватарка не больше 2 МБ

LOAN_DAYS = 14      # на сколько дней выдаётся книга
EXTEND_DAYS = 7     # на сколько дней можно продлить (один раз)
MAX_LOANS = 7       # лимит книг на руках

# ---------------------------------------------------------------- данные ----
# id, название, автор, год, жанр, страниц, оттенок обложки, строка, описание, настроения, флаги
# флаги: n — новинка, h — хит, s — скоро в наличии
_RAW = [
    (1, "Мастер и Маргарита", "М. Булгаков", 1967, "Роман", 480, 350, "«Рукописи не горят.»",
     "Воланд приезжает в Москву, а параллельно разворачивается роман о Понтии Пилате.", "think dream", "h"),
    (2, "Преступление и наказание", "Ф. Достоевский", 1866, "Драма", 608, 25, "«Тварь ли я дрожащая или право имею?»",
     "Студент Раскольников проверяет свою теорию на деле и расплачивается совестью.", "think thrill", ""),
    (3, "Война и мир", "Л. Толстой", 1869, "Роман", 1300, 215, "«Нет величия там, где нет простоты, добра и правды.»",
     "Эпопея о судьбах людей на фоне наполеоновских войн.", "think calm", ""),
    (4, "Анна Каренина", "Л. Толстой", 1877, "Драма", 864, 330, "«Все счастливые семьи похожи друг на друга.»",
     "Любовь, нарушившая правила света, и цена, которую за неё приходится платить.", "think calm", ""),
    (5, "Евгений Онегин", "А. Пушкин", 1833, "Роман", 224, 150, "«Мы все учились понемногу чему-нибудь и как-нибудь.»",
     "Роман в стихах о скучающем денди, несостоявшейся любви и дуэли.", "calm dream", ""),
    (6, "Идиот", "Ф. Достоевский", 1869, "Драма", 640, 48, "«Красота спасёт мир.»",
     "Добрый и открытый князь Мышкин попадает в вихрь страстей петербургского света.", "think", "s"),
    (7, "Отцы и дети", "И. Тургенев", 1862, "Роман", 288, 120, "«Природа не храм, а мастерская.»",
     "Спор поколений, нигилист Базаров и чувство, которое ломает убеждения.", "calm think", ""),
    (8, "Собачье сердце", "М. Булгаков", 1925, "Фантастика", 160, 265, "«Разруха не в клозетах, а в головах.»",
     "Профессор превращает пса в человека и получает куда больше проблем, чем ожидал.", "think thrill", ""),
    (9, "1984", "Дж. Оруэлл", 1949, "Антиутопия", 352, 0, "«Большой Брат следит за тобой.»",
     "Мир тотального контроля, где под надзором даже мысли.", "think thrill", "h"),
    (10, "Скотный двор", "Дж. Оруэлл", 1945, "Антиутопия", 144, 95, "«Все животные равны, но некоторые равнее других.»",
     "Притча о революции: животные захватывают ферму и строят «справедливое» общество.", "think", ""),
    (11, "О дивный новый мир", "О. Хаксли", 1932, "Антиутопия", 288, 190, "Общество, где счастье стало обязанностью.",
     "Идеальный мир без боли и выбора, в котором цена комфорта — свобода.", "think dream", "n"),
    (12, "451° по Фаренгейту", "Р. Брэдбери", 1953, "Антиутопия", 256, 12, "Мир, где книги сжигают.",
     "Пожарный, который сжигает книги, однажды открывает одну из них.", "think thrill", "n"),
    (13, "Марсианские хроники", "Р. Брэдбери", 1950, "Фантастика", 320, 15, "Рассказы о Марсе и человеческих мечтах.",
     "Люди колонизируют Марс и привозят туда всё то же, от чего бежали с Земли.", "dream calm", "s"),
    (14, "Дюна", "Ф. Герберт", 1965, "Фантастика", 704, 38, "«Страх убивает разум.»",
     "Песчаная планета, борьба за пряность и рождение нового мессии.", "dream thrill", "n"),
    (15, "Солярис", "С. Лем", 1961, "Фантастика", 256, 225, "Океан, который умеет думать.",
     "Станция над загадочным океаном, который читает мысли и воспоминания людей.", "think dream", "n"),
    (16, "Убийство в «Восточном экспрессе»", "А. Кристи", 1934, "Детектив", 256, 355, "Поезд, снег и двенадцать подозреваемых.",
     "Поезд застрял в снегах, в вагоне убийство, и у каждого пассажира есть секрет.", "thrill", "h"),
    (17, "Собака Баскервилей", "А. Конан Дойл", 1902, "Детектив", 288, 140, "Туманные болота и призрачный пёс.",
     "Холмс и Ватсон разбираются с легендой о гигантской собаке на болотах Девона.", "thrill", ""),
    (18, "И никого не стало", "А. Кристи", 1939, "Детектив", 272, 240, "Остров, где гости исчезают один за другим.",
     "Десять незнакомцев на острове, и ни у одного нет шанса уйти.", "thrill", "s"),
    (19, "Три товарища", "Э. М. Ремарк", 1936, "Роман", 480, 165, "Дружба и любовь в эпоху потерь.",
     "Трое друзей, любовь и попытка собрать мирную жизнь из того, что осталось после войны.", "calm dream", ""),
    (20, "Великий Гэтсби", "Ф. С. Фицджеральд", 1925, "Роман", 192, 50, "Мечта, которая светила слишком ярко.",
     "Эпоха джаза, роскошные вечеринки и мечта, ради которой герой готов на всё.", "calm think", "n"),
    (21, "Маленький принц", "А. де Сент-Экзюпери", 1943, "Новелла", 96, 205, "«Самого главного глазами не увидишь.»",
     "Добрая философская сказка о дружбе, любви и о том, что действительно важно.", "calm dream", "h"),
    (22, "Старик и море", "Э. Хемингуэй", 1952, "Новелла", 128, 195, "«Человека можно уничтожить, но нельзя победить.»",
     "Старый рыбак один на один с огромной рыбой в открытом море.", "calm think", ""),
    (23, "Шинель", "Н. Гоголь", 1842, "Новелла", 48, 280, "Маленький человек и большая мечта о шинели.",
     "Скромный чиновник копит на новую шинель, и эта мечта меняет его жизнь.", "think calm", ""),
    (24, "Пикник на обочине", "А. и Б. Стругацкие", 1972, "Фантастика", 224, 72, "Зона, в которой исполняются желания.",
     "Сталкеры идут в Зону за артефактами, а Зона присматривается к ним.", "thrill dream", "n"),
]

BOOKS = [
    dict(id=r[0], title=r[1], author=r[2], year=r[3], genre=r[4], pages=r[5], hue=r[6],
         line=r[7], desc=r[8], moods=r[9].split(), new="n" in r[10], hit="h" in r[10], soon="s" in r[10])
    for r in _RAW
]
BOOK = {b["id"]: b for b in BOOKS}

RU_MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
             "августа", "сентября", "октября", "ноября", "декабря"]
RU_WD = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def fmt_date(d):
    return f"{RU_WD[d.weekday()]}, {d.day} {RU_MONTHS[d.month - 1]}"


def plural(n, forms):
    n = abs(int(n))
    if 11 <= n % 100 <= 14:
        return forms[2]
    if n % 10 == 1:
        return forms[0]
    if 2 <= n % 10 <= 4:
        return forms[1]
    return forms[2]


def days_txt(n):
    return f"{n} {plural(n, ('день', 'дня', 'дней'))}"


def reader_status(reads, on_hands):
    if reads >= 25:
        return "Заядлый читатель"
    if on_hands >= 3:
        return "Сфокусированный читатель"
    if on_hands >= 1:
        return "Читатель в пути"
    return "Начинающий читатель"


def long_date(d):
    return f"{d.day} {RU_MONTHS[d.month - 1]} {d.year}"


def length_bucket(pages):
    return "short" if pages <= 300 else "medium" if pages <= 600 else "long"


def build_events():
    today = date.today()
    fri = today + timedelta(days=(4 - today.weekday()) % 7)
    raw = [
        (1, 0, "18:00", "Лекторий, 2 этаж", "Дискуссия", "ИИ и литература. Кто напишет бестселлер будущего?",
         "Писатели, редакторы и исследователи спорят: заменит ли нейросеть автора или станет его соавтором. Живой разговор, вопросы из зала и мини-эксперимент с коллективным сюжетом."),
        (2, 1, "16:00", "Большой читальный зал", "Слэм", "Книжный слэм: антиутопии XXI века",
         "Участники по очереди за пять минут защищают любимую антиутопию, а зал голосует. Побеждает книга, после которой страшнее всего выходить на улицу."),
        (3, 1, "12:00", "Клубная комната", "Клуб", "Классика по субботам: Достоевский сегодня",
         "Читаем главы вслух и обсуждаем, почему «Преступление и наказание» не стареет. Приносите свои любимые цитаты."),
        (4, 2, "11:00", "Мастерская, 1 этаж", "Мастер-класс", "Реставрация книг: вторая жизнь старого тома",
         "Реставратор покажет, как склеить корешок, очистить страницы и вернуть книге форму. Все материалы выдаём на месте."),
        (5, 2, "14:00", "Детский абонемент", "Детям", "Читаем вместе: сказки для всей семьи",
         "Громкие чтения, театр теней и книжная лотерея. Для детей от 4 до 10 лет и их родителей."),
        (6, 0, "20:00", "Малый зал", "Кино", "Вечер кино по книгам",
         "Смотрим экранизацию и обсуждаем, чем фильм отличается от книги. Чай и пледы предоставляем."),
    ]
    out = []
    for i, off, tm, place, tag, title, body in raw:
        d = fri + timedelta(days=off)
        out.append(dict(id=i, title=title, date=fmt_date(d), time=tm, place=place, tag=tag, body=body,
                        meta=f"{fmt_date(d)}, {tm} — {place}", _k=(off, tm)))
    out.sort(key=lambda e: e["_k"])
    for e in out:
        e.pop("_k")
    return out


def build_news():
    today = date.today()
    raw = [
        (1, 1, "Каталог", "Пополнение каталога: +500 новых книг",
         "В фонд поступило более 500 изданий: современная проза, научпоп, книги на иностранных языках и редкие переиздания. Все новинки уже доступны в каталоге."),
        (2, 3, "Подборка", "Главные новинки этой осени",
         "Редакция собрала книги, которые стоит прочитать, пока за окном дожди: от антиутопий до уютных детективов. Подборка лежит на стойке у входа и в разделе «Новинки»."),
        (3, 6, "Сервис", "Обновлён график работы коворкинга",
         "Коворкинг открыт ежедневно с 8:00 до 20:00, как и вся библиотека. Добавили пять мест с розетками и тихую зону без разговоров."),
        (4, 9, "Клуб", "Открыта запись в клуб читателей",
         "Раз в месяц собираемся и обсуждаем одну книгу. Первая встреча пройдёт на ближайших выходных, записаться можно у библиотекаря."),
        (5, 14, "Архив", "Оцифрованы новые архивные документы",
         "В разделе «История» появились материалы за 1914–1953 годы: письма читателей, отчёты и фотографии залов."),
    ]
    return [dict(id=i, title=t, tag=tag, body=body, meta=fmt_date(today - timedelta(days=ago)), date=fmt_date(today - timedelta(days=ago)))
            for i, ago, tag, t, body in raw]


TIMELINE = [
    ("1875", "Основание", "Открылась небольшая городская читальня: один зал, первые списки читателей и 1 200 томов."),
    ("1911", "Расширение залов", "Здание перестроили, появились новые читальные залы и отдельный абонемент."),
    ("1985", "Реставрация", "Исторический корпус отреставрировали, а фонд разобрали и описали заново."),
    ("2025", "Модернизация", "Запустили электронный каталог, коворкинг и онлайн-сервисы для читателей."),
]

ARCHIVE = [
    ("1875–1898", "Устав читальни, первые списки читателей и рукописный каталог."),
    ("1898–1910", "Отчёты о росте фонда и открытие воскресной школы при читальне."),
    ("1911–1913", "Проекты перестройки здания и чертежи новых читальных залов."),
    ("1914–1953", "Письма читателей, эвакуация фонда и восстановление работы после войны."),
    ("1954–1964", "Открытие детского абонемента и первые тематические выставки."),
    ("1964–1982", "Картотека нового образца и начало межбиблиотечного обмена."),
    ("1982–1990", "Подготовка к реставрации, фотографии залов, смета работ."),
    ("1991–2011", "Новые правила работы, первые компьютеры и электронный каталог."),
    ("2011–2026", "Оцифровка фонда, коворкинг и онлайн-сервисы для читателей."),
]

DOCS = {}
for _i, (_period, _text) in enumerate(ARCHIVE, 1):
    DOCS[f"arch-{_i}"] = dict(title=f"Документ №{_i}, {_period} годы", meta="Архивные материалы", body=_text)
DOCS["sched-month"] = dict(
    title="Расписание на месяц", meta="Часы работы",
    body="Все залы, абонемент и коворкинг: ежедневно с 8:00 до 20:00.\nЧитальный зал периодики: с 9:00 до 19:00.\nЛекторий и мероприятия: с пятницы по воскресенье, начало по афише.\nГардероб закрывается в 19:45.")
DOCS["sched-holidays"] = dict(
    title="Ближайшие праздники", meta="Часы работы",
    body="4 ноября: работаем с 10:00 до 18:00.\n31 декабря: сокращённый день, до 18:00.\n1–3 января: библиотека закрыта.\nТочные даты уточняйте на стойке информации.")
DOCS["sched-shifts"] = dict(
    title="Смены на месяц", meta="Часы работы",
    body="Первая смена: 8:00–14:00, вторая смена: 14:00–20:00.\nНа абонементе всегда дежурят двое библиотекарей.\nКонсультация по подбору книг: в любое время работы библиотеки.")

# --------------------------------------------------------------------- БД ----
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL, name TEXT NOT NULL, email TEXT, password_hash TEXT NOT NULL,
  avatar TEXT, bio TEXT NOT NULL DEFAULT '', created TEXT);
CREATE TABLE IF NOT EXISTS loans(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL, book_id INTEGER NOT NULL,
  taken TEXT NOT NULL, due TEXT NOT NULL, returned_at TEXT, extended INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS favorites(
  user_id INTEGER NOT NULL, kind TEXT NOT NULL, item_id INTEGER NOT NULL,
  PRIMARY KEY(user_id, kind, item_id));
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT, email TEXT, text TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS friendships(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  requester_id INTEGER NOT NULL, addressee_id INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending', created TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(requester_id, addressee_id));
"""


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def seed_social(con):
    """Демо-друзья для аккаунта demo (создаются один раз)."""
    demo = con.execute("SELECT id FROM users WHERE username='demo'").fetchone()
    if not demo or con.execute("SELECT 1 FROM users WHERE username='anna'").fetchone():
        return
    today = date.today()
    con.execute("UPDATE users SET bio=? WHERE id=? AND bio=''",
                ("Читаю по вечерам и собираю любимые цитаты.", demo[0]))
    people = [
        ("anna", "Анна", "Люблю детективы и чай с лимоном.", [16, 17, 18, 2, 7]),
        ("ilya", "Илья", "Фантастика по ночам, классика по выходным.", [14, 15, 24, 13, 8, 12]),
        ("maria", "Мария", "Только классика, только бумажные книги.", [3, 4, 5, 19]),
        ("sergey", "Сергей", "Новичок в клубе читателей.", [21]),
    ]
    ids = {}
    for username, name, bio, read in people:
        cur = con.execute("INSERT INTO users(username,name,email,password_hash,bio,created) VALUES(?,?,?,?,?,?)",
                          (username, name, None, generate_password_hash("demo123"), bio,
                           (today - timedelta(days=60)).isoformat()))
        ids[username] = cur.lastrowid
        for i, bid in enumerate(read):
            taken = today - timedelta(days=30 + i * 9)
            due = taken + timedelta(days=LOAN_DAYS)
            con.execute("INSERT INTO loans(user_id,book_id,taken,due,returned_at) VALUES(?,?,?,?,?)",
                        (cur.lastrowid, bid, taken.isoformat(), due.isoformat(), (due - timedelta(days=2)).isoformat()))
    for who in ("anna", "ilya"):   # уже друзья demo
        con.execute("INSERT INTO friendships(requester_id,addressee_id,status) VALUES(?,?,'accepted')",
                    (demo[0], ids[who]))
    # Мария ждёт ответа на заявку; Сергей пока не знаком с demo (его можно найти поиском)
    con.execute("INSERT INTO friendships(requester_id,addressee_id,status) VALUES(?,?,'pending')",
                (ids["maria"], demo[0]))


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    # миграция: если library.db создана старой версией сайта, добавляем новые колонки
    cols = {r[1] for r in con.execute("PRAGMA table_info(users)")}
    for col, ddl in (("avatar", "TEXT"), ("bio", "TEXT NOT NULL DEFAULT ''"), ("created", "TEXT")):
        if col not in cols:
            con.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
    con.execute("UPDATE users SET created=date('now') WHERE created IS NULL")
    if not con.execute("SELECT 1 FROM users WHERE username='demo'").fetchone():
        today = date.today()
        cur = con.execute("INSERT INTO users(username,name,email,password_hash) VALUES(?,?,?,?)",
                          ("demo", "Алексей", "demo@example.com", generate_password_hash("demo123")))
        uid = cur.lastrowid
        # (книга, взята дней назад, срок через N дней) — отрицательный срок = просрочено
        for bid, ago, due_in in [(3, 2, 12), (2, 7, 7), (1, 12, 2), (4, 19, -5), (5, 17, -3)]:
            con.execute("INSERT INTO loans(user_id,book_id,taken,due) VALUES(?,?,?,?)",
                        (uid, bid, (today - timedelta(days=ago)).isoformat(), (today + timedelta(days=due_in)).isoformat()))
        returned = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
        for i, bid in enumerate(returned):
            taken = today - timedelta(days=40 + i * 6)
            due = taken + timedelta(days=LOAN_DAYS)
            back = due + timedelta(days=3 if i % 7 == 3 else -2)
            con.execute("INSERT INTO loans(user_id,book_id,taken,due,returned_at) VALUES(?,?,?,?,?)",
                        (uid, bid, taken.isoformat(), due.isoformat(), back.isoformat()))
        for kind, item in [("book", 1), ("book", 9), ("book", 21), ("event", 1)]:
            con.execute("INSERT INTO favorites VALUES(?,?,?)", (uid, kind, item))
    seed_social(con)
    con.commit()
    con.close()


init_db()

# ------------------------------------------------------------ сессия/общее ----


@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        g.user = db().execute("SELECT id, username, name, email, avatar, bio, created FROM users WHERE id=?", (uid,)).fetchone()
        if g.user is None:
            session.clear()


@app.context_processor
def inject_globals():
    favs, loaned, pending = [], [], 0
    if g.user:
        pending = db().execute("SELECT COUNT(*) FROM friendships WHERE addressee_id=? AND status='pending'",
                               (g.user["id"],)).fetchone()[0]
        favs = [f"{r['kind']}:{r['item_id']}" for r in
                db().execute("SELECT kind, item_id FROM favorites WHERE user_id=?", (g.user["id"],))]
        loaned = [r["book_id"] for r in
                  db().execute("SELECT book_id FROM loans WHERE user_id=? AND returned_at IS NULL", (g.user["id"],))]
    state = dict(user={"name": g.user["name"]} if g.user else None, favs=favs, loaned=loaned,
                 flashes=get_flashed_messages(with_categories=True))
    return dict(current_user=g.user, sm_state=state, books_map={b["id"]: b for b in BOOKS},
                pending_requests=pending)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify(ok=False, error="Войдите в аккаунт", login="/login"), 401
            flash("Войдите, чтобы открыть эту страницу", "info")
            return redirect(f"/login?next={request.path}")
        return view(*args, **kwargs)
    return wrapper


def safe_next(target):
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return "/"


def recommended_ids(user):
    rng = random.Random(date.today().toordinal())
    pool = [b["id"] for b in BOOKS if not b["soon"]]
    if not user:
        return rng.sample(pool, 3)
    rows = db().execute("SELECT book_id FROM loans WHERE user_id=?", (user["id"],)).fetchall()
    seen = {r["book_id"] for r in rows}
    ids = []
    if rows:
        top = Counter(BOOK[r["book_id"]]["genre"] for r in rows).most_common(1)[0][0]
        ids = [b["id"] for b in BOOKS if b["genre"] == top and b["id"] not in seen and not b["soon"]][:3]
    rest = [i for i in pool if i not in seen and i not in ids]
    rng.shuffle(rest)
    return (ids + rest)[:3]


# ---------------------------------------------------------------- страницы ----


@app.route("/")
def home():
    today = date.today()
    featured = BOOKS[today.timetuple().tm_yday % len(BOOKS)]
    collections = []
    for genre, text in [("Антиутопия", "Миры, в которых что-то пошло не так"),
                        ("Детектив", "Улики, алиби и неожиданные финалы"),
                        ("Фантастика", "Другие планеты и другие законы"),
                        ("Роман", "Большие истории о людях и времени")]:
        collections.append(dict(genre=genre, text=text, count=sum(1 for b in BOOKS if b["genre"] == genre)))
    return render_template(
        "home.html", featured=featured, collections=collections,
        reco=recommended_ids(g.user),
        new=[b["id"] for b in BOOKS if b["new"]][:3],
        hits=[b["id"] for b in BOOKS if b["hit"]][:3],
        soon=[b["id"] for b in BOOKS if b["soon"]][:3])


@app.route("/selection")
def selection():
    return render_template("selection.html")


@app.route("/new")
def new_books():
    return render_template("new.html", ids=[b["id"] for b in BOOKS if b["new"]])


@app.route("/catalog")
def catalog():
    return render_template(
        "catalog.html",
        genres=sorted({b["genre"] for b in BOOKS}),
        authors=sorted({b["author"] for b in BOOKS}),
        decades=sorted({b["year"] // 10 * 10 for b in BOOKS}),
        total=len(BOOKS))


@app.route("/my-books")
@login_required
def my_books():
    today = date.today()
    active, overdue, done = [], [], []
    rows = db().execute("SELECT * FROM loans WHERE user_id=? ORDER BY due", (g.user["id"],)).fetchall()
    for r in rows:
        b = BOOK[r["book_id"]]
        due, taken = date.fromisoformat(r["due"]), date.fromisoformat(r["taken"])
        if r["returned_at"]:
            done.append(dict(book=b, late=date.fromisoformat(r["returned_at"]) > due))
            continue
        left = (due - today).days
        total = max((due - taken).days, 1)
        item = dict(id=r["id"], book=b, left=left, due=fmt_date(due), extended=bool(r["extended"]),
                    pct=max(4, min(100, round(left / total * 100))),
                    tone="green" if left > 7 else "yellow" if left >= 3 else "red",
                    days_txt=days_txt(max(left, 0)), over_txt=days_txt(-left) if left < 0 else "")
        (overdue if left < 0 else active).append(item)
    reads = len({d["book"]["id"] for d in done})
    on_time = sum(1 for d in done if not d["late"])
    on_hands = len(active) + len(overdue)
    rings = [
        dict(key="blue", r=90, label="Читательская активность", pct=min(100, round(reads / 20 * 100)),
             note=f"{reads} из 20 книг в цели"),
        dict(key="orange", r=70, label="Книг сдано вовремя", pct=round(on_time / len(done) * 100) if done else 0,
             note=f"{on_time} из {len(done)}"),
        dict(key="green", r=50, label="Осталось прочитать", pct=min(100, round(on_hands / MAX_LOANS * 100)),
             note=f"на руках {on_hands} из {MAX_LOANS}"),
    ]
    status = reader_status(reads, on_hands)
    return render_template("my-books.html", active=active, overdue=overdue, rings=rings, status=status,
                           has_any=bool(rows), max_loans=MAX_LOANS)


@app.route("/read-books")
@login_required
def read_books():
    rows = db().execute(
        "SELECT book_id, MAX(returned_at) AS m FROM loans WHERE user_id=? AND returned_at IS NOT NULL "
        "GROUP BY book_id ORDER BY m DESC", (g.user["id"],)).fetchall()
    read = [BOOK[r["book_id"]] for r in rows]
    genres = Counter(b["genre"] for b in read)
    authors = Counter(b["author"] for b in read)
    top = genres.most_common(5)
    top_val = top[0][1] if top else 0
    axis_max = max(5, -(-top_val // 5) * 5)
    bars = [dict(name=n, n=v, h=round(v / axis_max * 100)) for n, v in top]
    fav_rows = db().execute("SELECT item_id FROM favorites WHERE user_id=? AND kind='book'", (g.user["id"],)).fetchall()
    return render_template(
        "read-books.html", read_ids=[b["id"] for b in read], bars=bars,
        axis=[round(axis_max * k / 4) for k in (4, 3, 2, 1, 0)],
        fav_genre=genres.most_common(1)[0][0] if genres else "—",
        fav_author=authors.most_common(1)[0][0] if authors else "—",
        fav_ids=[r["item_id"] for r in fav_rows if r["item_id"] in BOOK])


@app.route("/history")
def history():
    docs = [dict(id=k, **v) for k, v in DOCS.items() if k.startswith("arch-")]
    return render_template("history.html", timeline=TIMELINE, docs=docs)


@app.route("/hours")
def hours():
    docs = [dict(id=k, **v) for k, v in DOCS.items() if k.startswith("sched-")]
    return render_template("hours.html", docs=docs)


@app.route("/events")
def events():
    return render_template("events.html", events=build_events())


@app.route("/news")
def news():
    return render_template("news.html", news=build_news())


@app.route("/contacts")
def contacts():
    return render_template("contacts.html")


@app.route("/doc/<key>.txt")
def doc_download(key):
    d = DOCS.get(key)
    if d is None:
        abort(404)
    text = (f"{d['title']}\n{'=' * len(d['title'])}\n\n{d['body']}\n\n"
            "Областная библиотека «Сфера Мысли»\n(демонстрационный материал)\n")
    return Response(text, mimetype="text/plain; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={key}.txt"})


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


# ----------------------------------------------------------------- авторизация ----


@app.route("/login", methods=["GET", "POST"])
def login():
    nxt = safe_next(request.values.get("next"))
    if g.user:
        return redirect(nxt)
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        user = db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["uid"] = user["id"]
            flash(f"С возвращением, {user['name']}!", "success")
            n = db().execute("SELECT COUNT(*) FROM friendships WHERE addressee_id=? AND status='pending'",
                             (user["id"],)).fetchone()[0]
            if n:
                flash(f"Новых заявок в друзья: {n}. Загляните в профиль", "info")
            return redirect(nxt)
        flash("Неверное имя пользователя или пароль", "error")
    return render_template("auth.html", mode="login", next=nxt, form=request.form)


@app.route("/register", methods=["GET", "POST"])
def register():
    nxt = safe_next(request.values.get("next"))
    if g.user:
        return redirect(nxt)
    if request.method == "POST":
        f = request.form
        username = f.get("username", "").strip().lower()
        name = f.get("name", "").strip()
        email = f.get("email", "").strip()
        pw, confirm = f.get("password", ""), f.get("confirm", "")
        error = None
        if not re.fullmatch(r"[a-z0-9_.-]{3,24}", username):
            error = "Имя пользователя: 3–24 символа, латиница, цифры, точка, дефис или подчёркивание"
        elif not name or len(name) > 40:
            error = "Укажите ваше имя (до 40 символов)"
        elif email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            error = "Проверьте адрес почты"
        elif len(pw) < 6:
            error = "Пароль должен быть не короче 6 символов"
        elif pw != confirm:
            error = "Пароли не совпадают"
        elif db().execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            error = "Это имя пользователя уже занято"
        if error:
            flash(error, "error")
        else:
            cur = db().execute("INSERT INTO users(username,name,email,password_hash,created) VALUES(?,?,?,?,?)",
                               (username, name, email, generate_password_hash(pw), date.today().isoformat()))
            db().commit()
            session.clear()
            session["uid"] = cur.lastrowid
            flash("Аккаунт создан! Добавьте фото и пару слов о себе", "success")
            # после регистрации ведём в профиль (если человек не шёл на другую страницу)
            return redirect("/profile#settings" if nxt == "/" else nxt)
    return render_template("auth.html", mode="register", next=nxt, form=request.form)


@app.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из аккаунта", "info")
    return redirect("/")


# --------------------------------------------------------------------- API ----


def search_books(q="", genre="", author="", decade=""):
    tokens = [t for t in q.lower().replace("ё", "е").split() if t]
    result = []
    for b in BOOKS:
        if genre and b["genre"] != genre:
            continue
        if author and b["author"] != author:
            continue
        if decade and str(b["year"] // 10 * 10) != decade:
            continue
        hay = f'{b["title"]} {b["author"]} {b["year"]} {b["genre"]}'.lower().replace("ё", "е")
        if all(t in hay for t in tokens):
            result.append(b)
    return result


@app.get("/api/search")
def api_search():
    return jsonify(search_books(request.args.get("q", ""), request.args.get("genre", ""),
                                request.args.get("author", ""), request.args.get("decade", "")))


@app.post("/api/recommend")
def api_recommend():
    d = request.get_json(silent=True) or {}
    mood, genre, length = d.get("mood"), d.get("genre"), d.get("length")
    mood_txt = {"calm": "спокойное настроение", "think": "хочется подумать",
                "thrill": "нужна интрига", "dream": "хочется помечтать"}
    scored = []
    for b in BOOKS:
        score, why = random.random() * 0.6, []
        if mood in b["moods"]:
            score += 3
            why.append(f"подходит под настроение: {mood_txt[mood]}")
        if genre and genre != "any" and b["genre"] == genre:
            score += 4
            why.append(f"жанр: {b['genre'].lower()}")
        if length and length != "any" and length_bucket(b["pages"]) == length:
            score += 2
            why.append(f"{b['pages']} страниц, как вы хотели")
        if b["soon"]:
            score -= 1
        scored.append((score, b, why))
    scored.sort(key=lambda x: -x[0])
    return jsonify([dict(book=b, why=why or ["просто хорошая книга на сегодня"]) for _, b, why in scored[:3]])


@app.post("/api/favorite")
@login_required
def api_favorite():
    d = request.get_json(silent=True) or {}
    kind, item = d.get("kind"), d.get("id")
    if kind not in ("book", "event", "news") or not isinstance(item, int):
        return jsonify(ok=False, error="Некорректный запрос"), 400
    con = db()
    cur = con.execute("DELETE FROM favorites WHERE user_id=? AND kind=? AND item_id=?", (g.user["id"], kind, item))
    fav = cur.rowcount == 0
    if fav:
        con.execute("INSERT INTO favorites VALUES(?,?,?)", (g.user["id"], kind, item))
    con.commit()
    return jsonify(ok=True, fav=fav)


@app.post("/api/borrow")
@login_required
def api_borrow():
    bid = (request.get_json(silent=True) or {}).get("book_id")
    book = BOOK.get(bid) if isinstance(bid, int) else None
    if book is None:
        return jsonify(ok=False, error="Книга не найдена"), 404
    if book["soon"]:
        return jsonify(ok=False, error="Эта книга появится в наличии позже"), 409
    con, uid = db(), g.user["id"]
    if con.execute("SELECT 1 FROM loans WHERE user_id=? AND book_id=? AND returned_at IS NULL", (uid, bid)).fetchone():
        return jsonify(ok=False, error="Эта книга уже у вас на руках"), 409
    on_hands = con.execute("SELECT COUNT(*) FROM loans WHERE user_id=? AND returned_at IS NULL", (uid,)).fetchone()[0]
    if on_hands >= MAX_LOANS:
        return jsonify(ok=False, error=f"Лимит: {MAX_LOANS} книг одновременно. Сдайте одну из взятых"), 409
    today = date.today()
    due = today + timedelta(days=LOAN_DAYS)
    con.execute("INSERT INTO loans(user_id,book_id,taken,due) VALUES(?,?,?,?)", (uid, bid, today.isoformat(), due.isoformat()))
    con.commit()
    return jsonify(ok=True, message=f"«{book['title']}» ваша до {fmt_date(due)}")


def _own_active_loan(loan_id):
    if not isinstance(loan_id, int):
        return None
    return db().execute("SELECT * FROM loans WHERE id=? AND user_id=? AND returned_at IS NULL",
                        (loan_id, g.user["id"])).fetchone()


@app.post("/api/extend")
@login_required
def api_extend():
    loan = _own_active_loan((request.get_json(silent=True) or {}).get("loan_id"))
    if loan is None:
        return jsonify(ok=False, error="Выдача не найдена"), 404
    due = date.fromisoformat(loan["due"])
    if loan["extended"]:
        return jsonify(ok=False, error="Продлить можно только один раз"), 409
    if due < date.today():
        return jsonify(ok=False, error="Просроченную книгу продлить нельзя, сдайте её"), 409
    new_due = due + timedelta(days=EXTEND_DAYS)
    db().execute("UPDATE loans SET due=?, extended=1 WHERE id=?", (new_due.isoformat(), loan["id"]))
    db().commit()
    return jsonify(ok=True, message=f"Срок продлён до {fmt_date(new_due)}")


@app.post("/api/return")
@login_required
def api_return():
    loan = _own_active_loan((request.get_json(silent=True) or {}).get("loan_id"))
    if loan is None:
        return jsonify(ok=False, error="Выдача не найдена"), 404
    db().execute("UPDATE loans SET returned_at=? WHERE id=?", (date.today().isoformat(), loan["id"]))
    db().commit()
    return jsonify(ok=True, message=f"Книга «{BOOK[loan['book_id']]['title']}» сдана. Спасибо!")


@app.post("/api/contact")
def api_contact():
    d = request.get_json(silent=True) or {}
    name, email, text = (str(d.get(k, "")).strip() for k in ("name", "email", "text"))
    if not name or len(text) < 5:
        return jsonify(ok=False, error="Напишите имя и сообщение (минимум 5 символов)"), 400
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify(ok=False, error="Проверьте адрес почты"), 400
    db().execute("INSERT INTO messages(name,email,text) VALUES(?,?,?)", (name[:80], email[:120], text[:2000]))
    db().commit()
    return jsonify(ok=True, message="Сообщение отправлено. Мы ответим в рабочее время")


# ------------------------------------------------------------------ профиль ----
AVATAR_RE = re.compile(r"[0-9]+_[0-9a-f]{16}\.(png|jpg|webp)")


def sniff_image(data):
    """Определяем формат по первым байтам файла, а не по расширению."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def delete_avatar_file(filename):
    if filename and AVATAR_RE.fullmatch(filename):
        try:
            os.remove(os.path.join(UPLOAD_DIR, filename))
        except OSError:
            pass


def user_stats(uid):
    con = db()
    reads = con.execute("SELECT COUNT(DISTINCT book_id) FROM loans WHERE user_id=? AND returned_at IS NOT NULL",
                        (uid,)).fetchone()[0]
    on_hands = con.execute("SELECT COUNT(*) FROM loans WHERE user_id=? AND returned_at IS NULL", (uid,)).fetchone()[0]
    fav_books = con.execute("SELECT COUNT(*) FROM favorites WHERE user_id=? AND kind='book'", (uid,)).fetchone()[0]
    friends = con.execute("SELECT COUNT(*) FROM friendships WHERE status='accepted' AND (requester_id=? OR addressee_id=?)",
                          (uid, uid)).fetchone()[0]
    rows = con.execute("SELECT book_id, MAX(returned_at) AS m FROM loans WHERE user_id=? AND returned_at IS NOT NULL "
                       "GROUP BY book_id ORDER BY m DESC", (uid,)).fetchall()
    genres = Counter(BOOK[r["book_id"]]["genre"] for r in rows)
    return dict(reads=reads, on_hands=on_hands, favs=fav_books, friends=friends,
                recent=[r["book_id"] for r in rows[:6]],
                top_genre=genres.most_common(1)[0][0] if genres else "—")


def relation(me, other):
    """Как связаны два читателя: none / sent / incoming / friends."""
    f = db().execute("SELECT id, requester_id, status FROM friendships "
                     "WHERE (requester_id=? AND addressee_id=?) OR (requester_id=? AND addressee_id=?)",
                     (me, other, other, me)).fetchone()
    if f is None:
        return dict(state="none", id=None)
    if f["status"] == "accepted":
        return dict(state="friends", id=f["id"])
    return dict(state="sent" if f["requester_id"] == me else "incoming", id=f["id"])


_PEOPLE_SQL = """
SELECT f.id AS fid, u.id, u.username, u.name, u.avatar, u.bio,
       (SELECT COUNT(DISTINCT book_id) FROM loans WHERE user_id=u.id AND returned_at IS NOT NULL) AS reads
FROM friendships f
JOIN users u ON u.id = CASE WHEN f.requester_id=? THEN f.addressee_id ELSE f.requester_id END
WHERE {where} ORDER BY u.name"""


def friends_of(uid):
    return db().execute(_PEOPLE_SQL.format(where="f.status='accepted' AND (f.requester_id=? OR f.addressee_id=?)"),
                        (uid, uid, uid)).fetchall()


def incoming_requests(uid):
    return db().execute(_PEOPLE_SQL.format(where="f.status='pending' AND f.addressee_id=?"),
                        (uid, uid)).fetchall()


def outgoing_requests(uid):
    return db().execute(_PEOPLE_SQL.format(where="f.status='pending' AND f.requester_id=?"),
                        (uid, uid)).fetchall()


@app.route("/profile")
@login_required
def profile():
    uid = g.user["id"]
    stats = user_stats(uid)
    created = date.fromisoformat(g.user["created"]) if g.user["created"] else date.today()
    return render_template(
        "profile.html", stats=stats, status=reader_status(stats["reads"], stats["on_hands"]),
        since=long_date(created), friends=friends_of(uid),
        incoming=incoming_requests(uid), outgoing=outgoing_requests(uid))


@app.route("/profile/<username>")
@login_required
def user_profile(username):
    other = db().execute("SELECT id, username, name, avatar, bio, created FROM users WHERE username=?",
                         (username.lower(),)).fetchone()
    if other is None:
        abort(404)
    if other["id"] == g.user["id"]:
        return redirect("/profile")
    stats = user_stats(other["id"])
    created = date.fromisoformat(other["created"]) if other["created"] else date.today()
    return render_template(
        "user.html", other=other, stats=stats, status=reader_status(stats["reads"], stats["on_hands"]),
        since=long_date(created), rel=relation(g.user["id"], other["id"]))


@app.route("/avatar/<filename>")
def avatar_file(filename):
    if not AVATAR_RE.fullmatch(filename):
        abort(404)
    resp = send_from_directory(UPLOAD_DIR, filename, max_age=60 * 60 * 24 * 30)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.errorhandler(413)
def too_large(_e):
    flash("Файл слишком большой: максимум 2 МБ", "error")
    return redirect("/profile#settings")


@app.post("/profile/edit")
@login_required
def profile_edit():
    name = request.form.get("name", "").strip()
    bio = request.form.get("bio", "").strip()
    email = request.form.get("email", "").strip()
    error = None
    if not name or len(name) > 40:
        error = "Имя должно быть от 1 до 40 символов"
    elif len(bio) > 200:
        error = "О себе: не больше 200 символов"
    elif email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        error = "Проверьте адрес почты"
    if error:
        flash(error, "error")
        return redirect("/profile#settings")
    db().execute("UPDATE users SET name=?, bio=?, email=? WHERE id=?", (name, bio, email, g.user["id"]))
    db().commit()
    flash("Профиль сохранён", "success")
    return redirect("/profile")


@app.post("/profile/avatar")
@login_required
def profile_avatar():
    f = request.files.get("avatar")
    if not f or not f.filename:
        flash("Сначала выберите фото", "error")
        return redirect("/profile#settings")
    data = f.read(AVATAR_MAX + 1)
    if len(data) > AVATAR_MAX:
        flash("Файл слишком большой: максимум 2 МБ", "error")
        return redirect("/profile#settings")
    ext = sniff_image(data)
    if ext is None:
        flash("Подойдут только фото в формате PNG, JPG или WebP", "error")
        return redirect("/profile#settings")
    filename = f"{g.user['id']}_{secrets.token_hex(8)}.{ext}"
    with open(os.path.join(UPLOAD_DIR, filename), "wb") as out:
        out.write(data)
    delete_avatar_file(g.user["avatar"])
    db().execute("UPDATE users SET avatar=? WHERE id=?", (filename, g.user["id"]))
    db().commit()
    flash("Фото обновлено", "success")
    return redirect("/profile")


@app.post("/profile/avatar/remove")
@login_required
def profile_avatar_remove():
    delete_avatar_file(g.user["avatar"])
    db().execute("UPDATE users SET avatar=NULL WHERE id=?", (g.user["id"],))
    db().commit()
    flash("Фото удалено", "info")
    return redirect("/profile")


@app.post("/profile/password")
@login_required
def profile_password():
    cur_pw = request.form.get("current", "")
    new_pw = request.form.get("new", "")
    confirm = request.form.get("confirm", "")
    row = db().execute("SELECT password_hash FROM users WHERE id=?", (g.user["id"],)).fetchone()
    if not check_password_hash(row["password_hash"], cur_pw):
        error = "Текущий пароль указан неверно"
    elif len(new_pw) < 6:
        error = "Новый пароль должен быть не короче 6 символов"
    elif new_pw != confirm:
        error = "Новые пароли не совпадают"
    else:
        error = None
    if error:
        flash(error, "error")
        return redirect("/profile#settings")
    db().execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_pw), g.user["id"]))
    db().commit()
    flash("Пароль изменён", "success")
    return redirect("/profile")


# ------------------------------------------------------------------ друзья ----


@app.get("/api/users/search")
@login_required
def api_users_search():
    q = request.args.get("q", "").strip().lstrip("@").casefold()
    if len(q) < 2:
        return jsonify([])
    rows = db().execute("SELECT id, username, name, avatar FROM users WHERE id != ? LIMIT 1000",
                        (g.user["id"],)).fetchall()
    result = []
    for r in rows:
        if q in r["username"] or q in r["name"].casefold():
            rel = relation(g.user["id"], r["id"])
            result.append(dict(id=r["id"], username=r["username"], name=r["name"], avatar=r["avatar"],
                               state=rel["state"], fid=rel["id"]))
            if len(result) >= 8:
                break
    return jsonify(result)


@app.post("/api/friends/request")
@login_required
def api_friend_request():
    username = str((request.get_json(silent=True) or {}).get("username", "")).strip().lower()
    other = db().execute("SELECT id, name FROM users WHERE username=?", (username,)).fetchone()
    if other is None:
        return jsonify(ok=False, error="Читатель не найден"), 404
    me = g.user["id"]
    if other["id"] == me:
        return jsonify(ok=False, error="Это вы сами :)"), 400
    rel = relation(me, other["id"])
    if rel["state"] == "friends":
        return jsonify(ok=False, error="Вы уже друзья"), 409
    if rel["state"] == "sent":
        return jsonify(ok=False, error="Заявка уже отправлена"), 409
    con = db()
    if rel["state"] == "incoming":   # он уже звал нас в друзья: просто принимаем
        con.execute("UPDATE friendships SET status='accepted' WHERE id=?", (rel["id"],))
        con.commit()
        return jsonify(ok=True, message=f"Теперь вы друзья с {other['name']}")
    con.execute("INSERT INTO friendships(requester_id, addressee_id) VALUES(?, ?)", (me, other["id"]))
    con.commit()
    return jsonify(ok=True, message=f"Заявка отправлена: {other['name']}")


@app.post("/api/friends/respond")
@login_required
def api_friend_respond():
    d = request.get_json(silent=True) or {}
    fid, act = d.get("id"), d.get("action")
    me = g.user["id"]
    row = db().execute("SELECT * FROM friendships WHERE id=? AND (requester_id=? OR addressee_id=?)",
                       (fid, me, me)).fetchone() if isinstance(fid, int) else None
    if row is None:
        return jsonify(ok=False, error="Заявка не найдена"), 404
    con = db()
    if act == "accept":
        if row["addressee_id"] != me or row["status"] != "pending":
            return jsonify(ok=False, error="Эту заявку нельзя принять"), 409
        con.execute("UPDATE friendships SET status='accepted' WHERE id=?", (fid,))
        message = "Теперь вы друзья"
    elif act in ("decline", "cancel", "remove"):
        con.execute("DELETE FROM friendships WHERE id=?", (fid,))
        message = {"decline": "Заявка отклонена", "cancel": "Заявка отменена", "remove": "Удалён из друзей"}[act]
    else:
        return jsonify(ok=False, error="Неизвестное действие"), 400
    con.commit()
    return jsonify(ok=True, message=message)


if __name__ == "__main__":
    app.run(debug=True)

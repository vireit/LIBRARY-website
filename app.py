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
import sqlite3
from collections import Counter
from datetime import date, timedelta
from functools import wraps

from flask import (Flask, Response, abort, flash, g, get_flashed_messages,
                   jsonify, redirect, render_template, request, session)
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
  username TEXT UNIQUE NOT NULL, name TEXT NOT NULL, email TEXT, password_hash TEXT NOT NULL);
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


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
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
    con.commit()
    con.close()


init_db()

# ------------------------------------------------------------ сессия/общее ----


@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        g.user = db().execute("SELECT id, username, name, email FROM users WHERE id=?", (uid,)).fetchone()
        if g.user is None:
            session.clear()


@app.context_processor
def inject_globals():
    favs, loaned = [], []
    if g.user:
        favs = [f"{r['kind']}:{r['item_id']}" for r in
                db().execute("SELECT kind, item_id FROM favorites WHERE user_id=?", (g.user["id"],))]
        loaned = [r["book_id"] for r in
                  db().execute("SELECT book_id FROM loans WHERE user_id=? AND returned_at IS NULL", (g.user["id"],))]
    state = dict(user={"name": g.user["name"]} if g.user else None, favs=favs, loaned=loaned,
                 flashes=get_flashed_messages(with_categories=True))
    return dict(current_user=g.user, sm_state=state, books_map={b["id"]: b for b in BOOKS})


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
    if reads >= 25:
        status = "Заядлый читатель"
    elif on_hands >= 3:
        status = "Сфокусированный читатель"
    elif on_hands >= 1:
        status = "Читатель в пути"
    else:
        status = "Начинающий читатель"
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
            cur = db().execute("INSERT INTO users(username,name,email,password_hash) VALUES(?,?,?,?)",
                               (username, name, email, generate_password_hash(pw)))
            db().commit()
            session.clear()
            session["uid"] = cur.lastrowid
            flash("Аккаунт создан. Добро пожаловать в библиотеку!", "success")
            return redirect(nxt)
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


if __name__ == "__main__":
    app.run(debug=True)

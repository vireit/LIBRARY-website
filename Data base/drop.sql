-- =====================================================================
-- ОСТОРОЖНО: удаляет все таблицы сайта вместе с данными.
-- Нужен только для разработки, чтобы начать с чистой базы:
--   python init_db.py --reset
-- =====================================================================
DROP VIEW  IF EXISTS v_books;
DROP TABLE IF EXISTS messages, favorites, loans, events, news, books, users, authors, genres CASCADE;

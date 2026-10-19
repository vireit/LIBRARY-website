/* Сфера Мысли — script.js
   Интерфейс: карточки книг, окна, слайдер, каталог, подбор, избранное, выдача книг. */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const SM = window.SM || { user: null, favs: [], loaned: [], flashes: [] };
  const BOOKS = window.BOOKS || {};
  const INFO = {};
  const plural = (n, f) => { n = Math.abs(n); const m = n % 100, d = n % 10; return m >= 11 && m <= 14 ? f[2] : d === 1 ? f[0] : d >= 2 && d <= 4 ? f[1] : f[2]; };
  const BOOK_FORMS = ['книга', 'книги', 'книг'];

  /* ---------- уведомления ---------- */
  const toast = (msg, type = 'info') => {
    const box = $('#toasts'); if (!box) return;
    const t = document.createElement('div');
    t.className = 'toast ' + type; t.textContent = msg; box.append(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 400); }, 3800);
  };
  const toastAfterReload = msg => sessionStorage.setItem('sm_toast', msg);

  const api = async (url, body) => {
    let r;
    try {
      r = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : undefined);
    } catch { toast('Нет связи с сервером. Проверьте соединение', 'error'); return { ok: false }; }
    let j = {}; try { j = await r.json(); } catch { /* пустой ответ */ }
    if (r.status === 401) { location.href = '/login?next=' + encodeURIComponent(location.pathname + location.search); return { ok: false }; }
    return j;
  };

  /* ---------- модальное окно ---------- */
  const modal = $('#modal'), mBody = $('#modalBody');
  let mTimer, lastFocus;
  const openModal = html => {
    clearTimeout(mTimer);
    if (modal.hidden) lastFocus = document.activeElement;
    mBody.innerHTML = html; modal.hidden = false;
    requestAnimationFrame(() => modal.classList.add('open'));
    document.body.classList.add('no-scroll');
    syncHearts();
    $('.modal-close', modal).focus({ preventScroll: true });
  };
  const closeModal = () => {
    modal.classList.remove('open'); document.body.classList.remove('no-scroll');
    mTimer = setTimeout(() => { modal.hidden = true; mBody.innerHTML = ''; }, 260);
    if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
  };

  /* ---------- избранное ---------- */
  const LS_KEY = 'sm_favs';
  const favs = new Set(SM.user ? SM.favs : JSON.parse(localStorage.getItem(LS_KEY) || '[]'));
  const syncHearts = () => $$('[data-fav]').forEach(b => {
    const on = favs.has(b.dataset.fav);
    b.classList.toggle('active', on); b.textContent = on ? '❤' : '♡';
    b.setAttribute('aria-pressed', on);
  });
  const toggleFav = async key => {
    const [kind, id] = key.split(':');
    if (SM.user) {
      const r = await api('/api/favorite', { kind, id: +id });
      if (!r.ok) return toast(r.error || 'Не удалось сохранить', 'error');
      r.fav ? favs.add(key) : favs.delete(key);
    } else {
      favs.has(key) ? favs.delete(key) : favs.add(key);
      localStorage.setItem(LS_KEY, JSON.stringify([...favs]));
    }
    syncHearts();
    toast(favs.has(key) ? 'Добавлено в избранное' : 'Убрано из избранного');
  };

  /* ---------- карточки книг ---------- */
  const coverHTML = b => `<div class="cover" style="--h:${b.hue}"><span class="cv-top">${esc(b.author)}</span><span class="cv-title">${esc(b.title)}</span><i class="cv-orn"></i><span class="cv-year">${b.year}</span></div>`;
  const badge = b => b.soon ? '<span class="tag soon">Скоро</span>' : SM.loaned.includes(b.id) ? '<span class="tag mine">У вас</span>' : b.new ? '<span class="tag new">Новинка</span>' : '';
  const cardHTML = b => `
    <article class="glass-card book-card tilt reveal" data-book="${b.id}" tabindex="0" role="button" aria-label="${esc(b.title)}, ${esc(b.author)}">
      <div class="book-card-image">${coverHTML(b)}
        <button class="heart" type="button" data-fav="book:${b.id}" aria-label="В избранное">♡</button>
        <button class="card-menu" type="button" aria-label="О книге">•••</button>${badge(b)}
      </div>
      <div class="book-card-info"><h3>${esc(b.title)}</h3><p class="line">${esc(b.line)}</p>
        <div class="book-meta"><span>${esc(b.author)}</span><span>${b.year}</span></div></div>
    </article>`;

  /* появление при прокрутке + наклон карточек */
  const io = 'IntersectionObserver' in window ? new IntersectionObserver(entries => entries.forEach(en => {
    if (!en.isIntersecting) return;
    const el = en.target; io.unobserve(el); el.classList.add('in');
    if (el.classList.contains('tilt')) setTimeout(() => { el.classList.remove('reveal'); el.style.removeProperty('--d'); }, 1200);
  }), { threshold: 0.12, rootMargin: '0px 0px -5% 0px' }) : null;
  const observe = root => $$('.reveal:not([data-obs])', root).forEach((el, i) => {
    el.dataset.obs = 1;
    if (!io) return el.classList.add('in');
    el.style.setProperty('--d', Math.min((i % 6) * 0.07, 0.4) + 's');
    io.observe(el);
  });
  const bindTilt = root => $$('.glass-card:not([data-t])', root).forEach(c => {
    c.dataset.t = 1;
    c.addEventListener('pointermove', e => {
      const r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      c.style.setProperty('--mx', x * 100 + '%'); c.style.setProperty('--my', y * 100 + '%');
      if (c.classList.contains('tilt') && e.pointerType === 'mouse' && !reduce) {
        c.style.setProperty('--rx', ((0.5 - y) * 6).toFixed(2) + 'deg');
        c.style.setProperty('--ry', ((x - 0.5) * 8).toFixed(2) + 'deg');
        c.style.setProperty('--ty', '-4px');
      }
    });
    c.addEventListener('pointerleave', () => ['--rx', '--ry', '--ty'].forEach(p => c.style.removeProperty(p)));
  });
  const prepare = root => { syncHearts(); observe(root); bindTilt(root); };

  const renderBooks = (target, items) => {
    const el = typeof target === 'string' ? $(target) : target;
    if (!el) return;
    const list = items.map(x => (typeof x === 'object' ? x : BOOKS[x])).filter(Boolean);
    list.forEach(b => { BOOKS[b.id] = b; });
    el.innerHTML = list.length ? list.map(cardHTML).join('') : '<div class="empty-state">📚 Ничего не найдено. Попробуйте изменить запрос.</div>';
    prepare(el);
  };

  /* ---------- окно книги ---------- */
  const openBook = id => {
    const b = BOOKS[id]; if (!b) return;
    let action;
    if (b.soon) action = '<button class="btn btn-outline" type="button" disabled>Скоро в наличии</button>';
    else if (SM.loaned.includes(id)) action = '<a class="btn btn-outline" href="/my-books">Книга у вас, к моим книгам</a>';
    else if (!SM.user) action = `<a class="btn btn-primary" href="/login?next=${encodeURIComponent(location.pathname)}">Войти, чтобы взять</a>`;
    else action = `<button class="btn btn-primary" type="button" data-borrow="${id}">Взять на 14 дней</button>`;
    openModal(`<div class="book-modal"><div class="bm-cover">${coverHTML(b)}</div><div class="bm-info">
      <div class="chips"><span class="chip">${esc(b.genre)}</span><span class="chip">${b.year} год</span><span class="chip">${b.pages} стр.</span></div>
      <h2>${esc(b.title)}</h2><p class="bm-author">${esc(b.author)}</p>
      <p class="line">${esc(b.line)}</p><p>${esc(b.desc)}</p>
      <div class="btn-row">${action}<button class="heart heart-lg" type="button" data-fav="book:${id}" aria-label="В избранное">♡</button></div></div></div>`);
  };

  const openInfo = (kind, id) => {
    const it = (INFO[kind] || []).find(x => String(x.id) === String(id)); if (!it) return;
    const favKind = kind === 'events' ? 'event' : kind === 'news' ? 'news' : null;
    const actions = kind === 'docs'
      ? `<a class="btn btn-primary" href="/doc/${esc(it.id)}.txt" download>Скачать</a>`
      : `<button class="heart heart-lg" type="button" data-fav="${favKind}:${it.id}" aria-label="В избранное">♡</button>`;
    openModal(`<div class="info-modal"><span class="tag-pill">${esc(it.tag || it.meta)}</span><h2>${esc(it.title)}</h2>
      ${it.tag && it.meta ? `<div class="meta">${esc(it.meta)}</div>` : ''}<p>${esc(it.body)}</p><div class="btn-row">${actions}</div></div>`);
  };

  /* ---------- слайдер (coverflow) ---------- */
  class Coverflow {
    constructor(el, ids) {
      this.el = el; this.i = 0; this.drag = false;
      this.items = ids.map(id => BOOKS[id]).filter(Boolean);
      if (!this.items.length) return;
      this.build(); this.bind(); this.update();
    }
    build() {
      this.el.innerHTML = `<button class="cf-arrow prev" type="button" aria-label="Назад">←</button>
        <div class="cf-stage">${this.items.map((b, k) => `
          <div class="cf-slide" data-i="${k}">${coverHTML(b)}
            <button class="heart" type="button" data-fav="book:${b.id}" aria-label="В избранное">♡</button>
            <button class="card-menu" type="button" data-more aria-label="О книге">•••</button>
            <div class="cf-info"><h3>${esc(b.title)}</h3><p class="line">${esc(b.line)}</p>
              <div class="book-meta"><span>${b.year} год</span><span>${esc(b.author)}</span></div></div>
          </div>`).join('')}</div>
        <button class="cf-arrow next" type="button" aria-label="Вперёд">→</button>
        <div class="cf-dots">${this.items.map((_, k) => `<button class="cf-dot" type="button" data-d="${k}" aria-label="Книга ${k + 1}"></button>`).join('')}</div>`;
      this.slides = $$('.cf-slide', this.el); this.dots = $$('.cf-dot', this.el);
      this.prev = $('.prev', this.el); this.next = $('.next', this.el);
      syncHearts();
    }
    go(n) { this.i = Math.max(0, Math.min(this.items.length - 1, n)); this.update(); }
    update() {
      this.slides.forEach((s, k) => {
        const o = k - this.i, a = Math.abs(o);
        s.style.setProperty('--o', o); s.style.setProperty('--a', Math.min(a, 3));
        s.style.setProperty('--op', a > 2 ? 0 : 1 - a * 0.25);
        s.style.zIndex = 20 - a; s.style.pointerEvents = a > 2 ? 'none' : 'auto';
        s.classList.toggle('active', o === 0);
      });
      this.dots.forEach((d, k) => d.classList.toggle('on', k === this.i));
      this.prev.disabled = this.i === 0; this.next.disabled = this.i === this.items.length - 1;
    }
    bind() {
      this.prev.addEventListener('click', () => this.go(this.i - 1));
      this.next.addEventListener('click', () => this.go(this.i + 1));
      this.dots.forEach(d => d.addEventListener('click', () => this.go(+d.dataset.d)));
      const stage = $('.cf-stage', this.el); let sx = null;
      stage.addEventListener('pointerdown', e => { sx = e.clientX; this.drag = false; });
      stage.addEventListener('pointerup', e => {
        if (sx === null) return;
        const dx = e.clientX - sx; sx = null;
        if (Math.abs(dx) > 10) this.drag = true;
        if (Math.abs(dx) > 45) this.go(this.i + (dx < 0 ? 1 : -1));
      });
      stage.addEventListener('click', e => {
        if (this.drag) { this.drag = false; return; }
        if (e.target.closest('[data-fav]')) return;
        const s = e.target.closest('.cf-slide'); if (!s) return;
        const k = +s.dataset.i;
        if (k === this.i || e.target.closest('[data-more]')) openBook(this.items[k].id); else this.go(k);
      });
      document.addEventListener('keydown', e => {
        if (!modal.hidden || /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) return;
        if (e.key === 'ArrowLeft') this.go(this.i - 1);
        if (e.key === 'ArrowRight') this.go(this.i + 1);
      });
    }
  }

  /* ---------- каталог ---------- */
  const initCatalog = grid => {
    const q = $('#searchInput'), g = $('#genreFilter'), a = $('#authorFilter'), d = $('#decadeFilter');
    const meta = $('#searchMeta'), reset = $('#resetFilters');
    const url = new URLSearchParams(location.search);
    q.value = url.get('q') || '';
    [[g, 'genre'], [a, 'author'], [d, 'decade']].forEach(([sel, key]) => { const v = url.get(key); if (v && [...sel.options].some(o => o.value === v)) sel.value = v; });
    let seq = 0, timer;
    const run = async () => {
      const my = ++seq, p = new URLSearchParams();
      if (q.value.trim()) p.set('q', q.value.trim());
      if (g.value) p.set('genre', g.value);
      if (a.value) p.set('author', a.value);
      if (d.value) p.set('decade', d.value);
      const filtered = [...p.keys()].length > 0;
      reset.hidden = !filtered; grid.classList.add('loading');
      try {
        const data = await (await fetch('/api/search?' + p)).json();
        if (my !== seq) return;
        renderBooks(grid, data);
        const n = data.length;
        meta.innerHTML = filtered
          ? (n ? `Найдено: <strong>${n}</strong> ${plural(n, BOOK_FORMS)}` : 'Ничего не найдено 😔')
          : `Всего в каталоге: <strong>${n}</strong> ${plural(n, BOOK_FORMS)}`;
        history.replaceState(null, '', filtered ? '?' + p : location.pathname);
      } catch { toast('Не удалось загрузить каталог', 'error'); }
      finally { if (my === seq) grid.classList.remove('loading'); }
    };
    q.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(run, 220); });
    [g, a, d].forEach(s => s.addEventListener('change', run));
    reset.addEventListener('click', () => { q.value = ''; g.value = a.value = d.value = ''; run(); });
    run();
  };

  /* ---------- подбор книги ---------- */
  const WIZ = [
    { key: 'mood', q: 'Какое у вас настроение?', opts: [['calm', '🌿 Спокойное'], ['think', '🧠 Хочу подумать'], ['thrill', '⚡ Нужна интрига'], ['dream', '✨ Хочу помечтать']] },
    { key: 'genre', q: 'Какие жанры вам ближе?', opts: [['any', 'Любые'], ['Роман', 'Роман'], ['Драма', 'Драма'], ['Детектив', 'Детектив'], ['Фантастика', 'Фантастика'], ['Антиутопия', 'Антиутопия'], ['Новелла', 'Новелла']] },
    { key: 'length', q: 'Сколько времени есть на чтение?', opts: [['short', 'Пара вечеров'], ['medium', 'Пара недель'], ['long', 'Готов к большой книге'], ['any', 'Не важно']] },
  ];
  const initWizard = box => {
    const res = $('#wizResults'); let step = 0, answers = {};
    const renderStep = () => {
      const s = WIZ[step];
      box.innerHTML = `<div class="wiz-progress"><i style="width:${step / WIZ.length * 100}%"></i></div>
        <h2 class="wiz-q">${s.q}</h2>
        <div class="wiz-opts">${s.opts.map(([v, t]) => `<button type="button" class="opt" data-v="${esc(v)}">${esc(t)}</button>`).join('')}</div>
        ${step ? '<button type="button" class="wiz-back">Назад</button>' : ''}`;
      requestAnimationFrame(() => { const bar = $('.wiz-progress i', box); if (bar) bar.style.width = (step + 1) / WIZ.length * 100 + '%'; });
    };
    const finish = async () => {
      box.innerHTML = '<p class="lead" style="margin:0 auto">Подбираем книги…</p>';
      const list = await api('/api/recommend', answers);
      if (!Array.isArray(list)) { box.innerHTML = '<p class="lead" style="margin:0 auto">Не получилось подобрать книги.</p><div class="btn-row center"><button class="btn btn-primary" id="wizStart" type="button">Попробовать снова</button></div>'; return; }
      box.innerHTML = '<p class="lead" style="margin:0 auto">Готово! Три книги ждут вас ниже.</p>';
      $('#wizWhy').innerHTML = list.map(x => `<li><b>${esc(x.book.title)}</b>: ${esc(x.why.join(', '))}</li>`).join('');
      renderBooks('#wizGrid', list.map(x => x.book));
      res.hidden = false;
      res.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    };
    box.addEventListener('click', e => {
      if (e.target.closest('#wizStart')) { step = 0; answers = {}; renderStep(); return; }
      if (e.target.closest('.wiz-back')) { step = Math.max(0, step - 1); renderStep(); return; }
      const o = e.target.closest('.opt'); if (!o) return;
      answers[WIZ[step].key] = o.dataset.v; step++;
      step < WIZ.length ? renderStep() : finish();
    });
    $('#wizAgain').addEventListener('click', () => { res.hidden = true; step = 0; answers = {}; renderStep(); box.scrollIntoView({ behavior: 'smooth', block: 'center' }); });
  };

  /* ---------- часы работы ---------- */
  const initHours = el => {
    const tick = () => {
      const parts = new Intl.DateTimeFormat('ru-RU', { timeZone: 'Europe/Moscow', hour: 'numeric', minute: 'numeric', hour12: false }).formatToParts(new Date());
      const mins = (+parts.find(p => p.type === 'hour').value % 24) * 60 + +parts.find(p => p.type === 'minute').value;
      const open = mins >= 480 && mins < 1200;
      el.className = 'status-pill ' + (open ? 'open' : 'closed');
      el.textContent = open ? 'Открыто сейчас, до 20:00' : mins < 480 ? 'Закрыто, откроемся в 8:00' : 'Закрыто, откроемся завтра в 8:00';
    };
    tick(); setInterval(tick, 60000);
  };

  /* ---------- вход и регистрация ---------- */
  const initAuth = () => {
    $$('[data-pw]').forEach(b => b.addEventListener('click', () => {
      const i = b.previousElementSibling, show = i.type === 'password';
      i.type = show ? 'text' : 'password'; b.textContent = show ? 'Скрыть' : 'Показать';
    }));
    const bar = $('#strength'), pw = $('#password'), confirm = $('#confirm');
    if (bar && pw) pw.addEventListener('input', () => {
      const v = pw.value; let s = 0;
      if (v.length >= 6) s++; if (v.length >= 10) s++; if (/[a-zа-я]/.test(v) && /[A-ZА-Я]/.test(v) && /\d/.test(v)) s++; if (/[^\w\s]/.test(v)) s++;
      bar.dataset.s = v ? Math.max(1, s) : 0;
    });
    if (confirm) $('#authForm').addEventListener('submit', e => {
      confirm.setCustomValidity(confirm.value === pw.value ? '' : 'Пароли не совпадают');
      if (!confirm.reportValidity()) e.preventDefault();
    });
    const demo = $('[data-demo]');
    if (demo) demo.addEventListener('click', () => { $('#username').value = 'demo'; $('#password').value = 'demo123'; $('#authForm').requestSubmit(); });
  };

  /* ---------- форма контактов ---------- */
  const initContact = form => form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = $('button[type=submit]', form); btn.disabled = true;
    const r = await api('/api/contact', { name: form.name.value, email: form.email.value, text: form.text.value });
    btn.disabled = false;
    if (r.ok) { toast(r.message, 'success'); form.text.value = ''; } else toast(r.error || 'Не удалось отправить', 'error');
  });

  /* ---------- профиль: вкладки, друзья, аватар ---------- */
  const avatarHTML = u => u.avatar
    ? `<span class="av av-md"><img src="/avatar/${esc(u.avatar)}" alt=""></span>`
    : `<span class="av av-md" style="--ah:${(u.id * 47) % 360}">${esc((u.name || '?')[0].toUpperCase())}</span>`;
  const personRow = u => {
    let btn;
    if (u.state === 'none') btn = `<button class="btn btn-outline" type="button" data-friend-add="${esc(u.username)}">Добавить в друзья</button>`;
    else if (u.state === 'incoming') btn = `<button class="btn btn-primary" type="button" data-friend-add="${esc(u.username)}">Принять заявку</button>`;
    else btn = `<span class="rel-note ${u.state === 'friends' ? 'ok' : ''}">${u.state === 'sent' ? 'Заявка отправлена' : 'Уже друзья'}</span>`;
    return `<div class="person"><a class="person-main" href="/profile/${esc(u.username)}">${avatarHTML(u)}<span><b>${esc(u.name)}</b><small>@${esc(u.username)}</small></span></a><div class="person-actions">${btn}</div></div>`;
  };
  const initTabs = () => {
    const btns = $$('[data-tab]'); if (!btns.length) return;
    const show = name => {
      if (!$(`[data-panel="${name}"]`)) name = 'overview';
      btns.forEach(b => { const on = b.dataset.tab === name; b.classList.toggle('on', on); b.setAttribute('aria-selected', on); });
      $$('[data-panel]').forEach(p => { p.hidden = p.dataset.panel !== name; if (!p.hidden) prepare(p); });
    };
    const go = (name, scroll) => {
      show(name); history.replaceState(null, '', '#' + name);
      if (scroll) $('.tabs-bar').scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    };
    btns.forEach(b => b.addEventListener('click', () => go(b.dataset.tab)));
    $$('[data-tab-go]').forEach(b => b.addEventListener('click', () => go(b.dataset.tabGo, true)));
    show(location.hash.slice(1) || 'overview');
  };
  const initFriendSearch = input => {
    const box = $('#friendResults'); let timer, seq = 0;
    input.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const q = input.value.trim(), my = ++seq;
        if (q.replace('@', '').length < 2) { box.innerHTML = ''; return; }
        const list = await api('/api/users/search?q=' + encodeURIComponent(q));
        if (my !== seq || !Array.isArray(list)) return;
        box.innerHTML = list.length ? list.map(personRow).join('')
          : '<p class="hint">Никого не нашли. Проверьте логин: он написан под именем в профиле друга.</p>';
      }, 260);
    });
  };
  const initAvatarForm = input => {
    const preview = $('#avatarPreview'), save = $('#avatarSave');
    input.addEventListener('change', () => {
      const file = input.files[0]; if (!file) return;
      if (file.size > 2 * 1024 * 1024) { toast('Файл больше 2 МБ, выберите другой', 'error'); input.value = ''; save.disabled = true; return; }
      if (!/^image\/(png|jpeg|webp)$/.test(file.type)) { toast('Подойдут только PNG, JPG или WebP', 'error'); input.value = ''; save.disabled = true; return; }
      preview.innerHTML = `<span class="av av-xl"><img src="${URL.createObjectURL(file)}" alt=""></span>`;
      save.disabled = false;
    });
  };
  const initBioCount = area => {
    const out = $('#bioCount'), upd = () => { out.textContent = area.value.length + '/200'; };
    area.addEventListener('input', upd); upd();
  };

  /* ---------- общие обработчики ---------- */
  const action = async (btn, url, body) => {
    btn.disabled = true;
    const r = await api(url, body);
    if (r.ok) { toastAfterReload(r.message); location.reload(); }
    else { toast(r.error || 'Не получилось', 'error'); btn.disabled = false; }
  };

  document.addEventListener('click', async e => {
    const t = e.target;
    if (t.closest('[data-close]')) return closeModal();
    const fav = t.closest('[data-fav]');
    if (fav) { e.preventDefault(); return toggleFav(fav.dataset.fav); }
    const ext = t.closest('[data-extend]');
    if (ext) return action(ext, '/api/extend', { loan_id: +ext.dataset.extend });
    const ret = t.closest('[data-return]');
    if (ret) return action(ret, '/api/return', { loan_id: +ret.dataset.return });
    const bor = t.closest('[data-borrow]');
    if (bor) {
      const id = +bor.dataset.borrow; bor.disabled = true;
      const r = await api('/api/borrow', { book_id: id });
      if (!r.ok) { toast(r.error || 'Не получилось взять книгу', 'error'); bor.disabled = false; return; }
      SM.loaned.push(id);
      if (location.pathname === '/my-books') { toastAfterReload(r.message); location.reload(); return; }
      toast(r.message, 'success'); openBook(id); return;
    }
    const fadd = t.closest('[data-friend-add]');
    if (fadd) return action(fadd, '/api/friends/request', { username: fadd.dataset.friendAdd });
    const fact = t.closest('[data-friend-act]');
    if (fact) { const [id, act] = fact.dataset.friendAct.split(':'); return action(fact, '/api/friends/respond', { id: +id, action: act }); }
    const inf = t.closest('[data-info]');
    if (inf) { const [k, id] = inf.dataset.info.split(':'); return openInfo(k, id); }
    const bk = t.closest('[data-book]');
    if (bk) openBook(+bk.dataset.book);
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !modal.hidden) closeModal();
    if ((e.key === 'Enter' || e.key === ' ') && e.target.matches?.('.book-card')) { e.preventDefault(); openBook(+e.target.dataset.book); }
  });

  /* плавный переход между страницами */
  document.addEventListener('click', e => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const a = e.target.closest('a[href]');
    if (!a || a.target || a.hasAttribute('download')) return;
    const u = new URL(a.href, location.href);
    if (u.origin !== location.origin || u.pathname.startsWith('/doc/') || (u.pathname === location.pathname && u.search === location.search)) return;
    e.preventDefault(); document.body.classList.add('leaving');
    setTimeout(() => { location.href = u.href; }, 170);
  });
  addEventListener('pageshow', () => document.body.classList.remove('leaving'));

  /* ---------- запуск ---------- */
  document.addEventListener('DOMContentLoaded', () => {
    const header = $('#siteHeader'), burger = $('#burger');
    const onScroll = () => header.classList.toggle('scrolled', scrollY > 20);
    onScroll(); addEventListener('scroll', onScroll, { passive: true });
    burger.addEventListener('click', () => { const open = header.classList.toggle('open'); burger.setAttribute('aria-expanded', open); });

    (SM.flashes || []).forEach(([cat, msg]) => toast(msg, cat));
    const later = sessionStorage.getItem('sm_toast');
    if (later) { sessionStorage.removeItem('sm_toast'); toast(later, 'success'); }

    $$('[data-books]').forEach(el => renderBooks(el, JSON.parse(el.dataset.books)));
    $$('[data-cf]').forEach(el => new Coverflow(el, JSON.parse(el.dataset.cf)));
    const grid = $('[data-catalog]'); if (grid) initCatalog(grid);
    const wiz = $('#wizard'); if (wiz) initWizard(wiz);
    const hrs = $('#openNow'); if (hrs) initHours(hrs);
    const cf = $('#contactForm'); if (cf) initContact(cf);
    if ($('#authForm')) initAuth();
    initTabs();
    const fs = $('#friendSearch'); if (fs) initFriendSearch(fs);
    const av = $('#avatarInput'); if (av) initAvatarForm(av);
    const bio = $('#pBio'); if (bio) initBioCount(bio);
    prepare(document);
  });

  window.App = { renderBooks, Coverflow, openBook, info: (kind, list) => { INFO[kind] = list; } };
})();

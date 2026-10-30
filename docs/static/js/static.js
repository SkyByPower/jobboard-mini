/* JumysBoard — GitHub Pages статикалық көшірмесі үшін ғана (freeze.py қосады).
   Сервер жоқ болғандықтан: сүзгі/сұрыптау браузерде, кіру демо аккаунттармен,
   өзгерістер сақталмайды. window.STATIC_SITE = {root, lang, state, path}. */
(() => {
  "use strict";
  const S = window.STATIC_SITE || { root: "./", lang: "kk", state: "guest", path: "/" };
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const I18N = (s) => (window.I18N && window.I18N[s]) || s;
  const toast = (msg, cat = "info") => (window.showToast ? window.showToast(msg, cat) : alert(msg));

  const STR = {
    kk: {
      banner: "Бұл — сайттың статикалық демо нұсқасы: кіру демо аккаунттармен жұмыс істейді, өзгерістер сақталмайды.",
      readonly: "Демо нұсқа: өзгерістер сақталмайды. Толық жұмыс үшін жобаны компьютерде іске қосыңыз.",
      loginOk: "Қош келдіңіз! Сіз демо аккаунтпен кірдіңіз.",
      loginBad: "Демо нұсқада тек admin / admin123 немесе aruzhan / user123 жұмыс істейді.",
      register: "Демо нұсқада тіркелу сақталмайды. aruzhan / user123 арқылы кіріңіз.",
      logout: "Сіз жүйеден шықтыңыз.",
      filterNA: "Демо нұсқада бұл іздеу қолжетімсіз.",
      clearAll: "Барлығын тазалау",
      salary: (n) => `${n} ₸-ден`,
    },
    ru: {
      banner: "Это статическая демо-версия сайта: вход работает с демо-аккаунтами, изменения не сохраняются.",
      readonly: "Демо-версия: изменения не сохраняются. Для полной работы запустите проект на компьютере.",
      loginOk: "Добро пожаловать! Вы вошли в демо-аккаунт.",
      loginBad: "В демо-версии работают только admin / admin123 и aruzhan / user123.",
      register: "В демо-версии регистрация не сохраняется. Войдите как aruzhan / user123.",
      logout: "Вы вышли из аккаунта.",
      filterNA: "В демо-версии этот поиск недоступен.",
      clearAll: "Сбросить всё",
      salary: (n) => `от ${n} ₸`,
    },
  }[S.lang === "ru" ? "ru" : "kk"];

  const langPrefix = S.lang === "ru" ? "ru/" : "";
  const store = (k, v) => {
    try { if (v === undefined) { const x = sessionStorage.getItem(k); sessionStorage.removeItem(k); return x; } sessionStorage.setItem(k, v); }
    catch (e) { return null; }
  };
  const go = (path, msg, cat) => { if (msg) store("static-flash", `${cat}|${msg}`); location.href = S.root + path; };

  /* ---------- келесі бетке қалдырылған хабарлама және бірінші кірудегі ескерту */
  const flash = store("static-flash");
  if (flash) { const [cat, ...m] = flash.split("|"); toast(m.join("|"), cat); }
  try {
    if (!localStorage.getItem("static-banner")) { toast(STR.banner, "info"); localStorage.setItem("static-banner", "1"); }
  } catch (e) { /* storage жоқ */ }

  /* ---------- формалар: серверсіз өңдеу */
  document.addEventListener("submit", (e) => {
    const form = e.target;
    if ((form.getAttribute("method") || "get").toLowerCase() !== "post") return;
    if (form.dataset.confirm && !form.dataset.confirmed) return; // алдымен растау модалы (main.js)
    e.preventDefault();
    e.stopImmediatePropagation();
    const action = form.dataset.staticAction || S.path;

    if (S.path === "/auth/login" && action === "/auth/login") {
      const login = ($("#login")?.value || "").trim().toLowerCase();
      const pass = $("#password")?.value || "";
      if ((login === "admin" || login === "admin@jobboard.kz") && pass === "admin123") return go(`${langPrefix}a/admin/`, STR.loginOk, "success");
      if ((login === "aruzhan" || login === "aruzhan@mail.kz") && pass === "user123") return go(`${langPrefix}u/`, STR.loginOk, "success");
      return toast(STR.loginBad, "danger");
    }
    if (action === "/auth/logout") return go(langPrefix, STR.logout, "info");
    if (action === "/auth/register") return toast(STR.register, "info");
    if (form.classList.contains("save-form")) {
      const btn = $("button", form);
      const on = !btn.classList.contains("on");
      btn.classList.toggle("on", on);
      btn.innerHTML = `<i class="bi bi-heart${on ? "-fill" : ""}"></i>`;
      btn.classList.remove("pop"); void btn.offsetWidth; btn.classList.add("pop");
      return toast(on ? I18N("Сақталғандарға қосылды") : I18N("Сақталғандардан алынды"), on ? "success" : "info");
    }
    toast(STR.readonly, "warning");
  }, true);

  /* ---------- сұраныс параметрлері: freeze.py-мен бірдей кілт (FNV-1a) */
  const canonical = (search) => Array.from(new URLSearchParams(search))
    .filter(([k, v]) => v && k !== "csrf_token")
    .sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0))
    .map(([k, v]) => `${k}=${v}`).join("&");
  const fnv = (s) => {
    let h = 0x811c9dc5;
    for (const b of new TextEncoder().encode(s)) h = Math.imul(h ^ b, 0x01000193) >>> 0;
    return h.toString(16).padStart(8, "0");
  };

  if (S.path === "/vacancies") {
    filterVacancies();
  } else if (location.search) {
    // басқа беттер: алдын ала сақталған нұсқасы болса, соған ауысамыз
    const key = canonical(location.search);
    if (key) {
      const file = `q-${fnv(key)}.html`;
      fetch(file, { method: "HEAD" })
        .then((r) => (r.ok ? location.replace(file + location.hash) : toast(STR.filterNA, "warning")))
        .catch(() => toast(STR.filterNA, "warning"));
    }
  }

  /* ---------- вакансиялар: іздеу, сүзгі, сұрыптау, беттеу браузерде */
  function filterVacancies() {
    const form = document.getElementById("filterForm");
    const grid = $("section [data-stagger]");
    if (!form || !grid) return;
    const params = new URLSearchParams(location.search);
    const get = (k) => (params.get(k) || "").trim();
    const types = params.getAll("type");
    const sort = get("sort") || "new";

    Array.from(form.elements).forEach((el) => {
      if (!el.name) return;
      if (el.type === "checkbox") el.checked = types.includes(el.value);
      else if (el.name === "sort") el.value = sort;
      else if (params.has(el.name)) el.value = get(el.name);
    });

    const q = get("q").toLowerCase();
    const city = get("city"), exp = get("experience"), company = get("company");
    const salary = parseInt(get("salary_from"), 10) || 0;
    const num = (el, k) => parseInt(el.dataset[k], 10) || 0;
    const cards = Array.from(grid.children);
    const found = cards.filter((c) =>
      (!q || c.dataset.search.includes(q)) &&
      (!city || c.dataset.city === city) &&
      (!company || c.dataset.company === company) &&
      (!types.length || types.includes(c.dataset.type)) &&
      (!exp || c.dataset.exp === exp) &&
      (!salary || num(c, "salHi") >= salary));

    const by = {
      new: (a, b) => num(b, "created") - num(a, "created"),
      old: (a, b) => num(a, "created") - num(b, "created"),
      salary_desc: (a, b) => num(b, "salHi") - num(a, "salHi"),
      salary_asc: (a, b) => num(a, "salLo") - num(b, "salLo"),
      title: (a, b) => (a.dataset.title < b.dataset.title ? -1 : a.dataset.title > b.dataset.title ? 1 : 0),
    }[sort] || ((a, b) => num(b, "created") - num(a, "created"));
    found.sort((a, b) => by(a, b) || num(b, "id") - num(a, "id"));

    const per = 6;
    const pages = Math.max(1, Math.ceil(found.length / per));
    const page = Math.min(Math.max(parseInt(get("page"), 10) || 1, 1), pages);
    const visible = found.slice((page - 1) * per, page * per);
    cards.forEach((c) => { c.style.display = "none"; });
    visible.forEach((c, i) => { c.style.display = ""; c.style.setProperty("--i", i); grid.appendChild(c); });

    const count = $(".toolbar .count b");
    if (count) count.textContent = found.length;

    const urlWith = (changes) => {
      const p = new URLSearchParams(location.search);
      Object.entries(changes).forEach(([k, v]) => (v == null ? p.delete(k) : p.set(k, v)));
      const s = p.toString();
      return s ? `?${s}` : "./";
    };
    $$(".seg-control a").forEach((a) => {
      const key = new URL(a.href).searchParams.get("sort") || "new";
      a.href = urlWith({ sort: key, page: null });
      a.classList.toggle("on", key === sort);
    });

    // беттеу (_macros.html pagination сияқты белгілеу)
    const section = grid.parentElement;
    $(".pagination", section)?.remove();
    if (pages > 1) {
      const nav = document.createElement("nav");
      nav.className = "pagination";
      const item = (n, html, cls) => (n ? `<a href="${urlWith({ page: n })}">${html}</a>` : `<span class="${cls}">${html}</span>`);
      let html = item(page > 1 && page - 1, '<i class="bi bi-chevron-left"></i>', "disabled");
      for (let n = 1; n <= pages; n++) html += n === page ? `<span class="current" aria-current="page">${n}</span>` : item(n, n);
      html += item(page < pages && page + 1, '<i class="bi bi-chevron-right"></i>', "disabled");
      nav.innerHTML = html;
      grid.after(nav);
    }

    // таңдалған сүзгілер чиптері
    const chips = [];
    if (get("q")) chips.push(`«${get("q")}»`);
    const optText = (name) => form.elements[name]?.selectedOptions?.[0]?.textContent.trim();
    if (city) chips.push(optText("city"));
    $$("input[type=checkbox][name=type]").filter((c) => c.checked).forEach((c) => chips.push(c.parentElement.textContent.trim()));
    if (exp) chips.push(optText("experience"));
    if (salary) chips.push(STR.salary(salary));
    if (chips.length) {
      const box = document.createElement("div");
      box.className = "chips";
      chips.filter(Boolean).forEach((t) => box.appendChild(Object.assign(document.createElement("span"), { className: "chip", textContent: t })));
      const clear = Object.assign(document.createElement("a"), { className: "chip", href: "./", innerHTML: `${STR.clearAll} <i class="bi bi-x"></i>` });
      clear.style.cssText = "background:var(--surface-2);color:var(--muted)";
      box.appendChild(clear);
      grid.before(box);
    }

    if (!found.length) {
      const empty = document.createElement("div");
      empty.className = "card empty reveal zoom in";
      empty.innerHTML = `<div class="ico"><i class="bi bi-search"></i></div><h3></h3><p class="muted"></p><a class="btn btn-primary" href="./"></a>`;
      $("h3", empty).textContent = I18N("Ештеңе табылмады");
      $("p", empty).textContent = I18N("Сүзгі шарттарын өзгертіп көріңіз.");
      $("a", empty).textContent = I18N("Сүзгіні тазалау");
      grid.after(empty);
    }
  }
})();

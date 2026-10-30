/* JumysBoard — интерфейс анимациялары мен шағын интерактивтілік */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  // аударма: сервер window.I18N сөздігін береді (кілт — қазақша мәтін)
  const T = (s, vars = {}) => Object.entries(vars).reduce(
    (r, [k, v]) => r.replace(`{${k}}`, v), (window.I18N && window.I18N[s]) || s);

  /* ---------- тема (ашық / қараңғы) */
  const root = document.documentElement;
  const themeBtn = $("#themeToggle");
  const syncThemeIcon = () => {
    if (themeBtn) themeBtn.innerHTML = root.dataset.theme === "dark" ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
  };
  syncThemeIcon();
  themeBtn?.addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    try { localStorage.setItem("theme", root.dataset.theme); } catch (e) { /* storage жоқ */ }
    syncThemeIcon();
  });

  /* ---------- тіл ауыстырғыш: алдымен «пилюля» сырғиды, сосын бет ауысады */
  document.addEventListener("click", (e) => {
    const link = e.target.closest(".lang-switch a");
    if (!link || link.classList.contains("on") || e.ctrlKey || e.metaKey) return;
    e.preventDefault();
    const sw = link.parentElement;
    sw.classList.add("switching");
    sw.dataset.lang = link.dataset.code;
    document.querySelector("main")?.animate(
      [{ opacity: 1, transform: "none" }, { opacity: 0, transform: "translateY(8px)" }],
      { duration: reduceMotion ? 0 : 260, fill: "forwards", easing: "ease-in" });
    setTimeout(() => { location.href = link.href; }, reduceMotion ? 0 : 280);
  });

  /* ---------- навбар, прогресс, жоғарыға */
  const nav = $(".nav");
  const progress = $(".scroll-progress");
  const toTop = $(".to-top");
  const onScroll = () => {
    const y = window.scrollY;
    nav?.classList.toggle("scrolled", y > 10);
    toTop?.classList.toggle("show", y > 600);
    if (progress) {
      const h = document.documentElement.scrollHeight - innerHeight;
      progress.style.transform = `scaleX(${h > 0 ? y / h : 0})`;
    }
  };
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();
  toTop?.addEventListener("click", () => scrollTo({ top: 0, behavior: "smooth" }));

  $(".nav-burger")?.addEventListener("click", (e) => {
    $(".nav-links").classList.toggle("open");
    e.currentTarget.innerHTML = $(".nav-links").classList.contains("open") ? '<i class="bi bi-x-lg"></i>' : '<i class="bi bi-list"></i>';
  });

  const userMenu = $(".user-menu");
  userMenu?.querySelector(".user-chip").addEventListener("click", (e) => {
    e.stopPropagation();
    userMenu.classList.toggle("open");
  });
  document.addEventListener("click", (e) => {
    if (userMenu && !userMenu.contains(e.target)) userMenu.classList.remove("open");
  });

  /* ---------- scroll reveal (кезекпен пайда болу) */
  const revealEls = $$(".reveal");
  if ("IntersectionObserver" in window && !reduceMotion) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
    $$("[data-stagger]").forEach((parent) => {
      Array.from(parent.children).forEach((child, i) => child.style.setProperty("--i", i % 12));
    });
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("in"));
  }

  /* ---------- сандарды санау анимациясы */
  const animateCount = (el) => {
    const target = parseInt(el.dataset.count, 10) || 0;
    if (reduceMotion) { el.textContent = target.toLocaleString("ru-RU"); return; }
    const dur = 1400, start = performance.now();
    const step = (t) => {
      const p = Math.min((t - start) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 4);
      el.textContent = Math.round(target * eased).toLocaleString("ru-RU");
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  const countIO = "IntersectionObserver" in window ? new IntersectionObserver((entries) => {
    entries.forEach((en) => { if (en.isIntersecting) { animateCount(en.target); countIO.unobserve(en.target); } });
  }) : null;
  $$("[data-count]").forEach((el) => (countIO ? countIO.observe(el) : animateCount(el)));

  /* ---------- прогресс-жолақтар (админ статистика) */
  const barIO = "IntersectionObserver" in window ? new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting) { en.target.style.width = en.target.dataset.width; barIO.unobserve(en.target); }
    });
  }) : null;
  $$("[data-width]").forEach((el) => (barIO ? barIO.observe(el) : (el.style.width = el.dataset.width)));

  /* ---------- hero сөз ауыстырғыш */
  const rot = $(".rotator");
  if (rot && !reduceMotion) {
    const words = $$("span", rot);
    let i = 0;
    setInterval(() => {
      const cur = words[i];
      cur.classList.remove("on"); cur.classList.add("out");
      setTimeout(() => cur.classList.remove("out"), 600);
      i = (i + 1) % words.length;
      words[i].classList.add("on");
    }, 2400);
  }

  /* ---------- spotlight: тышқан артынан жарық */
  document.addEventListener("pointermove", (e) => {
    const card = e.target.closest?.(".spotlight");
    if (!card) return;
    const r = card.getBoundingClientRect();
    card.style.setProperty("--mx", `${e.clientX - r.left}px`);
    card.style.setProperty("--my", `${e.clientY - r.top}px`);
  }, { passive: true });

  /* ---------- ripple эффекті */
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn");
    if (!btn || reduceMotion) return;
    const r = btn.getBoundingClientRect();
    const size = Math.max(r.width, r.height);
    const s = document.createElement("span");
    s.className = "ripple";
    s.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX - r.left - size / 2}px;top:${e.clientY - r.top - size / 2}px`;
    btn.appendChild(s);
    setTimeout(() => s.remove(), 650);
  });

  /* ---------- toast хабарламалар */
  const closeToast = (t) => { t.classList.add("hide"); setTimeout(() => t.remove(), 420); };
  window.showToast = (msg, cat = "info") => {
    const icons = { success: "check-lg", danger: "x-lg", warning: "exclamation-lg", info: "info-lg" };
    const wrap = $(".toasts") || document.body.appendChild(Object.assign(document.createElement("div"), { className: "toasts" }));
    const t = document.createElement("div");
    t.className = `toast ${cat}`;
    t.setAttribute("role", "status");
    t.innerHTML = `<div class="t-ico"><i class="bi bi-${icons[cat] || icons.info}"></i></div><div class="t-msg"></div><button class="t-close" aria-label="${T("Жабу")}"><i class="bi bi-x"></i></button><div class="t-bar"></div>`;
    t.querySelector(".t-msg").textContent = msg;
    wrap.appendChild(t);
    bindToast(t);
  };
  const bindToast = (t) => {
    let timer = setTimeout(() => closeToast(t), 5000);
    t.addEventListener("mouseenter", () => clearTimeout(timer));
    t.addEventListener("mouseleave", () => { timer = setTimeout(() => closeToast(t), 1800); });
    t.querySelector(".t-close").addEventListener("click", () => closeToast(t));
  };
  $$(".toast").forEach(bindToast);

  /* ---------- растау модалы (өшіру т.б.) */
  const modal = $("#confirmModal");
  let pendingForm = null;
  const openModal = (form) => {
    pendingForm = form;
    $("#confirmText").textContent = form.dataset.confirm;
    $("#confirmTitle").textContent = form.dataset.confirmTitle || T("Сенімдісіз бе?");
    modal.classList.add("open");
    setTimeout(() => $("#confirmYes").focus(), 50);
  };
  const closeModal = () => { modal.classList.remove("open"); pendingForm = null; };
  document.addEventListener("submit", (e) => {
    const form = e.target;
    if (form.dataset.confirm && !form.dataset.confirmed && modal) {
      e.preventDefault();
      openModal(form);
    }
  });
  $("#confirmYes")?.addEventListener("click", () => {
    if (!pendingForm) return;
    const f = pendingForm;
    f.dataset.confirmed = "1";
    closeModal();
    f.requestSubmit ? f.requestSubmit() : f.submit();
  });
  $$("[data-close-modal]").forEach((el) => el.addEventListener("click", closeModal));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && modal?.classList.contains("open")) closeModal(); });

  /* ---------- CV dropzone: клиент жағындағы тексеру */
  $$(".dropzone").forEach((dz) => {
    const input = $("input[type=file]", dz);
    const maxMb = parseFloat(dz.dataset.maxMb || "5");
    const show = () => {
      const f = input.files[0];
      dz.classList.remove("invalid", "has-file");
      $(".dz-error", dz.parentElement)?.remove();
      if (!f) return;
      let err = "";
      if (!/\.pdf$/i.test(f.name)) err = T("Тек PDF файлдар рұқсат етіледі.");
      else if (f.size > maxMb * 1024 * 1024) err = T("Файл {mb} МБ-тан аспауы керек.", { mb: maxMb });
      if (err) {
        input.value = "";
        dz.classList.add("invalid");
        dz.insertAdjacentHTML("afterend", `<div class="error dz-error"><i class="bi bi-exclamation-circle"></i>${err}</div>`);
        return;
      }
      $(".dz-name", dz).textContent = f.name;
      $(".dz-size", dz).textContent = f.size < 1024 ? `${f.size} Б` : f.size < 1048576 ? `${(f.size / 1024).toFixed(0)} КБ` : `${(f.size / 1048576).toFixed(1)} МБ`;
      dz.closest(".field")?.classList.remove("has-error");
      $$(".error:not(.dz-error)", dz.closest(".field")).forEach((e) => e.remove());
      dz.classList.add("has-file");
    };
    input.addEventListener("change", show);
    ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("drag"); }));
    ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, () => dz.classList.remove("drag")));
    dz.addEventListener("drop", (e) => {
      e.preventDefault();
      if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; show(); }
    });
  });

  /* ---------- сервер қатесін пайдаланушы түзеткенде алып тастау */
  document.addEventListener("input", (e) => {
    const f = e.target.closest?.(".field.has-error");
    if (f && !e.target.matches("input[type=file]")) {
      f.classList.remove("has-error");
      $$(".error", f).forEach((el) => el.remove());
    }
  });

  /* ---------- таңба санағыш */
  $$("textarea[maxlength], input[data-counter]").forEach((el) => {
    const max = parseInt(el.getAttribute("maxlength"), 10);
    if (!max) return;
    const c = document.createElement("div");
    c.className = "counter";
    el.after(c);
    const upd = () => { c.textContent = `${el.value.length} / ${max}`; c.classList.toggle("over", el.value.length >= max); };
    el.addEventListener("input", upd);
    upd();
  });

  /* ---------- құпиясөзді көрсету + күші */
  $$(".pw-toggle").forEach((b) => b.addEventListener("click", () => {
    const inp = b.parentElement.querySelector("input");
    inp.type = inp.type === "password" ? "text" : "password";
    b.innerHTML = inp.type === "password" ? '<i class="bi bi-eye"></i>' : '<i class="bi bi-eye-slash"></i>';
  }));
  const pw = $("input[data-strength]");
  const meter = $(".pw-meter span");
  if (pw && meter) {
    pw.addEventListener("input", () => {
      const v = pw.value;
      let s = 0;
      if (v.length >= 6) s++;
      if (v.length >= 10) s++;
      if (/\d/.test(v) && /\D/.test(v)) s++;
      if (/[A-ZА-ЯӘҒҚҢӨҰҮҺІ]/.test(v) && /[^A-Za-z0-9А-Яа-яӘәҒғҚқҢңӨөҰұҮүҺһІі]/.test(v)) s++;
      const colors = ["#f0466b", "#f0466b", "#f5a524", "#10c9b4", "#12b981"];
      meter.style.width = `${(s / 4) * 100}%`;
      meter.style.background = colors[s];
    });
  }

  /* ---------- демо аккаунттарды толтыру */
  $$("[data-demo]").forEach((b) => b.addEventListener("click", () => {
    const [login, pass] = b.dataset.demo.split(":");
    const l = $("#login"), p = $("#password");
    if (l && p) { l.value = login; p.value = pass; l.dispatchEvent(new Event("input")); p.focus(); }
  }));

  /* ---------- вакансияны сақтау (AJAX) */
  document.addEventListener("submit", async (e) => {
    const form = e.target.closest(".save-form");
    if (!form) return;
    e.preventDefault();
    const btn = $("button", form);
    try {
      const res = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });
      if (res.redirected || res.status === 401) { location.href = res.url; return; }
      if (!res.ok) throw new Error(res.status);
      const data = await res.json();
      btn.classList.toggle("on", data.saved);
      btn.innerHTML = `<i class="bi bi-heart${data.saved ? "-fill" : ""}"></i>`;
      btn.classList.remove("pop"); void btn.offsetWidth; btn.classList.add("pop");
      showToast(data.saved ? T("Сақталғандарға қосылды") : T("Сақталғандардан алынды"), data.saved ? "success" : "info");
    } catch (err) {
      showToast(T("Қате орын алды, қайталап көріңіз."), "danger");
    }
  });

  /* ---------- сүзгі: select/checkbox өзгергенде автоматты жіберу */
  // өрістер форманың ішінде немесе form="..." атрибуты арқылы байланысуы мүмкін
  document.addEventListener("change", (e) => {
    const f = e.target.form;
    if (f && "autosubmit" in f.dataset && e.target.matches("select, input[type=checkbox], input[type=radio]")) {
      f.requestSubmit ? f.requestSubmit() : f.submit();
    }
  });
  $(".filter-toggle")?.addEventListener("click", () => $(".filters").classList.toggle("open"));

  /* ---------- API токенін көшіру */
  $$("[data-copy]").forEach((b) => b.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(b.dataset.copy); showToast(T("Көшірілді!"), "success"); }
    catch (e) { showToast(T("Көшіру мүмкін болмады"), "warning"); }
  }));
})();

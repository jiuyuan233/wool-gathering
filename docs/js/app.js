// 薅羊毛情报站前端逻辑
(function () {
  "use strict";

  const ACCENT = {
    ai: "#4a9eff",
    games: "#4ade80",
  };

  let ALL = [];
  let META = null;
  let currentFilter = "all";

  async function fetchJSON(path) {
    const r = await fetch(path, { cache: "no-store" });
    if (!r.ok) throw new Error(`${path}: ${r.status}`);
    return r.json();
  }

  function fmtDate(s) {
    if (!s) return "?";
    return s;
  }

  function daysBetween(a, b) {
    if (!a || !b) return null;
    const d1 = new Date(a), d2 = new Date(b);
    if (isNaN(d1) || isNaN(d2)) return null;
    return Math.round((d2 - d1) / 86400000);
  }

  function parseD(s) {
    if (!s) return null;
    const d = new Date(s);
    return isNaN(d) ? null : d;
  }

  function renderMeta() {
    const bar = document.getElementById("metaBar");
    if (!META) {
      bar.innerHTML = '<span class="meta-item">⏱ 暂无元数据</span>';
      return;
    }
    const gen = META.generated_at ? new Date(META.generated_at).toLocaleString("zh-CN", { hour12: false }) : "?";
    const cats = META.by_category || {};
    const ai = cats.ai || {}, gm = cats.games || {};
    bar.innerHTML = `
      <span class="meta-item">⏱ 更新于 ${gen}</span>
      <span class="meta-item">🤖 AI: ${ai.active || 0} 进行中 / ${ai.total || 0} 总计</span>
      <span class="meta-item">🎮 游戏: ${gm.active || 0} 进行中 / ${gm.total || 0} 总计</span>
      <span class="meta-item">📦 共 ${META.total || 0} 条</span>
    `;
  }

  function getFiltered() {
    let list = ALL.slice();
    if (currentFilter === "ai") list = list.filter(a => a.category === "ai");
    else if (currentFilter === "games") list = list.filter(a => a.category === "games");
    else if (currentFilter === "active") list = list.filter(a => a.status === "active");
    else if (currentFilter === "upcoming") list = list.filter(a => a.status === "upcoming");
    // 排序：active 优先
    const order = { active: 0, upcoming: 1, ended: 2 };
    list.sort((a, b) => (order[a.status] - order[b.status]) || ((a.end_date || "").localeCompare(b.end_date || "")));
    return list;
  }

  function renderTimeline() {
    const root = document.getElementById("timeline");
    const showEnded = document.getElementById("showEnded").checked;
    const showUpcoming = document.getElementById("showUpcoming").checked;
    let list = getFiltered();
    if (!showEnded) list = list.filter(a => a.status !== "ended");
    if (!showUpcoming) list = list.filter(a => a.status !== "upcoming");

    if (!list.length) {
      root.innerHTML = '<div class="timeline-empty">暂无活动</div>';
      return;
    }

    // 计算时间轴范围：取所有活动起止的 min/max，前后各留 1 天
    let minD = null, maxD = null;
    list.forEach(a => {
      const s = parseD(a.start_date), e = parseD(a.end_date);
      if (s) { if (!minD || s < minD) minD = s; if (!maxD || s > maxD) maxD = s; }
      if (e) { if (!minD || e < minD) minD = e; if (!maxD || e > maxD) maxD = e; }
    });
    if (!minD || !maxD) {
      root.innerHTML = '<div class="timeline-empty">活动缺少日期信息</div>';
      return;
    }
    minD = new Date(minD); minD.setDate(minD.getDate() - 1);
    maxD = new Date(maxD); maxD.setDate(maxD.getDate() + 1);
    const totalMs = maxD - minD;
    const today = META && META.today ? parseD(META.today) : new Date();

    function pct(d) {
      if (!d) return 0;
      return Math.max(0, Math.min(100, ((d - minD) / totalMs) * 100));
    }

    // 生成刻度（5 等分）
    const ticks = [];
    for (let i = 0; i <= 5; i++) {
      const t = new Date(minD.getTime() + (totalMs * i) / 5);
      ticks.push({ pct: i * 20, label: t.toISOString().slice(0, 10) });
    }

    let html = '<div class="tl-axis">';
    html += '<div class="tl-header"><div></div><div class="tl-track-header">';
    ticks.forEach(t => {
      html += `<span class="tl-tick" style="left:${t.pct}%">${t.label.slice(5)}</span>`;
    });
    html += '</div></div>';

    list.forEach(a => {
      const s = parseD(a.start_date), e = parseD(a.end_date);
      const left = pct(s), right = pct(e);
      const width = Math.max(0.5, right - left);
      const color = ACCENT[a.category] || "#888";
      const cls = a.status;
      const todayMark = pct(today);
      const progressPct = a.progress_pct || 0;
      const daysLeft = a.days_left;
      const totalDays = a.total_days;
      const tip = `${a.title} | ${fmtDate(a.start_date)} ~ ${fmtDate(a.end_date)} | ${daysLeft != null ? "剩 " + daysLeft + " 天" : ""}`;

      html += `<div class="tl-row">`;
      html += `<div class="tl-label" title="${escapeHtml(a.title)}"><span class="cat-dot ${a.category}"></span>${escapeHtml(a.title).slice(0, 22)}</div>`;
      html += `<div class="tl-track">`;
      // 今天标记（只在第一条画一次也行，但每条都画更直观）
      html += `<div class="tl-today" style="left:${todayMark}%"></div>`;
      html += `<div class="tl-bar ${cls}" style="left:${left}%; width:${width}%; --bar-color:${color}; --bar-color2:${color};" title="${escapeHtml(tip)}">`;
      if (a.status === "active") {
        html += `<div class="tl-progress" style="width:${progressPct}%"></div>`;
      }
      html += `<span class="tl-tooltip">${escapeHtml(tip)}</span>`;
      html += `</div></div></div>`;
    });
    html += '</div>';
    root.innerHTML = html;
  }

  function renderCards() {
    const root = document.getElementById("cards");
    const list = getFiltered();
    if (!list.length) {
      root.innerHTML = '<div class="loading">暂无活动</div>';
      return;
    }
    root.innerHTML = list.map(a => {
      const color = ACCENT[a.category] || "#888";
      const statusLabel = { active: "🟢 进行中", upcoming: "🟡 即将开始", ended: "⚫ 已结束" }[a.status] || a.status;
      const claimUrl = a.claim_url || a.source_url || "#";
      const sourceUrl = a.source_url || "#";
      const time = `${fmtDate(a.start_date)} ~ ${fmtDate(a.end_date)}`;
      const progress = a.progress_pct || 0;
      const daysLeft = a.days_left;
      const totalDays = a.total_days;
      const dlText = a.status === "ended" ? "已结束"
        : a.status === "upcoming" ? "未开始"
        : (daysLeft != null ? `还剩 ${daysLeft} 天 / 共 ${totalDays || "?"} 天` : "进行中");
      const tags = (a.tags || []).map(t => `<span class="card-tag">${escapeHtml(t)}</span>`).join("");
      const reqs = (a.requirements || []).length
        ? `<div class="card-req">领取条件：<ul>${a.requirements.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul></div>`
        : "";
      const value = a.value ? `<div class="card-value">🎁 <strong>${escapeHtml(a.value)}</strong></div>` : "";
      const desc = a.description ? `<div class="card-desc">${escapeHtml(a.description)}</div>` : "";

      return `
        <div class="card ${a.status}" style="--card-color:${color}">
          <div class="card-header">
            <div class="card-title">${escapeHtml(a.title)}</div>
            <span class="card-cat ${a.category}">${a.category === "ai" ? "AI" : "游戏"}</span>
          </div>
          <span class="card-status ${a.status}">${statusLabel}</span>
          ${value}
          <div class="card-time">⏰ ${time}</div>
          <div class="card-progress-wrap"><div class="card-progress" style="width:${progress}%"></div></div>
          <div class="card-days-left">${dlText}</div>
          ${desc}
          ${tags ? `<div class="card-tags">${tags}</div>` : ""}
          ${reqs}
          <div class="card-actions">
            <a class="card-btn primary" href="${escapeAttr(claimUrl)}" target="_blank" rel="noopener nofollow">前往领取 →</a>
            <a class="card-btn secondary" href="${escapeAttr(sourceUrl)}" target="_blank" rel="noopener nofollow">来源</a>
          </div>
        </div>
      `;
    }).join("");
  }

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function escapeAttr(s) {
    return escapeHtml(s);
  }

  function updateRepoLink() {
    // 优先用 meta.repository（Action 注入），否则从 Pages URL 推断
    const link = document.getElementById("repoLink");
    if (!link) return;
    let repo = META && META.repository;
    if (!repo) {
      // 从 https://owner.github.io/repo/ 推断
      const m = window.location.pathname.match(/^\/([^/]+)\/([^/]+)\//);
      if (m) repo = `${m[1]}.github.io`.replace(".github.io", "") + "/" + m[2];
    }
    if (repo) {
      link.href = `https://github.com/${repo}`;
      link.textContent = repo.split("/")[1] || "wool-gathering";
    } else {
      link.href = "https://github.com/search?q=wool-gathering";
    }
  }

  function bindEvents() {
    document.querySelectorAll(".filter-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentFilter = btn.dataset.filter;
        renderTimeline();
        renderCards();
      });
    });
    document.getElementById("showEnded").addEventListener("change", renderTimeline);
    document.getElementById("showUpcoming").addEventListener("change", renderTimeline);
  }

  async function init() {
    try {
      const [acts, meta] = await Promise.all([
        fetchJSON("data/activities.json"),
        fetchJSON("data/meta.json").catch(() => null),
      ]);
      ALL = Array.isArray(acts) ? acts : [];
      META = meta;
      renderMeta();
      updateRepoLink();
      renderTimeline();
      renderCards();
      bindEvents();
    } catch (e) {
      console.error(e);
      document.getElementById("timeline").innerHTML = `<div class="loading">加载失败：${escapeHtml(e.message)}</div>`;
      document.getElementById("cards").innerHTML = `<div class="loading">加载失败：${escapeHtml(e.message)}</div>`;
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();

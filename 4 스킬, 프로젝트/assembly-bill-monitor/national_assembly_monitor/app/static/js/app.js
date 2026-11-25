// 국회 원문은 textContent로만 넣는다(HTML로 해석하지 않음 → XSS 방지).
const $ = (s) => document.querySelector(s);
const state = { keyword: "", page: 1, pageSize: 20, polling: null };

function fmtTime(iso) {
  return iso ? iso.replace("T", " ").slice(0, 16) : "-";
}

async function getJSON(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function loadKeywords() {
  const { keywords } = await getJSON("/api/keywords");
  const box = $("#keyword-chips");
  box.replaceChildren();
  for (const k of ["", ...keywords]) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip" + (k === state.keyword ? " on" : "");
    b.textContent = k || "전체";
    b.onclick = () => { state.keyword = k; loadKeywords(); loadBills(true); };
    box.append(b);
  }
}

function renderCard(b) {
  const node = $("#card-tpl").content.firstElementChild.cloneNode(true);
  const badges = node.querySelector(".badges");
  if (b.is_new) {
    const s = document.createElement("span"); s.className = "badge new"; s.textContent = "NEW"; badges.append(s);
  }
  for (const k of b.keywords) {
    const s = document.createElement("span"); s.className = "badge kw"; s.textContent = k; badges.append(s);
  }
  node.querySelector(".name").textContent = b.bill_name;
  node.querySelector(".no").textContent = b.bill_number;
  node.querySelector(".proposer").textContent = b.proposer || "-";
  node.querySelector(".date").textContent = b.propose_date || "-";
  node.querySelector(".status").textContent = b.proc_result || "계류(처리 전)";
  node.querySelector(".committee").textContent = b.committee || "미정";

  const pre = node.querySelector(".text");
  const toggle = node.querySelector(".toggle");
  if (b.summary_status === "ok" && b.summary_text) {
    pre.textContent = b.summary_text;
    requestAnimationFrame(() => {
      if (pre.scrollHeight > pre.clientHeight + 4) {
        toggle.hidden = false;
        toggle.onclick = () => {
          const c = pre.classList.toggle("collapsed");
          toggle.textContent = c ? "펼치기" : "접기";
        };
      } else {
        pre.classList.remove("collapsed");
      }
    });
  } else {
    pre.classList.remove("collapsed");
    pre.classList.add("empty");
    pre.textContent = b.summary_status === "failed"
      ? "원문을 가져오지 못했습니다. 다음 조사 때 다시 시도합니다."
      : "국회에서 별도의 제안이유 및 주요내용이 제공되지 않습니다.";
  }
  const a = node.querySelector(".link");
  if (b.source_url && /^https?:\/\//.test(b.source_url)) a.href = b.source_url; else a.remove();
  return node;
}

async function loadBills(reset) {
  if (reset) { state.page = 1; $("#bills").replaceChildren(); }
  const p = new URLSearchParams({ page: state.page, page_size: state.pageSize });
  if (state.keyword) p.set("keyword", state.keyword);
  const q = $("#q").value.trim(); if (q) p.set("q", q);
  const st = $("#status").value; if (st) p.set("status", st);
  if ($("#new-only").checked) p.set("new_only", "true");
  const data = await getJSON("/api/bills?" + p);
  for (const b of data.items) $("#bills").append(renderCard(b));
  $("#count").textContent = data.total ? `관련 의안 ${data.total}건` : "저장된 의안이 없습니다. [최신 조사]를 눌러 주세요.";
  $("#more-btn").hidden = state.page * state.pageSize >= data.total;
}

function showMessage(text, kind) {
  const m = $("#sync-message");
  m.textContent = text; m.className = "message " + (kind || ""); m.hidden = !text;
}

function setRunning(running, label) {
  const btn = $("#sync-btn");
  btn.disabled = running;
  btn.textContent = running ? "조사 중..." : "최신 조사";
  const pr = $("#sync-progress");
  pr.hidden = !running;
  pr.textContent = label || "";
}

async function refreshStatus(afterRun) {
  const s = await getJSON("/api/sync/status");
  if (!s.running) {
    const last = s.last_completed_at || (s.status === "completed" ? s.finished_at : null);
    $("#last-sync").textContent = "마지막 조사: " + fmtTime(last);
  }
  if (s.running) {
    let label = s.label || "조사 중...";
    if (s.detail_total) label += ` (${s.detail_done || 0}/${s.detail_total})`;
    setRunning(true, label);
    if (!state.polling) state.polling = setInterval(() => refreshStatus(true), 1500);
    return;
  }
  setRunning(false);
  if (state.polling) { clearInterval(state.polling); state.polling = null; }
  if (afterRun) {
    if (s.status === "completed") {
      showMessage(`완료: 관련 ${s.related_found}건 (신규 ${s.inserted}, 변경 ${s.updated}, 변동 없음 ${s.unchanged}, 실패 ${s.failed})`
        + (s.warning ? ` — ${s.warning}` : ""), s.failed || s.warning ? "warn" : "ok");
    } else if (s.status === "failed") {
      showMessage("조사 실패: " + (s.error_message || "알 수 없는 오류"), "error");
    }
    loadBills(true);
  } else if (s.status === "failed" && s.error_message) {
    showMessage("마지막 조사 실패: " + s.error_message, "error");
  }
}

$("#sync-btn").onclick = async () => {
  showMessage("");
  setRunning(true, "조사 준비 중...");
  try {
    const r = await getJSON("/api/sync", { method: "POST" });
    if (r.status === "already_running") showMessage("이미 조사가 진행 중입니다.", "warn");
    refreshStatus(true);
  } catch (e) {
    setRunning(false);
    showMessage("조사를 시작하지 못했습니다: " + e.message, "error");
  }
};
$("#more-btn").onclick = () => { state.page += 1; loadBills(false); };
let qTimer;
$("#q").oninput = () => { clearTimeout(qTimer); qTimer = setTimeout(() => loadBills(true), 300); };
$("#status").onchange = () => loadBills(true);
$("#new-only").onchange = () => loadBills(true);

loadKeywords();
loadBills(true).catch((e) => showMessage("목록을 불러오지 못했습니다: " + e.message, "error"));
refreshStatus(false);

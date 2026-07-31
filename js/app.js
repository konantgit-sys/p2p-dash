// ═══ P2P Agent Mesh — Dashboard v0.5.1 ═══
// Modular edition — js/app.js
// Core logic: polling, rendering, topology, charts, actions

// ═══════════════════════════════════════════
// ═══ TAB SWITCHING
// ═══════════════════════════════════════════
document.querySelectorAll('nav .tabs button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('nav .tabs button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('section').forEach(s => s.classList.remove('active'));
    const sec = document.getElementById('sec-' + btn.dataset.tab);
    sec.classList.add('active');
    sec.style.animation = 'none';
    sec.offsetHeight;
    sec.style.animation = 'tabFade .35s ease-out';
    if (btn.dataset.tab === 'topo') setTimeout(drawTopology, 100);
  });
});

// ═══════════════════════════════════════════
// ═══ CARD GLOW — mouse tracking
// ═══════════════════════════════════════════
document.querySelectorAll('.card').forEach(card => {
  card.addEventListener('mousemove', e => {
    const r = card.getBoundingClientRect();
    card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
    card.style.setProperty('--my', (e.clientY - r.top) + 'px');
  });
});

// ═══════════════════════════════════════════
// ═══ PARTICLE SYSTEM
// ═══════════════════════════════════════════
(function() {
  const c = document.getElementById('particles'), ctx = c.getContext('2d');
  let w, h, particles = [], flows = [];
  function resize() { w = c.width = window.innerWidth; h = c.height = window.innerHeight; }
  resize();
  window.addEventListener('resize', resize);
  for (let i = 0; i < 40; i++)
    particles.push({ x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - .5) * .25, vy: (Math.random() - .5) * .25, r: Math.random() * 1.8 + .4, o: Math.random() * .3 + .06 });
  for (let i = 0; i < 6; i++)
    flows.push({ ax: Math.random() * w, ay: Math.random() * h, bx: Math.random() * w, by: Math.random() * h, progress: Math.random(), speed: .0015 + Math.random() * .003 });
  function draw() {
    ctx.clearRect(0, 0, w, h);
    particles.forEach(p => { p.x += p.vx; p.y += p.vy; if (p.x < 0) p.x = w; if (p.x > w) p.x = 0; if (p.y < 0) p.y = h; if (p.y > h) p.y = 0; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fillStyle = `rgba(0,200,255,${p.o})`; ctx.fill(); });
    for (let i = 0; i < particles.length; i++)
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i], b = particles[j];
        const dx = a.x - b.x, dy = a.y - b.y, dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 90) { ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.strokeStyle = `rgba(0,200,255,${.025 * (1 - dist / 90)})`; ctx.lineWidth = .4; ctx.stroke(); }
      }
    flows.forEach(f => {
      f.progress += f.speed;
      if (f.progress > 1) { f.progress = 0; f.ax = Math.random() * w; f.ay = Math.random() * h; f.bx = Math.random() * w; f.by = Math.random() * h; }
      const x = f.ax + (f.bx - f.ax) * f.progress, y = f.ay + (f.by - f.ay) * f.progress;
      ctx.beginPath(); ctx.arc(x, y, 1.2, 0, Math.PI * 2); ctx.fillStyle = 'rgba(0,200,255,.4)'; ctx.fill();
    });
    requestAnimationFrame(draw);
  }
  draw();
})();

// ═══════════════════════════════════════════
// ═══ PAUSE / RESUME
// ═══════════════════════════════════════════
function togglePause() {
  polling = !polling;
  const btn = document.getElementById('btnPause');
  if (!polling) {
    btn.classList.add('paused');
    btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>';
    poll();
  } else {
    btn.classList.remove('paused');
    btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>';
  }
}

// ═══════════════════════════════════════════
// ═══ TOAST NOTIFICATIONS
// ═══════════════════════════════════════════
function showToast(cap, payload, ts) {
  const c = document.getElementById('toastContainer');
  const el = document.createElement('div'); el.className = 'toast';
  const capName = cap.replace('agent:', '');
  const preview = typeof payload === 'string' ? payload.slice(0, 80) : JSON.stringify(payload).slice(0, 80);
  el.innerHTML = `<div class="toast-cap">⚡ ${capName}</div><div class="toast-body">${preview}${preview.length >= 80 ? '…' : ''}</div><div class="toast-time">${rt(ts)}</div>`;
  c.appendChild(el);
  setTimeout(() => { el.classList.add('removing'); setTimeout(() => el.remove(), 300); }, 4000);
}

// ═══════════════════════════════════════════
// ═══ THEME TOGGLE
// ═══════════════════════════════════════════
function toggleTheme() {
  const cur = document.documentElement.getAttribute('data-theme');
  const next = cur === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('p2p-dash-theme', next);
  updateThemeIcon(next);
  if (window._timelineData) drawTimelineCanvas(window._timelineData);
}
function updateThemeIcon(t) {
  const btn = document.getElementById('btnTheme');
  if (t === 'light') {
    btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  } else {
    btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
  }
}
(function initTheme() {
  const saved = localStorage.getItem('p2p-dash-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  updateThemeIcon(saved);
})();

// ═══════════════════════════════════════════
// ═══ EMIT MESSAGE
// ═══════════════════════════════════════════
async function emitMsg() {
  const capEl = document.getElementById('emitCap'), customEl = document.getElementById('emitCapCustom');
  const cap = capEl.value === 'custom' ? customEl.value.trim() || 'custom' : capEl.value;
  let payloadInput = document.getElementById('emitPayload').value.trim() || 'ping';
  let payload;
  try { payload = JSON.parse(payloadInput); if (typeof payload !== 'object' || Array.isArray(payload)) payload = { text: payloadInput }; }
  catch (e) { payload = { text: payloadInput }; }
  if (!cap) { showToast('error', 'Enter capability', ''); return; }
  try {
    const res = await fetch(`${API}/emit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ capability: cap, payload }) });
    const data = await res.json();
    if (res.ok) { showToast(cap, '✓ Sent: ' + (data.msg_id || data.status || '').slice(0, 60), ''); document.getElementById('emitPayload').value = ''; }
    else showToast('error', 'Emit failed: ' + (data.error || res.status), '');
  } catch (e) { showToast('error', 'Emit error: ' + e.message, ''); }
}
document.getElementById('emitCap').addEventListener('change', function() {
  document.getElementById('emitCapCustom').style.display = this.value === 'custom' ? '' : 'none';
});

// ═══════════════════════════════════════════
// ═══ EXPORT LOG
// ═══════════════════════════════════════════
function exportLog() {
  if (!allMessages.length) return;
  const blob = new Blob([JSON.stringify(allMessages, null, 2)], { type: 'application/json' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = `p2p-mesh-log-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
  a.click(); URL.revokeObjectURL(a.href);
}

// ═══════════════════════════════════════════
// ═══ CHART UTILITIES
// ═══════════════════════════════════════════
function drawLineChart(canvasId, data, color1, color2, minY, maxY) {
  const c = document.getElementById(canvasId); if (!c || !data.length) return;
  const ctx = c.getContext('2d'), W = c.width = c.offsetWidth, H = c.height = c.offsetHeight;
  ctx.clearRect(0, 0, W, H); if (data.length < 2) return;
  const yMin = minY ?? Math.min(...data) * .9, yMax = maxY ?? Math.max(...data) * 1.1 || 1;
  const range = yMax - yMin || 1, stepX = W / (data.length - 1);
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, color1 + '30'); grad.addColorStop(1, 'transparent');
  ctx.beginPath(); ctx.moveTo(0, H);
  data.forEach((v, i) => ctx.lineTo(i * stepX, H - (v - yMin) / range * H));
  ctx.lineTo(W, H); ctx.closePath(); ctx.fillStyle = grad; ctx.fill();
  ctx.beginPath();
  data.forEach((v, i) => { const x = i * stepX, y = H - (v - yMin) / range * H; if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); });
  ctx.strokeStyle = color1; ctx.lineWidth = 2; ctx.stroke();
  data.forEach((v, i) => { const x = i * stepX, y = H - (v - yMin) / range * H; ctx.beginPath(); ctx.arc(x, y, 2.5, 0, Math.PI * 2); ctx.fillStyle = color1; ctx.fill(); });
}

function drawLatHistory() {
  const c = document.getElementById('latHistory'); if (!c || latHistory.length < 2) return;
  const ctx = c.getContext('2d'), W = c.width = c.offsetWidth, H = c.height = c.offsetHeight;
  ctx.clearRect(0, 0, W, H);
  const p50s = latHistory.map(p => p.p50), p99s = latHistory.map(p => p.p99);
  const yMax = Math.max(...p99s, 1) * 1.15, range = yMax || 1, stepX = W / (latHistory.length - 1);
  // p99 fill + line (purple)
  ctx.beginPath(); ctx.moveTo(0, H);
  p99s.forEach((v, i) => ctx.lineTo(i * stepX, H - (v / range) * H));
  ctx.lineTo(W, H); ctx.closePath();
  const g2 = ctx.createLinearGradient(0, 0, 0, H); g2.addColorStop(0, 'rgba(168,85,247,.15)'); g2.addColorStop(1, 'transparent');
  ctx.fillStyle = g2; ctx.fill();
  ctx.beginPath(); p99s.forEach((v, i) => { const x = i * stepX, y = H - (v / range) * H; i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
  ctx.strokeStyle = '#a855f7'; ctx.lineWidth = 1.5; ctx.stroke();
  // p50 fill + line (cyan)
  ctx.beginPath(); ctx.moveTo(0, H);
  p50s.forEach((v, i) => ctx.lineTo(i * stepX, H - (v / range) * H));
  ctx.lineTo(W, H); ctx.closePath();
  const g1 = ctx.createLinearGradient(0, 0, 0, H); g1.addColorStop(0, 'rgba(0,200,255,.12)'); g1.addColorStop(1, 'transparent');
  ctx.fillStyle = g1; ctx.fill();
  ctx.beginPath(); p50s.forEach((v, i) => { const x = i * stepX, y = H - (v / range) * H; i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
  ctx.strokeStyle = 'var(--accent)'; ctx.lineWidth = 1.5; ctx.stroke();
}

// ═══════════════════════════════════════════
// ═══ ANIMATED COUNTER
// ═══════════════════════════════════════════
function animateValue(el, target, suffix) {
  suffix = suffix || '';
  const start = parseInt(el.textContent) || 0;
  if (start === target) { el.textContent = target + suffix; return; }
  const dur = 400; let st;
  function f(ts) { st ||= ts; const p = Math.min((ts - st) / dur, 1), v = Math.round(start + (target - start) * p); el.textContent = v + suffix; if (p < 1) requestAnimationFrame(f); else el.textContent = target + suffix; }
  requestAnimationFrame(f);
}

// ═══════════════════════════════════════════
// ═══ GAUGES
// ═══════════════════════════════════════════
function updateGauge(id, val, maxV) {
  const el = document.getElementById(id); if (!el) return;
  el.setAttribute('stroke-dashoffset', 132 * (1 - Math.min(val / maxV, 1)));
}
function updateGaugeVal(id, val) {
  const el = document.getElementById(id); if (el) el.textContent = val < 10 ? val.toFixed(1) : Math.round(val);
}

// ═══════════════════════════════════════════
// ═══ SPARKLINES
// ═══════════════════════════════════════════
const sparkData = { peers: [], msgs: [], wal: [] };
function updateSparkline(id, val, maxLen) {
  maxLen = maxLen || 14;
  const arr = sparkData[id] = sparkData[id] || [];
  arr.push(val); if (arr.length > maxLen) arr.shift();
  const el = document.getElementById(id + 'Sparkline'); if (!el) return;
  const max = Math.max(...arr, 1);
  el.innerHTML = arr.map(v => `<div class="bar" style="height:${Math.max(3, (v / max) * 28)}px"></div>`).join('');
}

// ═══════════════════════════════════════════
// ═══ API HELPERS
// ═══════════════════════════════════════════
const API = '/api';
let polling = true;
async function f(url) { try { const r = await fetch(url); return await r.json(); } catch (e) { return { status: 'error', error: e.message }; } }
const NAMES = { 'dashboard': '🎯 dash', 'cryter-agent': '🤖 cryter', 'forecaster-agent': '🤖 forecaster', 'archivist-agent': '🤖 archivist', 'mesh-connector': '🔗 conn', 'relay-mesh-bridge': '🌉 bridge' };
function rn(id) { return NAMES[id] || id.slice(0, 20) + '...'; }
function rt(ts) { return new Date((ts || 0) * 1000).toLocaleTimeString(currentLang === 'ru' ? 'ru-RU' : 'en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }); }
function renderMsg(msg) {
  const p = msg.payload || {}, from = msg.from || p.from || '?', cap = msg.capability || p.capability || msg.type || '?';
  const ts = msg.ts || msg._received_at || 0, sig = (msg.signature || '').slice(0, 8) + '...', ps = JSON.stringify(p).slice(0, 80);
  const json = encodeURIComponent(JSON.stringify(msg, null, 2));
  return `<div class="msg-row" onclick="showDetail('${json}')" style="cursor:pointer" title="Click for details"><span class="msg-from" title="${from}">${rn(from)}</span><span class="msg-cap">${cap}</span><span class="msg-payload" title="${ps}">${ps}</span><span class="msg-signature">${sig}</span><span class="msg-ts">${rt(ts)}</span></div>`;
}

function showDetail(json) {
  document.getElementById('msgDetail').textContent = decodeURIComponent(json);
  document.getElementById('msgModal').style.display = 'flex';
}

// ═══════════════════════════════════════════
// ═══ MAIN UPDATE
// ═══════════════════════════════════════════
let allMessages = [], historyPoints = [], latHistory = [];

async function updateAll() {
  const [metrics, status, peers, sys, stats, hist] = await Promise.all([
    f(`${API}/metrics`), f(`${API}/status`), f(`${API}/peers`), f(`${API}/system`),
    f(`${API}/messages/stats`), f(`${API}/metrics/history`),
  ]);

  if (metrics.status === 'ok') {
    const d = metrics.data;
    animateValue(document.getElementById('peersCount'), d.peers ?? 0);
    animateValue(document.getElementById('msgCount'), d.message_count ?? 0);
    animateValue(document.getElementById('walMetric'), d.wal_count ?? 0);
    animateValue(document.getElementById('dhtCount'), d.dht_entries ?? 0);
    animateValue(document.getElementById('topicCount'), d.topic_count ?? 0);
    animateValue(document.getElementById('msgRate'), d.msg_rate || 0, '');
    document.getElementById('sigPassed').textContent = d.sig_stats?.passed ?? 0;
    document.getElementById('sigRejected').textContent = (d.sig_stats?.rejected_rate ?? 0) + (d.sig_stats?.rejected_sig ?? 0);
    if (d.latency) {
      updateGauge('gaugeP50', d.latency.p50_ms, 50); updateGauge('gaugeP99', d.latency.p99_ms, 100); updateGauge('gaugeAvg', d.latency.avg_ms, 50);
      updateGaugeVal('gaugeP50Val', d.latency.p50_ms); updateGaugeVal('gaugeP99Val', d.latency.p99_ms); updateGaugeVal('gaugeAvgVal', d.latency.avg_ms);
      document.getElementById('latN').textContent = d.latency.samples || 0;
      latHistory.push({ t: Date.now(), p50: d.latency.p50_ms, p99: d.latency.p99_ms });
      if (latHistory.length > 60) latHistory.shift();
      drawLatHistory();
    }
    updateSparkline('peers', d.peers ?? 0); updateSparkline('msgs', d.message_count ?? 0); updateSparkline('wal', d.wal_count ?? 0);
    document.getElementById('walPreview').innerHTML = '';
    if (d.msg_rate != null) {
      historyPoints.push(d.msg_rate); if (historyPoints.length > 30) historyPoints.shift();
      drawLineChart('rateChart', historyPoints, getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#00c8ff', 'rgba(0,200,255,', 0, Math.max(...historyPoints, 5));
    }
  }

  if (hist.status === 'ok' && hist.data.points.length >= 2) {
    const pts = hist.data.points;
    drawLineChart('trendChart', pts.map(p => p.msg_rate || 0), '#22c55e', 'rgba(34,197,94,', 0, Math.max(...pts.map(p => p.msg_rate || 0), 5));
  }

  if (sys.status === 'ok') {
    document.getElementById('sysMem').textContent = (sys.data.memory_pct || 0) + '% (' + (sys.data.memory_used_gb || 0) + '/' + (sys.data.memory_total_gb || 0) + ' GB)';
    document.getElementById('sysDisk').textContent = (sys.data.disk_pct || 0) + '% (' + (sys.data.disk_used_gb || 0) + '/' + (sys.data.disk_total_gb || 0) + ' GB)';
    document.getElementById('sysLoad').textContent = (sys.data.load_avg || 0).toFixed(1);
    document.getElementById('sysProcs').textContent = sys.data.processes || '-';
  }
  if (metrics.status === 'ok') document.getElementById('sysUptime').textContent = Math.floor((metrics.data.uptime || 0) / 60) + ' min';

  if (stats.status === 'ok') {
    const byCap = stats.data.by_capability || {};
    const maxCap = Math.max(...Object.values(byCap), 1);
    const el = document.getElementById('typeDist');
    el.innerHTML = Object.entries(byCap).map(([k, v]) =>
      `<div class="dist-bar"><span class="dist-label">${k}</span><div class="dist-track"><div class="dist-fill" style="width:${(v / maxCap * 100).toFixed(0)}%;background:var(--accent)"></div></div><span class="dist-count">${v}</span></div>`
    ).join('');
    const sel = document.getElementById('msgFilter');
    sel.innerHTML = '<option value="all">All capabilities</option>' + Object.keys(byCap).map(c => `<option value="${c}">${c}</option>`).join('');
  }

  if (peers.status === 'ok') {
    const names = peers.data.peer_names || [];
    const list = document.getElementById('peerList');
    list.innerHTML = names.length ? names.map(n => `<div style="padding:2px 0">⬤ <span style="color:var(--accent)">${n.name}</span> <span style="color:var(--muted);font-size:9px">${n.peer_id.slice(0, 16)}</span></div>`).join('') : '<span style="color:var(--muted)">—</span>';
  }

  if (status.status === 'ok') {
    const dot = document.getElementById('navStatus'), heroDot = document.getElementById('heroStatusDot');
    if (dot) dot.className = 'status-dot online';
    if (heroDot) heroDot.className = 'status-dot online';
  }
}

// ═══════════════════════════════════════════
// ═══ MESSAGE LOG
// ═══════════════════════════════════════════
let _lastSeenId = null;
async function updateMsgs() {
  const prevCount = allMessages.length;
  allMessages = [];
  const res = await f(`${API}/messages?limit=200`);
  if (res.status === 'ok') {
    allMessages = res.data.messages || [];
    renderMsgList(allMessages);
    document.getElementById('msgTotal').textContent = res.data.total || 0;
    if (allMessages.length > prevCount && prevCount > 0) {
      const newest = allMessages[0];
      if (newest && newest.id !== _lastSeenId) {
        _lastSeenId = newest.id;
        showToast(newest.capability || 'event', newest.payload || newest.data, '');
      }
    }
    if (allMessages.length && allMessages[0] && allMessages[0].id !== _lastSeenId) {
      _lastSeenId = allMessages[0].id;
    }
  }
}

function renderMsgList(msgs) {
  const list = document.getElementById('msgList');
  if (!msgs.length) { list.innerHTML = `<div style="padding:32px;text-align:center;color:var(--muted);font-size:13px">${t('log.waiting')}</div>`; return; }
  list.innerHTML = msgs.map(renderMsg).join('');
}

// ═══════════════════════════════════════════
// ═══ SEARCH & FILTER
// ═══════════════════════════════════════════
document.getElementById('msgSearch').addEventListener('input', function() { applyFilter(); });
document.getElementById('msgFilter').addEventListener('change', function() { applyFilter(); });
function applyFilter() {
  const q = document.getElementById('msgSearch').value.toLowerCase();
  const cap = document.getElementById('msgFilter').value;
  let filtered = allMessages;
  if (cap !== 'all') filtered = filtered.filter(m => (m.capability || m.payload?.capability || '') === cap);
  if (q) filtered = filtered.filter(m => JSON.stringify(m).toLowerCase().includes(q));
  renderMsgList(filtered);
}

// ═══════════════════════════════════════════
// ═══ DHT & DISCOVERY & TIMELINE
// ═══════════════════════════════════════════
async function updateDHT() {
  const res = await f(`${API}/dht`);
  if (res.status === 'ok') {
    const entries = res.data.entries || [];
    const list = document.getElementById('dhtList');
    list.innerHTML = entries.length ? entries.map(e => {
      const v = e.value || {}, name = v.agent_id || e.key.replace('agent:', ''), caps = (v.capabilities || []).join(', '), upt = v.uptime ? Math.round(v.uptime) + 's' : '-';
      return `<div style="padding:2px 0;border-bottom:1px solid rgba(255,255,255,.02)"><span style="color:var(--accent2)">${name}</span><span style="color:var(--muted);font-size:9px;margin-left:6px">${caps}</span><span style="color:var(--muted);font-size:9px;float:right">⏱ ${upt}</span></div>`;
    }).join('') : '<span style="color:var(--muted)">—</span>';
  }

  const disc = await f(`${API}/discovery`);
  const dl = document.getElementById('discoveryList');
  if (disc.status === 'ok' && disc.data.attempts.length) {
    const items = disc.data.attempts.slice(-12).reverse();
    dl.innerHTML = items.map(a => {
      const t = rt(a.ts), dht = a.dht_size ? '<span style="color:var(--accent2)">' + a.dht_size + ' entries</span>' : '<span style="color:var(--muted)">DHT empty</span>',
        tcp = a.tcp_connections ? '<span style="color:var(--green)">' + a.tcp_connections + ' conn</span>' : '<span style="color:var(--muted)">0 conn</span>';
      return `<div style="padding:3px 0;border-bottom:1px solid rgba(255,255,255,.02);display:flex;justify-content:space-between"><span>${t}</span><span style="display:flex;gap:10px">${dht} ${tcp}</span></div>`;
    }).join('');
  } else dl.innerHTML = '<span style="color:var(--muted)">No discovery attempts yet</span>';

  const tl = await f(`${API}/timeline`);
  if (tl.status === 'ok' && tl.data.events.length) {
    window._timelineData = tl.data.events;
    drawTimelineCanvas(window._timelineData);
  } else {
    const c = document.getElementById('timelineCanvas');
    if (c) {
      const ctx = c.getContext('2d'); ctx.clearRect(0, 0, c.width, c.height);
      const style = getComputedStyle(document.documentElement);
      ctx.fillStyle = style.getPropertyValue('--muted').trim() || '#5a6e8e'; ctx.font = '12px Inter'; ctx.fillText('No connection events yet', 12, 50);
    }
    document.getElementById('timelineLegend').innerHTML = '<span style="color:var(--muted)">0 events</span>';
  }
}

function drawTimelineCanvas(events) {
  const c = document.getElementById('timelineCanvas');
  if (!c || !events.length) return;
  const ctx = c.getContext('2d'), W = c.width = c.offsetWidth, H = 100;
  ctx.clearRect(0, 0, W, H);

  const style = getComputedStyle(document.documentElement);
  const cyan = style.getPropertyValue('--accent').trim() || '#00c8ff';
  const purple = style.getPropertyValue('--purple').trim() || '#a855f7';
  const green = style.getPropertyValue('--green').trim() || '#22c55e';
  const muted = style.getPropertyValue('--muted').trim() || '#5a6e8e';

  const enriched = [];
  for (let i = 0; i < events.length; i++) {
    const e = events[i];
    let type = 'announce', color = cyan, glow = cyan + '44';
    const prev = i > 0 ? events[i - 1] : null;
    if (prev) {
      const gap = e.ts - prev.ts;
      if (gap > 600) { type = 'reconnect'; color = '#f59e0b'; glow = 'rgba(245,158,11,.35)'; }
      else if (gap > 300) { type = 'gap'; color = '#ef4444'; glow = 'rgba(239,68,68,.35)'; }
    }
    enriched.push({ ...e, type, color, glow });
  }

  const rows = { announce: 25, gap: 50, reconnect: 75 };
  const padH = 20, drawW = W - padH * 2;
  const minTs = Math.min(...events.map(e => e.ts));
  const maxTs = Math.max(...events.map(e => e.ts));
  const range = (maxTs - minTs) || 1;

  Object.entries(rows).forEach(([type, y]) => {
    ctx.beginPath(); ctx.strokeStyle = 'rgba(255,255,255,.04)'; ctx.lineWidth = 1;
    ctx.moveTo(padH, y); ctx.lineTo(W - padH, y); ctx.stroke();
  });

  enriched.forEach(e => {
    const x = padH + ((e.ts - minTs) / range) * drawW;
    const y = rows[e.type] || 50;
    const grd = ctx.createRadialGradient(x, y, 0, x, y, 6);
    grd.addColorStop(0, e.glow); grd.addColorStop(1, 'transparent');
    ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fillStyle = grd; ctx.fill();
    ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fillStyle = e.color; ctx.fill();
  });

  ctx.fillStyle = muted; ctx.font = '8px Inter,sans-serif';
  const steps = 5;
  for (let i = 0; i <= steps; i++) {
    const x = padH + (i / steps) * drawW;
    const d = new Date((minTs + (i / steps) * range) * 1000);
    const lbl = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    ctx.fillText(lbl, x - 14, 95);
  }

  document.getElementById('timelineLegend').innerHTML = `
    <span style="display:flex;align-items:center;gap:4px"><span style="width:6px;height:6px;border-radius:50%;background:var(--accent)"></span>Announce</span>
    <span style="display:flex;align-items:center;gap:4px"><span style="width:6px;height:6px;border-radius:50%;background:#f59e0b"></span>Reconnect</span>
    <span style="display:flex;align-items:center;gap:4px"><span style="width:6px;height:6px;border-radius:50%;background:#ef4444"></span>Gap</span>
    <span style="font-size:9px;color:var(--muted)">${events.length} events</span>
  `;
}

// ═══════════════════════════════════════════
// ═══ TOPOLOGY — Canvas Graph
// ═══════════════════════════════════════════
let topoData = { nodes: [], edges: [] }, topoAnim;

async function drawTopology() {
  const canvas = document.getElementById('topoCanvas'); if (!canvas) return;
  const ctx = canvas.getContext('2d');
  try {
    const peers = await f(`${API}/peers`), dht = await f(`${API}/dht`);
    topoData.nodes = [{ id: 'dashboard', label: 'dash', x: .5, y: .5, type: 'local' }];
    if (peers.status === 'ok') (peers.data.peer_names || []).forEach((p, i) => {
      const a = (i / Math.max(peers.data.peer_names.length, 1)) * Math.PI * 2;
      topoData.nodes.push({ id: p.name, label: rn(p.name), x: .5 + Math.cos(a) * .35, y: .5 + Math.sin(a) * .35, type: 'peer' });
    });
    if (dht.status === 'ok') (dht.data.entries || []).forEach((e, i) => {
      const v = e.value || {}, name = v.agent_id || e.key.replace('agent:', '');
      if (!topoData.nodes.find(n => n.id === name)) {
        const a = (i / Math.max(dht.data.entries.length, 1)) * Math.PI * 2 + .3;
        topoData.nodes.push({ id: name, label: name.slice(0, 14), x: .5 + Math.cos(a) * .45, y: .5 + Math.sin(a) * .45, type: 'relay' });
      }
    });
  } catch (e) { /* keep defaults */ }
  topoData.edges = topoData.nodes.filter(n => n.id !== 'dashboard').map(n => ({ from: 'dashboard', to: n.id }));

  let phase = 0; cancelAnimationFrame(topoAnim);
  function render() {
    const W = canvas.width = canvas.offsetWidth, H = canvas.height = canvas.offsetHeight;
    ctx.clearRect(0, 0, W, H); phase += .018;

    topoData.edges.forEach((e, i) => {
      const from = topoData.nodes.find(n => n.id === e.from), to = topoData.nodes.find(n => n.id === e.to);
      if (!from || !to) return;
      const fx = from.x * W, fy = from.y * H, tx = to.x * W, ty = to.y * H;
      ctx.beginPath(); ctx.moveTo(fx, fy); ctx.lineTo(tx, ty);
      ctx.strokeStyle = `rgba(0,200,255,${.05 + .015 * Math.sin(phase + i * .4)})`; ctx.lineWidth = 1; ctx.stroke();
      const dp = (phase * .28 + i * .12) % 1, dx = fx + (tx - fx) * dp, dy = fy + (ty - fy) * dp;
      ctx.beginPath(); ctx.arc(dx, dy, 2, 0, Math.PI * 2); ctx.fillStyle = `rgba(0,200,255,${.45 + .25 * Math.sin(phase + i)})`; ctx.fill();
      ctx.shadowColor = '#00c8ff'; ctx.shadowBlur = 6; ctx.fill(); ctx.shadowBlur = 0;
    });

    topoData.nodes.forEach(n => {
      const x = n.x * W, y = n.y * H, cols = { local: { fill: '#00c8ff', glow: '#00c8ff' }, peer: { fill: '#22c55e', glow: '#22c55e' }, relay: { fill: '#a855f7', glow: '#a855f7' } };
      const col = cols[n.type] || cols.peer, rad = n.type === 'local' ? 10 : 7;
      const pulse = n.type === 'local' ? (1 + .12 * Math.sin(phase * 2)) : 1;
      const g = ctx.createRadialGradient(x, y, 0, x, y, rad * 2.5 * pulse);
      g.addColorStop(0, col.glow + '40'); g.addColorStop(1, 'transparent');
      ctx.fillStyle = g; ctx.fillRect(x - rad * 2.5 * pulse, y - rad * 2.5 * pulse, rad * 5 * pulse, rad * 5 * pulse);
      ctx.beginPath(); ctx.arc(x, y, rad, 0, Math.PI * 2); ctx.fillStyle = col.fill; ctx.fill();
      ctx.strokeStyle = col.fill + '60'; ctx.lineWidth = 2; ctx.stroke();
      ctx.fillStyle = '#e8eef8'; ctx.font = '9px Inter,system-ui'; ctx.textAlign = 'center'; ctx.fillText(n.label, x, y + rad + 13);
    });
    topoAnim = requestAnimationFrame(render);
  }
  render();

  const peers = topoData.nodes.filter(n => n.id !== 'dashboard');
  const listEl = document.getElementById('topoPeerList');
  if (listEl) listEl.innerHTML = peers.length ? peers.map(p => {
    const col = p.type === 'peer' ? 'var(--green)' : 'var(--purple)';
    return `<div style="padding:3px 0;border-bottom:1px solid rgba(255,255,255,.02)"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${col};margin-right:8px;box-shadow:0 0 6px ${col}"></span><span style="color:var(--text2)">${p.label}</span><span style="color:var(--muted);font-size:10px;margin-left:6px">${p.type}</span></div>`;
  }).join('') : '<span style="color:var(--muted)">No peers connected</span>';
}

// ═══════════════════════════════════════════
// ═══ POLLING LOOP
// ═══════════════════════════════════════════
async function poll() {
  if (!polling) return;
  await Promise.all([updateAll(), updateMsgs(), updateDHT()]);
  setTimeout(poll, 3000);
}

// ═══════════════════════════════════════════
// ═══ EMIT FORM — dashboard panel
// ═══════════════════════════════════════════
document.getElementById('emitForm').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = e.target.querySelector('button'); btn.disabled = true; btn.textContent = '...';
  const fd = new FormData(e.target);
  const topic = fd.get('topic') || 'agent:echo';
  let payload; try { payload = JSON.parse(fd.get('payload')); } catch { payload = { msg: fd.get('payload') }; }
  const res = await fetch(`${API}/emit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ topic, capability: fd.get('capability'), payload }) });
  const data = await res.json();
  btn.disabled = false; btn.textContent = 'Emit';
  if (data.msg_id) showToast(fd.get('capability'), '✓ ' + data.msg_id.slice(0, 24) + '...', '');
  else showToast('error', '❌ ' + (data.detail || 'Failed'), '');
});

// ═══════════════════════════════════════════
// ═══ STARTUP
// ═══════════════════════════════════════════
applyLang();
poll();

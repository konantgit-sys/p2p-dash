// ═══ I18N — Translations & Language Switching ═══
// p2p-dash v0.5.1 — modular edition

const I18N = {
  en: {
    'nav.dash':'Dashboard','nav.topo':'Topology','nav.about':'About',
    'hero.badge':'P2P Agent Mesh v0.5.1','hero.title':'Decentralized Mesh Transport','hero.sub':'Live dashboard — peer-to-peer agent communication',
    'card.peers':'Peers','card.peers_sub':'P2P mesh nodes','card.msgs':'Messages','card.msgs_sub':'Received via mesh',
    'card.wal':'WAL Buffer','card.wal_sub':'SQLite WAL entries','card.dht':'DHT','card.dht_sub':'Agents in DHT cache',
    'card.topics':'Topics','card.topics_sub':'Active subscriptions','card.sig':'Sig Gate','card.sig_passed':'Passed',
    'card.sig_rej':'Rejected','card.sig_sub':'Signature verification','card.lat':'Latency','card.lat_samples':'samples:',
    'card.throughput':'Throughput','card.msg_trend':'Message Rate Trend','card.msg_types':'Message Types','card.system':'System',
    'emit.title':'Emit Message','emit.btn':'Emit',
    'log.title':'Message Log','log.waiting':'Waiting for messages...',
    'actions.title':'Quick Actions',
    'topo.local':'This node (dashboard)','topo.peer':'Peer agents','topo.relay':'Relay/bridge',
    'topo.peers_title':'Peer Details','topo.discovery_title':'Discovery Log','topo.timeline_title':'Connection Timeline',
    'about.what_title':'What is P2P Agent Mesh?',
    'about.what_text':'A decentralized publish/subscribe transport for AI agents — no central broker, pure TCP + JSON-lines. Agents communicate directly peer-to-peer with end-to-end ChaCha20-Poly1305 encryption and Ed25519 signatures.',
    'about.arch_title':'SNIN Architecture',
    'about.arch_text':'P2P Agent Mesh is the transport layer (L2) of SNIN V5. Smart Router distributes traffic across 4 channels: Direct, Gossip, Mesh, and Nostr. Mesh provides low-latency direct agent-to-agent communication with DHT-based discovery.',
    'about.links_title':'Links',
  },
  ru: {
    'nav.dash':'Дашборд','nav.topo':'Топология','nav.about':'О проекте',
    'hero.badge':'P2P Agent Mesh v0.5.1','hero.title':'Децентрализованный Mesh-транспорт','hero.sub':'Живой дашборд — peer-to-peer коммуникация агентов',
    'card.peers':'Пиры','card.peers_sub':'Узлы P2P-сети','card.msgs':'Сообщения','card.msgs_sub':'Получено через mesh',
    'card.wal':'WAL Буфер','card.wal_sub':'Записи SQLite WAL','card.dht':'DHT','card.dht_sub':'Агенты в DHT-кэше',
    'card.topics':'Топики','card.topics_sub':'Активные подписки','card.sig':'Sig Gate','card.sig_passed':'Пройдено',
    'card.sig_rej':'Отклонено','card.sig_sub':'Проверка подписей','card.lat':'Задержка','card.lat_samples':'замеров:',
    'card.throughput':'Пропускная','card.msg_trend':'Тренд сообщений','card.msg_types':'Типы сообщений','card.system':'Система',
    'emit.title':'Отправить сообщение','emit.btn':'Отправить',
    'log.title':'Лог сообщений','log.waiting':'Ожидание сообщений...',
    'actions.title':'Быстрые действия',
    'topo.local':'Этот узел (дашборд)','topo.peer':'Пиры-агенты','topo.relay':'Релей/мост',
    'topo.peers_title':'Детали пиров','topo.discovery_title':'Лог обнаружения','topo.timeline_title':'Хронология подключений',
    'about.what_title':'Что такое P2P Agent Mesh?',
    'about.what_text':'Децентрализованный pub/sub транспорт для AI-агентов — без центрального брокера, на чистом TCP + JSON-lines. Агенты общаются напрямую (peer-to-peer) с E2E-шифрованием ChaCha20-Poly1305 и Ed25519-подписями.',
    'about.arch_title':'Архитектура SNIN',
    'about.arch_text':'P2P Agent Mesh — транспортный слой (L2) SNIN V5. Smart Router распределяет трафик по 4 каналам: Direct, Gossip, Mesh и Nostr. Mesh обеспечивает низкую задержку прямого общения агентов с DHT-обнаружением.',
    'about.links_title':'Ссылки',
  }
};

let currentLang = 'en';
function t(k) { return I18N[currentLang]?.[k] || I18N['en'][k] || k; }
function applyLang(){
  document.documentElement.lang = currentLang;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.getAttribute('data-i18n'));
  });
  document.querySelectorAll('.lang-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.lang === currentLang)
  );
}
document.querySelectorAll('.lang-btn').forEach(b =>
  b.addEventListener('click', () => { currentLang = b.dataset.lang; applyLang(); })
);

# SNIN P2P Agent Mesh v0.6 — Roadmap

Спека от 2026-08-03. Цель: закрыть 3 разрыва с мировым уровнем.

---

## Исходное состояние (v0.5.2)

| Параметр | Значение | Разрыв |
|:--|:--|:--|
| NAT Traversal | ❌ localhost only | Iroh 95%, libp2p 70% |
| Консенсус | ❌ SPEC.md есть, кода нет | libp2p — Raft на уровне приложения |
| Масштаб | ⚠️ 1 нода, 1 пир, 3 агента | mesh-llm: 6 нод, 25 клиентов |
| DHT | ⚠️ 78 строк, 3 записи, bridge-driven | libp2p Kademlia: тысячи строк |

---

## Фаза 1: NAT Traversal + Multi-node (v0.6.0)

### Что делаем
- Транспорт слушает на `0.0.0.0` вместо `127.0.0.1`
- Добавляем STUN-подобный механизм через relay (`/api/register_peer`)
- mesh_peer может подключаться с удалённой машины
- Auto-discovery: при старте транспорт регистрируется в relay mesh-сети

### Спека
1. `transport.py`: `host="0.0.0.0"`, `port` — из переменной окружения `P2P_PORT` (fallback 39001)
2. Relay endpoint: `POST /api/register_peer {peer_id, addr, port}` — регистрация внешнего пира
3. `GET /api/known_peers` — список известных пиров для mesh_peer
4. mesh_peer: `--host <IP>` — подключается к удалённому дашборду
5. NAT check: `GET /api/health` с внешнего IP → подтверждение доступности

### Критерии готовности
- [ ] `curl http://<внешний_IP>:8090/api/health` → 200 (не localhost)
- [ ] mesh_peer с удалённой машины: handshake + heartbeat
- [ ] Peers ≥ 2 (локальный + удалённый)
- [ ] mesh=online с обоими пирами

### Коммит
`v0.6.0 — NAT traversal: bind 0.0.0.0, peer registration, remote mesh_peer`

---

## Фаза 2: Raft Consensus (v0.6.1)

### Что делаем
- Реализуем минимальный Raft: leader election + log replication
- 3 состояния: Follower → Candidate → Leader
- Heartbeat от лидера раз в 500ms
- WAL = Raft log (уже есть 39K записей)

### Спека
1. `phase0/raft.py`: класс RaftNode
   - `election_timeout`: 150-300ms random
   - `heartbeat_interval`: 500ms
   - `request_vote(term, candidate_id, last_log_index, last_log_term) → vote_granted`
   - `append_entries(term, leader_id, prev_log_index, prev_log_term, entries) → success`
2. Raft-сообщения идут через существующий TCP-транспорт (topic `_raft`)
3. Raft-лидер — единственный, кто пишет в WAL
4. Тесты: 3-node симуляция (3 инстанса transport.py в asyncio)
   - leader election за <2 секунд
   - log replication: лидер пишет → followers подтверждают
   - failover: лидер падает → новый лидер за <5 секунд

### Критерии готовности
- [ ] `python3 phase0/raft.py test` — 5 тестов проходят
- [ ] 3-node симуляция: leader elected за <2s
- [ ] WAL реплицируется на все ноды
- [ ] `/api/system` показывает `raft_role: "leader"` или `"follower"`
- [ ] `/api/health` → `consensus: "raft_active"`

### Коммит
`v0.6.1 — Raft consensus: leader election, log replication, 3-node tests`

---

## Фаза 3: DHT + Multi-agent Scale (v0.6.2)

### Что делаем
- DHT: динамическое обнаружение агентов (не только bridge)
- Каждый агент при старте публикует себя в DHT
- Bucket refresh каждые 60 секунд
- Поддержка до 50 агентов в DHT

### Спека
1. `phase0/dht.py`: добавляем Kademlia buckets (8 buckets по 3 бита)
2. `publish_self()` — агент публикует `{did, capabilities, endpoints}` в DHT
3. `find_agents(capability)` — поиск агентов по capability
4. `refresh_buckets()` — фоновая задача раз в 60s
5. Убираем жёсткую привязку к bridge для DHT-популяции

### Критерии готовности
- [ ] DHT entries > 3 (без bridge)
- [ ] Запуск второго инстанса → оба видят друг друга в DHT за <10s
- [ ] `find_agents("ping")` → возвращает dashboard
- [ ] 50 агентов в симуляции → DHT работает без деградации

### Коммит
`v0.6.2 — DHT Kademlia buckets, self-publish, 50-agent scale test`

---

## Итоговая цель (v0.6.2)

| Параметр | Было (v0.5.2) | Станет (v0.6.2) |
|:--|:--|:--|
| NAT Traversal | ❌ localhost | ✅ 0.0.0.0 + remote peer |
| Консенсус | ❌ SPEC only | ✅ Raft leader election + replication |
| DHT | ⚠️ 78 строк, bridge-driven | ✅ Kademlia buckets, self-publish |
| Peers | 1 | ≥ 2 (удалённый + локальный) |
| Агентов в DHT | 3 | ≥ 10 |
| Морфо-оценка | 8.4/10 | 9.2/10 |

---

## Валидация (общая)

```bash
# NAT
curl http://<внешний_IP>:8090/api/health  # должен вернуть 200

# Raft
curl -s http://localhost:8090/api/system | jq .raft_role  # "leader"

# DHT
curl -s http://localhost:8090/api/dht | jq '.data.count'  # > 3, растёт динамически

# Peers
curl -s http://localhost:8090/api/peers | jq '.data.count'  # ≥ 2
```

# distributed-bank-2pc

> Built as a course project for **CMPE541 — Advanced Database Systems** (M.Sc. in Computer Engineering).

A small distributed banking system that demonstrates how to keep money safe when multiple machines are touching the same accounts at the same time.

It implements three classical database / distributed systems building blocks from scratch:

- **Two-Phase Commit (2PC)** for atomic transactions across replicated nodes
- **A Distributed Lock Manager (DLM)** with shared/exclusive (S/X) lock semantics
- **Wait-Die deadlock prevention** using transaction timestamps

The goal is not to be a production database — it's to make these concepts concrete by actually building them, and to document the tradeoffs along the way.

---

## The Problem

Imagine two bank branches, each with their own server and their own copy of the account ledger. A customer at Branch 1 transfers 500 TL from Account A to Account B. At the same moment, another customer at Branch 2 transfers 700 TL from Account A to Account C. Account A only has 1000 TL.

Without coordination, the following can happen:

- Both nodes read balance = 1000
- Both nodes calculate "new balance = 1000 - amount" independently
- Both nodes write back. One write overwrites the other (lost update).
- Account A ends up with -200 TL, or with the wrong balance, and the two replicas disagree.

This is the classic concurrency problem in distributed systems. Solving it requires answering three questions:

1. **How do we serialize conflicting operations?** → locking
2. **How do we keep replicas in sync atomically?** → 2PC
3. **How do we prevent deadlocks when transactions wait on each other?** → Wait-Die

This project answers each of these explicitly.

---

## Architecture

```
                    ┌─────────────────────┐
                    │   DLM (Flask, :5000)│
                    │  Lock Manager + Tx  │
                    │  Timestamp Service  │
                    └──────────┬──────────┘
                               │
                       ┌───────┴───────┐
                       │   Redis :6379 │
                       │ (shared state)│
                       └───────────────┘
                               ▲
                  ┌────────────┴────────────┐
                  │                         │
        ┌─────────┴─────────┐     ┌─────────┴─────────┐
        │  Node 1 (:5001)   │◄───►│  Node 2 (:5002)   │
        │  Flask + SQLite   │ 2PC │  Flask + SQLite   │
        └───────────────────┘     └───────────────────┘
```

- The **DLM** is a separate service. It hands out locks and transaction timestamps. State is in Redis so it could be made HA later.
- Each **node** is a Flask service with its own SQLite database. Nodes are full replicas — every node holds every account.
- A transfer initiated on Node 1 acquires locks via the DLM, then runs 2PC against all other nodes to keep replicas consistent.

---

## How It Works

### 1. Locking (S/X locks)

Every account is a lockable resource. Two lock modes exist, mirroring database textbook semantics:

- **S (shared)** — multiple transactions can hold S on the same resource. Used for reads.
- **X (exclusive)** — only one transaction can hold X. Used for writes. Conflicts with both S and X held by other transactions.

Locks are stored in Redis under `lock:{resource_id}` as a JSON list of holders. Each holder has a `tx_id`, `mode`, `ts` (transaction timestamp) and `expires_at` lease.

**Why a lease?** If a node crashes while holding a lock, the lock would otherwise live forever and block every future transaction on that resource. The lease (default 10s) lets the system recover automatically. Live transactions can extend their lease via `/lock_extend`.

### 2. Two-Phase Commit (2PC)

When Node 1 receives a `transfer`, it acts as the **coordinator**:

**Phase 1 — Prepare:**
- Coordinator computes new balances locally.
- Coordinator sends `/prepare` to every other node with `(tx_id, account_id, new_balance)`.
- Each participant tries to acquire the X-lock locally and stages the new balance in memory (`prepared_txs`).
- Each participant votes YES or NO.

**Phase 2 — Commit / Abort:**
- If all votes are YES, the coordinator commits its own SQLite transaction and then sends `/commit` to all participants.
- If any vote is NO, the coordinator sends `/abort` and rolls back.

This guarantees that either all replicas reflect the transfer or none do.

### 3. Wait-Die Deadlock Prevention

When two transactions want conflicting locks, naive waiting can deadlock (T1 holds A and wants B; T2 holds B and wants A). Wait-Die avoids deadlocks using transaction timestamps:

- If the requester is **older** than the lock holder → **wait** (retry).
- If the requester is **younger** than the holder → **die** (abort and retry with the same timestamp).

Older transactions are never killed, so they eventually finish. Younger transactions may be aborted but keep their original timestamp on retry, so they age and eventually become "old" themselves. No deadlock, no starvation.

**Why Wait-Die over Wound-Wait?** Wait-Die only aborts the requester (a transaction that hasn't started doing work yet on this resource), while Wound-Wait aborts the holder (which has already done work). For a learning project where I wanted abort cost to be low and easy to reason about, Wait-Die was the cleaner choice.

### 4. Deadlock Prevention via Lock Ordering

In `transfer(from_id, to_id, amount)`, locks are always acquired in `min(from, to)` then `max(from, to)` order — independent of the direction of the transfer. This is the standard "dining philosophers" trick: if all transactions agree on a global order for acquiring resources, hold-and-wait cycles cannot form. Wait-Die is the safety net; lock ordering is the first line of defense.

---

## Project Structure

```
.
├── dlm/                      # Distributed Lock Manager service
│   ├── api.py                # Flask endpoints
│   ├── lock_manager.py       # S/X locks + Wait-Die logic
│   ├── tx_manager.py         # Transaction IDs + timestamps
│   └── storage.py            # Redis client
├── node/                     # Bank node service
│   ├── api.py                # Flask endpoints (transfer, deposit, balance, 2PC)
│   ├── node_service.py       # Coordinator logic
│   ├── dlm_client.py         # HTTP client to DLM
│   ├── replication_client.py # 2PC client to peer nodes
│   ├── db.py                 # SQLite wrapper
│   └── config.py             # Per-node config
├── scripts/
│   ├── run_dlm.py            # Start the DLM
│   ├── run_node1.py          # Start Node 1 (:5001)
│   ├── run_node2.py          # Start Node 2 (:5002)
│   └── test.py               # Integration tests for lock conflicts + replication
└── requirements.txt
```

---

## Running Locally

**Prerequisites:** Python 3.10+, Redis running on `127.0.0.1:6379`.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Redis (if not already running)
redis-server

# 3. In separate terminals:
python scripts/run_dlm.py       # DLM on :5000
python scripts/run_node1.py     # Node 1 on :5001
python scripts/run_node2.py     # Node 2 on :5002

# 4. Run the integration tests
python scripts/test.py
```

The test script verifies:

- Both nodes are healthy and replicas start equal
- A deposit on Node 1 is replicated to Node 2 via 2PC
- **S-S** lock requests on the same account succeed concurrently (compatible)
- **S-X**, **X-S**, and **X-X** requests conflict as expected (Wait-Die kicks in)

---

## API Reference

### Node endpoints (`:5001`, `:5002`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/ping` | Health check |
| `GET` | `/balance/<account_id>` | Read balance (acquires S-lock) |
| `POST` | `/deposit` | Deposit (acquires X-lock, runs 2PC) |
| `POST` | `/transfer` | Transfer between two accounts (2PC + lock ordering) |
| `POST` | `/prepare` | 2PC participant: prepare phase |
| `POST` | `/commit` | 2PC participant: commit phase |
| `POST` | `/abort` | 2PC participant: abort phase |
| `GET` | `/test_s_lock/<id>` | Helper: hold S-lock for 3s (used by tests) |
| `GET` | `/test_x_lock/<id>` | Helper: hold X-lock for 3s (used by tests) |

### DLM endpoints (`:5000`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/begin_tx` | Start a transaction, return `tx_id` and timestamp |
| `POST` | `/end_tx` | Mark transaction finished |
| `POST` | `/lock_acquire` | Request S or X lock; returns `GRANTED`, `RETRY`, or `ABORT` |
| `POST` | `/lock_extend` | Extend lock lease |
| `POST` | `/unlock_all` | Release all locks held by a transaction |

---

## Future Improvements

This project intentionally stops at "demonstrates the concept clearly." Things I would add for a more production-leaning version:

- **Atomic lock acquisition.** Currently `_load_holders` and `_save_holders` in the DLM are not atomic — under high contention, two concurrent acquire requests could overwrite each other. The fix is a Redis Lua script (or `WATCH`/`MULTI`/`EXEC`) that does the read-modify-write in one round trip.
- **Exponential backoff on lock retries.** Today retries use a fixed 200ms delay, which can cause thundering-herd effects under contention.
- **TX-locks mapping cleanup on crash.** The `tx_locks:{tx_id}` index doesn't have its own TTL — if a coordinator crashes between `unlock_all` and `end_tx`, the index can leak. Adding a TTL or a periodic janitor would close this.
- **Coordinator failure recovery in 2PC.** Standard 2PC blocks if the coordinator dies between phase 1 and phase 2. Three-Phase Commit (3PC) or a Paxos/Raft-based coordinator would lift this limitation.
- **`docker-compose` setup.** Single-command bring-up for all services + Redis.
- **Proper unit tests** with `pytest`, alongside the existing integration test.
- **Metrics & structured logging.** Currently the system is observable only via Flask debug logs.

---

## Concepts Demonstrated

- Distributed transactions (2PC: prepare / commit / abort)
- Concurrency control with shared/exclusive locks
- Deadlock prevention (Wait-Die + global lock ordering)
- Lock leasing for crash recovery
- Coordinator/participant pattern
- Service separation (lock manager as an independent service)

---

## Academic Background

This project was developed as a course project for **CMPE541 — Advanced Database Systems**, a graduate-level course in the M.Sc. in Computer Engineering program. The course covers transaction management, concurrency control, distributed databases, and recovery — and this implementation was a way to ground those topics in working code rather than just exam answers.

Specifically, the design choices in this repo trace back to standard references in the field:

- **2PC protocol** — Bernstein, Hadzilacos, and Goodman, *Concurrency Control and Recovery in Database Systems* (1987).
- **Strict two-phase locking with S/X modes** — Gray and Reuter, *Transaction Processing: Concepts and Techniques* (1993).
- **Wait-Die deadlock prevention** — Rosenkrantz, Stearns, and Lewis, "System Level Concurrency Control for Distributed Database Systems" (1978).

Working from these primary sources (rather than blog posts) was a deliberate choice: the original papers make the assumptions and tradeoffs explicit in a way that secondary summaries usually flatten.

---

<details>
<summary><b>🇹🇷 Türkçe açıklama</b></summary>

# distributed-bank-2pc

> Bilgisayar Mühendisliği Yüksek Lisansı kapsamında **CMPE541 — Advanced Database Systems** dersi için yapıldı.

Birden fazla makinenin aynı anda aynı hesaplara dokunduğu bir bankacılık sisteminde paranın tutarlı kalmasını sağlayan küçük bir distributed sistem demosu.

Üç klasik database / distributed systems yapı taşını sıfırdan implement ediyor:

- **Two-Phase Commit (2PC)** — replica'lar arasında atomik transaction'lar için
- **Distributed Lock Manager (DLM)** — shared/exclusive (S/X) lock semantiği ile
- **Wait-Die deadlock prevention** — transaction timestamp'leri kullanarak

Amaç production-grade bir database yapmak değil; bu kavramları gerçekten kod yazarak somutlaştırmak ve yol boyunca tradeoff'ları belgelemek.

## Problem

İki banka şubesi düşün, her birinin kendi sunucusu ve kendi hesap defterinin (ledger) bir kopyası var. Şube 1'deki müşteri A hesabından B hesabına 500 TL transfer ediyor. Tam o sırada Şube 2'deki başka bir müşteri A hesabından C hesabına 700 TL transfer ediyor. A hesabında sadece 1000 TL var.

Koordinasyon olmadan şu olabilir:

- İki node da bakiyeyi 1000 olarak okur
- İki node da bağımsız olarak "yeni bakiye = 1000 - tutar" hesaplar
- İki node da yazar. Bir yazma diğerini ezer (lost update).
- A hesabı -200 TL ile veya yanlış bakiye ile kalır ve iki replica birbirinden farklı görür.

Distributed systems'in klasik concurrency problemi. Çözmek için üç soruyu cevaplamak gerekir:

1. **Çakışan operasyonları nasıl serialize ederiz?** → locking
2. **Replica'ları nasıl atomik tutarız?** → 2PC
3. **Birbirini bekleyen transaction'larda deadlock'u nasıl önleriz?** → Wait-Die

Bu proje üçünü de açıkça cevaplıyor.

## Mimari

DLM ayrı bir servis (port 5000), Redis'i shared state olarak kullanıyor. Her bank node'u (5001, 5002) kendi Flask + SQLite'ı ile çalışıyor ve replikasyonu 2PC ile yapıyor. Mimari diyagramı için yukarıdaki İngilizce bölüme bak.

## Nasıl Çalışıyor

**Locking:** Her hesap kilitlenebilir bir kaynak. S-lock (paylaşımlı, okuma için) ve X-lock (özel, yazma için). Lock'lar Redis'te tutulur, `expires_at` lease'i sayesinde bir node çökerse lock sonsuza kadar takılı kalmaz.

**2PC:** Transfer'i alan node coordinator olur. Önce prepare fazında diğer node'lara haber verir, hepsi YES derse commit fazına geçer, biri NO derse hepsine abort gönderir.

**Wait-Die:** İki transaction çakıştığında timestamp'lere bakar. İsteyen daha eskiyse → bekle. İsteyen daha gençse → öl (abort + retry). Eski transaction asla öldürülmez, bu yüzden starvation yok.

**Lock ordering:** `transfer`'da her zaman önce `min(from, to)` sonra `max(from, to)` lock'lanıyor — yöne bakılmaksızın. Bu, klasik "dining philosophers" çözümü; cycle oluşamaz. Wait-Die güvenlik ağı, lock ordering ilk savunma hattı.

## Çalıştırma

**Gereksinimler:** Python 3.10+, Redis çalışır durumda.

```bash
pip install -r requirements.txt
redis-server

# ayrı terminallerde:
python scripts/run_dlm.py
python scripts/run_node1.py
python scripts/run_node2.py
python scripts/test.py
```

## Future Improvements

İngilizce bölümdeki "Future Improvements" başlığına bak — Lua script ile atomik lock acquire, exponential backoff, docker-compose, pytest unit testleri, 3PC ile coordinator failure recovery vb.

</details>

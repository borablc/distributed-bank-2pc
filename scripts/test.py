import threading
import time
from typing import Any, Dict, Tuple
import requests

NODE1 = "http://127.0.0.1:5001"
NODE2 = "http://127.0.0.1:5002"
NODES = [NODE1, NODE2]


# ----------------- HTTP HELPERS ----------------- #

def http_get(url: str) -> Tuple[int, Any]:
    try:
        resp = requests.get(url, timeout=10)
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        return resp.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}


def http_post(url: str, payload: Dict) -> Tuple[int, Any]:
    try:
        resp = requests.post(url, json=payload, timeout=10)
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        return resp.status_code, data
    except Exception as e:
        return 0, {"error": str(e)}


def print_header(title: str):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# ----------------- BASIC TESTS ----------------- #

def test_servers_up():
    print_header("TEST 1: Nodelar ayakta mı /ping")

    for node in NODES:
        code, data = http_get(f"{node}/ping")
        print(f"{node}/ping -> {code}, {data}")
        if code != 200:
            print(f"[ERROR] {node} ayakta değil gibi görünüyor.")


def get_balance(node: str, account_id: int) -> Tuple[int, Dict]:
    code, data = http_get(f"{node}/balance/{account_id}")
    if isinstance(data, dict):
        return code, data
    return code, {"raw": data}


def test_data_equality(account_ids=(1, 2, 3)):
    print_header("TEST 2: Replica datası aynı mı?")

    for acc_id in account_ids:
        c1, b1 = get_balance(NODE1, acc_id)
        c2, b2 = get_balance(NODE2, acc_id)
        print(f"Account {acc_id} -> node1: {c1}, {b1}")
        print(f"Account {acc_id} -> node2: {c2}, {b2}")

        if c1 == 200 and c2 == 200:
            if b1.get("balance") != b2.get("balance"):
                print(f"[ERROR] Account {acc_id} için replica mismatch!"
                      f"node1={b1.get('balance')} node2={b2.get('balance')}")
            else:
                print(f"[OK] Account {acc_id} için balance'lar eşit.")
        else:
            print(f"[WARN] Account {acc_id} için balance okunamadı.")


def test_deposit_replication(account_id: int = 1, amount: int = 100):
    print_header("TEST 3: Deposit replication")

    # önceki balance
    c1_before, b1_before = get_balance(NODE1, account_id)
    c2_before, b2_before = get_balance(NODE2, account_id)
    print(f"Before deposit -> node1: {c1_before}, {b1_before}")
    print(f"Before deposit -> node2: {c2_before}, {b2_before}")

    code, resp = http_post(f"{NODE1}/deposit", {
        "account_id": account_id,
        "amount": amount,
    })
    print(f"Deposit node1 -> {code}, {resp}")

    # sonraki
    c1_after, b1_after = get_balance(NODE1, account_id)
    c2_after, b2_after = get_balance(NODE2, account_id)
    print(f"After deposit  -> node1: {c1_after}, {b1_after}")
    print(f"After deposit  -> node2: {c2_after}, {b2_after}")

    if c1_after == 200 and c2_after == 200:
        if b1_after.get("balance") != b2_after.get("balance"):
            print("[ERROR] Deposit sonrası replica mismatch!")
        else:
            print("[OK] Deposit sonrası replica'lar eşit.")
    else:
        print("[WARN] Deposit sonrası balance okunamadı.")


# ----------------- LOCK TEST THREAD HELPERS ----------------- #

def call_test_s_lock(node: str, account_id: int, label: str, results: Dict[str, Tuple[int, Any]]):
    print(f"[{label}] S-lock isteği -> {node}/test_s_lock/{account_id}")
    code, data = http_get(f"{node}/test_s_lock/{account_id}")
    print(f"[{label}] S-lock cevap -> {code}, {data}")
    results[label] = (code, data)


def call_test_x_lock(node: str, account_id: int, label: str, results: Dict[str, Tuple[int, Any]]):
    print(f"[{label}] X-lock isteği -> {node}/test_x_lock/{account_id}")
    code, data = http_get(f"{node}/test_x_lock/{account_id}")
    print(f"[{label}] X-lock cevap -> {code}, {data}")
    results[label] = (code, data)


# ----------------- LOCK TESTS ----------------- #

def test_s_s_compatible(account_id: int = 1):
    print_header("TEST 4: S-S compatible mı? (iki taraftan S-lock)")

    results: Dict[str, Tuple[int, Any]] = {}

    t1 = threading.Thread(target=call_test_s_lock,
                          args=(NODE1, account_id, "S1", results))
    t2 = threading.Thread(target=call_test_s_lock,
                          args=(NODE2, account_id, "S2", results))

    t1.start()
    # biraz overlap garantilemek için minik delay
    time.sleep(0.2)
    t2.start()

    t1.join()
    t2.join()

    s1 = results.get("S1", (0, {}))
    s2 = results.get("S2", (0, {}))

    ok1 = s1[0] == 200 and isinstance(s1[1], dict) and s1[1].get("status") == "ok"
    ok2 = s2[0] == 200 and isinstance(s2[1], dict) and s2[1].get("status") == "ok"

    if ok1 and ok2:
        print("[OK] Aynı account için iki farklı node S-lock alabiliyor (S-S compatible).")
    else:
        print("[WARN] S-S testinde beklenmeyen sonuç, loglara bakmak gerek.")


def test_s_x_conflict(account_id: int = 1):
    print_header("TEST 5: S-X conflict (S-lock varken X-lock)")

    results: Dict[str, Tuple[int, Any]] = {}

    # önce S-lock, sonra X-lock
    t1 = threading.Thread(target=call_test_s_lock,
                          args=(NODE1, account_id, "S", results))
    t2 = threading.Thread(target=call_test_x_lock,
                          args=(NODE2, account_id, "X", results))

    t1.start()
    time.sleep(0.2)
    t2.start()

    t1.join()
    t2.join()

    s_res = results.get("S", (0, {}))
    x_res = results.get("X", (0, {}))

    s_ok = s_res[0] == 200 and isinstance(s_res[1], dict) and s_res[1].get("status") == "ok"
    x_ok = x_res[0] == 200 and isinstance(x_res[1], dict) and x_res[1].get("status") == "ok"

    print(f"S-lock sonucu: {s_res}")
    print(f"X-lock sonucu: {x_res}")

    if s_ok and not x_ok:
        print("[OK] S-lock varken X-lock alamadık -> S-X conflict gözlendi (beklenen).")
    elif not s_ok and x_ok:
        print("[INFO] X yaşlı, S genç olmuş olabilir (Wait-Die sonucu). Yine conflict var.")
    else:
        print("[WARN] S-X testinde sonuçlar beklenenden farklı, DLM loglarını incelemek lazım.")

def test_x_s_conflict(account_id: int = 1):
    print_header("TEST 6: X-S conflict (X-lock varken S-lock)")
    results: Dict[str, Tuple[int, Any]] = {}

    # önce X-lock, sonra S-lock
    t1 = threading.Thread(target=call_test_x_lock,
                          args=(NODE1, account_id, "X", results))
    t2 = threading.Thread(target=call_test_s_lock,
                          args=(NODE2, account_id, "S", results))

    t1.start()
    time.sleep(0.2)
    t2.start()

    t1.join()
    t2.join()

    x_res = results.get("X", (0, {}))
    s_res = results.get("S", (0, {}))

    s_ok = s_res[0] == 200 and isinstance(s_res[1], dict) and s_res[1].get("status") == "ok"
    x_ok = x_res[0] == 200 and isinstance(x_res[1], dict) and x_res[1].get("status") == "ok"

    print(f"S-lock sonucu: {s_res}")
    print(f"X-lock sonucu: {x_res}")

    if x_ok and not s_ok:
        print("[OK] X-lock varken S-lock alamadık -> X-S conflict gözlendi (beklenen).")
    elif s_ok and not x_ok:
        print("[INFO] S yaşlı, X genç olmuş olabilir (Wait-Die sonucu). Yine conflict var.")
    else:
        print("[WARN] S-X testinde sonuçlar beklenenden farklı, DLM loglarını incelemek lazım.")

def test_x_x_conflict(account_id: int = 1):
    print_header("TEST 7: X-X conflict (iki taraf da X-lock)")

    results: Dict[str, Tuple[int, Any]] = {}

    t1 = threading.Thread(target=call_test_x_lock,
                          args=(NODE1, account_id, "X1", results))
    t2 = threading.Thread(target=call_test_x_lock,
                          args=(NODE2, account_id, "X2", results))

    t1.start()
    time.sleep(0.2)
    t2.start()

    t1.join()
    t2.join()

    x1 = results.get("X1", (0, {}))
    x2 = results.get("X2", (0, {}))

    x1_ok = x1[0] == 200 and isinstance(x1[1], dict) and x1[1].get("status") == "ok"
    x2_ok = x2[0] == 200 and isinstance(x2[1], dict) and x2[1].get("status") == "ok"

    print(f"X1 sonucu: {x1}")
    print(f"X2 sonucu: {x2}")

    if x1_ok and not x2_ok or x2_ok and not x1_ok:
        print("[OK] Aynı anda iki X-lock alamadık, X-X conflict doğru çalışıyor.")
    elif not x1_ok and not x2_ok:
        print("[INFO] Her ikisi de reddedildi, policy’ye göre olabilir (örn. timestamp durumu).")
    else:
        print("[WARN] X-X testinde ikisi de başarılı görünüyor; lock mantığını kontrol et.")


# ----------------- MAIN ----------------- #

def main():
    print_header("DLM / LOCK TEST RUNNER")
    print("Bu script Node1 ve Node2'de /ping, /balance, /deposit, "
          "/test_s_lock, /test_x_lock endpoint'lerine güveniyor.\n")

    test_servers_up()
    test_data_equality()
    test_deposit_replication(account_id=1, amount=100)
    test_s_s_compatible(account_id=1)
    test_s_x_conflict(account_id=1)
    test_x_s_conflict(account_id=1)
    test_x_x_conflict(account_id=1)

    print("\nTüm lock testleri bitti.\n")


if __name__ == "__main__":
    main()

import sqlite3
import os

DB_FOLDER = os.path.join(os.path.dirname(__file__), "data")

class NodeDatabase:
    def __init__(self, node_id):
        self.node_id = node_id
        self.db_path = os.path.join(DB_FOLDER, f"node{node_id}.db")

        # Klasör yoksa oluştur
        os.makedirs(DB_FOLDER, exist_ok=True)

        # Bağlantı oluştur
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Tabloyu oluştur
        self._create_schema()

    def _create_schema(self):
        query = """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    # Basic operations
    def get_balance(self, account_id):
        cur = self.conn.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
        row = cur.fetchone()
        return row["balance"] if row else None

    def update_balance(self, account_id, new_balance):
        self.conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (new_balance, account_id))
        self.conn.commit()

    def create_account(self, account_id, initial_balance):
        self.conn.execute("INSERT INTO accounts (id, balance) VALUES (?, ?)", (account_id, initial_balance))
        self.conn.commit()

    # Transaction wrappers (2PC için kullanılacak)
    def begin(self):
        self.conn.execute("BEGIN")

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

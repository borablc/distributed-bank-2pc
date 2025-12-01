import sqlite3
import os

DB_FOLDER = os.path.join(os.path.dirname(__file__), "data")


class NodeDatabase:
    def __init__(self, node_id: int):
        self.node_id = node_id

        os.makedirs(DB_FOLDER, exist_ok=True)
        self.db_path = os.path.join(DB_FOLDER, f"node{node_id}.db")

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._create_schema()
        self._seed_initial_data() # Clearing and setting the base values for testing purposes.

    def _create_schema(self):
        query = """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    def _seed_initial_data(self):
        self.conn.execute("DELETE FROM accounts;")

        initial_accounts = [
            (1, 1000),
            (2, 1500),
            (3, 3000),
        ]

        self.conn.executemany(
            "INSERT INTO accounts (id, balance) VALUES (?, ?);",
            initial_accounts,
        )
        self.conn.commit()

    def begin(self):
        self.conn.execute("BEGIN")

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    # --- Basit CRUD ---

    def get_balance(self, account_id: int):
        cur = self.conn.execute(
            "SELECT balance FROM accounts WHERE id = ?",
            (account_id,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        return row["balance"]

    def create_account(self, account_id: int, initial_balance: int):
        self.conn.execute(
            "INSERT INTO accounts (id, balance) VALUES (?, ?)",
            (account_id, initial_balance)
        )

    def update_balance(self, account_id: int, new_balance: int):
        self.conn.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?",
            (new_balance, account_id)
        )
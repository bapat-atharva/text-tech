from BaseXClient import BaseXClient

# Configuration
BASEX_CONFIG = {
    "host": "localhost",
    "port": 1984,
    "user": "admin",
    "password": "admin"
}

class BaseXConnection:
    def __init__(self):
        self.client = None

    # init connection
    def connect(self):
        try:
            self.client = BaseXClient.Session(
                BASEX_CONFIG["host"],
                BASEX_CONFIG["port"],
                BASEX_CONFIG["user"],
                BASEX_CONFIG["password"]
            )

            return True
        except Exception as e:
            return False

    def close(self):
        if self.client:
            self.client.close()

    # connect to db directly
    def connect_db(self):
        try:
            self.connect()

            if self.is_database_open():
                return True
            self.client.execute("open BookCatalog")

            return True
        except Exception as e:
            return False

    def is_basex_alive(self):
        """Returns True if BaseX session is still alive."""
        try:
            # Send a minimal query that always succeeds
            self.client.query("1").execute()
            return True
        except Exception:
            return False

    def is_database_open(self):
        try:
            info = self.client.execute("info db")  # Returns DB name and stats if one is open
            return True
        except Exception:
            return False

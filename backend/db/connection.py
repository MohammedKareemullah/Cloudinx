import psycopg2
import psycopg2.extras
import psycopg2.extensions
from contextlib import contextmanager
from config.settings import DATABASE_URL

# Postgres NUMERIC comes back as decimal.Decimal, which can't be mixed with floats in the
# sizing/pricing math. Convert every NUMERIC to float at the driver level, once.
_DEC2FLOAT = psycopg2.extensions.new_type(
    psycopg2.extensions.DECIMAL.values,
    "DEC2FLOAT",
    lambda value, cur: float(value) if value is not None else None,
)
psycopg2.extensions.register_type(_DEC2FLOAT)


@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def init_schema(schema_path: str = "db/schema.sql"):
    with get_conn() as conn:
        with open(schema_path, encoding="utf-8") as f:
            sql = f.read()
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print(f"Schema applied from {schema_path}")

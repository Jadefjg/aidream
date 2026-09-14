from sqlalchemy import inspect, text


def migrate_schema(engine) -> None:
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    with engine.begin() as conn:
        if "tokens" in tables:
            cols = {c["name"] for c in insp.get_columns("tokens")}
            if "used_quota" not in cols:
                conn.execute(text("ALTER TABLE tokens ADD COLUMN used_quota INTEGER DEFAULT 0"))
        if "redemptions" in tables:
            cols = {c["name"] for c in insp.get_columns("redemptions")}
            if "name" not in cols:
                conn.execute(text("ALTER TABLE redemptions ADD COLUMN name VARCHAR(64) DEFAULT ''"))
            if "expired_time" not in cols:
                conn.execute(text("ALTER TABLE redemptions ADD COLUMN expired_time INTEGER DEFAULT 0"))
        if "upstream_channels" not in tables:
            conn.execute(text("""CREATE TABLE upstream_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(64) UNIQUE NOT NULL,
                base_url VARCHAR(512) NOT NULL, api_key VARCHAR(512) DEFAULT '',
                provider VARCHAR(32) DEFAULT 'openai', groups TEXT DEFAULT 'default',
                models TEXT DEFAULT '', priority INTEGER DEFAULT 0, status INTEGER DEFAULT 1,
                weight INTEGER DEFAULT 1, failure_count INTEGER DEFAULT 0,
                last_failure INTEGER DEFAULT 0, created_at INTEGER DEFAULT 0
            )"""))

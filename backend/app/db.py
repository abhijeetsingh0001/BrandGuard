import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "brandguard.db"

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rule_type TEXT NOT NULL,
            pattern TEXT NOT NULL,
            replacement TEXT DEFAULT '',
            severity TEXT NOT NULL DEFAULT 'medium',
            explanation TEXT NOT NULL DEFAULT '',
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_by TEXT NOT NULL DEFAULT 'Creator',
            reviewer TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
            rule_id INTEGER REFERENCES rules(id) ON DELETE SET NULL,
            rule_name TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            excerpt TEXT NOT NULL,
            explanation TEXT NOT NULL,
            suggestion TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
            actor TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        count = db.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
        if count == 0:
            db.executemany("""INSERT INTO rules
                (name, rule_type, pattern, replacement, severity, explanation)
                VALUES (?, ?, ?, ?, ?, ?)""", [
                ("Avoid absolute superlatives", "prohibited", "best", "a strong choice", "medium",
                 "Absolute superiority claims need approved evidence and may overstate what the brand can prove."),
                ("Avoid guaranteed outcomes", "prohibited", "guarantee", "designed to help", "high",
                 "Guaranteed outcomes are high-risk unless the organisation has approved substantiation."),
                ("Avoid unsupported percentage claims", "claim", r"\b\d+\s*%", "", "high",
                 "Percentage claims should be linked to an approved source before publication."),
                ("Use approved product name", "required", "BrandGuard", "BrandGuard", "low",
                 "Use the approved product name consistently where the product is referenced.")
            ])

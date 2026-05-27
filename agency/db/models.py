"""Database models for the AI Agency system."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "agency.db"


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            niche TEXT NOT NULL,
            city TEXT,
            state TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            rating REAL,
            review_count INTEGER,
            score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'new',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            contacted_at TEXT,
            last_followup_at TEXT,
            followup_count INTEGER DEFAULT 0,
            source TEXT DEFAULT 'google_places'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER REFERENCES leads(id),
            business_name TEXT NOT NULL,
            contact_name TEXT,
            email TEXT NOT NULL,
            phone TEXT,
            niche TEXT,
            service TEXT NOT NULL,
            plan TEXT DEFAULT 'starter',
            mrr REAL DEFAULT 0,
            setup_fee REAL DEFAULT 0,
            status TEXT DEFAULT 'onboarding',
            onboarded_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            next_report_at TEXT,
            stripe_customer_id TEXT,
            notes TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS services_delivered (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER REFERENCES clients(id),
            service_type TEXT NOT NULL,
            title TEXT,
            content TEXT,
            delivered_at TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'pending'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS outreach_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER REFERENCES leads(id),
            type TEXT NOT NULL,
            subject TEXT,
            body TEXT,
            sent_at TEXT DEFAULT (datetime('now')),
            opened INTEGER DEFAULT 0,
            replied INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS revenue_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER REFERENCES clients(id),
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            recorded_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS niche_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT,
            niche TEXT,
            title TEXT,
            description TEXT,
            budget_min REAL,
            budget_max REAL,
            score INTEGER,
            url TEXT,
            found_at TEXT DEFAULT (datetime('now')),
            acted_on INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def insert_lead(data: dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?" for _ in data])
    c.execute(f"INSERT OR IGNORE INTO leads ({cols}) VALUES ({placeholders})", list(data.values()))
    conn.commit()
    lid = c.lastrowid
    conn.close()
    return lid


def get_leads(status=None, limit=100):
    conn = get_conn()
    c = conn.cursor()
    if status:
        rows = c.execute("SELECT * FROM leads WHERE status=? LIMIT ?", (status, limit)).fetchall()
    else:
        rows = c.execute("SELECT * FROM leads LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_lead(lead_id: int, updates: dict):
    conn = get_conn()
    c = conn.cursor()
    sets = ", ".join([f"{k}=?" for k in updates])
    c.execute(f"UPDATE leads SET {sets} WHERE id=?", list(updates.values()) + [lead_id])
    conn.commit()
    conn.close()


def insert_client(data: dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?" for _ in data])
    c.execute(f"INSERT INTO clients ({cols}) VALUES ({placeholders})", list(data.values()))
    conn.commit()
    cid = c.lastrowid
    conn.close()
    return cid


def get_clients(status=None):
    conn = get_conn()
    c = conn.cursor()
    if status:
        rows = c.execute("SELECT * FROM clients WHERE status=?", (status,)).fetchall()
    else:
        rows = c.execute("SELECT * FROM clients").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_revenue(client_id: int, amount: float, rev_type: str, description: str = ""):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO revenue_log (client_id, amount, type, description) VALUES (?,?,?,?)",
        (client_id, amount, rev_type, description),
    )
    conn.commit()
    conn.close()


def get_mrr():
    conn = get_conn()
    c = conn.cursor()
    row = c.execute("SELECT SUM(mrr) as total FROM clients WHERE status='active'").fetchone()
    conn.close()
    return row["total"] or 0.0


def get_revenue_this_week():
    conn = get_conn()
    c = conn.cursor()
    row = c.execute(
        "SELECT SUM(amount) as total FROM revenue_log WHERE recorded_at >= datetime('now', '-7 days')"
    ).fetchone()
    conn.close()
    return row["total"] or 0.0


def log_outreach(lead_id: int, data: dict):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO outreach_log (lead_id, type, subject, body) VALUES (?,?,?,?)",
        (lead_id, data.get("type", "email"), data.get("subject", ""), data.get("body", "")),
    )
    conn.commit()
    conn.close()


def log_service_delivery(client_id: int, service_type: str, title: str, content: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO services_delivered (client_id, service_type, title, content, status) VALUES (?,?,?,?,'delivered')",
        (client_id, service_type, title, content),
    )
    conn.commit()
    conn.close()


def save_opportunity(data: dict):
    conn = get_conn()
    c = conn.cursor()
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?" for _ in data])
    c.execute(f"INSERT INTO niche_opportunities ({cols}) VALUES ({placeholders})", list(data.values()))
    conn.commit()
    conn.close()

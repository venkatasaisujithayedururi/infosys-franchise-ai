import sqlite3, os
import pandas as pd
from config import DB_PATH

def get_conn():
    """Establishes and returns a connection to the SQLite database with WAL enabled."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def save_chat_message(username, role, message):
    """Saves a user or assistant chat message to the history ledger."""
    try:
        with get_conn() as conn:
            conn.execute("INSERT INTO chat_history (username, role, message) VALUES (?, ?, ?);", (username, role, message))
            conn.commit()
    except Exception:
        pass

def load_chat_history(username=None, limit=100):
    """Loads chat history for a specific user or the global system up to the specified limit."""
    try:
        with get_conn() as conn:
            if username:
                df = pd.read_sql("SELECT role, message FROM chat_history WHERE username=? ORDER BY id ASC LIMIT ?;", conn, params=(username, limit))
                if df.empty:
                    df = pd.read_sql("SELECT role, message FROM chat_history ORDER BY id ASC LIMIT ?;", conn, params=(limit,))
            else:
                df = pd.read_sql("SELECT role, message FROM chat_history ORDER BY id ASC LIMIT ?;", conn, params=(limit,))

            res = []
            for _, r in df.iterrows():
                content_val = str(r.get("message") or r.get("content") or "")
                res.append({
                    "role": str(r.get("role", "assistant")),
                    "content": content_val,
                    "message": content_val
                })
            return res
    except Exception:
        return []

def clear_chat_history(username=None):
    """Clears stored chat history entries."""
    try:
        with get_conn() as conn:
            if username:
                conn.execute("DELETE FROM chat_history WHERE username=?;", (username,))
            else:
                conn.execute("DELETE FROM chat_history;")
            conn.commit()
    except Exception:
        pass

def init_db():
    """Initializes all database tables and executes migrations for existing database schemas."""
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            role TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,
            security_question TEXT,
            security_answer TEXT,
            profile_picture TEXT,
            failed_attempts INTEGER DEFAULT 0,
            lock_until DATETIME DEFAULT NULL,
            account_status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Safe migration for DBs created before these columns existed
        existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(users);").fetchall()}
        migrations = {
            "username": "ALTER TABLE users ADD COLUMN username TEXT;",
            "security_question": "ALTER TABLE users ADD COLUMN security_question TEXT;",
            "security_answer": "ALTER TABLE users ADD COLUMN security_answer TEXT;",
            "profile_picture": "ALTER TABLE users ADD COLUMN profile_picture TEXT;",
            "failed_attempts": "ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0;",
            "lock_until": "ALTER TABLE users ADD COLUMN lock_until DATETIME DEFAULT NULL;",
            "account_status": "ALTER TABLE users ADD COLUMN account_status TEXT DEFAULT 'active';",
        }
        for col, ddl in migrations.items():
            if col not in existing_cols:
                try:
                    conn.execute(ddl)
                except Exception:
                    pass

        conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id TEXT,
            outlet_id TEXT,
            severity TEXT,
            category TEXT,
            message TEXT,
            date TEXT,
            resolved INT DEFAULT 0
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            shipment_id TEXT PRIMARY KEY,
            origin_port TEXT,
            dest_port TEXT,
            carrier TEXT,
            status TEXT,
            eta TEXT,
            weight_kg REAL,
            hs_code TEXT,
            predicted_delay_risk REAL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS freight_quotes (
            quote_id TEXT PRIMARY KEY,
            shipment_id TEXT,
            customer_id TEXT,
            carrier TEXT,
            base_cost REAL,
            insurance REAL,
            customs_fee REAL,
            fuel_surcharge REAL,
            final_price REAL,
            margin_pct REAL,
            status TEXT,
            created_at TEXT
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ports (
            port_id TEXT PRIMARY KEY,
            port_name TEXT,
            country TEXT,
            congestion_index REAL,
            avg_dwell_days REAL,
            lat REAL,
            lon REAL,
            region TEXT
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS carriers (
            carrier_id TEXT PRIMARY KEY,
            name TEXT,
            rating REAL,
            on_time_pct REAL,
            avg_cost_index REAL,
            risk_level TEXT
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT,
            industry TEXT,
            priority_tier TEXT,
            credit_risk REAL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ml_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module TEXT,
            model_name TEXT,
            metric_name TEXT,
            metric_value REAL,
            trained_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS outlets (
            outlet_id TEXT PRIMARY KEY,
            outlet_name TEXT,
            location TEXT,
            tier TEXT,
            revenue REAL,
            operating_costs REAL,
            customer_satisfaction REAL,
            staff_headcount INT
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            staff_id TEXT PRIMARY KEY,
            outlet_id TEXT,
            name TEXT,
            role TEXT,
            salary REAL,
            overtime_hrs REAL,
            job_satisfaction INT,
            age INT,
            tenure_years INT,
            work_life_balance INT,
            predicted_attrition_prob REAL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            record_id TEXT PRIMARY KEY,
            outlet_id TEXT,
            sku_name TEXT,
            category TEXT,
            current_stock INT,
            reorder_threshold INT,
            weekly_demand REAL,
            lead_time_days INT,
            stockout_risk_prob REAL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS marketing (
            campaign_id TEXT PRIMARY KEY,
            outlet_id TEXT,
            campaign_name TEXT,
            channel TEXT,
            budget REAL,
            actual_roi REAL,
            reach INT,
            conversions INT,
            start_date TEXT,
            end_date TEXT
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id TEXT PRIMARY KEY,
            outlet_id TEXT,
            rating INT,
            comment TEXT,
            date TEXT,
            sentiment_score REAL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS audits (
            audit_id TEXT PRIMARY KEY,
            outlet_id TEXT,
            audit_date TEXT,
            score REAL,
            violations INT,
            category TEXT,
            status TEXT,
            notes TEXT
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS weather_risks (
            port_name TEXT PRIMARY KEY,
            current_severity INT,
            forecast TEXT,
            wind_speed REAL,
            wave_height REAL,
            temperature REAL
        );
        """)
        conn.commit()

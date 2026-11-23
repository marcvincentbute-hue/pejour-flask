"""Parameterized PostgreSQL access. One transaction per request or CLI command."""
import hashlib
import psycopg
from psycopg.rows import dict_row
from flask import g, current_app

def connection():
    if 'db' not in g:
        g.db = psycopg.connect(current_app.config['DATABASE_URL'], row_factory=dict_row)
    return g.db

def execute(sql, params=()):
    return connection().execute(sql, params)

def one(sql, params=()):
    return execute(sql, params).fetchone()

def all_rows(sql, params=()):
    return execute(sql, params).fetchall()

def lock(value):
    # Transaction advisory locks serialize requests across workers and browsers.
    number = int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], 'big', signed=True)
    execute('SELECT pg_advisory_xact_lock(%s)', (number,))

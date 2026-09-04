"""Demo authentication -- employee_id + password checked against a salted
hash in the employees table. Not enterprise-grade (no lockout, rate
limiting, or password policy); enough to gate access and identify who's
logged in for this prototype, per the user's explicit choice.
"""

import hashlib
import secrets
import sqlite3

from hr_rag.config import EMPLOYEE_DB_PATH, PASSWORD_HASH_ITERATIONS


def hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    """Returns (salt_hex, hash_hex). Pass an existing salt_hex to verify
    against a stored hash; omit it to generate a new salt for a new password."""
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_HASH_ITERATIONS)
    return salt.hex(), digest.hex()


def verify_login(employee_id: str, password: str) -> bool:
    conn = sqlite3.connect(EMPLOYEE_DB_PATH)
    try:
        cur = conn.execute(
            "SELECT password_salt, password_hash FROM employees WHERE employee_id = ?",
            (employee_id,),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return False
    salt_hex, stored_hash_hex = row
    _, computed_hash_hex = hash_password(password, salt_hex)
    return secrets.compare_digest(computed_hash_hex, stored_hash_hex)

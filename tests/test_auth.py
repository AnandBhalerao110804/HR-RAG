import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.seed_employees import DEMO_PASSWORD, seed
from hr_rag.auth import hash_password, verify_login


def setup_module():
    seed()


def test_hash_password_round_trip():
    salt_hex, hash_hex = hash_password("hunter2")
    _, recomputed_hex = hash_password("hunter2", salt_hex)
    assert recomputed_hex == hash_hex


def test_hash_password_wrong_password_does_not_match():
    salt_hex, hash_hex = hash_password("hunter2")
    _, wrong_hex = hash_password("not-hunter2", salt_hex)
    assert wrong_hex != hash_hex


def test_verify_login_accepts_correct_demo_password():
    assert verify_login("E1001", DEMO_PASSWORD) is True


def test_verify_login_rejects_wrong_password():
    assert verify_login("E1001", "wrong-password") is False


def test_verify_login_rejects_unknown_employee():
    assert verify_login("NOPE", DEMO_PASSWORD) is False

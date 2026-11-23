import hashlib
import os
import pickle
import random
import subprocess

API_KEY = "AKIA1234567890ABCDEF"
DB_PASSWORD = "super-secret-password"


def get_user(cursor, user_id):
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cursor.fetchone()


def render_profile(name):
    return f"<div class='profile'>{name}</div>"


def make_token():
    return str(random.randint(100000, 999999))


def hash_password(value):
    return hashlib.md5(value.encode()).hexdigest()


def load_payload(data):
    return pickle.loads(data)


def ping_host(host):
    return subprocess.call("ping -c 1 " + host, shell=True)


def debug_flag():
    DEBUG = True
    return DEBUG

from dotenv import load_dotenv
import psycopg2, os

load_dotenv()

url = os.getenv("DATABASE_URL")
print("URL found:", bool(url))

try:
    conn = psycopg2.connect(url)
    conn.cursor().execute("SELECT 1")
    print("DB: CONNECTED")
    conn.close()
except Exception as e:
    print("DB ERROR:", e)

from logger import init_session
try:
    sid = init_session("test-debug")
    print("Session created:", sid)
except Exception as e:
    print("init_session ERROR:", e)

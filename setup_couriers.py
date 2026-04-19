"""
╔══════════════════════════════════════════════════════════════╗
║          DROPLOCK — FIREBASE SETUP SCRIPT                    ║
║  Run this ONCE in your droplock folder.                      ║
║                                                              ║
║  Requirements:  pip install firebase-admin                   ║
║  Run with:      python setup_couriers.py                     ║
╚══════════════════════════════════════════════════════════════╝
"""
import os, time, sys

try:
    import firebase_admin
    from firebase_admin import credentials, auth, db as rtdb
except ImportError:
    print("❌ firebase-admin not installed.\n   Run:  pip install firebase-admin")
    sys.exit(1)

DATABASE_URL = "https://droplock-b2d6a-default-rtdb.europe-west1.firebasedatabase.app/"

# ── Auto-detect credentials file ────────────────────────────
CANDIDATES = [
    "firebase_credentials_json.json",
    "firebase_credentials.json",
    "droplock_credentials.json",
    "credentials.json",
]
CRED_PATH = None
for c in CANDIDATES:
    if os.path.exists(c):
        CRED_PATH = c
        break

if CRED_PATH is None:
    print("❌ No credentials file found in this folder.")
    print("   Looking for:", ", ".join(CANDIDATES))
    print("   Make sure your Firebase service-account JSON is in the same folder.")
    sys.exit(1)

print(f"\n🔑 Using credentials: {CRED_PATH}")

COURIERS = [
    {"email":"courier.tunis@droplock.com",   "password":"Droplock@Tunis1",   "name":"Courier Tunis",   "zone":"Tunis",   "locker":"locker_1"},
    {"email":"courier.ariana@droplock.com",  "password":"Droplock@Ariana2",  "name":"Courier Ariana",  "zone":"Ariana",  "locker":"locker_2"},
    {"email":"courier.lac@droplock.com",     "password":"Droplock@Lac3",     "name":"Courier Lac",     "zone":"Lac",     "locker":"locker_3"},
    {"email":"courier.manouba@droplock.com", "password":"Droplock@Manouba4", "name":"Courier Manouba", "zone":"Manouba", "locker":"locker_4"},
]

print("🔥 Connecting to Firebase...")
try:
    cred = credentials.Certificate(CRED_PATH)
    firebase_admin.initialize_app(cred, {"databaseURL": DATABASE_URL})
    print("   ✅ Connected!\n")
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    sys.exit(1)

ts      = int(time.time() * 1000)
results = []

for c in COURIERS:
    print(f"── {c['locker']} ({c['zone']})  →  {c['email']}")
    try:
        user = auth.create_user(email=c["email"], password=c["password"], display_name=c["name"])
        uid  = user.uid
        print(f"   ✅ Auth account created  (UID: {uid})")
    except firebase_admin.exceptions.AlreadyExistsError:
        user = auth.get_user_by_email(c["email"])
        uid  = user.uid
        print(f"   ℹ️  Already exists (UID: {uid})")
    except Exception as e:
        print(f"   ❌ Auth error: {e}"); continue

    profile = {
        "email": c["email"], "name": c["name"], "displayName": c["name"],
        "role": "courrier", "zone": c["zone"], "status": "active",
        "locker_id": c["locker"], "createdAt": ts,
    }
    try:
        rtdb.reference(f"users/{uid}").set(profile)
        rtdb.reference(f"profiles/{uid}").set(profile)
        print(f"   ✅ Database saved")
    except Exception as e:
        print(f"   ❌ DB error: {e}"); continue

    results.append({**c, "uid": uid})
    print()

locker_map = {r["locker"]: r["email"] for r in results}
try:
    rtdb.reference("config/lockerCourierMap").set(locker_map)
    print("✅ Locker map saved to Firebase /config/lockerCourierMap\n")
except Exception as e:
    print(f"⚠️  Map write failed: {e}\n")

line = "=" * 60
print(f"\n{line}")
print("  DROPLOCK — COURIER ACCOUNTS READY")
print(line)
for r in results:
    print(f"  {r['locker']:<12} {r['zone']:<10} {r['email']:<34} {r['password']}")
print(line)

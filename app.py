import streamlit as st
import json, uuid, time, random, string, base64, smtplib
from datetime import datetime
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import pyrebase

try:
    import qrcode
    QR_OK = True
except:
    QR_OK = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    PDF_OK = True
except:
    PDF_OK = False

# ════════════════════════════════════════════════════════════════════
# FIREBASE CONFIG  (Droplock project)
# ════════════════════════════════════════════════════════════════════
FIREBASE_CONFIG = {
    "apiKey":            "AIzaSyAU5wXJk-NZBgaYAEJ1Uw9bhsAyGQPyAd0",
    "authDomain":        "droplock-b2d6a.firebaseapp.com",
    "databaseURL":       "https://droplock-b2d6a-default-rtdb.europe-west1.firebasedatabase.app/",
    "projectId":         "droplock-b2d6a",
    "storageBucket":     "droplock-b2d6a.firebasestorage.app",
    "messagingSenderId": "1066803026351",
    "appId":             "1:1066803026351:web:69035a441d86e0e03ff75a",
    "measurementId":     "G-G70SLWBK4L",
}
firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
auth_fb  = firebase.auth()
db       = firebase.database()

# ════════════════════════════════════════════════════════════════════
# GMAIL
# ════════════════════════════════════════════════════════════════════
GMAIL_SENDER = "droplock.app@gmail.com"
GMAIL_PASS   = "vtkf lbgq wkwi crnh"

# ════════════════════════════════════════════════════════════════════
# LOCKER → ZONE mapping
# ════════════════════════════════════════════════════════════════════
LOCKER_ZONES = {
    "locker_1": "Tunis",
    "locker_2": "Ariana",
    "locker_3": "Lac",
    "locker_4": "Manouba",
}

# ════════════════════════════════════════════════════════════════════
# ZONE → COURIER EMAIL  (real accounts)
# ════════════════════════════════════════════════════════════════════
ZONE_COURIER_EMAIL = {
    "Lac":     "mehdigaming17@gmail.com",
    "Manouba": "courrier2@gmail.com",
    "Tunis":   "courrier3@gmail.com",
    "Ariana":  "courrier4@gmail.com",
}

# locker_id → courier email (derived)
LOCKER_COURIER_MAP = {lid: ZONE_COURIER_EMAIL[zone] for lid, zone in LOCKER_ZONES.items()}

# Zone → locker_id reverse map
ZONE_LOCKER = {v: k for k, v in LOCKER_ZONES.items()}

# Keyword → Zone (for auto-detecting zone from home address)
ADDRESS_ZONE_KEYWORDS = {
    "lac":     "Lac",
    "berges":  "Lac",
    "manouba": "Manouba",
    "ariana":  "Ariana",
    "raoued":  "Ariana",
    "sokra":   "Ariana",
    "tunis":   "Tunis",
    "centre":  "Tunis",
    "bardo":   "Tunis",
    "medina":  "Tunis",
}

def detect_zone_from_address(address):
    """Return best matching zone from address string, or None."""
    low = address.lower()
    for kw, zone in ADDRESS_ZONE_KEYWORDS.items():
        if kw in low:
            return zone
    return None

# ════════════════════════════════════════════════════════════════════
# PRODUCTS  — images Unsplash + prix TND réalistes
# ════════════════════════════════════════════════════════════════════
PRODUCTS = {
    "Smartphone": {
        "icon": "📱", "desc": "Latest smartphones & accessories",
        "weight": 0.3, "price": 1299.0, "badge": "TECH",
        "img": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&q=80",
    },
    "Laptop": {
        "icon": "💻", "desc": "Laptops, tablets & computers",
        "weight": 2.5, "price": 2850.0, "badge": "TECH",
        "img": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400&q=80",
    },
    "Headphone": {
        "icon": "🎧", "desc": "Premium headphones & earbuds",
        "weight": 0.4, "price": 299.0, "badge": "AUDIO",
        "img": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&q=80",
    },
    "Clavier Meca": {
        "icon": "⌨️", "desc": "Mechanical gaming & office keyboards",
        "weight": 1.1, "price": 459.0, "badge": "GAMING",
        "img": "https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=400&q=80",
    },
    "Shoes": {
        "icon": "👟", "desc": "Sneakers, boots & athletic footwear",
        "weight": 1.2, "price": 185.0, "badge": "MODE",
        "img": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&q=80",
    },
    "Clothing": {
        "icon": "👕", "desc": "Clothes, jackets & fashion accessories",
        "weight": 0.9, "price": 89.0, "badge": "MODE",
        "img": "https://images.unsplash.com/photo-1529374255404-311a2a4f1fd9?w=400&q=80",
    },
}

# ════════════════════════════════════════════════════════════════════
# PAGE CONFIG & CSS
# ════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Droplock", page_icon="🔒", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Instrument+Serif:ital@0;1&display=swap');
:root{--cream:#FAFAF8;--white:#FFF;--ink:#1A1A1A;--ink2:#555;--muted:#999;--border:#EBEBEB;
      --coral:#FF6B35;--rose:#FF3CAC;--mint:#22C87A;--indigo:#3D3EBD;
      --grad:linear-gradient(135deg,#FF6B35 0%,#FF3CAC 100%);--r:14px;}
html,body,[class*="css"]{font-family:'Plus Jakarta Sans',sans-serif;color:var(--ink);background:var(--cream)!important;}
.stApp{background:var(--cream)!important;}
.dl-brand{display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:.4rem;}
.dl-icon{width:48px;height:48px;background:var(--grad);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:22px;}
.dl-name{font-family:'Instrument Serif',serif;font-size:2rem;font-style:italic;letter-spacing:-.03em;color:var(--ink);}
.dl-tagline{text-align:center;color:var(--muted);font-size:.88rem;margin-bottom:2rem;}
.welcome-box{background:var(--grad);border-radius:22px;padding:1.8rem 1.6rem 1.5rem;color:white;margin-bottom:1.5rem;position:relative;overflow:hidden;}
.welcome-box::after{content:'🔒';position:absolute;right:1.2rem;bottom:-.6rem;font-size:6rem;opacity:.12;pointer-events:none;}
.welcome-box h2{font-family:'Instrument Serif',serif;font-size:1.8rem;font-style:italic;font-weight:400;color:white;margin:0 0 .4rem;line-height:1.15;}
.welcome-box p{font-size:.82rem;color:rgba(255,255,255,.72);margin:.1rem 0;}
.role-badge{display:inline-block;padding:.28rem .85rem;border-radius:40px;font-size:.73rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;margin-top:.6rem;background:rgba(255,255,255,.22);border:1px solid rgba(255,255,255,.35);color:white;}
.stButton>button{width:100%;background:var(--grad);color:white;border:none;padding:.75rem 1.2rem;border-radius:12px;font-family:'Plus Jakarta Sans',sans-serif;font-size:.92rem;font-weight:700;cursor:pointer;letter-spacing:.01em;transition:opacity .15s,transform .1s;box-shadow:0 4px 18px rgba(255,107,53,.28);}
.stButton>button:hover{opacity:.9;transform:translateY(-1px);box-shadow:0 6px 24px rgba(255,107,53,.38);}
.stTextInput label,.stSelectbox label{font-size:.78rem!important;font-weight:600!important;color:var(--ink2)!important;}
.stTextInput>div>div>input{background:var(--white)!important;border:1.5px solid var(--border)!important;border-radius:12px!important;font-size:.88rem!important;}
.stTextInput>div>div>input:focus{border-color:var(--coral)!important;box-shadow:0 0 0 3px rgba(255,107,53,.12)!important;}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:var(--white);border-radius:12px;padding:4px;border:1px solid var(--border);}
.stTabs [data-baseweb="tab"]{border-radius:8px;color:var(--muted);font-size:.85rem;font-weight:600;padding:.45rem .9rem;}
.stTabs [aria-selected="true"]{background:var(--grad)!important;color:white!important;}
.separator{text-align:center;color:var(--muted);margin:1.2rem 0;font-size:.8rem;letter-spacing:.08em;}
hr{border-color:var(--border)!important;}
#MainMenu{visibility:hidden;}footer{visibility:hidden;}header{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════════════════════════════════
_defaults = {
    "page": "login", "user_email": "", "user_role": "", "user_token": "",
    "user_id": "", "user_name": "",
    # shop flow
    "flow_step": "products",       # products|delivery|home|locker|confirm
    "flow_product": None,          # {"name","icon","desc","weight","price"}
    "flow_address": "",
    "flow_locker": None,           # {"id","nom","zone","position"}
    "flow_courier": None,
    "auto_zone": None,
    # booking result
    "booking_done": False,
    "booking_id": "", "booking_data": {}, "token_id": "",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ════════════════════════════════════════════════════════════════════
# HELPERS — Firebase
# ════════════════════════════════════════════════════════════════════
def _parse_fb_error(e):
    raw = str(e)
    try:
        body = e.args[1] if len(e.args) > 1 else raw
        return json.loads(body).get("error", {}).get("message", raw)
    except:
        pass
    try:
        start = raw.find("{")
        if start != -1:
            return json.loads(raw[start:]).get("error", {}).get("message", raw)
    except:
        pass
    return raw

def get_user_role(uid, token):
    try:
        r = db.child("users").child(uid).child("role").get(token)
        return r.val()
    except:
        return None

def register_user(uid, email, name, role, token):
    ts = int(time.time() * 1000)
    data = {"email": email, "name": name, "displayName": name,
            "role": role, "status": "active", "createdAt": ts, "zone": ""}
    db.child("users").child(uid).set(data, token)

def get_lockers(token):
    try:
        d = db.child("lockers").get(token)
        if d.val():
            result = {}
            for k, v in d.val().items():
                locker = dict(v)
                locker.setdefault("zone", LOCKER_ZONES.get(k, "Tunis"))
                result[k] = locker
            return result
        return {}
    except:
        return {}

def get_courier_for_locker(locker_id, token):
    email = LOCKER_COURIER_MAP.get(locker_id)
    if not email:
        return None
    try:
        all_users = db.child("users").get(token)
        if all_users.each():
            for u in all_users.each():
                v = u.val()
                if isinstance(v, dict) and v.get("role") == "courrier" and v.get("email") == email:
                    return {"uid": u.key(), **v}
    except:
        pass
    return None

def _gen_token():
    return "QR-S1-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def create_booking(uid, email, name, locker_id, locker_name, zone,
                   product, address, courier, token):
    bid  = str(uuid.uuid4())[:8].upper()
    ts   = int(time.time() * 1000)
    now  = datetime.now().strftime("%d/%m/%Y at %H:%M")
    c_id = courier["uid"]          if courier else ""
    c_em = courier.get("email","") if courier else ""
    c_nm = courier.get("name", c_em) if courier else "N/A"
    bdata = {
        "booking_id": bid, "user_id": uid, "user_email": email, "user_name": name,
        "locker_id": locker_id, "locker_name": locker_name, "locker_zone": zone,
        "produit": product["name"], "poids_kg": product["weight"],
        "prix": product["price"], "home_address": address,
        "timestamp": now, "statut": "en_attente",
        "courrier_id": c_id, "courrier_email": c_em, "courrier_name": c_nm,
        "createdAt": ts, "updatedAt": ts,
    }
    db.child("bookings").child(bid).set(bdata, token)
    db.child("lockers").child(locker_id).update({"statut": "reservé", "booking_id": bid}, token)
    tok = _gen_token()
    db.child("qrTokens").child(tok).set({
        "bookingId": bid, "lockerId": locker_id, "lockerName": locker_name,
        "lockerZone": zone, "issuedToUid": c_id, "userEmail": email,
        "produit": product["name"], "timestamp": now,
        "expiresAt": ts + 86400000, "usedAt": "",
    }, token)
    return bid, bdata, tok

def get_user_bookings(uid, token):
    try:
        d = db.child("bookings").order_by_child("user_id").equal_to(uid).get(token)
        if d.val():
            return [{"id": k, **v} for k, v in d.val().items() if isinstance(v, dict)]
        return []
    except:
        return []

def get_bookings_for_courier(token):
    try:
        d = db.child("bookings").get(token)
        if not d.val():
            return []
        return sorted(
            [{"id": k, **v} for k, v in d.val().items()
             if isinstance(v, dict) and v.get("statut") in ["en_attente","en_cours"]],
            key=lambda x: x.get("timestamp",""), reverse=True
        )
    except:
        return []

def get_delivered_bookings(token):
    try:
        d = db.child("bookings").get(token)
        if not d.val():
            return []
        return [{"id": k, **v} for k, v in d.val().items()
                if isinstance(v, dict) and v.get("statut") == "livré"]
    except:
        return []

def update_booking_status(bid, status, token):
    db.child("bookings").child(bid).update({"statut": status, "updatedAt": int(time.time()*1000)}, token)

def get_courier_tokens(courier_id, token):
    try:
        d = db.child("qrTokens").order_by_child("issuedToUid").equal_to(courier_id).get(token)
        if d.val():
            return {k: v for k, v in d.val().items() if isinstance(v, dict)}
        return {}
    except:
        return {}

def mark_token_used(tid, bid, token):
    ts = int(time.time()*1000)
    db.child("qrTokens").child(tid).update({"usedAt": ts}, token)
    if bid:
        db.child("bookings").child(bid).update({"statut":"livré","updatedAt":ts}, token)

def release_locker(locker_id, token):
    db.child("lockers").child(locker_id).update({"statut":"disponible","booking_id":None}, token)

def get_user_profile(uid, token):
    try:
        d = db.child("users").child(uid).get(token)
        return d.val() or {}
    except:
        return {}

def update_user_profile(uid, data, token):
    try:
        db.child("users").child(uid).update(data, token)
        return True
    except:
        return False

ZONES = ["Tunis","Ariana","Lac","Manouba"]

# ════════════════════════════════════════════════════════════════════
# HELPERS — QR
# ════════════════════════════════════════════════════════════════════
def qr_bytes(token_id):
    if not QR_OK:
        return b""
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(token_id)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a1a2e", back_color="white")
    buf = BytesIO(); img.save(buf, "PNG"); return buf.getvalue()

def qr_b64(data):
    if not QR_OK:
        return None
    qr = qrcode.QRCode(version=1, box_size=6, border=3)
    qr.add_data(json.dumps(data, ensure_ascii=False))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO(); img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()

# ════════════════════════════════════════════════════════════════════
# HELPERS — EMAIL
# ════════════════════════════════════════════════════════════════════
def send_user_email(to, booking_info):
    if not to or "@" not in to:
        return False, "Invalid email"
    try:
        bid   = booking_info.get("booking_id","—")
        prod  = booking_info.get("produit","—")
        lock  = booking_info.get("locker_name","—")
        addr  = booking_info.get("home_address","—")
        date  = booking_info.get("timestamp","—")
        prix  = booking_info.get("prix",0)
        tva   = round(prix*0.19,2)
        total = round(prix+tva,2)

        html = f"""
<html><body style="font-family:Arial,sans-serif;background:#f0f2f6;padding:20px;">
<div style="max-width:520px;margin:auto;background:white;border-radius:16px;padding:2rem;box-shadow:0 4px 20px rgba(0,0,0,.1);">
  <div style="text-align:center;background:linear-gradient(135deg,#FF6B35,#FF3CAC);color:white;padding:1.8rem;border-radius:12px;margin-bottom:1.5rem;">
    <h2 style="margin:0;font-size:1.8rem;">&#128274; Droplock</h2>
    <p style="margin:.5rem 0 0;opacity:.85;">Order Confirmed ✅</p>
  </div>
  <h3 style="color:#1A1A1A;">Your order has been confirmed!</h3>
  <p style="color:#555;line-height:1.6;">
    Thank you for your order. We will notify you as soon as it is delivered to your locker.
  </p>
  <div style="background:#f8f9fa;border-radius:12px;padding:1.2rem;margin:1.2rem 0;">
    <table style="width:100%;font-size:.9rem;">
      <tr><td style="color:#777;padding:6px 0;width:40%;">Order ID</td><td style="font-weight:700;">#{bid}</td></tr>
      <tr><td style="color:#777;padding:6px 0;">Product</td><td style="font-weight:600;">{prod}</td></tr>
      <tr><td style="color:#777;padding:6px 0;">Locker</td><td>&#128274; {lock}</td></tr>
      <tr><td style="color:#777;padding:6px 0;">Delivery address</td><td>&#128205; {addr}</td></tr>
      <tr><td style="color:#777;padding:6px 0;">Date</td><td>&#128197; {date}</td></tr>
      <tr><td style="color:#777;padding:6px 0;">Total</td><td style="font-weight:700;color:#FF6B35;">{total:.2f} TND</td></tr>
    </table>
  </div>
  <div style="background:#FFF4E0;border:1.5px solid #FFE08A;border-radius:10px;padding:1rem;text-align:center;">
    <p style="margin:0;font-weight:700;color:#9A6A00;">&#9203; Pending — We will email you once your package is delivered.</p>
  </div>
  <p style="color:#aaa;font-size:.75rem;text-align:center;margin-top:1.5rem;border-top:1px solid #eee;padding-top:1rem;">
    Automated message — Please do not reply.
  </p>
</div></body></html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Droplock — Order #{bid} confirmed ✅"
        msg["From"]    = GMAIL_SENDER
        msg["To"]      = to
        msg.attach(MIMEText(f"Order #{bid} confirmed. Product: {prod}. Total: {total:.2f} TND.", "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
            s.login(GMAIL_SENDER, GMAIL_PASS)
            s.sendmail(GMAIL_SENDER, [to], msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)

def send_courier_email(to, token_id, qr_png, booking_info):
    if not to or "@" not in to:
        return False, "Invalid email"
    try:
        html = f"""
<html><body style="font-family:Arial,sans-serif;background:#f0f2f6;padding:20px;">
<div style="max-width:520px;margin:auto;background:white;border-radius:16px;padding:2rem;box-shadow:0 4px 20px rgba(0,0,0,.1);">
  <div style="text-align:center;background:#1a1a2e;color:white;padding:1.5rem;border-radius:12px;margin-bottom:1.5rem;">
    <h2 style="margin:0;">&#128274; Droplock</h2>
    <p style="margin:.5rem 0 0;opacity:.8;">New delivery assigned to you</p>
  </div>
  <table style="width:100%;font-size:.9rem;margin-bottom:1rem;">
    <tr style="background:#f8f9fa;"><td style="padding:9px;font-weight:bold;width:40%;">Client</td><td style="padding:9px;">{booking_info.get('user_email','-')}</td></tr>
    <tr><td style="padding:9px;font-weight:bold;">Product</td><td style="padding:9px;">{booking_info.get('produit','-')}</td></tr>
    <tr style="background:#f8f9fa;"><td style="padding:9px;font-weight:bold;">Locker</td><td style="padding:9px;">{booking_info.get('locker_name','-')}</td></tr>
    <tr><td style="padding:9px;font-weight:bold;">Client address</td><td style="padding:9px;">&#128205; {booking_info.get('home_address','-')}</td></tr>
    <tr style="background:#f8f9fa;"><td style="padding:9px;font-weight:bold;">Date</td><td style="padding:9px;">{booking_info.get('timestamp','-')}</td></tr>
  </table>
  <div style="background:#f8f9fa;border:2px dashed #1a1a2e;border-radius:8px;padding:1rem;text-align:center;font-family:monospace;font-size:1.4rem;font-weight:bold;letter-spacing:2px;margin-bottom:1rem;">
    {token_id}
  </div>
  {'<div style="text-align:center;"><img src="cid:qr" width="200" style="border-radius:8px;border:2px solid #eee;"/></div>' if qr_png else ''}
  <p style="color:#aaa;font-size:.75rem;text-align:center;margin-top:1.5rem;border-top:1px solid #eee;padding-top:1rem;">Automated message — Do not reply.</p>
</div></body></html>"""

        root = MIMEMultipart("related")
        root["Subject"] = f"Droplock — Delivery assigned [{token_id}]"
        root["From"]    = GMAIL_SENDER
        root["To"]      = to
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(f"New delivery. Token: {token_id}. Locker: {booking_info.get('locker_name','-')}.", "plain", "utf-8"))
        alt.attach(MIMEText(html, "html", "utf-8"))
        root.attach(alt)
        if qr_png:
            img = MIMEImage(qr_png, _subtype="png")
            img.add_header("Content-ID", "<qr>")
            img.add_header("Content-Disposition", "inline", filename="qr.png")
            root.attach(img)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
            s.login(GMAIL_SENDER, GMAIL_PASS)
            s.sendmail(GMAIL_SENDER, [to], root.as_string())
        return True, None
    except Exception as e:
        return False, str(e)


def send_delivery_notification_email(to, booking_info):
    """Email sent to user when courier marks the delivery as delivered."""
    if not to or "@" not in to:
        return False, "Invalid email"
    try:
        bid   = booking_info.get("booking_id","—")
        prod  = booking_info.get("produit","—")
        lock  = booking_info.get("locker_name","—")
        zone  = booking_info.get("locker_zone","—")
        date  = booking_info.get("timestamp","—")
        prix  = booking_info.get("prix", 0)
        tva   = round(prix * 0.19, 2)
        total = round(prix + tva, 2)
        now   = datetime.now().strftime("%d/%m/%Y at %H:%M")

        html = f"""
<html><body style="font-family:Arial,sans-serif;background:#f0f2f6;padding:20px;">
<div style="max-width:520px;margin:auto;background:white;border-radius:16px;padding:2rem;box-shadow:0 4px 20px rgba(0,0,0,.1);">
  <div style="text-align:center;background:linear-gradient(135deg,#22C87A,#0B6B42);color:white;padding:1.8rem;border-radius:12px;margin-bottom:1.5rem;">
    <div style="font-size:2.5rem;margin-bottom:.4rem;">📦✅</div>
    <h2 style="margin:0;font-size:1.6rem;">Your package has arrived!</h2>
    <p style="margin:.5rem 0 0;opacity:.85;font-size:.9rem;">Order #{bid}</p>
  </div>
  <h3 style="color:#1A1A1A;margin:0 0 .5rem;">Please collect your package</h3>
  <p style="color:#555;line-height:1.6;margin-bottom:1.2rem;">
    Your courier has confirmed that your <strong>{prod}</strong> is now stored in the locker below.
    Please pick it up at your earliest convenience.
  </p>
  <div style="background:#f8f9fa;border-radius:12px;padding:1.2rem;margin:1.2rem 0;">
    <table style="width:100%;font-size:.9rem;">
      <tr><td style="color:#777;padding:6px 0;width:40%;">Order ID</td><td style="font-weight:700;">#{bid}</td></tr>
      <tr><td style="color:#777;padding:6px 0;">Product</td><td style="font-weight:600;">{prod}</td></tr>
      <tr><td style="color:#777;padding:6px 0;">Locker</td><td>&#128274; {lock}</td></tr>
      <tr><td style="color:#777;padding:6px 0;">Zone</td><td>🗺️ {zone}</td></tr>
      <tr><td style="color:#777;padding:6px 0;">Delivered at</td><td>&#128197; {now}</td></tr>
      <tr><td style="color:#777;padding:6px 0;">Total</td><td style="font-weight:700;color:#FF6B35;">{total:.2f} TND</td></tr>
    </table>
  </div>
  <div style="background:#E6FBF2;border:1.5px solid #AEEFD1;border-radius:10px;padding:1rem;text-align:center;margin-bottom:1rem;">
    <p style="margin:0;font-weight:700;color:#0B6B42;font-size:1rem;">&#128274; Head to <strong>{lock}</strong> to collect your package!</p>
  </div>
  <p style="color:#aaa;font-size:.75rem;text-align:center;margin-top:1.5rem;border-top:1px solid #eee;padding-top:1rem;">
    Automated message — Please do not reply · Droplock
  </p>
</div></body></html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📦 Your package is ready for pickup — #{bid}"
        msg["From"]    = GMAIL_SENDER
        msg["To"]      = to
        msg.attach(MIMEText(f"Your {prod} has been delivered to {lock}. Please collect it. Order #{bid}.", "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
            s.login(GMAIL_SENDER, GMAIL_PASS)
            s.sendmail(GMAIL_SENDER, [to], msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)

# ════════════════════════════════════════════════════════════════════
# HELPERS — PDF INVOICE
# ════════════════════════════════════════════════════════════════════
def generate_pdf(bdata, token_id):
    if not PDF_OK:
        return None
    buf = BytesIO()
    DARK  = colors.HexColor("#1a1a2e")
    CORAL = colors.HexColor("#FF6B35")
    GREEN = colors.HexColor("#28a745")
    LGRAY = colors.HexColor("#f8f9fa")
    BORD  = colors.HexColor("#dee2e6")
    GRAY  = colors.HexColor("#6c757d")
    W     = colors.white

    doc = SimpleDocTemplate(buf, pagesize=A4,
          leftMargin=2*cm, rightMargin=2*cm, topMargin=1.5*cm, bottomMargin=2*cm)
    ss  = getSampleStyleSheet()

    def sty(name, **kw):
        return ParagraphStyle(name, parent=ss["Normal"], **kw)

    title_s  = sty("t", fontSize=26, fontName="Helvetica-Bold", textColor=W, alignment=TA_CENTER)
    sub_s    = sty("s", fontSize=10, fontName="Helvetica", textColor=colors.HexColor("#b0c4de"), alignment=TA_CENTER)
    sec_s    = sty("sec", fontSize=12, fontName="Helvetica-Bold", textColor=DARK, spaceBefore=10, spaceAfter=5)
    lbl_s    = sty("l", fontSize=9, fontName="Helvetica-Bold", textColor=GRAY)
    val_s    = sty("v", fontSize=9, fontName="Helvetica", textColor=DARK)
    tok_s    = sty("tk", fontSize=15, fontName="Helvetica-Bold", textColor=DARK, alignment=TA_CENTER)
    foot_s   = sty("f", fontSize=7, fontName="Helvetica", textColor=GRAY, alignment=TA_CENTER)
    right_s  = sty("r", fontSize=9, fontName="Helvetica", textColor=DARK, alignment=TA_RIGHT)
    rtot_s   = sty("rt", fontSize=11, fontName="Helvetica-Bold", textColor=GREEN, alignment=TA_RIGHT)

    story = []
    now_str = datetime.now().strftime("%d/%m/%Y at %H:%M")

    # Header
    h = Table([[Paragraph("🔒 Droplock", title_s)]], colWidths=[17*cm])
    h.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),DARK),
        ("TOPPADDING",(0,0),(-1,-1),16),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story.append(h)
    h2 = Table([[Paragraph("Delivery Invoice", sub_s)]], colWidths=[17*cm])
    h2.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#16213e")),
        ("BOTTOMPADDING",(0,0),(-1,-1),12),("TOPPADDING",(0,0),(-1,-1),4)]))
    story.append(h2); story.append(Spacer(1,.3*cm))

    # Meta
    meta = Table([[Paragraph(f"<b>Invoice #</b> {bdata.get('booking_id','—')}", val_s),
                   Paragraph(f"<b>Date:</b> {now_str}", right_s)]], colWidths=[8.5*cm,8.5*cm])
    meta.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),LGRAY),("BOX",(0,0),(-1,-1),.5,BORD),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10)]))
    story.append(meta); story.append(Spacer(1,.3*cm))

    def detail_table(rows, hdr_color):
        t = Table([[Paragraph(r[0],lbl_s), Paragraph(str(r[1]),val_s)] for r in rows],
                  colWidths=[4.5*cm,12.5*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),hdr_color),("TEXTCOLOR",(0,0),(-1,0),W),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),9),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[W,LGRAY]),
            ("BOX",(0,0),(-1,-1),.5,BORD),("INNERGRID",(0,0),(-1,-1),.3,BORD),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
        ]))
        return t

    # Order details
    story.append(Paragraph("📦 Order Details", sec_s))
    story.append(HRFlowable(width="100%",thickness=1,color=BORD,spaceAfter=5))
    story.append(detail_table([
        ["Field","Value"],
        ["Client",     bdata.get("user_name","—")],
        ["Email",      bdata.get("user_email","—")],
        ["Product",    bdata.get("produit","—")],
        ["Address",    bdata.get("home_address","—")],
        ["Date",       bdata.get("timestamp","—")],
        ["Status",     "⏳ Pending"],
    ], DARK)); story.append(Spacer(1,.3*cm))

    # Locker
    story.append(Paragraph("🔒 Locker", sec_s))
    story.append(HRFlowable(width="100%",thickness=1,color=BORD,spaceAfter=5))
    story.append(detail_table([
        ["Field","Value"],
        ["Locker Name", bdata.get("locker_name","—")],
        ["Zone",        bdata.get("locker_zone","—")],
    ], colors.HexColor("#2196F3"))); story.append(Spacer(1,.3*cm))

    # Courier
    story.append(Paragraph("🚚 Courier", sec_s))
    story.append(HRFlowable(width="100%",thickness=1,color=BORD,spaceAfter=5))
    story.append(detail_table([
        ["Field","Value"],
        ["Courier Name",  bdata.get("courrier_name","—")],
        ["Courier Email", bdata.get("courrier_email","—")],
    ], GRAY)); story.append(Spacer(1,.3*cm))

    # Token
    story.append(Paragraph("🎫 QR Token", sec_s))
    story.append(HRFlowable(width="100%",thickness=1,color=BORD,spaceAfter=5))
    tb = Table([[Paragraph(token_id, tok_s)]], colWidths=[17*cm])
    tb.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),LGRAY),("BOX",(0,0),(-1,-1),2,DARK),
        ("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12)]))
    story.append(tb); story.append(Spacer(1,.3*cm))

    # Pricing
    story.append(Paragraph("💰 Pricing", sec_s))
    story.append(HRFlowable(width="100%",thickness=1,color=BORD,spaceAfter=5))
    prix  = bdata.get("prix",0)
    tva   = round(prix*0.19,2)
    total = round(prix+tva,2)
    pt = Table([
        [Paragraph("Description",lbl_s), Paragraph("Amount",sty("ra",fontSize=9,fontName="Helvetica-Bold",textColor=GRAY,alignment=TA_RIGHT))],
        [Paragraph(f"Delivery fee ({bdata.get('produit','—')})",val_s), Paragraph(f"{prix:.2f} TND",right_s)],
        [Paragraph("VAT (19%)",val_s), Paragraph(f"{tva:.2f} TND",right_s)],
        [Paragraph("<b>TOTAL</b>",sty("tb",fontSize=11,fontName="Helvetica-Bold",textColor=DARK)),
         Paragraph(f"<b>{total:.2f} TND</b>",rtot_s)],
    ], colWidths=[12*cm,5*cm])
    pt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),DARK),("TEXTCOLOR",(0,0),(-1,0),W),
        ("ROWBACKGROUNDS",(0,1),(-1,-2),[W,LGRAY]),
        ("BACKGROUND",(0,-1),(-1,-1),colors.HexColor("#e8f5e9")),
        ("BOX",(0,0),(-1,-1),.5,BORD),("INNERGRID",(0,0),(-1,-1),.3,BORD),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),
    ]))
    story.append(pt); story.append(Spacer(1,.5*cm))

    story.append(HRFlowable(width="100%",thickness=1,color=BORD,spaceAfter=6))
    story.append(Paragraph("This invoice was automatically generated by Droplock. Keep it as proof of your order.", foot_s))
    story.append(Paragraph(f"droplock.app@gmail.com  •  {now_str}", foot_s))

    doc.build(story)
    return buf.getvalue()

# ════════════════════════════════════════════════════════════════════
# LOGOUT
# ════════════════════════════════════════════════════════════════════
def logout():
    for k, v in _defaults.items():
        st.session_state[k] = v

# ════════════════════════════════════════════════════════════════════
# PAGE — LOGIN
# ════════════════════════════════════════════════════════════════════
def page_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="dl-brand"><div class="dl-icon">🔒</div><span class="dl-name">Droplock</span></div>
    <div class="dl-tagline">Secure locker delivery, reimagined</div>
    """, unsafe_allow_html=True)

    st.markdown("""<div style="background:#fff;border:1px solid #EBEBEB;border-radius:22px;
    padding:2rem 1.8rem;max-width:400px;margin:0 auto;box-shadow:0 2px 40px rgba(0,0,0,.06);">""",
    unsafe_allow_html=True)
    st.markdown("<p style='font-size:1.05rem;font-weight:700;color:#1A1A1A;margin:0 0 1.4rem;'>Welcome back — sign in</p>", unsafe_allow_html=True)

    email    = st.text_input("Email address", placeholder="you@example.com", key="li_email")
    password = st.text_input("Password", type="password", key="li_pw")
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Sign In →", key="btn_login"):
        if not email or not password:
            st.error("⚠️ Please fill in all fields.")
        else:
            try:
                user = auth_fb.sign_in_with_email_and_password(email, password)
                role = get_user_role(user["localId"], user["idToken"])
                if role is None:
                    st.error("❌ Account not found. Please sign up.")
                else:
                    st.session_state.update({
                        "user_email": email, "user_id": user["localId"],
                        "user_token": user["idToken"],
                        "user_name": email.split("@")[0], "user_role": role,
                        "page": role if role in ["user","courrier"] else "login"
                    })
                    st.rerun()
            except Exception as e:
                err = _parse_fb_error(e)
                if "INVALID_PASSWORD" in err or "INVALID_LOGIN_CREDENTIALS" in err:
                    st.error("❌ Incorrect password.")
                elif "EMAIL_NOT_FOUND" in err:
                    st.error("❌ Email not found.")
                else:
                    st.error(f"❌ {err}")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="separator">— or —</div>', unsafe_allow_html=True)
    if st.button("Create an Account", key="btn_go_signup"):
        st.session_state.page = "signup"; st.rerun()

# ════════════════════════════════════════════════════════════════════
# PAGE — SIGNUP
# ════════════════════════════════════════════════════════════════════
def page_signup():
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="dl-brand"><div class="dl-icon">✏️</div><span class="dl-name">Droplock</span></div>
    <div class="dl-tagline">Join Droplock — it only takes a moment</div>
    """, unsafe_allow_html=True)

    st.markdown("""<div style="background:#fff;border:1px solid #EBEBEB;border-radius:22px;
    padding:2rem 1.8rem;max-width:400px;margin:0 auto;box-shadow:0 2px 40px rgba(0,0,0,.06);">""",
    unsafe_allow_html=True)

    email    = st.text_input("Email address", placeholder="you@example.com", key="su_email")
    password = st.text_input("Password", type="password", placeholder="At least 6 characters", key="su_pw")
    confirm  = st.text_input("Confirm password", type="password", key="su_confirm")
    role     = st.selectbox("I am a...", ["user","courrier"],
                 format_func=lambda x: "📦 User — I receive packages" if x=="user" else "🚚 Courier — I deliver packages",
                 key="su_role")
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Create My Account →", key="btn_signup"):
        if not email or not password or not confirm:
            st.error("⚠️ Please fill in all fields.")
        elif password != confirm:
            st.error("❌ Passwords do not match.")
        elif len(password) < 6:
            st.error("❌ Password must be at least 6 characters.")
        else:
            try:
                u  = auth_fb.create_user_with_email_and_password(email, password)
                si = auth_fb.sign_in_with_email_and_password(email, password)
                register_user(u["localId"], email, email.split("@")[0], role, si["idToken"])
                st.success("✅ Account created! You can now sign in.")
                st.balloons()
                time.sleep(1)
                st.session_state.page = "login"; st.rerun()
            except Exception as e:
                err = _parse_fb_error(e)
                if "EMAIL_EXISTS" in err:
                    st.error("❌ Email already registered.")
                elif "WEAK_PASSWORD" in err:
                    st.error("❌ Password too weak.")
                else:
                    st.error(f"❌ {err}")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown('<div class="separator">— or —</div>', unsafe_allow_html=True)
    if st.button("← Back to Sign In", key="btn_back"):
        st.session_state.page = "login"; st.rerun()

# ════════════════════════════════════════════════════════════════════
# PAGE — USER  (shop flow)
# ════════════════════════════════════════════════════════════════════
def page_user():
    name = st.session_state.user_name or st.session_state.user_email
    st.markdown(f"""
    <div class="welcome-box">
        <p style="font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;opacity:.7;margin-bottom:.2rem;">Welcome back</p>
        <h2>{name}!</h2>
        <p>{st.session_state.user_email}</p>
        <span class="role-badge">📦 User</span>
    </div>""", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🛍️ Shop", "📋 My Orders"])
    with tab1: _shop_flow()
    with tab2: _my_orders()

    st.markdown("---")
    if st.button("🚪 Sign Out", key="btn_logout_user"):
        logout(); st.rerun()

def _shop_flow():
    if st.session_state.booking_done:
        _confirmation(); return
    step = st.session_state.flow_step
    if   step == "products": _step_products()
    elif step == "delivery": _step_delivery()
    elif step == "home":     _step_home()
    elif step == "locker":   _step_locker()
    elif step == "confirm":  _step_confirm()

# ── STEP 1 — PRODUCTS ───────────────────────────────────────
def _step_products():
    st.markdown("""
    <div style="text-align:center;margin-bottom:1.5rem;">
        <p style="font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#FF6B35;margin:0 0 .3rem;">Droplock Store</p>
        <h2 style="font-family:'Instrument Serif',serif;font-style:italic;font-size:1.9rem;color:#1A1A1A;margin:0;">What would you like delivered?</h2>
        <p style="color:#999;font-size:.85rem;margin:.4rem 0 0;">Pick a product and we deliver it to your nearest locker.</p>
    </div>""", unsafe_allow_html=True)

    items = list(PRODUCTS.items())
    for i in range(0, len(items), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(items): break
            pname, pdata = items[idx]
            with col:
                badge = pdata.get("badge","")
                img   = pdata.get("img","")
                badge_html = f'<span style="background:#3D3EBD;color:white;font-size:.6rem;font-weight:700;letter-spacing:.06em;padding:.2rem .55rem;border-radius:20px;text-transform:uppercase;">{badge}</span>' if badge else ""
                img_html = (f'<img src="{img}" style="width:100%;height:130px;object-fit:cover;border-radius:12px;margin-bottom:.7rem;">'
                            if img else f'<div style="font-size:2.2rem;margin-bottom:.5rem;">{pdata["icon"]}</div>')
                st.markdown(f"""
                <div style="background:#fff;border:1.5px solid #EBEBEB;border-radius:20px;
                            padding:1rem 1rem 1.1rem;margin-bottom:.8rem;
                            box-shadow:0 2px 14px rgba(0,0,0,.05);overflow:hidden;">
                    {img_html}
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.3rem;">
                        <p style="font-size:.95rem;font-weight:700;color:#1A1A1A;margin:0;">{pname}</p>
                        {badge_html}
                    </div>
                    <p style="font-size:.75rem;color:#999;margin:0 0 .6rem;">{pdata['desc']}</p>
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-size:.7rem;color:#AAA;">✓ In stock</span>
                        <span style="font-size:1rem;font-weight:700;color:#FF6B35;">{pdata['price']:.2f} TND</span>
                    </div>
                </div>""", unsafe_allow_html=True)
                if st.button("Buy Now →", key=f"buy_{pname}"):
                    st.session_state.flow_product = {"name": pname, **pdata}
                    st.session_state.flow_step    = "delivery"
                    st.rerun()

# ── STEP 2 — DELIVERY ───────────────────────────────────────
def _step_delivery():
    pname = st.session_state.flow_product["name"] if st.session_state.flow_product else "—"
    st.markdown(f"""
    <div style="text-align:center;margin-bottom:1.8rem;">
        <p style="font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#FF6B35;margin:0 0 .3rem;">Delivery</p>
        <h2 style="font-family:'Instrument Serif',serif;font-style:italic;font-size:1.8rem;color:#1A1A1A;margin:0 0 .3rem;">How would you like to receive it?</h2>
        <p style="color:#999;font-size:.85rem;margin:0;">Selected: <strong style="color:#1A1A1A;">{pname}</strong></p>
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""<div style="background:#fff;border:1.5px solid #EBEBEB;border-radius:20px;
        padding:1.5rem 1.2rem;text-align:center;box-shadow:0 2px 14px rgba(0,0,0,.05);">
        <div style="font-size:2.5rem;margin-bottom:.5rem;">🏠</div>
        <p style="font-size:1rem;font-weight:700;color:#1A1A1A;margin:0 0 .3rem;">Home</p>
        <p style="font-size:.78rem;color:#999;margin:0 0 1rem;">Enter your address — we find your nearest locker.</p>
        </div>""", unsafe_allow_html=True)
        if st.button("🏠 Home", key="btn_home", use_container_width=True):
            st.session_state.flow_step = "home"; st.rerun()

    with col2:
        st.markdown("""<div style="background:#fff;border:1.5px solid #EBEBEB;border-radius:20px;
        padding:1.5rem 1.2rem;text-align:center;box-shadow:0 2px 14px rgba(0,0,0,.05);">
        <div style="font-size:2.5rem;margin-bottom:.5rem;">🔒</div>
        <p style="font-size:1rem;font-weight:700;color:#1A1A1A;margin:0 0 .3rem;">Droplock</p>
        <p style="font-size:.78rem;color:#999;margin:0 0 1rem;">Pick up directly from your nearest smart locker.</p>
        </div>""", unsafe_allow_html=True)
        if st.button("🔒 Droplock", key="btn_droplock", use_container_width=True):
            st.session_state.flow_step = "locker"; st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Back", key="btn_back_delivery"):
        st.session_state.flow_step = "products"; st.rerun()

# ── STEP 3a — HOME ADDRESS ──────────────────────────────────
def _step_home():
    st.markdown("""
    <div style="text-align:center;margin-bottom:1.5rem;">
        <p style="font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#FF6B35;margin:0 0 .3rem;">Your Address</p>
        <h2 style="font-family:'Instrument Serif',serif;font-style:italic;font-size:1.8rem;color:#1A1A1A;margin:0;">Where do you live?</h2>
        <p style="color:#999;font-size:.85rem;margin:.3rem 0 0;">We will find your nearest Droplock locker automatically.</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#fff;border:1px solid #EBEBEB;border-radius:20px;
    padding:1.8rem;box-shadow:0 2px 20px rgba(0,0,0,.05);">""", unsafe_allow_html=True)

    address = st.text_input("📍 Home address",
                placeholder="e.g. 12 Rue de la Liberté, Tunis",
                value=st.session_state.flow_address, key="inp_address")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", key="btn_back_home"):
            st.session_state.flow_step = "delivery"; st.rerun()
    with col2:
        if st.button("🔒 Droplock →", key="btn_find_locker"):
            if not address.strip():
                st.error("⚠️ Please enter your address.")
            else:
                st.session_state.flow_address = address.strip()
                # Auto-detect zone and pre-select locker + courier
                detected_zone = detect_zone_from_address(address.strip())
                if detected_zone:
                    st.session_state["auto_zone"] = detected_zone
                else:
                    st.session_state["auto_zone"] = None
                st.session_state.flow_step = "locker"; st.rerun()

# ── STEP 3b — LOCKER ────────────────────────────────────────
def _step_locker():
    auto_zone = st.session_state.get("auto_zone")

    if auto_zone:
        st.markdown(
            f'<div style="background:#EEF5FF;border:1.5px solid #3D3EBD;border-radius:14px;'
            f'padding:.8rem 1.1rem;margin-bottom:1.2rem;display:flex;align-items:center;gap:.7rem;">'
            f'<span style="font-size:1.2rem;">📍</span>'
            f'<div><p style="font-size:.7rem;font-weight:700;color:#3D3EBD;text-transform:uppercase;margin:0 0 .1rem;">Address detected</p>'
            f'<p style="font-size:.85rem;font-weight:600;color:#1A1A1A;margin:0;">Zone <strong style="color:#FF6B35;">{auto_zone}</strong> — recommended locker highlighted below.</p>'
            f'</div></div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            "<div style='text-align:center;margin-bottom:1.5rem;'>"
            "<p style='font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#FF6B35;margin:0 0 .3rem;'>Choose a Locker</p>"
            "<h2 style=\"font-family:'Instrument Serif',serif;font-style:italic;font-size:1.8rem;color:#1A1A1A;margin:0;\">Your pickup point</h2>"
            "<p style='color:#999;font-size:.85rem;margin:.4rem 0 0;'>A courier is already assigned to each locker.</p>"
            "</div>",
            unsafe_allow_html=True)

    token   = st.session_state.user_token
    lockers = get_lockers(token)

    any_available = any(v.get("statut") == "disponible" for v in lockers.values()) if lockers else False

    if not lockers or not any_available:
        st.markdown('<div style="text-align:center;padding:2.5rem;color:#999;"><div style="font-size:2.5rem;">😔</div><p style="font-weight:600;color:#555;">All lockers are currently occupied. Please try again later.</p></div>', unsafe_allow_html=True)
        if st.button("← Back", key="btn_back_no_locker"):
            st.session_state.flow_step = "delivery"; st.rerun()
        return

    locker_order = ["locker_1","locker_2","locker_3","locker_4"]
    if auto_zone and auto_zone in ZONE_LOCKER:
        preferred = ZONE_LOCKER[auto_zone]
        locker_order = [preferred] + [l for l in locker_order if l != preferred]

    for lid in locker_order:
        ldata        = lockers.get(lid, {})
        zone         = ldata.get("zone", LOCKER_ZONES.get(lid, "—"))
        locker_name  = ldata.get("nom", f"Locker {lid[-1]}")
        position     = ldata.get("position", "—")
        is_avail     = ldata.get("statut","") == "disponible"
        is_preferred = bool(auto_zone and zone == auto_zone)

        courier = get_courier_for_locker(lid, token) if is_avail else None
        c_email = ZONE_COURIER_EMAIL.get(zone, "—")
        c_name  = (courier.get("name", courier.get("email","")) if courier else "") or c_email

        avail_color  = "#C6F7E2" if is_avail else "#FFD9D9"
        avail_text   = "#0B6B42" if is_avail else "#8B2020"
        avail_label  = "● Available" if is_avail else "● Occupied"
        border_color = "#FF6B35" if (is_avail and is_preferred) else ("#22C87A" if is_avail else "#EBEBEB")
        opacity      = "1" if is_avail else ".5"

        # Build rec badge safely (no nested quotes inside f-string)
        rec_html = ""
        if is_preferred and is_avail:
            rec_html = ("<span style=\"background:#FF6B35;color:white;font-size:.62rem;"
                        "font-weight:700;padding:.15rem .55rem;border-radius:20px;"
                        "margin-left:.4rem;\">⭐ Recommended</span>")

        card = (
            f'<div style="background:#fff;border:2px solid {border_color};border-radius:18px;'
            f'padding:1.2rem 1.4rem;margin-bottom:.85rem;opacity:{opacity};box-shadow:0 2px 16px rgba(0,0,0,.05);">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
            f'<div style="flex:1;">'
            f'<div style="display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;margin-bottom:.5rem;">'
            f'<span style="background:{avail_color};color:{avail_text};font-size:.62rem;font-weight:700;'
            f'letter-spacing:.05em;text-transform:uppercase;padding:.2rem .6rem;border-radius:40px;">{avail_label}</span>'
            + rec_html +
            f'</div>'
            f'<h3 style="font-size:1.05rem;font-weight:800;color:#1A1A1A;margin:0 0 .2rem;">&#128274; {locker_name}</h3>'
            f'<p style="font-size:.78rem;color:#777;margin:0;">📍 {position} &nbsp;·&nbsp; 🗺️ <strong style="color:#FF6B35;">{zone}</strong></p>'
            f'</div>'
            f'<div style="text-align:right;padding-left:.8rem;flex-shrink:0;">'
            f'<p style="font-size:.62rem;color:#BBB;text-transform:uppercase;margin:0 0 .12rem;">Courier</p>'
            f'<p style="font-size:.78rem;font-weight:600;color:#555;margin:0;">🚚 {c_name}</p>'
            f'</div></div></div>'
        )
        st.markdown(card, unsafe_allow_html=True)

        if is_avail:
            btn_label = f"✅ Select this locker — {zone}" if is_preferred else f"Select — {locker_name} ({zone}) →"
            if st.button(btn_label, key=f"sel_locker_{lid}"):
                st.session_state.flow_locker  = {"id": lid, "nom": locker_name, "zone": zone, "position": position}
                if not courier:
                    courier = {"uid": "", "email": c_email, "name": c_email}
                st.session_state.flow_courier = courier
                st.session_state["auto_zone"] = None
                st.session_state.flow_step    = "confirm"
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Back", key="btn_back_locker"):
        st.session_state["auto_zone"] = None
        st.session_state.flow_step = "delivery"; st.rerun()

# ── STEP 4 — CONFIRM ────────────────────────────────────────
def _step_confirm():
    prod    = st.session_state.flow_product  or {}
    locker  = st.session_state.flow_locker   or {}
    courier = st.session_state.flow_courier
    address = st.session_state.flow_address  or "—"

    prix  = prod.get("price",0)
    tva   = round(prix*0.19,2)
    total = round(prix+tva,2)
    c_name  = courier.get("name",  courier.get("email","—")) if courier else "—"

    st.markdown("""
    <div style="text-align:center;margin-bottom:1.5rem;">
        <p style="font-size:.72rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#FF6B35;margin:0 0 .3rem;">Final Step</p>
        <h2 style="font-family:'Instrument Serif',serif;font-style:italic;font-size:1.8rem;color:#1A1A1A;margin:0;">Confirm Your Order</h2>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#fff;border:1px solid #EBEBEB;border-radius:20px;padding:1.5rem;
                box-shadow:0 2px 16px rgba(0,0,0,.05);margin-bottom:1.2rem;">
        <p style="font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#999;margin:0 0 1rem;">Order Summary</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin-bottom:1rem;">
            <div><p style="font-size:.7rem;color:#aaa;text-transform:uppercase;letter-spacing:.06em;margin:0 0 .2rem;">Product</p>
                 <p style="font-size:.95rem;font-weight:700;color:#1A1A1A;margin:0;">📦 {prod.get('name','—')}</p></div>
            <div><p style="font-size:.7rem;color:#aaa;text-transform:uppercase;letter-spacing:.06em;margin:0 0 .2rem;">Locker</p>
                 <p style="font-size:.95rem;font-weight:700;color:#1A1A1A;margin:0;">&#128274; {locker.get('nom','—')}</p></div>
            <div><p style="font-size:.7rem;color:#aaa;text-transform:uppercase;letter-spacing:.06em;margin:0 0 .2rem;">Zone</p>
                 <p style="font-size:.95rem;font-weight:700;color:#FF6B35;margin:0;">🗺️ {locker.get('zone','—')}</p></div>
            <div><p style="font-size:.7rem;color:#aaa;text-transform:uppercase;letter-spacing:.06em;margin:0 0 .2rem;">Courier</p>
                 <p style="font-size:.95rem;font-weight:700;color:#1A1A1A;margin:0;">🚚 {c_name}</p></div>
        </div>
        <div style="background:#f8f9fa;border-radius:10px;padding:.9rem;margin-bottom:.8rem;">
            <p style="font-size:.7rem;color:#aaa;text-transform:uppercase;letter-spacing:.06em;margin:0 0 .2rem;">Delivery Address</p>
            <p style="font-size:.9rem;font-weight:600;color:#1A1A1A;margin:0;">📍 {address}</p>
        </div>
        <hr style="border:none;border-top:1px solid #EBEBEB;margin:.8rem 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <p style="font-size:.78rem;color:#999;margin:0;">Delivery fee</p>
                <p style="font-size:.78rem;color:#999;margin:0;">VAT (19%)</p>
                <p style="font-size:.95rem;font-weight:700;color:#1A1A1A;margin:.4rem 0 0;">Total</p>
            </div>
            <div style="text-align:right;">
                <p style="font-size:.78rem;color:#555;margin:0;">{prix:.2f} TND</p>
                <p style="font-size:.78rem;color:#555;margin:0;">{tva:.2f} TND</p>
                <p style="font-size:1.1rem;font-weight:800;color:#FF6B35;margin:.4rem 0 0;">{total:.2f} TND</p>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", key="btn_back_confirm"):
            st.session_state.flow_step = "locker"; st.rerun()
    with col2:
        if st.button("✅ Confirm Order", key="btn_place_order"):
            _place_order(prod, locker, courier, address)

def _place_order(prod, locker, courier, address):
    with st.spinner("⏳ Placing your order..."):
        bid, bdata, tok = create_booking(
            uid=st.session_state.user_id, email=st.session_state.user_email,
            name=st.session_state.user_name, locker_id=locker["id"],
            locker_name=locker["nom"], zone=locker["zone"],
            product=prod, address=address, courier=courier,
            token=st.session_state.user_token,
        )
        binfo = {**bdata, "home_address": address}

        # Email to USER
        ok_u, err_u = send_user_email(st.session_state.user_email, binfo)

        # Email to COURIER
        qrpng = qr_bytes(tok)
        c_em  = courier.get("email","") if courier else ""
        if c_em:
            send_courier_email(c_em, tok, qrpng, binfo)

        if ok_u:
            st.success(f"📧 Confirmation email sent to **{st.session_state.user_email}**")
        else:
            st.warning(f"⚠️ Email not sent: {err_u}")

        st.session_state.booking_done = True
        st.session_state.booking_id   = bid
        st.session_state.booking_data = bdata
        st.session_state.token_id     = tok
        # reset flow
        st.session_state.flow_step    = "products"
        st.session_state.flow_product = None
        st.session_state.flow_address = ""
        st.session_state.flow_locker  = None
        st.session_state.flow_courier = None
        st.rerun()

def _confirmation():
    bid   = st.session_state.booking_id
    tok   = st.session_state.token_id
    bdata = st.session_state.booking_data

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#FF6B35,#FF3CAC);border-radius:18px;
                padding:1.4rem 1.5rem;color:white;margin-bottom:1rem;">
        <p style="font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;opacity:.75;margin:0 0 .2rem;">Order confirmed</p>
        <p style="font-family:'Instrument Serif',serif;font-size:1.5rem;font-style:italic;margin:0;">#{bid} ✓</p>
        <p style="font-size:.82rem;opacity:.8;margin:.4rem 0 0;">
            A confirmation email has been sent to your inbox. We will notify you once your package is delivered.
        </p>
    </div>""", unsafe_allow_html=True)

    prix  = bdata.get('prix',0)
    tva   = round(prix*0.19,2)
    total = round(prix+tva,2)
    st.markdown(f"""
    <div style="background:#fff;border:1px solid #EBEBEB;border-radius:20px;
                padding:1.4rem 1.5rem;margin-bottom:1rem;box-shadow:0 2px 16px rgba(0,0,0,.05);">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.9rem .5rem;">
            <div>
                <p style="font-size:.65rem;color:#BBB;text-transform:uppercase;letter-spacing:.07em;margin:0 0 .15rem;">Product</p>
                <p style="font-size:.92rem;font-weight:700;color:#1A1A1A;margin:0;">🛍️ {bdata.get('produit','—')}</p>
            </div>
            <div>
                <p style="font-size:.65rem;color:#BBB;text-transform:uppercase;letter-spacing:.07em;margin:0 0 .15rem;">Locker</p>
                <p style="font-size:.92rem;font-weight:700;color:#1A1A1A;margin:0;">🔒 {bdata.get('locker_name','—')}</p>
            </div>
            <div>
                <p style="font-size:.65rem;color:#BBB;text-transform:uppercase;letter-spacing:.07em;margin:0 0 .15rem;">Zone</p>
                <p style="font-size:.92rem;font-weight:700;color:#FF6B35;margin:0;">🗺️ {bdata.get('locker_zone','—')}</p>
            </div>
            <div>
                <p style="font-size:.65rem;color:#BBB;text-transform:uppercase;letter-spacing:.07em;margin:0 0 .15rem;">Courier</p>
                <p style="font-size:.92rem;font-weight:700;color:#1A1A1A;margin:0;">🚚 {bdata.get('courrier_name','—')}</p>
            </div>
            <div>
                <p style="font-size:.65rem;color:#BBB;text-transform:uppercase;letter-spacing:.07em;margin:0 0 .15rem;">Address</p>
                <p style="font-size:.88rem;font-weight:600;color:#555;margin:0;">📍 {bdata.get('home_address','—')}</p>
            </div>
            <div>
                <p style="font-size:.65rem;color:#BBB;text-transform:uppercase;letter-spacing:.07em;margin:0 0 .15rem;">Date</p>
                <p style="font-size:.88rem;font-weight:600;color:#555;margin:0;">📅 {bdata.get('timestamp','—')}</p>
            </div>
        </div>
        <hr style="border:none;border-top:1px solid #EBEBEB;margin:.9rem 0 .8rem;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem;">
            <div style="display:flex;align-items:center;gap:.6rem;">
                <code style="background:#F5F5F5;border:1px solid #E0E0E0;border-radius:8px;
                             padding:.3rem .7rem;font-size:.82rem;color:#3D3EBD;font-weight:700;">🎫 {tok}</code>
                <span style="background:#FFF4E0;color:#9A6A00;border:1.5px solid #FFE08A;
                             padding:.25rem .75rem;border-radius:40px;font-size:.7rem;font-weight:700;">🟡 Pending</span>
            </div>
            <p style="font-size:1.15rem;font-weight:800;color:#FF6B35;margin:0;">💰 {total:.2f} TND</p>
        </div>
    </div>""", unsafe_allow_html=True)

    if QR_OK:
        qrpng = qr_bytes(tok)
        st.markdown("### 📱 QR Code")
        st.image(qrpng, width=200, caption=tok)

    st.markdown("### 🧾 Invoice")
    pdf = generate_pdf(bdata, tok)
    if pdf:
        b64  = base64.b64encode(pdf).decode()
        fname = f"droplock_invoice_{bid}.pdf"
        st.markdown(f"""
        <a href="data:application/pdf;base64,{b64}" download="{fname}"
           style="display:inline-block;background:linear-gradient(135deg,#FF6B35,#FF3CAC);
                  color:white;padding:.65rem 1.4rem;border-radius:12px;text-decoration:none;
                  font-weight:700;font-size:.9rem;box-shadow:0 4px 16px rgba(255,107,53,.3);">
           📄 Download Invoice (PDF)
        </a><br><br>
        <iframe src="data:application/pdf;base64,{b64}" width="100%" height="580px"
                style="border:1px solid #EBEBEB;border-radius:16px;"></iframe>
        """, unsafe_allow_html=True)
    else:
        st.info("PDF generation unavailable — install reportlab.")

    if st.button("🛍️ Place Another Order", key="btn_new_order"):
        st.session_state.booking_done = False
        st.session_state.booking_id   = ""
        st.session_state.booking_data = {}
        st.session_state.token_id     = ""
        st.rerun()

def _my_orders():
    st.subheader("📋 My Orders")
    if st.button("🔄 Refresh", key="ref_orders"): st.rerun()
    bookings = get_user_bookings(st.session_state.user_id, st.session_state.user_token)
    if not bookings:
        st.markdown("""<div style="text-align:center;padding:3rem;color:#999;">
        <div style="font-size:2.5rem;margin-bottom:.8rem;">📭</div>
        <p style="font-weight:600;color:#555;">No orders yet</p>
        <p style="font-size:.85rem;">Go to the Shop tab to place your first order.</p></div>""", unsafe_allow_html=True)
        return
    STATUS = {
        "en_attente": ("Pending",     "#FFF4E0","#9A6A00","#FFE08A"),
        "en_cours":   ("In Progress", "#EEF0FF","#3D3EBD","#C5C5F5"),
        "livré":      ("Delivered",   "#E6FBF2","#0B6B42","#AEEFD1"),
        "annulé":     ("Cancelled",   "#FFF5F5","#8B2020","#FFC5C5"),
    }
    for b in sorted(bookings, key=lambda x: x.get("timestamp",""), reverse=True):
        s = b.get("statut","")
        label,bg,fg,br = STATUS.get(s,(s,"#F5F5F5","#555","#DDD"))
        st.markdown(f"""
        <div style="background:#fff;border:1px solid #EBEBEB;border-radius:16px;
                    padding:1rem 1.2rem;margin:.65rem 0;display:flex;justify-content:space-between;align-items:center;">
            <div>
                <p style="font-size:.7rem;font-weight:700;color:#CCC;text-transform:uppercase;margin:0 0 .2rem;">Order #{b.get('booking_id','—')}</p>
                <p style="font-size:.95rem;font-weight:700;color:#1A1A1A;margin:0 0 .2rem;">{b.get('produit','—')}</p>
                <p style="font-size:.76rem;color:#AAA;margin:0;">🔒 {b.get('locker_name','—')} · 🗺️ {b.get('locker_zone','—')} · 📅 {b.get('timestamp','—')}<br>💰 {b.get('prix',0):.2f} TND</p>
            </div>
            <div style="background:{bg};color:{fg};border:1.5px solid {br};padding:.3rem .85rem;
                        border-radius:40px;font-size:.72rem;font-weight:700;text-transform:uppercase;white-space:nowrap;">
                {label}
            </div>
        </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# PAGE — COURIER
# ════════════════════════════════════════════════════════════════════
def page_courrier():
    name = st.session_state.user_name or st.session_state.user_email
    st.markdown(f"""
    <div class="welcome-box">
        <p style="font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;opacity:.7;margin-bottom:.2rem;">Courier dashboard</p>
        <h2>{name}!</h2>
        <p>{st.session_state.user_email}</p>
        <span class="role-badge">📬 Courier Agent</span>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🎫 My QR Codes","📦 Deliveries","✅ History","⚙️ Settings"])
    with tab1: _courier_qr()
    with tab2: _courier_deliveries()
    with tab3: _courier_history()
    with tab4: _courier_settings()

    st.markdown("---")
    if st.button("🚪 Sign Out", key="btn_logout_courier"):
        logout(); st.rerun()

def _courier_qr():
    st.subheader("🎫 My QR Codes")
    if st.button("🔄 Refresh", key="ref_qr"): st.rerun()
    tokens = get_courier_tokens(st.session_state.user_id, st.session_state.user_token)
    if not tokens:
        st.markdown("""<div style="text-align:center;padding:3rem;color:#999;">
        <div style="font-size:2.5rem;">📭</div><p style="font-weight:600;color:#555;">No QR codes yet</p>
        <p style="font-size:.85rem;">They appear once a user places an order.</p></div>""", unsafe_allow_html=True)
        return
    total = len(tokens); used = sum(1 for t in tokens.values() if t.get("usedAt",""))
    c1,c2,c3 = st.columns(3)
    c1.metric("📦 Total", total); c2.metric("✅ Used", used); c3.metric("⏳ Pending", total-used)
    st.markdown("---")
    for tid, td in tokens.items():
        is_used = bool(td.get("usedAt",""))
        badge_bg = "#FFD9D9" if is_used else "#C6F7E2"
        badge_fg = "#8B2020" if is_used else "#0B6B42"
        badge    = "Used" if is_used else "Active"
        st.markdown(f"""
        <div style="background:#1A1A1A;border-radius:20px;padding:1.4rem 1.5rem;margin:.8rem 0;position:relative;overflow:hidden;">
            <div style="position:absolute;top:1rem;right:1.2rem;background:{badge_bg};color:{badge_fg};
                        padding:.25rem .7rem;border-radius:40px;font-size:.7rem;font-weight:700;text-transform:uppercase;">{badge}</div>
            <p style="font-size:.68rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:rgba(255,255,255,.45);margin:0 0 .4rem;">Delivery Token</p>
            <p style="font-family:'Instrument Serif',serif;font-size:1.5rem;font-style:italic;color:white;margin:0 0 1rem;">{tid}</p>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem;">
                <div><p style="font-size:.65rem;color:rgba(255,255,255,.4);text-transform:uppercase;margin:0 0 .1rem;">Locker</p>
                     <p style="font-size:.82rem;font-weight:600;color:rgba(255,255,255,.9);margin:0;">{td.get('lockerName',td.get('lockerId','—'))}</p></div>
                <div><p style="font-size:.65rem;color:rgba(255,255,255,.4);text-transform:uppercase;margin:0 0 .1rem;">Product</p>
                     <p style="font-size:.82rem;font-weight:600;color:rgba(255,255,255,.9);margin:0;">{td.get('produit','—')}</p></div>
                <div><p style="font-size:.65rem;color:rgba(255,255,255,.4);text-transform:uppercase;margin:0 0 .1rem;">Client</p>
                     <p style="font-size:.78rem;font-weight:600;color:rgba(255,255,255,.9);margin:0;overflow:hidden;text-overflow:ellipsis;">{td.get('userEmail','—')}</p></div>
            </div>
        </div>""", unsafe_allow_html=True)
        if QR_OK:
            st.image(qr_bytes(tid), width=180, caption=f"Scan · {tid}")
        if not is_used:
            if st.button("✅ Mark as Used", key=f"use_{tid}"):
                mark_token_used(tid, td.get("bookingId",""), st.session_state.user_token)
                if td.get("lockerId"):
                    release_locker(td["lockerId"], st.session_state.user_token)
                st.success(f"✅ Token {tid} marked as used!")
                st.rerun()
        st.markdown("---")

def _courier_deliveries():
    st.subheader("📦 Pending Deliveries")
    if st.button("🔄 Refresh", key="ref_del"): st.rerun()
    bookings = get_bookings_for_courier(st.session_state.user_token)
    if not bookings:
        st.markdown("""<div style="text-align:center;padding:3rem;color:#999;">
        <div style="font-size:2.5rem;">✅</div><p style="font-weight:600;color:#555;">All caught up!</p>
        <p style="font-size:.85rem;">No pending deliveries.</p></div>""", unsafe_allow_html=True)
        return
    st.markdown(f"<p style='font-size:.82rem;color:#999;'><b style='color:#FF6B35;'>{len(bookings)}</b> delivery(ies) to process</p>", unsafe_allow_html=True)
    tok = st.session_state.user_token
    for b in bookings:
        with st.expander(f"📦 #{b.get('booking_id','—')} — {b.get('produit','—')} · {b.get('user_name','—')}"):
            col_i, col_q = st.columns([2,1])
            with col_i:
                for lbl, val in [("👤 Client",b.get('user_name','—')),("📧 Email",b.get('user_email','—')),
                                  ("🛍️ Product",b.get('produit','—')),
                                  ("🔒 Locker",b.get('locker_name','—')),("🗺️ Zone",b.get('locker_zone','—')),
                                  ("📍 Address",b.get('home_address','—')),("📅 Date",b.get('timestamp','—'))]:
                    st.markdown(f"**{lbl}:** {val}")
            with col_q:
                if QR_OK:
                    qdata = {k: b.get(k) for k in ["booking_id","user_name","locker_name","produit","statut"]}
                    try: st.markdown(f'<img src="data:image/png;base64,{qr_b64(qdata)}" width="140"/>', unsafe_allow_html=True)
                    except: st.warning("QR unavailable")
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🚚 In Progress", key=f"ip_{b['id']}"):
                    update_booking_status(b["id"],"en_cours",tok); st.success("✅ Updated!"); st.rerun()
            with c2:
                if st.button("✅ Delivered", key=f"del_{b['id']}"):
                    update_booking_status(b["id"],"livré",tok)
                    release_locker(b["locker_id"],tok)
                    # Notify the user by email
                    user_email = b.get("user_email","")
                    if user_email:
                        send_delivery_notification_email(user_email, b)
                    st.success("✅ Delivery confirmed — locker released & user notified."); st.rerun()

def _courier_history():
    st.subheader("✅ Delivery History")
    done = get_delivered_bookings(st.session_state.user_token)
    if not done:
        st.markdown("""<div style="text-align:center;padding:3rem;color:#999;">
        <div style="font-size:2.5rem;">📋</div><p style="font-weight:600;color:#555;">No history yet</p></div>""", unsafe_allow_html=True)
        return
    st.markdown(f"<p style='font-size:.82rem;color:#999;margin-bottom:.8rem;'>{len(done)} delivery(ies) completed</p>", unsafe_allow_html=True)
    for b in sorted(done, key=lambda x: x.get("timestamp",""), reverse=True):
        st.markdown(f"""
        <div style="background:#fff;border:1px solid #EBEBEB;border-radius:16px;padding:1rem 1.2rem;margin:.65rem 0;border-left:3px solid #22C87A;">
            <p style="font-size:.95rem;font-weight:700;color:#1A1A1A;margin:0 0 .2rem;">#{b.get('booking_id','—')} — {b.get('produit','—')}</p>
            <p style="font-size:.76rem;color:#AAA;margin:0;">👤 {b.get('user_name','—')} · 🔒 {b.get('locker_name','—')} · 🗺️ {b.get('locker_zone','—')}</p>
            <p style="font-size:.76rem;margin:.3rem 0 0;">📅 {b.get('timestamp','—')} &nbsp;
                <span style="background:#E6FBF2;color:#0B6B42;border:1.5px solid #AEEFD1;padding:.15rem .6rem;border-radius:40px;font-size:.7rem;font-weight:700;">Delivered</span>
            </p>
        </div>""", unsafe_allow_html=True)

def _courier_settings():
    st.subheader("⚙️ Profile & Settings")
    uid   = st.session_state.user_id
    token = st.session_state.user_token
    prof  = get_user_profile(uid, token)
    cur_name = prof.get("name", st.session_state.user_name or "")
    cur_zone = prof.get("zone","")

    with st.form("courier_profile"):
        new_name = st.text_input("Full name", value=cur_name, key="cs_name")
        st.text_input("Email (read-only)", value=prof.get("email",""), disabled=True)
        zone_opts = [""] + ZONES
        zone_lbls = ["— Select your zone —"] + ZONES
        new_zone  = st.selectbox("My delivery zone", options=zone_opts,
                     format_func=lambda x: zone_lbls[zone_opts.index(x)],
                     index=zone_opts.index(cur_zone) if cur_zone in zone_opts else 0)
        if st.form_submit_button("💾 Save", use_container_width=True):
            if not new_name.strip():
                st.error("⚠️ Name cannot be empty.")
            elif not new_zone:
                st.error("⚠️ Please select a zone.")
            else:
                ok = update_user_profile(uid,{"name":new_name.strip(),"displayName":new_name.strip(),"zone":new_zone},token)
                if ok:
                    st.session_state.user_name = new_name.strip()
                    st.success(f"✅ Saved — zone: {new_zone}")
                    st.rerun()
                else:
                    st.error("❌ Save failed.")
    if cur_zone:
        st.markdown(f"""<div style="background:#FFF4F0;border-left:3px solid #FF6B35;border-radius:0 12px 12px 0;padding:1rem;margin-top:1rem;">
        <p style="font-size:.85rem;font-weight:700;color:#FF6B35;margin:0 0 .2rem;">📍 Current zone: {cur_zone}</p>
        <p style="font-size:.78rem;color:#999;margin:0;">You receive assignments for the <b>{cur_zone}</b> area.</p></div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# ROUTER
# ════════════════════════════════════════════════════════════════════
page = st.session_state.page

if page == "login":
    page_login()
elif page == "signup":
    page_signup()
elif page == "user":
    if not st.session_state.user_token:
        st.session_state.page = "login"; st.rerun()
    else:
        page_user()
elif page == "courrier":
    if not st.session_state.user_token:
        st.session_state.page = "login"; st.rerun()
    else:
        page_courrier()
"""
╔══════════════════════════════════════════════════════════════════════╗
║                  DROPLOCK — API SERVER                               ║
║                                                                      ║
║  Framework : FastAPI (serveur HTTP moderne Python)                   ║
║  Base URL  : http://localhost:8000                                   ║
║  Docs auto : http://localhost:8000/docs                              ║
║                                                                      ║
║  Lancement : uvicorn api:app --reload --port 8000                    ║
║  Installer  : pip install fastapi uvicorn firebase-admin             ║
╚══════════════════════════════════════════════════════════════════════╝

COMPRENDRE L'API EN 30 SECONDES
================================
Une API, c'est un serveur qui répond à des requêtes HTTP.
Chaque "route" est une URL qu'on peut appeler depuis n'importe où :
  - une app mobile
  - ton app Streamlit
  - un autre site web
  - Postman / un outil de test

Exemples de requêtes :
  GET  /lockers          → "donne-moi la liste des lockers"
  POST /bookings         → "crée une nouvelle commande"
  PUT  /bookings/ABC123/status  → "change le statut de cette commande"

L'authentification : on envoie le token Firebase dans le header.
  Authorization: Bearer <firebase_token>
"""

import os, json, time, uuid, random, string, smtplib, base64
from datetime import datetime
from io import BytesIO
from typing import Optional

# ── FastAPI ──────────────────────────────────────────────────────────
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# ── Firebase Admin SDK ───────────────────────────────────────────────
import firebase_admin
from firebase_admin import credentials, auth as fb_auth, db as rtdb

# ── Email ─────────────────────────────────────────────────────────────
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ════════════════════════════════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════════════════════════════════
DATABASE_URL  = "https://droplock-b2d6a-default-rtdb.europe-west1.firebasedatabase.app/"
CRED_FILE     = "firebase_credentials_json.json.json"   # même dossier que api.py
GMAIL_SENDER  = "droplock.app@gmail.com"
GMAIL_PASS    = "vtkf lbgq wkwi crnh"

LOCKER_ZONES  = {
    "locker_1": "Tunis",
    "locker_2": "Ariana",
    "locker_3": "Lac",
    "locker_4": "Manouba",
}

ZONE_COURIER_EMAIL = {
    "Lac":     "mehdigaming17@gmail.com",
    "Manouba": "courrier2@gmail.com",
    "Tunis":   "courrier3@gmail.com",
    "Ariana":  "courrier4@gmail.com",
}

LOCKER_COURIER_MAP = {lid: ZONE_COURIER_EMAIL[zone] for lid, zone in LOCKER_ZONES.items()}
ZONE_LOCKER        = {v: k for k, v in LOCKER_ZONES.items()}

ADDRESS_ZONE_KEYWORDS = {
    "lac": "Lac", "berges": "Lac", "manouba": "Manouba",
    "ariana": "Ariana", "raoued": "Ariana", "sokra": "Ariana",
    "tunis": "Tunis", "centre": "Tunis", "bardo": "Tunis", "medina": "Tunis",
}

PRODUCTS = {
    "Smartphone":   {"weight": 0.3,  "price": 1299.0, "badge": "TECH"},
    "Laptop":       {"weight": 2.5,  "price": 2850.0, "badge": "TECH"},
    "Headphone":    {"weight": 0.4,  "price": 299.0,  "badge": "AUDIO"},
    "Clavier Meca": {"weight": 1.1,  "price": 459.0,  "badge": "GAMING"},
    "Shoes":        {"weight": 1.2,  "price": 185.0,  "badge": "MODE"},
    "Clothing":     {"weight": 0.9,  "price": 89.0,   "badge": "MODE"},
}

# ════════════════════════════════════════════════════════════════════
# INITIALISATION FIREBASE
# ════════════════════════════════════════════════════════════════════
if not firebase_admin._apps:
    if not os.path.exists(CRED_FILE):
        raise FileNotFoundError(
            f"❌ Fichier credentials introuvable : {CRED_FILE}\n"
            "   Place firebase_credentials_json.json dans le même dossier que api.py"
        )
    cred = credentials.Certificate(CRED_FILE)
    firebase_admin.initialize_app(cred, {"databaseURL": DATABASE_URL})

db_ref = rtdb.reference   # raccourci pratique

# ════════════════════════════════════════════════════════════════════
# CRÉATION DE L'APP FASTAPI
# ════════════════════════════════════════════════════════════════════
app = FastAPI(
    title        = "Droplock API",
    description  = "API REST pour la plateforme de livraison Droplock 🔒",
    version      = "1.0.0",
    docs_url     = "/docs",     # interface Swagger auto → ouvre dans ton browser
    redoc_url    = "/redoc",    # interface ReDoc alternative
)

# CORS : autorise l'app Streamlit (et tout autre frontend) à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],   # En prod, remplace par ["https://ton-domaine.com"]
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# ════════════════════════════════════════════════════════════════════
# AUTHENTIFICATION  — vérification du token Firebase
# ════════════════════════════════════════════════════════════════════
def verify_token(authorization: str = Header(...)) -> dict:
    """
    Middleware d'auth : toutes les routes protégées reçoivent ce paramètre.
    Le client doit envoyer :  Authorization: Bearer <firebase_id_token>
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant. Format: Bearer <token>")
    token = authorization.split(" ", 1)[1]
    try:
        decoded = fb_auth.verify_id_token(token)
        return decoded   # contient uid, email, etc.
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token invalide : {str(e)}")

# ════════════════════════════════════════════════════════════════════
# MODÈLES PYDANTIC  — structure des données reçues dans les requêtes
# (Pydantic valide automatiquement que les champs sont présents et du bon type)
# ════════════════════════════════════════════════════════════════════
class BookingCreate(BaseModel):
    locker_id    : str
    product_name : str
    home_address : str

class BookingStatusUpdate(BaseModel):
    status: str   # "en_attente" | "en_cours" | "livré" | "annulé"

class ProfileUpdate(BaseModel):
    name : Optional[str] = None
    zone : Optional[str] = None

class TokenUse(BaseModel):
    token_id   : str
    booking_id : str

# ════════════════════════════════════════════════════════════════════
# HELPERS INTERNES
# ════════════════════════════════════════════════════════════════════
def _gen_qr_token() -> str:
    return "QR-S1-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def detect_zone(address: str) -> Optional[str]:
    low = address.lower()
    for kw, zone in ADDRESS_ZONE_KEYWORDS.items():
        if kw in low:
            return zone
    return None

def send_email_html(to: str, subject: str, html: str, plain: str) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_SENDER
        msg["To"]      = to
        msg.attach(MIMEText(plain, "plain", "utf-8"))
        msg.attach(MIMEText(html,  "html",  "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as s:
            s.login(GMAIL_SENDER, GMAIL_PASS)
            s.sendmail(GMAIL_SENDER, [to], msg.as_string())
        return True
    except:
        return False

# ════════════════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────────────────────────────
# ════════════════════════════════════════════════════════════════════

# ── 1. SANTÉ DE L'API ────────────────────────────────────────────────
@app.get("/", tags=["Système"])
def root():
    """Vérification rapide que le serveur tourne."""
    return {"status": "ok", "message": "Droplock API is running 🔒", "version": "1.0.0"}

@app.get("/health", tags=["Système"])
def health():
    return {"status": "healthy", "timestamp": int(time.time())}


# ── 2. CATALOGUE PRODUITS ────────────────────────────────────────────
@app.get("/products", tags=["Produits"])
def get_products():
    """
    Retourne la liste de tous les produits disponibles.
    Pas d'authentification requise (route publique).
    """
    return {
        "products": [
            {"name": name, **info}
            for name, info in PRODUCTS.items()
        ]
    }


# ── 3. LOCKERS ───────────────────────────────────────────────────────
@app.get("/lockers", tags=["Lockers"])
def get_lockers(user: dict = Depends(verify_token)):
    """
    Retourne tous les lockers avec leur statut (disponible / réservé).
    Requiert un token Firebase valide.
    """
    try:
        data = db_ref("lockers").get()
        if not data:
            return {"lockers": []}
        lockers = []
        for locker_id, info in data.items():
            if isinstance(info, dict):
                info["id"]   = locker_id
                info.setdefault("zone", LOCKER_ZONES.get(locker_id, "Tunis"))
                lockers.append(info)
        return {"lockers": lockers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/lockers/{locker_id}", tags=["Lockers"])
def get_locker(locker_id: str, user: dict = Depends(verify_token)):
    """Retourne les détails d'un locker spécifique."""
    try:
        data = db_ref(f"lockers/{locker_id}").get()
        if not data:
            raise HTTPException(status_code=404, detail="Locker introuvable")
        data["id"]   = locker_id
        data.setdefault("zone", LOCKER_ZONES.get(locker_id, "Tunis"))
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 4. COMMANDES (BOOKINGS) ──────────────────────────────────────────
@app.post("/bookings", status_code=201, tags=["Commandes"])
def create_booking(body: BookingCreate, user: dict = Depends(verify_token)):
    """
    Crée une nouvelle commande.

    Body JSON attendu :
    {
        "locker_id"    : "locker_1",
        "product_name" : "Smartphone",
        "home_address" : "12 Rue de Lac, Tunis"
    }

    Retourne le booking_id, le token QR, et les détails de la commande.
    """
    uid   = user["uid"]
    email = user.get("email", "")

    # Vérifie que le produit existe
    product = PRODUCTS.get(body.product_name)
    if not product:
        raise HTTPException(status_code=400, detail=f"Produit '{body.product_name}' inconnu. "
                            f"Choix valides : {list(PRODUCTS.keys())}")

    # Vérifie que le locker existe et est disponible
    locker_data = db_ref(f"lockers/{body.locker_id}").get()
    if not locker_data:
        raise HTTPException(status_code=404, detail="Locker introuvable")
    if locker_data.get("statut") == "reservé":
        raise HTTPException(status_code=409, detail="Ce locker est déjà réservé")

    # Récupère le profil utilisateur
    user_profile = db_ref(f"users/{uid}").get() or {}
    user_name    = user_profile.get("name", email)

    # Infos locker
    zone         = LOCKER_ZONES.get(body.locker_id, "Tunis")
    locker_name  = locker_data.get("nom", body.locker_id)

    # Trouve le coursier pour ce locker
    courier_email = LOCKER_COURIER_MAP.get(body.locker_id)
    courier_uid   = None
    courier_name  = "N/A"
    if courier_email:
        all_users = db_ref("users").get() or {}
        for u_uid, u_data in all_users.items():
            if isinstance(u_data, dict) and u_data.get("email") == courier_email:
                courier_uid  = u_uid
                courier_name = u_data.get("name", courier_email)
                break

    # Crée la commande
    bid = str(uuid.uuid4())[:8].upper()
    ts  = int(time.time() * 1000)
    now = datetime.now().strftime("%d/%m/%Y at %H:%M")

    booking = {
        "booking_id"    : bid,
        "user_id"       : uid,
        "user_email"    : email,
        "user_name"     : user_name,
        "locker_id"     : body.locker_id,
        "locker_name"   : locker_name,
        "locker_zone"   : zone,
        "produit"       : body.product_name,
        "poids_kg"      : product["weight"],
        "prix"          : product["price"],
        "home_address"  : body.home_address,
        "timestamp"     : now,
        "statut"        : "en_attente",
        "courrier_id"   : courier_uid or "",
        "courrier_email": courier_email or "",
        "courrier_name" : courier_name,
        "createdAt"     : ts,
        "updatedAt"     : ts,
    }

    # Écrit dans Firebase
    db_ref(f"bookings/{bid}").set(booking)
    db_ref(f"lockers/{body.locker_id}").update({"statut": "reservé", "booking_id": bid})

    # Crée le token QR pour le coursier
    qr_tok = _gen_qr_token()
    db_ref(f"qrTokens/{qr_tok}").set({
        "bookingId"   : bid,
        "lockerId"    : body.locker_id,
        "lockerName"  : locker_name,
        "lockerZone"  : zone,
        "issuedToUid" : courier_uid or "",
        "userEmail"   : email,
        "produit"     : body.product_name,
        "timestamp"   : now,
        "expiresAt"   : ts + 86400000,   # 24h
        "usedAt"      : "",
    })

    # Envoie l'email de confirmation au client
    prix  = product["price"]
    tva   = round(prix * 0.19, 2)
    total = round(prix + tva, 2)
    send_email_html(
        to      = email,
        subject = f"Droplock — Commande #{bid} confirmée ✅",
        plain   = f"Commande #{bid} confirmée. Produit : {body.product_name}. Total : {total:.2f} TND.",
        html    = f"""<html><body style="font-family:Arial,sans-serif;background:#f0f2f6;padding:20px;">
<div style="max-width:520px;margin:auto;background:white;border-radius:16px;padding:2rem;">
  <div style="background:linear-gradient(135deg,#FF6B35,#FF3CAC);color:white;padding:1.5rem;border-radius:12px;text-align:center;margin-bottom:1.5rem;">
    <h2 style="margin:0;">🔒 Droplock</h2>
    <p style="margin:.3rem 0 0;opacity:.85;">Commande confirmée ✅</p>
  </div>
  <table style="width:100%;font-size:.9rem;">
    <tr><td style="color:#777;padding:6px;width:40%;">ID Commande</td><td style="font-weight:700;">#{bid}</td></tr>
    <tr><td style="color:#777;padding:6px;">Produit</td><td>{body.product_name}</td></tr>
    <tr><td style="color:#777;padding:6px;">Locker</td><td>🔒 {locker_name}</td></tr>
    <tr><td style="color:#777;padding:6px;">Zone</td><td>📍 {zone}</td></tr>
    <tr><td style="color:#777;padding:6px;">Total</td><td style="font-weight:700;color:#FF6B35;">{total:.2f} TND</td></tr>
  </table>
</div></body></html>"""
    )

    return {
        "success"    : True,
        "booking_id" : bid,
        "qr_token"   : qr_tok,
        "booking"    : booking,
    }


@app.get("/bookings", tags=["Commandes"])
def get_my_bookings(user: dict = Depends(verify_token)):
    """Retourne toutes les commandes de l'utilisateur connecté."""
    uid = user["uid"]
    try:
        data = db_ref("bookings").order_by_child("user_id").equal_to(uid).get()
        if not data:
            return {"bookings": []}
        return {
            "bookings": [{"id": k, **v} for k, v in data.items() if isinstance(v, dict)]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bookings/courier/pending", tags=["Commandes"])
def get_courier_pending(user: dict = Depends(verify_token)):
    """
    Retourne les commandes 'en_attente' ou 'en_cours' (vue coursier).
    Accessible à tous les utilisateurs authentifiés — en prod,
    ajoute une vérification du rôle 'courrier'.
    """
    try:
        data = db_ref("bookings").get()
        if not data:
            return {"bookings": []}
        pending = [
            {"id": k, **v} for k, v in data.items()
            if isinstance(v, dict) and v.get("statut") in ["en_attente", "en_cours"]
        ]
        return {"bookings": sorted(pending, key=lambda x: x.get("createdAt", 0), reverse=True)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bookings/{booking_id}", tags=["Commandes"])
def get_booking(booking_id: str, user: dict = Depends(verify_token)):
    """Retourne les détails d'une commande spécifique."""
    try:
        data = db_ref(f"bookings/{booking_id}").get()
        if not data:
            raise HTTPException(status_code=404, detail="Commande introuvable")
        return {"id": booking_id, **data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/bookings/{booking_id}/status", tags=["Commandes"])
def update_booking_status(
    booking_id : str,
    body       : BookingStatusUpdate,
    user       : dict = Depends(verify_token)
):
    """
    Met à jour le statut d'une commande.

    Statuts valides : en_attente | en_cours | livré | annulé

    Body JSON :
    { "status": "en_cours" }
    """
    valid_statuses = ["en_attente", "en_cours", "livré", "annulé"]
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Statut '{body.status}' invalide. Choix : {valid_statuses}"
        )
    try:
        booking = db_ref(f"bookings/{booking_id}").get()
        if not booking:
            raise HTTPException(status_code=404, detail="Commande introuvable")

        db_ref(f"bookings/{booking_id}").update({
            "statut"    : body.status,
            "updatedAt" : int(time.time() * 1000),
        })

        # Si livré : libère le locker + notifie le client
        if body.status == "livré":
            locker_id = booking.get("locker_id")
            if locker_id:
                db_ref(f"lockers/{locker_id}").update({
                    "statut"     : "disponible",
                    "booking_id" : "",
                })
            user_email = booking.get("user_email", "")
            if user_email:
                _send_delivery_email(user_email, booking)

        return {"success": True, "booking_id": booking_id, "new_status": body.status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 5. TOKENS QR ─────────────────────────────────────────────────────
@app.get("/tokens/courier/{courier_uid}", tags=["Tokens QR"])
def get_courier_tokens(courier_uid: str, user: dict = Depends(verify_token)):
    """Retourne tous les tokens QR assignés à un coursier."""
    try:
        data = db_ref("qrTokens").order_by_child("issuedToUid").equal_to(courier_uid).get()
        if not data:
            return {"tokens": []}
        return {
            "tokens": [{"id": k, **v} for k, v in data.items() if isinstance(v, dict)]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tokens/use", tags=["Tokens QR"])
def use_token(body: TokenUse, user: dict = Depends(verify_token)):
    """
    Marque un token QR comme utilisé (scan par le coursier).

    Body JSON :
    {
        "token_id"   : "QR-S1-ABC123",
        "booking_id" : "A1B2C3D4"
    }
    """
    try:
        token_data = db_ref(f"qrTokens/{body.token_id}").get()
        if not token_data:
            raise HTTPException(status_code=404, detail="Token introuvable")
        if token_data.get("usedAt"):
            raise HTTPException(status_code=409, detail="Token déjà utilisé")

        now = datetime.now().strftime("%d/%m/%Y at %H:%M")
        db_ref(f"qrTokens/{body.token_id}").update({"usedAt": now})
        db_ref(f"bookings/{body.booking_id}").update({
            "statut"    : "livré",
            "updatedAt" : int(time.time() * 1000),
        })

        # Libère le locker
        locker_id = token_data.get("lockerId")
        if locker_id:
            db_ref(f"lockers/{locker_id}").update({"statut": "disponible", "booking_id": ""})

        return {"success": True, "token_id": body.token_id, "used_at": now}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 6. PROFIL UTILISATEUR ────────────────────────────────────────────
@app.get("/profile", tags=["Profil"])
def get_profile(user: dict = Depends(verify_token)):
    """Retourne le profil de l'utilisateur connecté."""
    uid = user["uid"]
    try:
        data = db_ref(f"users/{uid}").get() or {}
        return {"uid": uid, **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/profile", tags=["Profil"])
def update_profile(body: ProfileUpdate, user: dict = Depends(verify_token)):
    """
    Met à jour le profil de l'utilisateur.

    Body JSON (champs optionnels) :
    {
        "name" : "Mohamed Ali",
        "zone" : "Tunis"
    }
    """
    uid     = user["uid"]
    updates = {}
    if body.name is not None:
        updates["name"]        = body.name.strip()
        updates["displayName"] = body.name.strip()
    if body.zone is not None:
        if body.zone not in ["Tunis", "Ariana", "Lac", "Manouba", ""]:
            raise HTTPException(status_code=400, detail="Zone invalide")
        updates["zone"] = body.zone

    if not updates:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

    try:
        db_ref(f"users/{uid}").update(updates)
        return {"success": True, "updated": updates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 7. UTILITAIRES ───────────────────────────────────────────────────
@app.get("/zones", tags=["Utilitaires"])
def get_zones():
    """Retourne les zones disponibles et leurs lockers associés."""
    return {
        "zones": [
            {"zone": zone, "locker_id": locker_id, "courier_email": ZONE_COURIER_EMAIL.get(zone)}
            for locker_id, zone in LOCKER_ZONES.items()
        ]
    }

@app.get("/zones/detect", tags=["Utilitaires"])
def detect_zone_from_address(address: str):
    """
    Détecte automatiquement la zone à partir d'une adresse.

    Paramètre URL : ?address=12+Rue+du+Lac+Tunis
    """
    zone = detect_zone(address)
    if not zone:
        return {"zone": None, "message": "Zone non détectée pour cette adresse"}
    return {
        "zone"      : zone,
        "locker_id" : ZONE_LOCKER.get(zone),
    }


# ════════════════════════════════════════════════════════════════════
# HELPER EMAIL INTERNE (réutilisé depuis update_booking_status)
# ════════════════════════════════════════════════════════════════════
def _send_delivery_email(to: str, booking: dict):
    bid   = booking.get("booking_id", "—")
    prod  = booking.get("produit", "—")
    lock  = booking.get("locker_name", "—")
    prix  = booking.get("prix", 0)
    total = round(prix * 1.19, 2)
    now   = datetime.now().strftime("%d/%m/%Y at %H:%M")
    send_email_html(
        to      = to,
        subject = f"Droplock — Votre colis #{bid} est arrivé ! 📦✅",
        plain   = f"Votre commande #{bid} ({prod}) a été livrée au locker {lock}.",
        html    = f"""<html><body style="font-family:Arial,sans-serif;background:#f0f2f6;padding:20px;">
<div style="max-width:520px;margin:auto;background:white;border-radius:16px;padding:2rem;">
  <div style="background:linear-gradient(135deg,#22C87A,#0B6B42);color:white;padding:1.5rem;border-radius:12px;text-align:center;margin-bottom:1.5rem;">
    <div style="font-size:2.5rem;">📦✅</div>
    <h2 style="margin:.4rem 0 0;">Votre colis est arrivé !</h2>
    <p style="margin:.3rem 0 0;opacity:.85;">Commande #{bid}</p>
  </div>
  <table style="width:100%;font-size:.9rem;">
    <tr><td style="color:#777;padding:6px;width:40%;">Produit</td><td style="font-weight:700;">{prod}</td></tr>
    <tr><td style="color:#777;padding:6px;">Locker</td><td>🔒 {lock}</td></tr>
    <tr><td style="color:#777;padding:6px;">Livré le</td><td>📅 {now}</td></tr>
    <tr><td style="color:#777;padding:6px;">Total payé</td><td style="color:#22C87A;font-weight:700;">{total:.2f} TND</td></tr>
  </table>
  <p style="color:#aaa;font-size:.75rem;text-align:center;margin-top:1.5rem;border-top:1px solid #eee;padding-top:1rem;">Message automatique — Ne pas répondre.</p>
</div></body></html>"""
    )


# ════════════════════════════════════════════════════════════════════
# LANCEMENT DIRECT  (python api.py)
# ════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    print("""
╔══════════════════════════════════════════════════════╗
║         DROPLOCK API — Démarrage                     ║
╠══════════════════════════════════════════════════════╣
║  API    →  http://localhost:8000                     ║
║  Docs   →  http://localhost:8000/docs                ║
╚══════════════════════════════════════════════════════╝
""")
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
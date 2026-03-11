from flask import Flask, render_template, request, jsonify, redirect
import sqlite3, qrcode, os, time, json, base64
import numpy as np
import cv2
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from blockchain import blockchain

app = Flask(__name__)

GMAIL_USER = "pavithramadhan7@gmail.com"
GMAIL_PASS = "eabputoetrgxskpj"

def send_ticket_email(to_email, name, ticket_id, qr_path):
    try:
        msg = MIMEMultipart("related")
        msg["Subject"] = f"TechFest 2025 — Your Ticket #{ticket_id}"
        msg["From"]    = GMAIL_USER
        msg["To"]      = to_email
        html = f""" 
        <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#f5f0e8;padding:30px;border-radius:16px;">
          <div style="background:#1a1410;color:#fff;padding:24px;border-radius:12px;text-align:center;margin-bottom:20px;">
            <h1 style="font-size:32px;letter-spacing:3px;margin:0;">TECH<span style="color:#e8401c;">FEST</span> 2025</h1>
            <p style="color:#aaa;margin:6px 0 0;">December 25, 2025 &nbsp;·&nbsp; Chennai</p>
          </div>
          <div style="background:#d4edda;border:2px solid #28a745;border-radius:10px;padding:14px 18px;margin-bottom:20px;color:#155724;">
            <strong>✅ Ticket Confirmed!</strong> Your ticket is secured by Blockchain.
          </div>
          <div style="background:#fff;border:1px solid #e0d8cc;border-radius:12px;padding:20px;margin-bottom:20px;">
            <table style="width:100%;font-size:15px;">
              <tr><td style="color:#8a7f72;padding:8px 0;border-bottom:1px dashed #e0d8cc;">Name</td><td style="font-weight:600;padding:8px 0;border-bottom:1px dashed #e0d8cc;">{name}</td></tr>
              <tr><td style="color:#8a7f72;padding:8px 0;border-bottom:1px dashed #e0d8cc;">Ticket ID</td><td style="font-weight:600;padding:8px 0;border-bottom:1px dashed #e0d8cc;">#{ticket_id}</td></tr>
              <tr><td style="color:#8a7f72;padding:8px 0;">Status</td><td style="font-weight:600;padding:8px 0;color:#1a8a4a;">✅ Valid</td></tr>
            </table>
          </div>
          <div style="text-align:center;background:#fff;border:1px solid #e0d8cc;border-radius:12px;padding:20px;margin-bottom:20px;">
            <p style="font-size:12px;color:#8a7f72;margin-bottom:12px;">Show this QR at the entry gate</p>
            <img src="cid:qrcode" width="180" height="180" style="border:4px solid #e0d8cc;border-radius:10px;"/>
          </div>
          <div style="text-align:center;font-size:12px;color:#8a7f72;">TechFest 2025 · Powered by TicketSys</div>
        </div>"""
        msg.attach(MIMEText(html, "html"))
        with open(qr_path, "rb") as f:
            img = MIMEImage(f.read())
            img.add_header("Content-ID", "<qrcode>")
            img.add_header("Content-Disposition", "inline", filename="ticket_qr.png")
            msg.attach(img)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tickets(
            id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            email TEXT,
            org TEXT,
            used INTEGER DEFAULT 0,
            sold INTEGER DEFAULT 1,
            block_hash TEXT,
            face_path TEXT,
            source TEXT DEFAULT 'online'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS fake_attempts(
            id INTEGER PRIMARY KEY,
            ticket_id TEXT,
            reason TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def compare_faces(new_face, existing_path, threshold=3500000):
    if not os.path.exists(existing_path):
        return False
    existing = cv2.imread(existing_path, cv2.IMREAD_GRAYSCALE)
    if existing is None:
        return False
    existing_resized = cv2.resize(existing, (100, 100))
    diff  = cv2.absdiff(new_face, existing_resized)
    score = int(np.sum(diff.astype(np.int32)**2))
    return score < threshold

def decode_and_detect_face(image_b64):
    img_bytes = base64.b64decode(image_b64.split(",")[1])
    np_arr    = np.frombuffer(img_bytes, np.uint8)
    img       = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    cascade   = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    gray      = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces     = cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    return cv2.resize(gray[y:y+h, x:x+w], (100, 100))

def check_face_duplicate(face_img):
    conn = sqlite3.connect("database.db")
    c    = conn.cursor()
    c.execute("SELECT id, face_path FROM tickets WHERE face_path IS NOT NULL")
    rows = c.fetchall()
    conn.close()
    for row in rows:
        if compare_faces(face_img, row[1]):
            return row[0]
    return None

def save_face(ticket_id, face_img):
    if not os.path.exists("static/faces"):
        os.makedirs("static/faces")
    path = f"static/faces/{ticket_id}.jpg"
    cv2.imwrite(path, face_img)
    return path

def create_ticket_qr(ticket_id, block_hash):
    if not os.path.exists("static/qr"):
        os.makedirs("static/qr")
    token    = f"{ticket_id}-{int(time.time())}-{block_hash}"
    qr_path  = f"static/qr/{ticket_id}.png"
    qrcode.make(token).save(qr_path)
    return qr_path

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ticket_count")
def ticket_count():
    conn = sqlite3.connect("database.db")
    c    = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tickets")
    count = c.fetchone()[0]
    conn.close()
    return jsonify({"count": count})

@app.route("/check_email", methods=["POST"])
def check_email():
    data  = request.get_json()
    email = data.get("email", "")
    phone = data.get("phone", "")
    conn  = sqlite3.connect("database.db")
    c     = conn.cursor()
    c.execute("SELECT id FROM tickets WHERE email=? OR phone=?", (email, phone))
    row = c.fetchone()
    conn.close()
    return jsonify({"exists": row is not None})

@app.route("/book_with_face", methods=["POST"])
def book_with_face():
    data  = request.get_json()
    name  = data.get("name", "")
    phone = data.get("phone", "")
    email = data.get("email", "")
    org   = data.get("org", "")
    image = data.get("image", "")

    # Detect face
    face_img = decode_and_detect_face(image)
    if face_img is None:
        return jsonify({"status": "no_face", "message": "No face detected!"})

    # Check face duplicate (online + offline)
    dup_id = check_face_duplicate(face_img)
    if dup_id:
        return jsonify({"status": "face_duplicate", "ticket_id": dup_id})

    # Insert ticket
    conn = sqlite3.connect("database.db")
    c    = conn.cursor()
    c.execute("INSERT INTO tickets(name,phone,email,org,used,sold,source) VALUES (?,?,?,?,0,1,'online')",
              (name, phone, email, org))
    ticket_id = c.lastrowid
    conn.commit()

    block      = blockchain.create_block({"ticket_id": ticket_id, "name": name})
    block_hash = block["hash"]
    face_path  = save_face(ticket_id, face_img)
    qr_path    = create_ticket_qr(ticket_id, block_hash)

    c.execute("UPDATE tickets SET block_hash=?, face_path=? WHERE id=?",
              (block_hash, face_path, ticket_id))
    conn.commit()
    conn.close()

    # Send email
    if email:
        send_ticket_email(email, name, ticket_id, qr_path)

    return jsonify({"status": "success", "ticket_id": ticket_id})

@app.route("/ticket_page/<int:ticket_id>")
def ticket_page(ticket_id):
    conn = sqlite3.connect("database.db")
    c    = conn.cursor()
    c.execute("SELECT name,phone,email,org,block_hash FROM tickets WHERE id=?", (ticket_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return "Ticket not found", 404
    return render_template("ticket.html",
                           ticket_id=ticket_id,
                           name=row[0], phone=row[1],
                           email=row[2], org=row[3],
                           qr=f"static/qr/{ticket_id}.png",
                           ticket_status="original",
                           block_hash=row[4])

@app.route("/buy_from_seller")
def buy_from_seller():
    return render_template("buy_from_seller.html")

@app.route("/seller_gate")
def seller_gate():
    return render_template("seller_gate.html")

@app.route("/check_phone", methods=["POST"])
def check_phone():
    data  = request.get_json()
    phone = data.get("phone", "")
    conn  = sqlite3.connect("database.db")
    c     = conn.cursor()
    c.execute("SELECT id FROM tickets WHERE phone=?", (phone,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({"has_ticket": True, "phone": phone, "ticket_id": row[0]})
    return jsonify({"has_ticket": False})

@app.route("/verify_face", methods=["POST"])
def verify_face():
    data  = request.get_json()
    phone = data.get("phone", "")
    name  = data.get("name", "Walk-in")
    image = data.get("image", "")

    face_img = decode_and_detect_face(image)
    if face_img is None:
        return jsonify({"status": "error", "message": "No face detected! Better lighting-ல try பண்ணுங்க."})

    # Check face duplicate (online + offline same DB)
    dup_id = check_face_duplicate(face_img)
    if dup_id:
        return jsonify({"status": "duplicate", "ticket_id": dup_id})

    # Issue ticket
    conn = sqlite3.connect("database.db")
    c    = conn.cursor()
    c.execute("INSERT INTO tickets(name,phone,email,org,used,sold,source) VALUES (?,?,?,?,0,1,'offline')",
              (name, phone, "", "Walk-in"))
    ticket_id = c.lastrowid
    conn.commit()

    block      = blockchain.create_block({"ticket_id": ticket_id, "name": name})
    block_hash = block["hash"]
    face_path  = save_face(ticket_id, face_img)
    create_ticket_qr(ticket_id, block_hash)

    c.execute("UPDATE tickets SET block_hash=?, face_path=? WHERE id=?",
              (block_hash, face_path, ticket_id))
    conn.commit()
    conn.close()

    return jsonify({"status": "issued", "ticket_id": ticket_id, "name": name, "phone": phone})

@app.route("/verify", methods=["POST"])
def verify():
    ticket_id = int(request.form["ticket"])
    conn = sqlite3.connect("database.db")
    c    = conn.cursor()
    c.execute("SELECT used FROM tickets WHERE id=?", (ticket_id,))
    data = c.fetchone()
    if data is None:
        c.execute("INSERT INTO fake_attempts(ticket_id,reason,timestamp) VALUES (?,?,?)",
                  (ticket_id, "Ticket not found", time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        result = "Fake Ticket"
    elif data[0] == 1:
        result = "Ticket Already Used"
    else:
        c.execute("UPDATE tickets SET used=1 WHERE id=?", (ticket_id,))
        conn.commit()
        result = "Entry Allowed"
    conn.close()
    return render_template("verify.html", result=result)

@app.route("/check_qr", methods=["POST"])
def check_qr():
    try:
        data      = request.get_json()
        token     = data["ticket"]
        ticket_id = int(token.split("-")[0])
        conn = sqlite3.connect("database.db")
        c    = conn.cursor()
        c.execute("SELECT used, sold, name FROM tickets WHERE id=?", (ticket_id,))
        row = c.fetchone()
        if row is None:
            c.execute("INSERT INTO fake_attempts(ticket_id,reason,timestamp) VALUES (?,?,?)",
                      (ticket_id,"QR not in system",time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit(); conn.close()
            return jsonify({"status":"fake","result":"FAKE TICKET","detail":f"Ticket {ticket_id} not found!"})
        used, sold, name = row
        if used == 1:
            c.execute("INSERT INTO fake_attempts(ticket_id,reason,timestamp) VALUES (?,?,?)",
                      (ticket_id,"Already used",time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit(); conn.close()
            return jsonify({"status":"used","result":"ALREADY USED","detail":"Already used at entry!"})
        if sold == 1:
            c.execute("INSERT INTO fake_attempts(ticket_id,reason,timestamp) VALUES (?,?,?)",
                      (ticket_id,"Transfer attempt",time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit(); conn.close()
            return jsonify({"status":"already_sold","result":"TICKET NOT FOR SALE",
                            "detail":f"Belongs to {name}. Cannot transfer!","ticket_id":ticket_id,"name":name})
        c.execute("UPDATE tickets SET sold=1 WHERE id=?", (ticket_id,))
        conn.commit(); conn.close()
        return jsonify({"status":"valid","result":"ORIGINAL TICKET","detail":"Safe to buy!",
                        "ticket_id":ticket_id,"name":name})
    except Exception as e:
        return jsonify({"status":"error","result":"Error","detail":str(e)})

@app.route("/verify_qr", methods=["POST"])
def verify_qr():
    try:
        data      = request.get_json()
        parts     = data["ticket"].split("-")
        ticket_id = int(parts[0])
        scanned_hash = parts[2] if len(parts) >= 3 else None
        conn = sqlite3.connect("database.db")
        c    = conn.cursor()
        c.execute("SELECT used, block_hash, name FROM tickets WHERE id=?", (ticket_id,))
        ticket = c.fetchone()
        if ticket is None:
            c.execute("INSERT INTO fake_attempts(ticket_id,reason,timestamp) VALUES (?,?,?)",
                      (ticket_id,"QR not in system",time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit(); conn.close()
            return jsonify({"result":"Fake Ticket"})
        used, db_hash, name = ticket
        if scanned_hash and db_hash and scanned_hash != db_hash:
            c.execute("INSERT INTO fake_attempts(ticket_id,reason,timestamp) VALUES (?,?,?)",
                      (ticket_id,"Hash mismatch",time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit(); conn.close()
            return jsonify({"result":"Fake Ticket","reason":"Hash mismatch!"})
        if used == 1:
            conn.close()
            return jsonify({"result":"Ticket Already Used"})
        c.execute("UPDATE tickets SET used=1 WHERE id=?", (ticket_id,))
        conn.commit(); conn.close()
        return jsonify({"result":"Entry Allowed","name":name,"ticket_id":ticket_id})
    except Exception as e:
        return jsonify({"result":"Fake Ticket","reason":str(e)})

@app.route("/mark_used/<int:ticket_id>")
def mark_used(ticket_id):
    conn = sqlite3.connect("database.db")
    c    = conn.cursor()
    c.execute("UPDATE tickets SET used=1 WHERE id=?", (ticket_id,))
    conn.commit(); conn.close()
    return "<script>window.location='/admin'</script>"

@app.route("/admin")
def admin():
    conn = sqlite3.connect("database.db")
    c    = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tickets"); total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE used=1"); used = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE used=0"); not_used = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM fake_attempts"); fake_count = c.fetchone()[0]
    c.execute("SELECT id,name,sold,used FROM tickets ORDER BY id DESC"); tickets = c.fetchall()
    c.execute("SELECT ticket_id,reason,timestamp FROM fake_attempts ORDER BY id DESC LIMIT 20"); fakes = c.fetchall()
    conn.close()
    return render_template("admin.html", chain=blockchain.chain,
                           total=total, used=used, not_used=not_used,
                           fake_count=fake_count, tickets=tickets, fakes=fakes)

# ---- Multi-person booking routes ----

@app.route("/book_one_person", methods=["POST"])
def book_one_person():
    data  = request.get_json()
    name  = data.get("name","")
    email = data.get("email","")
    phone = data.get("phone","")
    image = data.get("image","")

    face_img = decode_and_detect_face(image)
    if face_img is None:
        return jsonify({"status":"no_face"})

    dup_id = check_face_duplicate(face_img)
    if dup_id:
        return jsonify({"status":"face_duplicate","ticket_id":dup_id})

    conn = sqlite3.connect("database.db")
    c    = conn.cursor()
    c.execute("INSERT INTO tickets(name,phone,email,org,used,sold,source) VALUES (?,?,?,?,0,1,'online')",
              (name, phone, email, ""))
    ticket_id = c.lastrowid
    conn.commit()

    block      = blockchain.create_block({"ticket_id":ticket_id,"name":name})
    block_hash = block["hash"]
    face_path  = save_face(ticket_id, face_img)
    qr_path    = create_ticket_qr(ticket_id, block_hash)

    c.execute("UPDATE tickets SET block_hash=?, face_path=? WHERE id=?",
              (block_hash, face_path, ticket_id))
    conn.commit()
    conn.close()

    return jsonify({"status":"success","ticket_id":ticket_id,"name":name})

@app.route("/send_group_email", methods=["POST"])
def send_group_email():
    data    = request.get_json()
    email   = data.get("email","")
    tickets = data.get("tickets",[])

    if not email or not tickets:
        return jsonify({"ok":False})

    try:
        msg = MIMEMultipart("related")
        msg["Subject"] = f"TechFest 2025 — Your {len(tickets)} Ticket(s)"
        msg["From"]    = GMAIL_USER
        msg["To"]      = email

        ticket_rows = ""
        for t in tickets:
            ticket_rows += f"""
            <tr>
              <td style="padding:10px;border-bottom:1px solid #eee;">{t['name']}</td>
              <td style="padding:10px;border-bottom:1px solid #eee;text-align:center;">#{t['ticket_id']}</td>
              <td style="padding:10px;border-bottom:1px solid #eee;text-align:center;color:#1a8a4a;">✅ Valid</td>
            </tr>"""

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#f5f0e8;padding:30px;border-radius:16px;">
          <div style="background:#1a1410;color:#fff;padding:24px;border-radius:12px;text-align:center;margin-bottom:20px;">
            <h1 style="font-size:32px;letter-spacing:3px;margin:0;">TECH<span style="color:#e8401c;">FEST</span> 2025</h1>
            <p style="color:#aaa;margin:6px 0 0;">December 25, 2025 · Chennai</p>
          </div>
          <div style="background:#d4edda;border:2px solid #28a745;border-radius:10px;padding:14px;margin-bottom:20px;color:#155724;">
            <strong>🎉 {len(tickets)} Ticket(s) Confirmed!</strong> All tickets secured by Blockchain.
          </div>
          <div style="background:#fff;border:1px solid #e0d8cc;border-radius:12px;overflow:hidden;margin-bottom:20px;">
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
              <thead>
                <tr style="background:#f5f0e8;">
                  <th style="padding:12px;text-align:left;color:#8a7f72;">NAME</th>
                  <th style="padding:12px;text-align:center;color:#8a7f72;">TICKET ID</th>
                  <th style="padding:12px;text-align:center;color:#8a7f72;">STATUS</th>
                </tr>
              </thead>
              <tbody>{ticket_rows}</tbody>
            </table>
          </div>"""

        # Attach QR for each ticket
        for i, t in enumerate(tickets):
            qr_path = f"static/qr/{t['ticket_id']}.png"
            html += f"""
          <div style="text-align:center;background:#fff;border:1px solid #e0d8cc;border-radius:12px;padding:16px;margin-bottom:12px;">
            <p style="font-size:12px;color:#8a7f72;margin-bottom:8px;">{t['name']} — Ticket #{t['ticket_id']}</p>
            <img src="cid:qr{i}" width="150" height="150" style="border:3px solid #e0d8cc;border-radius:8px;"/>
          </div>"""

        html += """
          <div style="text-align:center;font-size:12px;color:#8a7f72;">TechFest 2025 · Powered by TicketSys</div>
        </div>"""

        msg.attach(MIMEText(html, "html"))

        for i, t in enumerate(tickets):
            qr_path = f"static/qr/{t['ticket_id']}.png"
            if os.path.exists(qr_path):
                with open(qr_path,"rb") as f:
                    img = MIMEImage(f.read())
                    img.add_header("Content-ID", f"<qr{i}>")
                    img.add_header("Content-Disposition","inline",filename=f"ticket_{t['ticket_id']}.png")
                    msg.attach(img)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, email, msg.as_string())

        return jsonify({"ok":True})
    except Exception as e:
        print(f"Group email error: {e}")
        return jsonify({"ok":False,"error":str(e)})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host='0.0.0.0')


























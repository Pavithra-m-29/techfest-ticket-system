from flask import Flask, render_template, request, jsonify, redirect
import sqlite3, qrcode, os, time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from blockchain import blockchain

app = Flask(__name__)

# ============================================================
#  Gmail Config — இங்க உங்கள் details போடுங்க
# ============================================================
GMAIL_ADDRESS  = "pavithramadhan7@gmail.com"       # ← உங்கள் Gmail address
GMAIL_PASSWORD = "tpxt rawb sgkp fnio"  # ← 16-digit App Password

# ============================================================
#  EMAIL SEND FUNCTION
# ============================================================
def send_email(to_email, name, ticket_id):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎫 TechFest 2025 — Your Ticket is Booked! #{ticket_id}"
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = to_email

        # Plain text version
        text = f"""
Hi {name}!

Your TechFest 2025 ticket has been booked successfully! 🎉

Ticket ID : #{ticket_id}
Event     : TechFest 2025
Date      : December 25, 2025
Venue     : Chennai

Show your QR code at the entry gate.
Enjoy your moment! 🎊

— TechFest 2025 Team
        """

        # HTML version (nice looking email)
        html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<style>
  body {{ font-family: Arial, sans-serif; background: #f5f0e8; margin: 0; padding: 20px; }}
  .card {{ max-width: 480px; margin: 0 auto; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
  .header {{ background: #1a1410; padding: 32px; text-align: center; }}
  .header h1 {{ font-size: 36px; color: #e8401c; margin: 0; letter-spacing: 3px; }}
  .header p {{ color: #8a7f72; font-size: 13px; margin: 6px 0 0; }}
  .body {{ padding: 28px; }}
  .greeting {{ font-size: 18px; font-weight: 700; color: #1a1410; margin-bottom: 8px; }}
  .msg {{ font-size: 14px; color: #555; margin-bottom: 24px; line-height: 1.6; }}
  .ticket-box {{ background: #f5f0e8; border: 2px dashed #e0d8cc; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 24px; }}
  .ticket-label {{ font-size: 11px; color: #8a7f72; text-transform: uppercase; letter-spacing: 1px; }}
  .ticket-id {{ font-size: 32px; font-weight: 800; color: #e8401c; letter-spacing: 2px; margin: 6px 0; }}
  .info-row {{ display: flex; justify-content: space-between; font-size: 13px; padding: 8px 0; border-bottom: 1px dashed #e0d8cc; }}
  .info-row:last-child {{ border-bottom: none; }}
  .info-key {{ color: #8a7f72; }}
  .info-val {{ font-weight: 600; color: #1a1410; }}
  .footer {{ background: #1a1410; padding: 16px; text-align: center; font-size: 12px; color: #6b6b6b; }}
  .emoji {{ font-size: 48px; margin-bottom: 8px; display: block; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <h1>TECHFEST</h1>
    <p>2025 · Chennai · December 25</p>
  </div>
  <div class="body">
    <span class="emoji">🎉</span>
    <div class="greeting">Hi {name}!</div>
    <div class="msg">Your ticket has been booked successfully. Show the QR code at the entry gate to get in!</div>

    <div class="ticket-box">
      <div class="ticket-label">Your Ticket ID</div>
      <div class="ticket-id">#{ticket_id}</div>
      <div class="ticket-label">Show QR at entry gate</div>
    </div>

    <div class="info-row">
      <span class="info-key">Event</span>
      <span class="info-val">TechFest 2025</span>
    </div>
    <div class="info-row">
      <span class="info-key">Date</span>
      <span class="info-val">December 25, 2025</span>
    </div>
    <div class="info-row">
      <span class="info-key">Venue</span>
      <span class="info-val">Chennai</span>
    </div>
    <div class="info-row">
      <span class="info-key">Status</span>
      <span class="info-val" style="color:#1a8a4a">✅ Confirmed</span>
    </div>
  </div>
  <div class="footer">
    TechFest 2025 · Powered by TicketSys<br>
    Enjoy your moment! 🎊
  </div>
</div>
</body>
</html>
        """

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())

        print(f"✅ Email sent to {to_email}")

    except Exception as e:
        print(f"❌ Email error: {e}")

# ============================================================
#  DATABASE INIT
# ============================================================
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tickets(
            id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            email TEXT,
            used INTEGER DEFAULT 0,
            sold INTEGER DEFAULT 0
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

# ============================================================
#  ROUTES
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/book", methods=["POST"])
def book():
    name  = request.form.get("name", "")
    phone = request.form.get("phone", "")
    email = request.form.get("email", "")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO tickets(name, phone, email, used, sold) VALUES (?,?,?,0,1)",
              (name, phone, email))
    ticket_id = c.lastrowid
    conn.commit()
    conn.close()

    # QR generate
    token = f"{ticket_id}-{int(time.time())}"
    img = qrcode.make(token)
    if not os.path.exists("static/qr"):
        os.makedirs("static/qr")
    qr_path = f"static/qr/{ticket_id}.png"
    img.save(qr_path)

    # Blockchain
    blockchain.create_block({"ticket_id": ticket_id, "name": name})

    # ✅ Email Notification
    if email and "@" in email:
        send_email(email, name, ticket_id)

    return render_template("ticket.html",
                           ticket_id=ticket_id,
                           name=name,
                           qr=qr_path,
                           ticket_status="original")

@app.route("/verify", methods=["POST"])
def verify():
    ticket_id = int(request.form["ticket"])
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT used FROM tickets WHERE id=?", (ticket_id,))
    data = c.fetchone()
    if data is None:
        c.execute("INSERT INTO fake_attempts(ticket_id, reason, timestamp) VALUES (?,?,?)",
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
        data = request.get_json()
        token = data["ticket"]
        ticket_id = int(token.split("-")[0])
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT used, sold, name FROM tickets WHERE id=?", (ticket_id,))
        row = c.fetchone()

        if row is None:
            c.execute("INSERT INTO fake_attempts(ticket_id, reason, timestamp) VALUES (?,?,?)",
                      (ticket_id, "QR not in system", time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            return jsonify({"status": "fake", "result": "FAKE TICKET",
                            "detail": f"Ticket ID {ticket_id} does not exist. Do NOT buy!"})

        used, sold, name = row[0], row[1], row[2]

        if used == 1:
            c.execute("INSERT INTO fake_attempts(ticket_id, reason, timestamp) VALUES (?,?,?)",
                      (ticket_id, "Already used at entry", time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            return jsonify({"status": "used", "result": "ALREADY USED AT ENTRY",
                            "detail": f"Ticket {ticket_id} was already used. Do NOT buy!"})

        if sold == 1:
            c.execute("INSERT INTO fake_attempts(ticket_id, reason, timestamp) VALUES (?,?,?)",
                      (ticket_id, "Transfer attempt blocked", time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            return jsonify({"status": "already_sold", "result": "TICKET NOT FOR SALE",
                            "detail": f"Ticket {ticket_id} belongs to {name}. Cannot be transferred!",
                            "ticket_id": ticket_id, "name": name})

        c.execute("UPDATE tickets SET sold=1 WHERE id=?", (ticket_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "valid", "result": "ORIGINAL TICKET",
                        "detail": f"Ticket {ticket_id} verified. Safe to buy!",
                        "ticket_id": ticket_id, "name": name})

    except Exception as e:
        return jsonify({"status": "error", "result": "Error", "detail": str(e)})

@app.route("/verify_qr", methods=["POST"])
def verify_qr():
    data = request.get_json()
    ticket_id = int(data["ticket"].split("-")[0])
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT used FROM tickets WHERE id=?", (ticket_id,))
    ticket = c.fetchone()
    if ticket is None:
        result = "Fake Ticket"
    elif ticket[0] == 1:
        result = "Ticket Already Used"
    else:
        c.execute("UPDATE tickets SET used=1 WHERE id=?", (ticket_id,))
        conn.commit()
        result = "Entry Allowed"
    conn.close()
    return jsonify({"result": result})

@app.route("/buy_from_seller")
def buy_from_seller():
    return render_template("buy_from_seller.html")

@app.route("/entry_gate")
def entry_gate():
    return render_template("entry_gate.html")

@app.route("/mark_used/<int:ticket_id>")
def mark_used(ticket_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE tickets SET used=1 WHERE id=?", (ticket_id,))
    conn.commit()
    conn.close()
    return redirect("/admin")

@app.route("/admin")
def admin():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tickets")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE used=1")
    used = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM tickets WHERE used=0")
    not_used = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM fake_attempts")
    fake_count = c.fetchone()[0]
    c.execute("SELECT id, name, sold, used FROM tickets ORDER BY id DESC")
    tickets = c.fetchall()
    c.execute("SELECT ticket_id, reason, timestamp FROM fake_attempts ORDER BY id DESC LIMIT 20")
    fakes = c.fetchall()
    conn.close()
    return render_template("admin.html",
                           chain=blockchain.chain,
                           total=total,
                           used=used,
                           not_used=not_used,
                           fake_count=fake_count,
                           tickets=tickets,
                           fakes=fakes)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host='0.0.0.0')









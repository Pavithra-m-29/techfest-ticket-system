from flask import Flask, render_template, request, jsonify
import sqlite3, qrcode, os, time
from blockchain import blockchain

app = Flask(__name__)

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
            sold INTEGER DEFAULT 1
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

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/book", methods=["POST"])
def book():
    name  = request.form.get("name", "")
    phone = request.form.get("phone", "")
    email = request.form.get("email", "")
    org   = request.form.get("org", "")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO tickets(name,phone,email,org,used,sold) VALUES (?,?,?,?,0,1)",
              (name, phone, email, org))
    ticket_id = c.lastrowid
    conn.commit()
    conn.close()

    token = f"{ticket_id}-{int(time.time())}"
    img = qrcode.make(token)
    if not os.path.exists("static/qr"):
        os.makedirs("static/qr")
    qr_path = f"static/qr/{ticket_id}.png"
    img.save(qr_path)
    blockchain.create_block({"ticket_id": ticket_id, "name": name})

    return render_template("ticket.html",
                           ticket_id=ticket_id,
                           name=name,
                           phone=phone,
                           email=email,
                           org=org,
                           qr=qr_path,
                           ticket_status="original")

@app.route("/buy_from_seller")
def buy_from_seller():
    return render_template("buy_from_seller.html")

@app.route("/verify", methods=["POST"])
def verify():
    ticket_id = int(request.form["ticket"])
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
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
        data = request.get_json()
        token = data["ticket"]
        ticket_id = int(token.split("-")[0])
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT used, sold, name FROM tickets WHERE id=?", (ticket_id,))
        row = c.fetchone()

        if row is None:
            c.execute("INSERT INTO fake_attempts(ticket_id,reason,timestamp) VALUES (?,?,?)",
                      (ticket_id, "QR not in system", time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            return jsonify({"status":"fake","result":"FAKE TICKET",
                            "detail":f"Ticket {ticket_id} not found. Do NOT buy!"})

        used, sold, name = row[0], row[1], row[2]

        if used == 1:
            c.execute("INSERT INTO fake_attempts(ticket_id,reason,timestamp) VALUES (?,?,?)",
                      (ticket_id, "Already used at entry", time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            return jsonify({"status":"used","result":"ALREADY USED",
                            "detail":f"Ticket {ticket_id} was already used at entry. Do NOT buy!"})

        if sold == 1:
            c.execute("INSERT INTO fake_attempts(ticket_id,reason,timestamp) VALUES (?,?,?)",
                      (ticket_id, "Transfer attempt blocked", time.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            return jsonify({"status":"already_sold","result":"TICKET NOT FOR SALE",
                            "detail":f"Ticket {ticket_id} belongs to '{name}'. Cannot be transferred!",
                            "ticket_id":ticket_id,"name":name})

        c.execute("UPDATE tickets SET sold=1 WHERE id=?", (ticket_id,))
        conn.commit()
        conn.close()
        return jsonify({"status":"valid","result":"ORIGINAL TICKET",
                        "detail":f"Ticket {ticket_id} verified. Safe to buy!",
                        "ticket_id":ticket_id,"name":name})

    except Exception as e:
        return jsonify({"status":"error","result":"Error","detail":str(e)})

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

@app.route("/mark_used/<int:ticket_id>")
def mark_used(ticket_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE tickets SET used=1 WHERE id=?", (ticket_id,))
    conn.commit()
    conn.close()
    return '<script>window.location="/admin"</script>'

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
    c.execute("SELECT id,name,sold,used FROM tickets ORDER BY id DESC")
    tickets = c.fetchall()
    c.execute("SELECT ticket_id,reason,timestamp FROM fake_attempts ORDER BY id DESC LIMIT 20")
    fakes = c.fetchall()
    conn.close()
    return render_template("admin.html",
                           chain=blockchain.chain,
                           total=total, used=used,
                           not_used=not_used,
                           fake_count=fake_count,
                           tickets=tickets, fakes=fakes)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host='0.0.0.0')
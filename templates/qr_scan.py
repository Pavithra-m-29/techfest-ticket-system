import cv2
from pyzbar import pyzbar
import sqlite3

def verify_ticket(ticket_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT used FROM tickets WHERE id=?", (ticket_id,))
    data = c.fetchone()
    if data is None:
        result = "❌ Fake Ticket"
    elif data[0] == 1:
        result = "⚠ Ticket Already Used"
    else:
        c.execute("UPDATE tickets SET used=1 WHERE id=?",(ticket_id,))
        conn.commit()
        result = "✅ Entry Allowed"
    conn.close()
    return result

cap = cv2.VideoCapture(0)
print("🎥 Camera Opened. Show QR Code...")

while True:
    ret, frame = cap.read()
    if not ret: break
    qr_codes = pyzbar.decode(frame)
    for qr in qr_codes:
        qr_data = qr.data.decode("utf-8")
        ticket_id = int(qr_data.split("-")[0])
        result = verify_ticket(ticket_id)
        print(f"Ticket ID: {ticket_id} → {result}")
        x,y,w,h = qr.rect
        cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
        cv2.putText(frame,result,(x,y-10),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,255),2)
    cv2.imshow("QR Scanner", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

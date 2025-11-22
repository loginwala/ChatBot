from flask import Flask, request, jsonify, render_template
import smtplib
from email.mime.text import MIMEText

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)

# -----------------------------
# CONFIG
# -----------------------------
YOUR_EMAIL = "fraz24931@gmail.com"
YOUR_APP_PASSWORD = "amrd vsdj ndqz btrn"  # 16-digit Gmail App password

GOOGLE_SHEET_ID = "1mBGedEg-k2ziMOrZtbyP7v80CQb-ffvEPjxN_Unmp6E"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

CREDS = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
sheet_service = build("sheets", "v4", credentials=CREDS).spreadsheets()

# -----------------------------
# USER SESSION
# -----------------------------
user_state = {"step": None, "data": {}}

# -----------------------------
# SEND EMAIL FUNCTION
# -----------------------------
def send_email(message_text):
    msg = MIMEText(message_text)
    msg["Subject"] = "🚨 New Emergency Service Request"
    msg["From"] = YOUR_EMAIL
    msg["To"] = YOUR_EMAIL

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(YOUR_EMAIL, YOUR_APP_PASSWORD)
    server.sendmail(YOUR_EMAIL, YOUR_EMAIL, msg.as_string())
    server.quit()

# -----------------------------
# SAVE TO GOOGLE SHEET FUNCTION
# -----------------------------
def save_to_sheet(values):
    sheet_service.values().append(
        spreadsheetId=GOOGLE_SHEET_ID,
        range="Sheet1!A:D",
        valueInputOption="USER_ENTERED",
        body={"values": [values]},
    ).execute()

# -----------------------------
# MAIN CHATBOT LOGIC
# -----------------------------
def process_message(message):
    global user_state
    msg = message.lower().strip()

    if user_state["step"] is None:
        user_state["step"] = "ask_service"
        return "👋 Welcome! Do you need any service today? (yes / no)"

    if user_state["step"] == "ask_service":
        if "yes" in msg:
            user_state["step"] = "ask_emergency"
            return "⚠️ Is it emergency or normal?"
        else:
            user_state["step"] = None
            return "😊 Alright! Message us anytime."

    if user_state["step"] == "ask_emergency":
        if "emergency" in msg:
            user_state["step"] = "emergency_details"
            return "🚨 Emergency detected! Please share:\n• Full Name\n• Address\n• Contact Number"
        elif "normal" in msg:
            user_state["step"] = "normal_details"
            return "📝 Please provide:\n• Full Name\n• Address\n• Preferred Appointment Time"
        else:
            return "❗ Please type: emergency OR normal"

    if user_state["step"] == "emergency_details":
        user_state["data"]["info"] = message
        send_email(message)
        user_state["step"] = None
        return "🚑 Emergency registered! Our team is on the way. Stay safe."

    if user_state["step"] == "normal_details":
        user_state["data"]["info"] = message
        save_to_sheet([message])
        user_state["step"] = None
        return "📅 Your appointment is booked! Our team will visit at the chosen time."

    return "⚠️ Please follow instructions."

# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get_response", methods=["POST"])
def get_response():
    data = request.get_json()
    user_msg = data.get("message", "")
    reply = process_message(user_msg)
    return jsonify({"response": reply})

# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)

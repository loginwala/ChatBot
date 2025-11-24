from flask import Flask, request, jsonify, render_template
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

app = Flask(__name__)

# -----------------------------
# CONFIG
# -----------------------------
GOOGLE_SHEET_ID = "1mBGedEg-k2ziMOrZtbyP7v80CQb-ffvEPjxN_Unmp6E"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/gmail.send"]

# Load Google credentials
CREDS = service_account.Credentials.from_service_account_file(
    "credentials.json", scopes=SCOPES)

# Google Sheets service
sheet_service = build("sheets", "v4", credentials=CREDS).spreadsheets()

# Gmail service
gmail_service = build("gmail", "v1", credentials=CREDS)

# User session
user_state = {"step": None, "data": {}}

# -----------------------------
# Send Gmail Function
# -----------------------------
def send_gmail(subject, body):
    from email.mime.text import MIMEText
    import base64

    message = MIMEText(body)
    message["to"] = "fraz24931@gmail.com"  # Your Gmail
    message["from"] = "fraz24931@gmail.com"
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()

# -----------------------------
# Save to Google Sheet
# -----------------------------
def save_to_sheet(values):
    sheet_service.values().append(
        spreadsheetId=GOOGLE_SHEET_ID,
        range="Sheet1!A:D",
        valueInputOption="USER_ENTERED",
        body={"values": [values]},
    ).execute()

# -----------------------------
# Chatbot logic
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
        try:
            send_gmail("🚨 New Emergency Service Request", message)
        except Exception as e:
            print("Email error:", e)
        user_state["step"] = None
        return "🚑 Emergency registered! Our team is on the way. Stay safe."

    if user_state["step"] == "normal_details":
        user_state["data"]["info"] = message
        save_to_sheet([message])
        user_state["step"] = None
        return "📅 Your appointment is booked! Our team will visit at the chosen time."

    return "⚠️ Please follow instructions."

# -----------------------------
# Routes
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
# Render deployment fix
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

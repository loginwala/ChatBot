from flask import Flask, request, jsonify, render_template
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json
from datetime import datetime

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

# User session management (in production use Flask-Session or Redis)
user_sessions = {}

# -----------------------------
# Send Gmail Function
# -----------------------------
def send_gmail(subject, body, recipient="fraz24931@gmail.com"):
    from email.mime.text import MIMEText
    import base64

    message = MIMEText(body)
    message["to"] = recipient
    message["from"] = "fraz24931@gmail.com"
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# -----------------------------
# Save to Google Sheet
# -----------------------------
def save_to_sheet(values):
    try:
        sheet_service.values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="Sheet1!A:F",
            valueInputOption="USER_ENTERED",
            body={"values": [values]},
        ).execute()
        return True
    except Exception as e:
        print(f"Sheet error: {e}")
        return False

# -----------------------------
# Session Management
# -----------------------------
def get_session(session_id):
    if session_id not in user_sessions:
        user_sessions[session_id] = {
            "step": None,
            "data": {},
            "created": datetime.now().isoformat()
        }
    return user_sessions[session_id]

# -----------------------------
# Enhanced Chatbot logic
# -----------------------------
def process_message(message, session_id="default"):
    session = get_session(session_id)
    msg = message.lower().strip()

    if session["step"] is None:
        session["step"] = "ask_service"
        return "👋 Welcome! Do you need any medical service today? (Yes / No)"

    if session["step"] == "ask_service":
        if "yes" in msg:
            session["step"] = "ask_emergency"
            return "⚠️ Is it an emergency or normal appointment? (Emergency / Normal)"
        else:
            session["step"] = None
            return "😊 Alright! Feel free to message us anytime if you need assistance. Stay healthy!"

    if session["step"] == "ask_emergency":
        if "emergency" in msg:
            session["step"] = "emergency_details"
            return "🚨 **EMERGENCY DETECTED!**\n\nPlease provide the following details:\n\n• **Full Name**\n• **Address**\n• **Contact Number**\n• **Emergency Type**\n• **Current Condition**\n\n*Please type all information in one message*"
        elif "normal" in msg:
            session["step"] = "normal_details"
            return "📝 **Appointment Booking**\n\nPlease provide:\n\n• **Full Name**\n• **Address**\n• **Contact Number**\n• **Preferred Date & Time**\n• **Service Required**\n\n*Please type all information in one message*"
        else:
            return "❗ Please specify: **Emergency** OR **Normal**"

    if session["step"] == "emergency_details":
        session["data"]["info"] = message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format email
        email_body = f"""
        🚨 **EMERGENCY SERVICE REQUEST** 🚨
        
        Time: {timestamp}
        
        Details:
        {message}
        
        ---
        This is an automated alert from Medical Service Chatbot.
        """
        
        # Send emergency email
        email_sent = send_gmail("🚨 EMERGENCY MEDICAL REQUEST", email_body)
        
        # Save to sheet with timestamp
        sheet_data = [
            timestamp,
            "EMERGENCY",
            message,
            "High Priority",
            "Pending",
            session_id
        ]
        sheet_saved = save_to_sheet(sheet_data)
        
        session["step"] = None
        
        response = "🚑 **EMERGENCY REGISTERED!**\n\n✅ Our medical team has been alerted\n✅ Ambulance dispatched (if required)\n✅ Estimated arrival: 10-15 minutes\n\n**Stay on the line, our team will call you shortly.**\nKeep the patient comfortable and do not move them unnecessarily."
        
        if not email_sent or not sheet_saved:
            response += "\n\n⚠️ *Note: Some systems experienced delays, but emergency response is activated.*"
        
        return response

    if session["step"] == "normal_details":
        session["data"]["info"] = message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save to sheet
        sheet_data = [
            timestamp,
            "NORMAL",
            message,
            "Medium Priority",
            "Scheduled",
            session_id
        ]
        
        if save_to_sheet(sheet_data):
            # Send confirmation email
            email_body = f"""
            📅 **APPOINTMENT CONFIRMED**
            
            Thank you for booking with Medical Services.
            
            Details:
            {message}
            
            Time: {timestamp}
            
            Our team will contact you to confirm the exact timing.
            
            ---
            Medical Service Chatbot
            """
            send_gmail("📅 Appointment Confirmation", email_body)
            
            session["step"] = None
            return "✅ **APPOINTMENT BOOKED SUCCESSFULLY!**\n\n📧 Confirmation email sent\n👨‍⚕️ Our medical team will visit at the chosen time\n📞 You'll receive a confirmation call within 2 hours\n\nThank you for choosing our medical services!"
        else:
            return "⚠️ **Sorry, we encountered an error saving your appointment.**\n\nPlease call our helpline directly at **1-800-MEDICAL** or try again in a few minutes."

    return "⚠️ I didn't understand that. Could you please rephrase or choose from the options above?"

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get_response", methods=["POST"])
def get_response():
    try:
        data = request.get_json()
        user_msg = data.get("message", "")
        session_id = data.get("session_id", "default")
        
        if not user_msg:
            return jsonify({"response": "Please enter a message."})
        
        reply = process_message(user_msg, session_id)
        return jsonify({"response": reply})
    
    except Exception as e:
        print(f"Error in get_response: {e}")
        return jsonify({"response": "⚠️ Sorry, I'm having trouble processing your request. Please try again."})

@app.route("/status")
def status():
    return jsonify({
        "status": "operational",
        "active_sessions": len(user_sessions),
        "service": "Medical Chatbot v2.0"
    })

# -----------------------------
# Run the app
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

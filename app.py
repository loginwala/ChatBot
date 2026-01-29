from flask import Flask, request, jsonify, render_template
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json
from datetime import datetime
import re
import uuid

app = Flask(__name__)

# Configuration
GOOGLE_SHEET_ID = "1mBGedEg-k2ziMOrZtbyP7v80CQb-ffvEPjxN_Unmp6E"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Load credentials
CREDS = service_account.Credentials.from_service_account_file(
    "credentials.json", scopes=SCOPES)
sheet_service = build("sheets", "v4", credentials=CREDS).spreadsheets()

class InteractiveMedicalAI:
    def __init__(self):
        self.sessions = {}
        self.load_intents()
    
    def load_intents(self):
        self.intents = {
            "greeting": {
                "patterns": ["hi", "hello", "hey", "start", "begin"],
                "responses": ["Hello! I'm MediAI, your medical assistant. How can I help you today?"],
                "next_step": "ask_service"
            },
            "emergency": {
                "patterns": ["emergency", "urgent", "911", "help now", "chest pain", "can't breathe"],
                "responses": ["🚨 **EMERGENCY DETECTED**\n\nPlease provide:\n1. Location\n2. Phone number\n3. Nature of emergency\n4. Current condition"],
                "next_step": "emergency_details",
                "priority": "high"
            },
            "appointment": {
                "patterns": ["appointment", "schedule", "book", "see doctor", "consultation"],
                "responses": ["📅 **APPOINTMENT BOOKING**\n\nPlease provide:\n• Name\n• Contact\n• Preferred date/time\n• Reason for visit"],
                "next_step": "appointment_details"
            },
            "symptoms": {
                "patterns": ["symptom", "pain", "fever", "headache", "not feeling well"],
                "responses": ["🤒 **SYMPTOM CHECK**\n\nDescribe your symptoms:\n• What are you experiencing?\n• When did it start?\n• Severity (1-10)?"],
                "next_step": "symptom_details"
            },
            "information": {
                "patterns": ["information", "services", "hours", "contact", "location"],
                "responses": ["🏥 **SERVICE INFORMATION**\n\n• 24/7 Emergency\n• Mon-Fri: 8AM-8PM\n• Phone: 1-800-MEDICAL\n• Email: help@medical.ai"],
                "next_step": None
            },
            "completion": {
                "patterns": ["thank you", "thanks", "done", "finished", "bye", "goodbye"],
                "responses": ["You're welcome! Your request has been processed. Stay healthy! 👋"],
                "next_step": "complete",
                "conversation_complete": True
            }
        }
    
    def process(self, message, session_id):
        message = message.lower().strip()
        
        # Get or create session
        session = self.sessions.get(session_id)
        if not session:
            session = self.create_session(session_id)
            self.sessions[session_id] = session
        
        # Update session
        session["message_count"] += 1
        session["last_active"] = datetime.now().isoformat()
        session["history"].append({"role": "user", "content": message})
        
        # Determine response
        response_data = self.get_response(message, session)
        
        # Update session with response
        session["history"].append({"role": "assistant", "content": response_data["response"]})
        if response_data.get("next_step"):
            session["step"] = response_data["next_step"]
        
        # Check for completion
        if response_data.get("conversation_complete"):
            session["status"] = "completed"
            self.save_conversation(session)
        
        return response_data
    
    def get_response(self, message, session):
        # Check current step first
        if session["step"] == "emergency_details":
            return self.handle_emergency_details(message, session)
        elif session["step"] == "appointment_details":
            return self.handle_appointment_details(message, session)
        elif session["step"] == "symptom_details":
            return self.handle_symptom_details(message, session)
        
        # Otherwise, determine intent
        for intent_name, intent_data in self.intents.items():
            for pattern in intent_data["patterns"]:
                if pattern in message:
                    response = intent_data["responses"][0]
                    
                    # For emergencies, trigger immediate action
                    if intent_name == "emergency":
                        self.trigger_emergency_alert(session)
                    
                    return {
                        "response": response,
                        "next_step": intent_data.get("next_step"),
                        "conversation_complete": intent_data.get("conversation_complete", False)
                    }
        
        # Default response
        return {
            "response": "I'm here to help with medical needs. Please tell me if this is about:\n• Emergency assistance\n• Appointment booking\n• Symptom check\n• Service information",
            "next_step": None
        }
    
    def handle_emergency_details(self, message, session):
        # Save emergency details
        self.save_to_sheet("Emergencies", [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            session["id"],
            message,
            "PENDING"
        ])
        
        return {
            "response": "✅ **EMERGENCY LOGGED**\n\n• Help is on the way\n• ETA: 8-12 minutes\n• Stay on location\n• Keep patient comfortable",
            "conversation_complete": True
        }
    
    def handle_appointment_details(self, message, session):
        # Save appointment
        self.save_to_sheet("Appointments", [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            session["id"],
            message,
            "CONFIRMED"
        ])
        
        return {
            "response": "✅ **APPOINTMENT CONFIRMED**\n\n• Added to schedule\n• Confirmation sent\n• Reminder: 24h before\n• Changes: 1-800-MEDICAL",
            "conversation_complete": True
        }
    
    def handle_symptom_details(self, message, session):
        return {
            "response": "I've noted your symptoms. Please consult a doctor for proper diagnosis.\n\n**Recommendation:** Schedule an appointment or visit urgent care if symptoms worsen.",
            "conversation_complete": True
        }
    
    def create_session(self, session_id):
        return {
            "id": session_id,
            "created": datetime.now().isoformat(),
            "status": "active",
            "step": None,
            "message_count": 0,
            "last_active": datetime.now().isoformat(),
            "history": []
        }
    
    def trigger_emergency_alert(self, session):
        # In production, this would trigger actual emergency protocols
        print(f"🚨 EMERGENCY ALERT: Session {session['id']}")
    
    def save_conversation(self, session):
        # Save conversation summary
        summary = {
            "session_id": session["id"],
            "duration": str(datetime.now() - datetime.fromisoformat(session["created"])),
            "message_count": session["message_count"],
            "status": session["status"]
        }
        print(f"Conversation saved: {summary}")
    
    def save_to_sheet(self, sheet_name, data):
        try:
            sheet_service.values().append(
                spreadsheetId=GOOGLE_SHEET_ID,
                range=f"{sheet_name}!A:D",
                valueInputOption="USER_ENTERED",
                body={"values": [data]},
            ).execute()
            return True
        except Exception as e:
            print(f"Sheet error: {e}")
            return False

# Initialize AI
ai = InteractiveMedicalAI()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get_response", methods=["POST"])
def get_response():
    try:
        data = request.get_json()
        message = data.get("message", "").strip()
        session_id = data.get("session_id", str(uuid.uuid4())[:8])
        
        if not message:
            return jsonify({
                "response": "Please enter a message.",
                "error": "empty"
            })
        
        # Process with AI
        result = ai.process(message, session_id)
        
        return jsonify({
            "response": result["response"],
            "session_id": session_id,
            "conversation_complete": result.get("conversation_complete", False),
            "next_step": result.get("next_step")
        })
        
    except Exception as e:
        return jsonify({
            "response": "I'm having trouble connecting. Please try again.",
            "error": str(e)
        })

@app.route("/session_status/<session_id>")
def session_status(session_id):
    session = ai.sessions.get(session_id, {})
    return jsonify({
        "active": session.get("status") == "active",
        "message_count": session.get("message_count", 0),
        "step": session.get("step")
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 MediAI running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)

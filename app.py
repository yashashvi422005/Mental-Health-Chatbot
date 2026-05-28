import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from model import detect_crisis, detect_emotion, detect_intent
from response_generator import generate_response

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "wellness_data.json"
MAX_HISTORY = 20

COPING_TOOLS = [
    {
        "slug": "breathing-reset",
        "title": "Breathing Reset",
        "duration": "2 minutes",
        "description": "Slow the pace with a 4-4-6 breathing rhythm.",
        "steps": [
            "Inhale through your nose for 4 seconds.",
            "Hold gently for 4 seconds.",
            "Exhale slowly for 6 seconds.",
            "Repeat for five rounds.",
        ],
    },
    {
        "slug": "grounding-5-4-3-2-1",
        "title": "5-4-3-2-1 Grounding",
        "duration": "3 minutes",
        "description": "Use your senses to reconnect with the present moment.",
        "steps": [
            "Notice 5 things you can see.",
            "Notice 4 things you can feel.",
            "Notice 3 things you can hear.",
            "Notice 2 things you can smell.",
            "Notice 1 thing you can taste.",
        ],
    },
    {
        "slug": "journal-prompt",
        "title": "Gentle Journal Prompt",
        "duration": "5 minutes",
        "description": "Write without pressure using one guided reflection.",
        "steps": [
            "Name the feeling that has been following you today.",
            "Write what may have triggered it.",
            "Write one thing you need more of right now.",
            "End with one kind sentence to yourself.",
        ],
    },
]

CRISIS_RESOURCES = [
    "If you are in immediate danger, call your local emergency number right now.",
    "If you are in the U.S. or Canada, call or text 988 for immediate crisis support.",
    "Reach out to a trusted person and avoid being alone while you get help.",
]


def ensure_storage():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        save_data({"moods": [], "journals": []})


def load_data():
    ensure_storage()
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_data(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def timestamp_now():
    return datetime.now().isoformat(timespec="seconds")


def summarize_mood(history):
    if len(history) < 5:
        return None

    counts = Counter(history)
    dominant_emotion = counts.most_common(1)[0][0]
    labels = {
        "anger": "frustrated",
        "sadness": "low",
        "anxiety": "anxious",
        "positive": "more positive",
        "neutral": "steady",
    }
    return f"You've seemed mostly {labels.get(dominant_emotion, dominant_emotion)} in this chat."


def compute_streak(moods):
    unique_days = sorted({entry["date"] for entry in moods if entry.get("date")}, reverse=True)
    if not unique_days:
        return 0

    streak = 1
    previous = datetime.fromisoformat(unique_days[0]).date()
    for value in unique_days[1:]:
        current = datetime.fromisoformat(value).date()
        if (previous - current).days == 1:
            streak += 1
            previous = current
            continue
        break
    return streak


def format_mood_label(mood):
    labels = {
        "sadness": "Low",
        "anxiety": "Anxious",
        "anger": "Frustrated",
        "positive": "Positive",
        "neutral": "Steady",
    }
    return labels.get(mood, mood.title())


def build_dashboard_payload():
    data = load_data()
    moods = data.get("moods", [])
    journals = data.get("journals", [])
    recent_moods = moods[-7:]
    mood_counts = Counter(entry["mood"] for entry in moods if entry.get("mood"))
    dominant_mood = mood_counts.most_common(1)[0][0] if mood_counts else None
    latest_mood = moods[-1] if moods else None
    latest_journal = journals[-1] if journals else None

    return {
        "stats": {
            "total_check_ins": len(moods),
            "journal_entries": len(journals),
            "streak_days": compute_streak(moods),
            "dominant_mood": format_mood_label(dominant_mood) if dominant_mood else "No pattern yet",
        },
        "latest_mood": latest_mood,
        "latest_journal": latest_journal,
        "recent_moods": recent_moods,
        "mood_breakdown": [
            {"mood": format_mood_label(mood), "count": count}
            for mood, count in mood_counts.most_common()
        ],
        "journals": journals[-3:][::-1],
        "tools": COPING_TOOLS,
    }


def build_insights_payload():
    data = load_data()
    moods = data.get("moods", [])
    journals = data.get("journals", [])
    mood_counts = Counter(entry["mood"] for entry in moods if entry.get("mood"))
    dominant_mood = mood_counts.most_common(1)[0][0] if mood_counts else None

    summary = "Start logging a few daily check-ins to unlock more meaningful insight."
    if dominant_mood == "anxiety":
        summary = "Your recent check-ins lean anxious. Gentle routines and grounding tools may help."
    elif dominant_mood == "sadness":
        summary = "Your recent check-ins lean low. Journaling and trusted support may be helpful right now."
    elif dominant_mood == "anger":
        summary = "Your recent check-ins lean frustrated. Short decompression breaks may help release pressure."
    elif dominant_mood == "positive":
        summary = "Your recent check-ins lean positive. Notice what has been supporting that shift."
    elif dominant_mood == "neutral":
        summary = "Your recent check-ins look fairly steady. Keep noticing what helps you feel grounded."

    journal_tags = Counter(entry.get("emotion", "neutral") for entry in journals if entry.get("emotion"))
    return {
        "dominant_mood": format_mood_label(dominant_mood) if dominant_mood else "No pattern yet",
        "mood_breakdown": [
            {"mood": format_mood_label(mood), "count": count}
            for mood, count in mood_counts.most_common()
        ],
        "journal_breakdown": [
            {"emotion": format_mood_label(emotion), "count": count}
            for emotion, count in journal_tags.most_common()
        ],
        "summary": summary,
        "recent_notes": journals[-5:][::-1],
    }


def sanitize_history(items):
    safe_history = []
    for item in (items or [])[-3:]:
        if isinstance(item, dict):
            safe_history.append(
                {
                    "user": str(item.get("user", "")),
                    "bot": str(item.get("bot", "")),
                }
            )
    return safe_history


@app.route("/")
def dashboard():
    return render_template("dashboard.html", page="dashboard")


@app.route("/chat")
def chat_page():
    return render_template("chat.html", page="chat")


@app.route("/tracker")
def tracker_page():
    return render_template("tracker.html", page="tracker")


@app.route("/journal")
def journal_page():
    return render_template("journal.html", page="journal")


@app.route("/insights")
def insights_page():
    return render_template("insights.html", page="insights")


@app.route("/support")
def support_page():
    return render_template("support.html", page="support", crisis_resources=CRISIS_RESOURCES)


@app.route("/api/dashboard")
def dashboard_api():
    return jsonify(build_dashboard_payload())


@app.route("/api/insights")
def insights_api():
    return jsonify(build_insights_payload())


@app.route("/api/tools")
def tools_api():
    return jsonify({"tools": COPING_TOOLS, "crisis_resources": CRISIS_RESOURCES})


@app.route("/api/moods", methods=["GET", "POST"])
def moods_api():
    data = load_data()

    if request.method == "GET":
        return jsonify({"entries": data.get("moods", [])[::-1]})

    payload = request.get_json(silent=True) or {}
    mood = (payload.get("mood") or "").strip().lower()
    note = (payload.get("note") or "").strip()

    if mood not in {"sadness", "anxiety", "anger", "positive", "neutral"}:
        return jsonify({"error": "Please choose a valid mood."}), 400

    entry = {
        "id": timestamp_now(),
        "mood": mood,
        "note": note,
        "created_at": timestamp_now(),
        "date": datetime.now().date().isoformat(),
    }
    data.setdefault("moods", []).append(entry)
    data["moods"] = data["moods"][-60:]
    save_data(data)
    return jsonify({"entry": entry, "dashboard": build_dashboard_payload()}), 201


@app.route("/api/journals", methods=["GET", "POST"])
def journals_api():
    data = load_data()

    if request.method == "GET":
        return jsonify({"entries": data.get("journals", [])[::-1]})

    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()
    emotion = (payload.get("emotion") or "neutral").strip().lower()

    if not title or not content:
        return jsonify({"error": "Please add both a title and journal entry."}), 400

    entry = {
        "id": timestamp_now(),
        "title": title,
        "content": content,
        "emotion": emotion if emotion else "neutral",
        "created_at": timestamp_now(),
    }
    data.setdefault("journals", []).append(entry)
    data["journals"] = data["journals"][-60:]
    save_data(data)
    return jsonify({"entry": entry, "insights": build_insights_payload()}), 201


@app.route("/api/chat", methods=["POST"])
def chat_api():
    payload = request.get_json(silent=True) or {}
    user_message = (payload.get("message") or "").strip()
    conversation_history = sanitize_history(payload.get("conversation_history"))
    emotion_history = [str(item) for item in (payload.get("emotion_history") or [])[-19:]]

    if not user_message:
        return jsonify({"error": "Please enter a message before sending."}), 400

    emotion, confidence = detect_emotion(user_message)
    intent = detect_intent(user_message)
    crisis = detect_crisis(user_message)

    response = generate_response(
        emotion=emotion,
        intent=intent,
        crisis=crisis,
        user_message=user_message,
        conversation_history=conversation_history,
    )

    updated_emotions = emotion_history + [emotion]
    return jsonify(
        {
            "response": response,
            "emotion": emotion,
            "intent": intent,
            "confidence": round(confidence, 3),
            "mood_summary": summarize_mood(updated_emotions),
            "emotion_history": updated_emotions[-MAX_HISTORY:],
            "crisis": crisis,
        }
    )


if __name__ == "__main__":
    ensure_storage()
    app.run(debug=True)

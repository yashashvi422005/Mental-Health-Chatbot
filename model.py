from transformers import pipeline


try:
    emotion_classifier = pipeline(
        "text-classification",
        model="SamLowe/roberta-base-go_emotions",
        top_k=1
    )
except Exception:
    emotion_classifier = None

try:
    intent_classifier = pipeline(
        "zero-shot-classification",
        model="MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
    )
except Exception:
    intent_classifier = None


def _contains_any(text, phrases):
    return any(phrase in text for phrase in phrases)


def map_emotion(emotion):
    anger_group = ["anger", "annoyance", "disapproval"]
    sadness_group = ["sadness", "grief", "disappointment"]
    anxiety_group = ["fear", "nervousness", "confusion"]
    positive_group = ["joy", "gratitude", "relief", "optimism", "admiration", "love"]

    if emotion in anger_group:
        return "anger"

    if emotion in sadness_group:
        return "sadness"

    if emotion in anxiety_group:
        return "anxiety"

    if emotion in positive_group:
        return "positive"

    return "neutral"


def detect_emotion(text):
    lowered = text.lower()

    anger_phrases = [
        "on my nerves",
        "getting on my nerves",
        "annoying",
        "so annoying",
        "frustrated",
        "pissed off",
        "mad at",
        "angry",
        "fed up",
    ]
    sadness_phrases = [
        "sad",
        "still sad",
        "need comfort",
        "some comfort",
        "feel alone",
        "feeling alone",
        "feel empty",
        "feeling low",
        "feel low",
        "i feel sad",
        "i am sad",
        "down today",
        "broke up",
        "break up",
        "heartbroken",
        "broken up",
    ]
    anxiety_phrases = [
        "stressed",
        "stress",
        "anxious",
        "worried",
        "panic",
        "overthinking",
        "overwhelmed",
        "nervous",
    ]
    positive_phrases = [
        "feeling great",
        "i feel great",
        "i'm happy",
        "i am happy",
        "good news",
        "excited",
        "grateful",
    ]

    if _contains_any(lowered, anger_phrases):
        return "anger", 0.95

    if _contains_any(lowered, sadness_phrases):
        return "sadness", 0.9

    if _contains_any(lowered, anxiety_phrases):
        return "anxiety", 0.9

    if _contains_any(lowered, positive_phrases):
        return "positive", 0.9

    if emotion_classifier is None:
        return "neutral", 0.5

    result = emotion_classifier(text)

    raw_emotion = result[0][0]["label"]
    confidence = result[0][0]["score"]

    emotion = map_emotion(raw_emotion)

    return emotion, confidence


def detect_intent(text):
    lowered = text.lower()

    if _contains_any(lowered, ["can we talk", "talk to me", "need advice", "what should i do"]):
        return "asking for advice"

    if _contains_any(lowered, ["on my nerves", "frustrated", "annoying", "fed up", "angry"]):
        return "expressing frustration"

    if _contains_any(lowered, ["some comfort", "need comfort", "feeling low", "i feel sad", "i am sad", "sad", "broke up", "break up", "heartbroken"]):
        return "expressing sadness"

    if _contains_any(lowered, ["stressed", "anxious", "worried", "overwhelmed", "panic"]):
        return "expressing anxiety"

    if _contains_any(lowered, ["happy", "great", "good news", "excited", "grateful"]):
        return "sharing something positive"

    if intent_classifier is None:
        return "general conversation"

    labels = [
        "greeting",
        "saying goodbye",
        "expressing frustration",
        "asking for advice",
        "expressing anger",
        "expressing sadness",
        "expressing anxiety",
        "sharing something positive",
        "general conversation"
    ]

    result = intent_classifier(text, labels)

    return result["labels"][0]


def detect_crisis(text):
    crisis_keywords = [
        "suicide",
        "kill myself",
        "killing myself",
        "end my life",
        "want to die",
        "no reason to live",
        "life is meaningless",
        "i don't want to live",
        "hurt myself",
        "harm myself",
        "self harm",
        "self-harm",
        "end it all",
        "better off dead",
        "can't go on",
        "overdose",
        "take my own life"
    ]

    text = text.lower()

    for word in crisis_keywords:
        if word in text:
            return True

    return False

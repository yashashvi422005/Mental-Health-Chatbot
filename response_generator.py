import random


def _contains_phrase(message, phrases):
    return any(phrase in message for phrase in phrases)


def _recent_topic(conversation_history):
    if not conversation_history:
        return None

    recent_user_message = conversation_history[-1].get("user", "").strip()
    if not recent_user_message:
        return None

    return recent_user_message[:90]


def _is_brief_support_request(message):
    support_requests = [
        "some comfort",
        "comfort",
        "can we talk",
        "talk to me",
        "i need help",
        "need help",
        "help me",
    ]
    return message in support_requests


def _is_explicit_advice_request(message):
    advice_phrases = [
        "what should i do",
        "what do i do",
        "need advice",
        "give me advice",
        "can you help me decide",
        "help me decide",
        "what would help",
        "what would you do",
        "can you help",
        "i need help",
        "need help",
    ]
    return _contains_phrase(message, advice_phrases)


def _is_negative_checkin(message):
    negative_messages = {
        "not good",
        "bad",
        "very bad",
        "not okay",
        "not fine",
        "not great",
        "rough",
        "rough day",
    }
    return message in negative_messages


def _is_closing_message(message):
    closing_messages = {
        "no",
        "nope",
        "nah",
        "not really",
        "nothing",
        "nothing else",
        "that's all",
        "that's it",
        "thats all",
        "thats it",
        "all good",
        "i'm okay",
        "im okay",
        "ok",
        "okay",
        "kk",
    }
    return message in closing_messages


def _last_bot_message(conversation_history):
    if not conversation_history:
        return ""
    return conversation_history[-1].get("bot", "")


def _is_generic_emotion_message(message):
    generic_messages = {
        "sad",
        "still sad",
        "upset",
        "angry",
        "still angry",
        "anxious",
        "still anxious",
        "stressed",
        "still stressed",
        "happy",
        "still happy",
        "fine",
        "okay",
        "ok",
    }
    return message in generic_messages


def _is_question(text):
    return "?" in text


def _choose_non_repeating(options, previous_message):
    for option in options:
        if option != previous_message:
            return option
    return options[0]


def _is_positive_followup(previous_bot_message):
    positive_followups = [
        "what made this feel meaningful for you",
        "tell me more about it",
        "what stood out the most",
    ]
    lowered = previous_bot_message.lower()
    return any(phrase in lowered for phrase in positive_followups)


def generate_response(emotion, intent, crisis, user_message, conversation_history=None):
    conversation_history = conversation_history or []
    message = user_message.lower().strip()

    greetings = {"hi", "hello", "hey", "hii", "heyy", "yo"}
    farewells = ["bye", "goodbye", "see you", "ok bye", "bye bye", "take care"]
    thanks = ["thanks", "thank you", "thx"]
    recent_topic = _recent_topic(conversation_history)
    previous_bot_message = _last_bot_message(conversation_history)

    words = message.split()

    if crisis:
        return (
            "I'm really sorry you're carrying this right now. You deserve immediate support. "
            "You should call 9152987821 for help. "
            "If you're in immediate danger, call emergency services now. "
            "If you can, please reach out to a trusted person and stay with them while you get help."
        )

    if len(words) <= 3 and any(greet in words for greet in greetings):
        return _choose_non_repeating(
            [
                "hey :) what's up?",
                "hey, i'm here. what's going on?",
                "hi :) how are you doing?",
            ],
            previous_bot_message,
        )

    if _contains_phrase(message, farewells) or intent == "saying goodbye":
        return _choose_non_repeating(
            [
                "take care, okay? i'm here if you need me later.",
                "bye for now. hope things feel a little lighter soon.",
                "okay, take care of yourself.",
            ],
            previous_bot_message,
        )

    if _contains_phrase(message, thanks):
        return _choose_non_repeating(
            [
                "anytime :)",
                "of course, i'm here.",
                "glad i could help a little.",
            ],
            previous_bot_message,
        )

    if _is_brief_support_request(message):
        return _choose_non_repeating(
            [
                "Of course. I'm here with you. What feels hardest right now?",
                "We can talk. What's weighing on you the most at the moment?",
                "I'm here to listen. Do you want to start with what's been bothering you?",
            ],
            previous_bot_message,
        )

    if _is_negative_checkin(message):
        return _choose_non_repeating(
            [
                "ahh that sucks... what happened?",
                "ugh, i'm sorry. want to tell me what happened?",
                "damn, okay... what's going on?",
            ],
            previous_bot_message,
        )

    if _is_closing_message(message):
        if _is_question(previous_bot_message):
            return _choose_non_repeating(
                [
                    "that's okay. take care, alright?",
                    "no worries. we can leave it here for now.",
                    "alright. i'm here if you want to talk later.",
                ],
                previous_bot_message,
            )
        return _choose_non_repeating(
            [
                "take care. i'm here if you want to talk later.",
                "alright, take it easy.",
                "okay. be kind to yourself, yeah?",
            ],
            previous_bot_message,
        )

    if emotion == "sadness":
        return _choose_non_repeating(
            [
                "yeah, that sounds heavy... what happened?",
                "i'm sorry, that really sucks. want to talk about it?",
                "aw, that's rough... what’s been going on?",
            ],
            previous_bot_message,
        )

    if emotion == "anger":
        return _choose_non_repeating(
            [
                "yeah, that sounds really frustrating... what happened?",
                "ugh, i'd be annoyed too. what set it off?",
                "that sounds exhausting... what happened?",
            ],
            previous_bot_message,
        )

    if emotion == "anxiety":
        return _choose_non_repeating(
            [
                "yeah, that feeling can get heavy... want to talk about what's stressing you?",
                "that sounds like a lot... what's stressing you the most?",
                "i get that... what's making it feel so intense right now?",
            ],
            previous_bot_message,
        )

    if emotion == "positive" or intent == "sharing something positive":
        return _choose_non_repeating(
            [
                "aww, that's nice :) what made you feel that way?",
                "that's really good to hear. what happened?",
                "okayyy, i love that. what made it good?",
            ],
            previous_bot_message,
        )

    if recent_topic and len(words) <= 6 and _is_positive_followup(previous_bot_message) and not _is_explicit_advice_request(message):
        return _choose_non_repeating(
            [
                "That sounds lovely. It seems like that added to the good feeling.",
                "That makes sense. Little moments like that can really lift the mood.",
                "That sounds nice. It's good when something simple adds a bit of joy to the day.",
            ],
            previous_bot_message,
        )

    if intent == "asking for advice" and _is_explicit_advice_request(message):
        if recent_topic:
            return "we can figure it out together. what's the hardest part right now?"
        return "we can figure it out together. what would help most right now?"

    return _choose_non_repeating(
        [
            "i'm here. want to tell me a little more?",
            "yeah, talk to me. what's going on?",
            "i'm listening... what happened?",
        ],
        previous_bot_message,
    )

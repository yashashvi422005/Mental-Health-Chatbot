let conversationHistory = [];
let emotionHistory = [];
let selectedMood = "neutral";

document.addEventListener("DOMContentLoaded", () => {
    const page = document.body.dataset.page;

    if (page === "dashboard") {
        loadDashboard();
    }

    if (page === "chat") {
        setupChatPage();
    }

    if (page === "tracker") {
        setupMoodTracker();
    }

    if (page === "journal") {
        setupJournalPage();
    }

    if (page === "insights") {
        loadInsights();
    }

    if (page === "support") {
        loadTools();
    }
});

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Something went wrong.");
    }

    return data;
}

function createCard(title, body, meta = "") {
    return `
        <article class="card">
            <p class="card-kicker">${meta}</p>
            <h3>${title}</h3>
            <p>${body}</p>
        </article>
    `;
}

async function loadDashboard() {
    const data = await fetchJson("/api/dashboard");
    const stats = document.getElementById("dashboard-stats");
    const panels = document.getElementById("dashboard-panels");

    stats.innerHTML = `
        <article class="stat-card">
            <p class="stat-label">Total Check-ins</p>
            <p class="stat-value">${data.stats.total_check_ins}</p>
        </article>
        <article class="stat-card">
            <p class="stat-label">Journal Entries</p>
            <p class="stat-value">${data.stats.journal_entries}</p>
        </article>
        <article class="stat-card">
            <p class="stat-label">Current Streak</p>
            <p class="stat-value">${data.stats.streak_days} day${data.stats.streak_days === 1 ? "" : "s"}</p>
        </article>
        <article class="stat-card">
            <p class="stat-label">Dominant Mood</p>
            <p class="stat-value">${data.stats.dominant_mood}</p>
        </article>
    `;

    const latestMood = data.latest_mood
        ? `<div class="panel">
            <h3>Latest check-in</h3>
            <p class="lead-copy">${formatMood(data.latest_mood.mood)}</p>
            <p class="muted">${data.latest_mood.note || "No note added."}</p>
        </div>`
        : `<div class="panel"><h3>Latest check-in</h3><p class="muted">No mood logged yet. Start with a quick check-in on the tracker page.</p></div>`;

    const latestJournal = data.latest_journal
        ? `<div class="panel">
            <h3>Latest journal</h3>
            <p class="lead-copy">${data.latest_journal.title}</p>
            <p class="muted">${truncateText(data.latest_journal.content, 140)}</p>
        </div>`
        : `<div class="panel"><h3>Latest journal</h3><p class="muted">No journal entries yet. Write a quick reflection to start building insight.</p></div>`;

    const breakdown = data.mood_breakdown.length
        ? data.mood_breakdown.map(item => `<div class="bar-row"><span>${item.mood}</span><strong>${item.count}</strong></div>`).join("")
        : `<p class="muted">Your mood pattern will appear here after a few check-ins.</p>`;

    const tools = data.tools.map(tool => createCard(tool.title, tool.description, tool.duration)).join("");

    panels.innerHTML = `
        ${latestMood}
        ${latestJournal}
        <div class="panel">
            <h3>Mood breakdown</h3>
            <div class="bar-list">${breakdown}</div>
        </div>
        <div class="panel">
            <h3>Quick tools</h3>
            <div class="card-grid">${tools}</div>
        </div>
    `;
}

function setupChatPage() {
    const input = document.getElementById("message");
    input.addEventListener("keypress", (event) => {
        if (event.key === "Enter") {
            sendMessage();
        }
    });

    appendMessage("bot", "Welcome in. You can vent, reflect, or ask for calm practical support.");
}

async function sendMessage() {
    const input = document.getElementById("message");
    const message = input.value.trim();
    const chatbox = document.getElementById("chatbox");
    const sendButton = document.getElementById("send-button");
    const moodSummary = document.getElementById("mood-summary");

    if (!message) {
        return;
    }

    appendMessage("user", message);
    input.value = "";
    chatbox.scrollTop = chatbox.scrollHeight;

    const typing = document.createElement("div");
    typing.className = "message bot";
    typing.id = "typing";
    typing.textContent = "Listening...";
    chatbox.appendChild(typing);
    sendButton.disabled = true;

    try {
        const data = await fetchJson("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                message: message,
                conversation_history: conversationHistory,
                emotion_history: emotionHistory,
            }),
        });

        typing.remove();
        appendMessage("bot", data.response);

        conversationHistory.push({ user: message, bot: data.response });
        conversationHistory = conversationHistory.slice(-20);
        emotionHistory = Array.isArray(data.emotion_history) ? data.emotion_history : emotionHistory;

        if (data.mood_summary) {
            moodSummary.hidden = false;
            moodSummary.textContent = data.mood_summary;
        }
    } catch (error) {
        typing.remove();
        appendMessage("bot", error.message || "I'm having trouble connecting right now.");
    } finally {
        sendButton.disabled = false;
        input.focus();
        chatbox.scrollTop = chatbox.scrollHeight;
    }
}

function appendMessage(role, text) {
    const chatbox = document.getElementById("chatbox");
    const messageNode = document.createElement("div");
    messageNode.className = `message ${role}`;
    messageNode.textContent = text;
    chatbox.appendChild(messageNode);
}

function setupMoodTracker() {
    const moodButtons = document.querySelectorAll(".mood-option");
    const saveButton = document.getElementById("save-mood-button");

    moodButtons.forEach((button) => {
        button.addEventListener("click", () => {
            selectedMood = button.dataset.mood;
            moodButtons.forEach((item) => item.classList.remove("selected"));
            button.classList.add("selected");
        });
    });

    document.querySelector('.mood-option[data-mood="neutral"]').classList.add("selected");
    saveButton.addEventListener("click", saveMoodEntry);
    loadMoodEntries();
}

async function saveMoodEntry() {
    const note = document.getElementById("mood-note").value.trim();
    const feedback = document.getElementById("mood-feedback");

    try {
        await fetchJson("/api/moods", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ mood: selectedMood, note: note }),
        });

        document.getElementById("mood-note").value = "";
        feedback.textContent = "Mood saved. Your dashboard and insights are updated.";
        loadMoodEntries();
    } catch (error) {
        feedback.textContent = error.message;
    }
}

async function loadMoodEntries() {
    const data = await fetchJson("/api/moods");
    const list = document.getElementById("mood-list");

    if (!data.entries.length) {
        list.innerHTML = `<p class="muted">No mood entries yet. Add your first daily check-in.</p>`;
        return;
    }

    list.innerHTML = data.entries.map((entry) => `
        <article class="stack-item">
            <div class="stack-head">
                <strong>${formatMood(entry.mood)}</strong>
                <span>${formatDate(entry.created_at)}</span>
            </div>
            <p>${entry.note || "No note added."}</p>
        </article>
    `).join("");
}

function setupJournalPage() {
    document.getElementById("save-journal-button").addEventListener("click", saveJournalEntry);
    loadJournalEntries();
}

async function saveJournalEntry() {
    const title = document.getElementById("journal-title").value.trim();
    const emotion = document.getElementById("journal-emotion").value;
    const content = document.getElementById("journal-content").value.trim();
    const feedback = document.getElementById("journal-feedback");

    try {
        await fetchJson("/api/journals", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ title, emotion, content }),
        });

        document.getElementById("journal-title").value = "";
        document.getElementById("journal-content").value = "";
        feedback.textContent = "Journal entry saved.";
        loadJournalEntries();
    } catch (error) {
        feedback.textContent = error.message;
    }
}

async function loadJournalEntries() {
    const data = await fetchJson("/api/journals");
    const list = document.getElementById("journal-list");

    if (!data.entries.length) {
        list.innerHTML = `<p class="muted">No journal entries yet. Start with one honest reflection.</p>`;
        return;
    }

    list.innerHTML = data.entries.map((entry) => `
        <article class="stack-item">
            <div class="stack-head">
                <strong>${entry.title}</strong>
                <span>${formatDate(entry.created_at)}</span>
            </div>
            <p class="pill">${formatMood(entry.emotion)}</p>
            <p>${truncateText(entry.content, 180)}</p>
        </article>
    `).join("");
}

async function loadInsights() {
    const data = await fetchJson("/api/insights");
    document.getElementById("insights-summary").textContent = data.summary;
    document.getElementById("insights-stats").innerHTML = `
        <div class="mini-stat">
            <span>Dominant mood</span>
            <strong>${data.dominant_mood}</strong>
        </div>
        <div class="mini-stat">
            <span>Journal themes</span>
            <strong>${data.journal_breakdown.length}</strong>
        </div>
    `;

    renderBarList("insights-breakdown", data.mood_breakdown, "mood");
    renderBarList("journal-breakdown", data.journal_breakdown, "emotion");

    const notes = document.getElementById("insights-notes");
    if (!data.recent_notes.length) {
        notes.innerHTML = `<p class="muted">Your recent reflections will appear here once you add a few journal entries.</p>`;
        return;
    }

    notes.innerHTML = data.recent_notes.map((entry) => `
        <article class="stack-item">
            <div class="stack-head">
                <strong>${entry.title}</strong>
                <span>${formatDate(entry.created_at)}</span>
            </div>
            <p>${truncateText(entry.content, 160)}</p>
        </article>
    `).join("");
}

async function loadTools() {
    const data = await fetchJson("/api/tools");
    const grid = document.getElementById("tools-grid");

    grid.innerHTML = data.tools.map((tool) => `
        <article class="panel">
            <p class="card-kicker">${tool.duration}</p>
            <h3>${tool.title}</h3>
            <p>${tool.description}</p>
            <ol class="steps">
                ${tool.steps.map((step) => `<li>${step}</li>`).join("")}
            </ol>
        </article>
    `).join("");
}

function renderBarList(targetId, items, keyName) {
    const target = document.getElementById(targetId);
    if (!items.length) {
        target.innerHTML = `<p class="muted">Not enough data yet.</p>`;
        return;
    }

    const maxValue = Math.max(...items.map((item) => item.count), 1);
    target.innerHTML = items.map((item) => `
        <div class="bar-item">
            <div class="bar-meta">
                <span>${item[keyName]}</span>
                <strong>${item.count}</strong>
            </div>
            <div class="bar-track">
                <div class="bar-fill" style="width:${(item.count / maxValue) * 100}%"></div>
            </div>
        </div>
    `).join("");
}

function formatMood(mood) {
    const labels = {
        positive: "Positive",
        neutral: "Steady",
        anxiety: "Anxious",
        sadness: "Low",
        anger: "Frustrated",
    };
    return labels[mood] || mood;
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) {
        return text;
    }

    return `${text.slice(0, maxLength).trim()}...`;
}

function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleString();
}

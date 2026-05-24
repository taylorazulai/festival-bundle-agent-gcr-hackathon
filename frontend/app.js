const chatMessages = document.getElementById("chat-messages");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const errorBanner = document.getElementById("error-banner");
const errorText = document.getElementById("error-text");
const retryBtn = document.getElementById("retry-btn");

let lastMessage = "";
let loadingEl = null;

function marginClass(percent) {
  if (percent > 50) return "margin-excellent";
  if (percent >= 30) return "margin-good";
  if (percent >= 15) return "margin-tight";
  return "margin-unprofitable";
}

function categoryEmoji(category) {
  const map = {
    Drinks: "🥤",
    Food: "🌮",
    Merchandise: "👕",
    Accessories: "✨",
  };
  return map[category] || "🎁";
}

function renderBundleCards(bundles) {
  if (!bundles || bundles.length === 0) return "";

  const cards = bundles
    .map((b) => {
      const savings = (b.retail_price - b.bundle_price).toFixed(2);
      const items = (b.items || [])
        .map((name) => `<span>${name}</span>`)
        .join(" · ");
      return `
        <div class="bundle-card">
          <h4>${escapeHtml(b.name)}</h4>
          <div class="bundle-items">${items}</div>
          <div class="price-row">
            Retail: $${b.retail_price.toFixed(2)} → Bundle: $${b.bundle_price.toFixed(2)}
            (Save $${savings}!)
          </div>
          <span class="margin-badge ${marginClass(b.margin_percent)}">
            ${b.margin_percent.toFixed(1)}% margin
          </span>
        </div>
      `;
    })
    .join("");

  return `<div class="bundle-cards">${cards}</div>`;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatMarkdownLite(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/### (.+)/g, "<h3>$1</h3>")
    .replace(/\n/g, "<br>");
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showError(message) {
  errorText.textContent = message;
  errorBanner.classList.remove("hidden");
}

function hideError() {
  errorBanner.classList.add("hidden");
}

function addMessage(role, content, bundles = []) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = formatMarkdownLite(content);

  if (bundles.length > 0) {
    bubble.innerHTML += renderBundleCards(bundles);
  }

  wrapper.appendChild(bubble);
  chatMessages.appendChild(wrapper);
  scrollToBottom();
}

function showLoading() {
  loadingEl = document.createElement("div");
  loadingEl.className = "message agent loading";
  loadingEl.innerHTML = `
    <div class="bubble">
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="dot"></span>
    </div>
  `;
  chatMessages.appendChild(loadingEl);
  scrollToBottom();
}

function hideLoading() {
  if (loadingEl) {
    loadingEl.remove();
    loadingEl = null;
  }
}

const CHAT_TIMEOUT_MS = 15000;

async function sendMessage(text) {
  const message = (text || messageInput.value).trim();
  if (!message) return;

  lastMessage = message;
  messageInput.value = "";
  hideError();
  sendBtn.disabled = true;

  addMessage("user", message);
  showLoading();

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS);

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
      signal: controller.signal,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }

    const data = await res.json();
    hideLoading();
    addMessage("agent", data.response || "No response.", data.bundles || []);
  } catch (err) {
    hideLoading();
    if (err.name === "AbortError") {
      showError(
        "The agent is taking too long. Here's a quick tip: Try asking for specific items like 'Bundle Lemonade and Kettle Corn'"
      );
    } else {
      showError(err.message || "Failed to reach the agent. Is the server running?");
    }
  } finally {
    clearTimeout(timeoutId);
    sendBtn.disabled = false;
    messageInput.focus();
  }
}

sendBtn.addEventListener("click", () => sendMessage());
messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

retryBtn.addEventListener("click", () => {
  if (lastMessage) sendMessage(lastMessage);
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const prompt = chip.dataset.prompt;
    messageInput.value = prompt;
    sendMessage(prompt);
  });
});

addMessage(
  "agent",
  "Welcome! Ask me about your festival inventory, overstocked items, bundle deals, pricing, or promo copy."
);

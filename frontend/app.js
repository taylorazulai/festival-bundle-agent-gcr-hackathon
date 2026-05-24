const chatMessages = document.getElementById("chat-messages");
const messageInput = document.getElementById("message-input");
const sendBtn = document.getElementById("send-btn");
const errorBanner = document.getElementById("error-banner");
const errorText = document.getElementById("error-text");
const retryBtn = document.getElementById("retry-btn");
const scrollBottomBtn = document.getElementById("scroll-bottom-btn");
const recentList = document.getElementById("recent-list");

const menuBtn = document.getElementById("menu-btn");
const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebar-overlay");

const pillMongo = document.getElementById("pill-mongo");
const pillGemini = document.getElementById("pill-gemini");
const footerDot = document.getElementById("footer-dot");
const footerStatusText = document.getElementById("footer-status-text");

let lastMessage = "";
let loadingEl = null;
let welcomeEl = null;
let isLoading = false;

const CHAT_TIMEOUT_MS = 15000;
const HEALTH_POLL_MS = 6000;

function nowTime() {
  try {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = String(text ?? "");
  return div.innerHTML;
}

function formatMarkdownLite(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/### (.+)/g, "<h3>$1</h3>")
    .replace(/\n/g, "<br>");
}

function marginClass(percent) {
  const p = Number(percent);
  if (Number.isNaN(p)) return "margin-good";
  if (p > 50) return "margin-excellent";
  if (p >= 30) return "margin-good";
  return p >= 15 ? "margin-tight" : "margin-unprofitable";
}

function categoryColor(category) {
  const map = {
    Drinks: "#0ea5e9",
    Food: "#f59e0b",
    Merchandise: "#e11d48",
    Accessories: "#8b5cf6",
  };
  return map[category] || "";
}

function categoryEmoji(category) {
  const map = { Drinks: "🥤", Food: "🌮", Merchandise: "👕", Accessories: "✨" };
  return map[category] || "🎁";
}

function isNearBottom(el, thresholdPx = 120) {
  return el.scrollHeight - el.scrollTop - el.clientHeight < thresholdPx;
}

function scrollToBottom(force = false) {
  const near = isNearBottom(chatMessages);
  if (force || near) chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setScrollBtnVisibility() {
  if (isNearBottom(chatMessages)) scrollBottomBtn.classList.add("hidden");
  else scrollBottomBtn.classList.remove("hidden");
}

function showError(message) {
  errorText.textContent = message;
  errorBanner.classList.remove("hidden");
}

function hideError() {
  errorBanner.classList.add("hidden");
}

function clearWelcome() {
  if (!welcomeEl) return;
  welcomeEl.remove();
  welcomeEl = null;
}

function renderWelcome() {
  clearWelcome();
  welcomeEl = document.createElement("div");
  welcomeEl.className = "welcome";
  welcomeEl.innerHTML = `
    <div class="welcome-hero">
      <div class="welcome-art" aria-hidden="true">🎪📦✨</div>
      <h2>Welcome back</h2>
      <p class="welcome-sub">Query inventory, generate bundles, and ship promo copy in seconds.</p>
    </div>
    <div class="feature-grid" role="group" aria-label="Quick actions">
      <div class="feature-card" data-prompt="Show overstocked items" tabindex="0" role="button">
        <div class="feature-card-icon" aria-hidden="true">📊</div>
        <h3>Query Inventory</h3>
        <p>Find what to move first.</p>
      </div>
      <div class="feature-card" data-prompt="Create bundles" tabindex="0" role="button">
        <div class="feature-card-icon" aria-hidden="true">🎯</div>
        <h3>Generate Bundles</h3>
        <p>Optimize price and margin.</p>
      </div>
      <div class="feature-card" data-prompt="Create promo copy for my best bundles" tabindex="0" role="button">
        <div class="feature-card-icon" aria-hidden="true">✍️</div>
        <h3>Create Promo Copy</h3>
        <p>Copy-paste ready captions.</p>
      </div>
    </div>
  `;
  chatMessages.appendChild(welcomeEl);

  welcomeEl.querySelectorAll(".feature-card").forEach((card) => {
    const handler = () => {
      const prompt = card.dataset.prompt;
      sendMessage(prompt);
    };

    card.addEventListener("click", handler);
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handler();
      }
    });
  });
}

function renderLoading() {
  if (loadingEl) return;
  loadingEl = document.createElement("div");
  loadingEl.className = "loading-state";
  loadingEl.innerHTML = `
    <div class="loading-orb" aria-hidden="true"></div>
    <div class="loading-text">Analyzing inventory…</div>
    <div class="skeleton-wrap" aria-hidden="true">
      <div class="skeleton-line w-80"></div>
      <div class="skeleton-line w-60"></div>
      <div class="skeleton-line w-40"></div>
    </div>
  `;
  chatMessages.appendChild(loadingEl);
  scrollToBottom(true);
}

function hideLoading() {
  if (!loadingEl) return;
  loadingEl.remove();
  loadingEl = null;
}

function renderUserMessage(text) {
  clearWelcome();

  const wrapper = document.createElement("div");
  wrapper.className = "message user";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = formatMarkdownLite(text);

  const time = document.createElement("div");
  time.className = "message-time";
  time.textContent = nowTime();

  wrapper.appendChild(bubble);
  wrapper.appendChild(time);
  chatMessages.appendChild(wrapper);
  scrollToBottom(true);
}

function renderBundleCard(bundle) {
  const name = escapeHtml(bundle?.name ?? "Bundle");
  const items = Array.isArray(bundle?.items) ? bundle.items : [];
  const retail = Number(bundle?.retail_price ?? 0);
  const price = Number(bundle?.bundle_price ?? 0);
  const margin = Number(bundle?.margin_percent ?? 0);
  const savings = retail && price ? Math.max(0, retail - price) : 0;

  // Backend doesn't currently return category; keep the hook for future compatibility.
  const category = bundle?.category || bundle?.bundle_category || "";
  const catLabel = category ? escapeHtml(category) : "";
  const catColor = category ? categoryColor(category) : "";
  const catEmoji = category ? categoryEmoji(category) : "🎪";

  const promo =
    bundle?.promo_copy ||
    bundle?.promo ||
    bundle?.promo_text ||
    bundle?.social_caption ||
    bundle?.tagline ||
    "";

  const el = document.createElement("div");
  el.className = "bundle-card";
  if (catColor) el.style.setProperty("--category-color", catColor);

  el.innerHTML = `
    <div class="bundle-card-inner">
      <div class="bundle-card-header">
        <div>
          <div class="bundle-card-title">${catEmoji} ${name}</div>
          ${catLabel ? `<div class="bundle-category">${catLabel}</div>` : ``}
        </div>
        <span class="margin-badge ${marginClass(margin)}">${Number.isFinite(margin) ? margin.toFixed(1) : "—"}% margin</span>
      </div>
      <ul class="bundle-items">
        ${items.map((it) => `<li>${escapeHtml(it)}</li>`).join("")}
      </ul>
      <div class="bundle-price-row">
        <span class="price-retail">$${Number.isFinite(retail) ? retail.toFixed(2) : "0.00"}</span>
        <span class="price-bundle">$${Number.isFinite(price) ? price.toFixed(2) : "0.00"}</span>
        ${savings ? `<span class="savings-badge">Save $${savings.toFixed(2)}</span>` : ``}
      </div>
      ${
        promo
          ? `
        <div class="promo-block">
          <div class="promo-label">Promo copy</div>
          <div class="promo-copy-wrap">
            <div class="promo-copy">${escapeHtml(String(promo))}</div>
            <button type="button" class="btn-copy" data-copy="${escapeHtml(String(promo))}">Copy</button>
          </div>
        </div>
      `
          : ``
      }
    </div>
  `;

  return el;
}

function updateRecentItemsFromBundles(bundles) {
  const names = new Set();
  bundles.forEach((b) => {
    (Array.isArray(b?.items) ? b.items : []).forEach((it) => names.add(it));
  });
  const list = Array.from(names).slice(0, 8);
  if (list.length === 0) return;

  recentList.innerHTML = "";
  list.forEach((n) => {
    const li = document.createElement("li");
    li.textContent = n;
    recentList.appendChild(li);
  });
}

function renderAgentMessage(text, bundles = []) {
  clearWelcome();

  const wrapper = document.createElement("div");
  wrapper.className = "message agent";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = formatMarkdownLite(text);

  if (Array.isArray(bundles) && bundles.length > 0) {
    const cardsWrap = document.createElement("div");
    cardsWrap.className = "bundle-cards";
    bundles.forEach((b) => cardsWrap.appendChild(renderBundleCard(b)));
    bubble.appendChild(cardsWrap);
    updateRecentItemsFromBundles(bundles);
  }

  const time = document.createElement("div");
  time.className = "message-time";
  time.textContent = nowTime();

  wrapper.appendChild(bubble);
  wrapper.appendChild(time);
  chatMessages.appendChild(wrapper);
  scrollToBottom(true);
}

function setSidebarOpen(isOpen) {
  sidebar.classList.toggle("is-open", isOpen);
  sidebarOverlay.hidden = !isOpen;
  menuBtn.setAttribute("aria-expanded", String(isOpen));
}

function closeSidebar() {
  setSidebarOpen(false);
}

function updateActiveNav(viewName) {
  document.querySelectorAll(".nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.view === viewName);
  });
}

function showDashboard() {
  chatMessages.innerHTML = "";
  welcomeEl = null;
  loadingEl = null;
  renderWelcome();
  updateActiveNav("dashboard");
  if (window.innerWidth < 768) closeSidebar();
}

function showChat() {
  updateActiveNav("chat");
  messageInput.focus();
  scrollToBottom(true);
  if (window.innerWidth < 768) closeSidebar();
}

function triggerQuery(queryText) {
  if (isLoading) return;

  if (welcomeEl || document.querySelector(".welcome")) {
    chatMessages.innerHTML = "";
    welcomeEl = null;
  }

  updateActiveNav("chat");
  sendMessage(queryText);

  if (window.innerWidth < 768) closeSidebar();
}

async function sendMessage(text) {
  const message = (text || messageInput.value).trim();
  if (!message || isLoading) return;

  isLoading = true;
  lastMessage = message;
  messageInput.value = "";
  hideError();
  sendBtn.disabled = true;
  setSidebarOpen(false);

  renderUserMessage(message);
  renderLoading();

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
    renderAgentMessage(data.response || "No response.", data.bundles || []);
  } catch (err) {
    hideLoading();
    if (err?.name === "AbortError") {
      showError(
        "The agent is taking too long. Try a narrower ask like “Create bundles for Lemonade and Kettle Corn”."
      );
    } else {
      showError(err?.message || "Failed to reach the agent. Is the server running?");
    }
  } finally {
    clearTimeout(timeoutId);
    isLoading = false;
    sendBtn.disabled = false;
    messageInput.focus();
  }
}

async function pollHealthOnce() {
  try {
    const res = await fetch("/health", { method: "GET" });
    if (!res.ok) throw new Error("health not ok");
    const data = await res.json();

    const mongoOk = data.database === "connected";
    const geminiOk = Boolean(data.gemini);

    pillMongo.classList.toggle("is-ok", mongoOk);
    pillMongo.classList.toggle("is-warn", !mongoOk);
    pillMongo.classList.remove("is-error");

    pillGemini.classList.toggle("is-ok", geminiOk);
    pillGemini.classList.toggle("is-warn", !geminiOk);
    pillGemini.classList.remove("is-error");

    footerDot.classList.toggle("is-ok", mongoOk && geminiOk);

    const pieces = [
      `MongoDB ${mongoOk ? "Connected" : "Initializing"}`,
      `Gemini ${geminiOk ? "Active" : "Config needed"}`,
      `MCP ${data.mcp === "connected" ? "Ready" : "Initializing"}`,
    ];
    footerStatusText.textContent = `Status: ${pieces.join(" • ")}`;
  } catch {
    pillMongo.classList.remove("is-ok", "is-warn");
    pillMongo.classList.add("is-error");
    pillGemini.classList.remove("is-ok", "is-warn");
    pillGemini.classList.add("is-error");
    footerDot.classList.remove("is-ok");
    footerStatusText.textContent =
      "Status: Server unreachable • Check that the backend is running";
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

scrollBottomBtn.addEventListener("click", () => scrollToBottom(true));
chatMessages.addEventListener("scroll", setScrollBtnVisibility);

chatMessages.addEventListener("click", async (e) => {
  const btn = e.target?.closest?.(".btn-copy");
  if (!btn) return;
  const text = btn.getAttribute("data-copy") || "";

  try {
    await navigator.clipboard.writeText(text);
    btn.classList.add("copied");
    const prev = btn.textContent;
    btn.textContent = "Copied";
    setTimeout(() => {
      btn.textContent = prev || "Copy";
      btn.classList.remove("copied");
    }, 1200);
  } catch {
    // Clipboard can be blocked by browser permissions; fail silently.
  }
});

menuBtn.addEventListener("click", () => {
  const open = sidebar.classList.contains("is-open");
  setSidebarOpen(!open);
});

sidebarOverlay.addEventListener("click", () => setSidebarOpen(false));

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", (e) => {
    e.preventDefault();
    const view = item.dataset.view;
    if (view === "dashboard") showDashboard();
    else if (view === "chat") showChat();
    else if (view === "inventory") triggerQuery("Show all inventory items");
    else if (view === "bundles") triggerQuery("What bundles can I create?");
  });
});

renderWelcome();
updateActiveNav("dashboard");
pollHealthOnce();
setInterval(pollHealthOnce, HEALTH_POLL_MS);
setScrollBtnVisibility();

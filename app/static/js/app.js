/*
  DocuMind AI - Phase 1 frontend script.

  This file ONLY handles UI behavior:
    - sidebar open/close (mobile)
    - theme switching + persistence
    - textarea auto-resize
    - showing a typed message in the chat area

  It does NOT call any AI/RAG backend - there isn't one yet.
*/

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initSidebar();
  initChatInput();
});

/* ---------------- Theme ---------------- */

function initTheme() {
  const root = document.documentElement;
  const savedTheme = localStorage.getItem("documind-theme") || "dark";
  applyTheme(savedTheme);

  const toggleBtn = document.getElementById("themeToggle");
  const mobileToggleBtn = document.getElementById("mobileThemeToggle");

  function handleToggle() {
    const current = root.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
    localStorage.setItem("documind-theme", next);
  }

  toggleBtn.addEventListener("click", handleToggle);
  mobileToggleBtn.addEventListener("click", handleToggle);
}

function applyTheme(theme) {
  const root = document.documentElement;
  root.setAttribute("data-theme", theme);

  const label = document.getElementById("themeToggleLabel");
  const icon = document.querySelector("#themeToggle i");
  const mobileIcon = document.querySelector("#mobileThemeToggle i");

  const isDark = theme === "dark";
  label.textContent = isDark ? "Dark mode" : "Light mode";
  icon.className = isDark ? "bi bi-moon-stars" : "bi bi-sun";
  mobileIcon.className = isDark ? "bi bi-moon-stars" : "bi bi-sun";
}

/* ---------------- Sidebar (mobile off-canvas) ---------------- */

function initSidebar() {
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  const openBtn = document.getElementById("menuToggle");
  const closeBtn = document.getElementById("sidebarClose");

  function openSidebar() {
    sidebar.classList.add("open");
    backdrop.classList.add("show");
  }

  function closeSidebar() {
    sidebar.classList.remove("open");
    backdrop.classList.remove("show");
  }

  openBtn.addEventListener("click", openSidebar);
  closeBtn.addEventListener("click", closeSidebar);
  backdrop.addEventListener("click", closeSidebar);

  // Close the drawer automatically when a nav item is picked on mobile
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      if (window.innerWidth <= 860) closeSidebar();
    });
  });
}

/* ---------------- Chat input + suggestion cards ---------------- */

function initChatInput() {
  const input = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const welcomeScreen = document.getElementById("welcomeScreen");
  const chatArea = document.getElementById("chatArea");
  const chatMessages = document.getElementById("chatMessages");

  // Auto-resize the textarea as the user types
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
  });

  // Clicking a suggestion card fills the input with that prompt
  document.querySelectorAll(".suggestion-card").forEach((card) => {
    card.addEventListener("click", () => {
      input.value = card.dataset.prompt;
      input.focus();
    });
  });

  function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    // First message: switch from the welcome screen to the chat view
    if (!chatArea.classList.contains("active")) {
      welcomeScreen.style.display = "none";
      chatArea.classList.add("active");
    }

    addMessage(text, "user");

    input.value = "";
    input.style.height = "auto";

    // NOTE: Phase 1 does not generate AI responses. A real reply will
    // be added here once the backend RAG pipeline exists in a later phase.
  }

  function addMessage(text, sender) {
    const wrapper = document.createElement("div");
    wrapper.className = `chat-message ${sender}`;

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.innerHTML = sender === "user"
      ? '<i class="bi bi-person"></i>'
      : '<i class="bi bi-stars"></i>';

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.textContent = text;

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    chatMessages.appendChild(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}
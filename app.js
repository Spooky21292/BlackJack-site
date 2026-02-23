const API_BASE = "https://PASTE_YOUR_RAILWAY_DOMAIN_HERE";

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const initData = tg?.initData || "";
const user = tg?.initDataUnsafe?.user || {};
const currentUserId = user.id || null;
const isApiBasePlaceholder = API_BASE.includes("PASTE_YOUR_RAILWAY_DOMAIN_HERE");
const normalizedApiBase = API_BASE.replace(/\/$/, "");

const greetingEl = document.getElementById("greeting");
const statusEl = document.getElementById("status");
const tabsEl = document.getElementById("tabs");
const tasksSection = document.getElementById("tasks-section");
const leaderboardSection = document.getElementById("leaderboard-section");
const tasksListEl = document.getElementById("tasks-list");
const leaderboardListEl = document.getElementById("leaderboard-list");
const listTitleEl = document.getElementById("list-title");
const taskForm = document.getElementById("task-form");

const tabTitles = {
  active: "Активные задачи",
  today: "Задачи на сегодня",
  completed: "Завершённые задачи",
};

let currentTab = "active";

greetingEl.textContent = `Привет, ${user.first_name || "друг"}`;

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.style.color = isError ? "#ef4444" : "#98a2b3";
}

function formatDate(ts) {
  return new Date(ts * 1000).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getSetupError() {
  if (isApiBasePlaceholder) {
    return "Укажите Railway URL в app.js (переменная API_BASE).";
  }

  if (!initData) {
    return "Откройте Mini App внутри Telegram (нужен X-TG-INITDATA).";
  }

  return "";
}

async function apiFetch(path, options = {}) {
  const setupError = getSetupError();
  if (setupError) {
    throw new Error(setupError);
  }

  const headers = {
    "Content-Type": "application/json",
    "X-TG-INITDATA": initData,
    ...(options.headers || {}),
  };

  let response;
  try {
    response = await fetch(`${normalizedApiBase}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error("Не удалось подключиться к backend. Проверьте API_BASE и CORS на сервере.");
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail || "Ошибка запроса";

    if (response.status === 401) {
      throw new Error("401: initData не прошли проверку. Откройте Mini App из Telegram и проверьте BOT_TOKEN.");
    }
    if (response.status === 403) {
      throw new Error("403: доступ запрещён. Проверьте настройки backend.");
    }
    if (response.status === 404) {
      throw new Error("404: endpoint не найден. Проверьте API_BASE и маршруты backend.");
    }

    throw new Error(`${response.status}: ${detail}`);
  }

  return response.json();
}

function renderTasks(tasks) {
  tasksListEl.innerHTML = "";

  if (!tasks.length) {
    tasksListEl.innerHTML = '<div class="task-item">Пока задач нет.</div>';
    return;
  }

  tasks.forEach((task) => {
    const item = document.createElement("div");
    item.className = "task-item";
    item.innerHTML = `
      <div class="task-top">
        <p class="task-title">${escapeHtml(task.title)}</p>
        <span class="task-deadline">${formatDate(task.deadline)}</span>
      </div>
      <p class="task-desc">${escapeHtml(task.description || "")}</p>
      <div class="actions">
        ${task.status === "active" ? `<button class="btn btn-primary" data-action="complete" data-id="${task.id}">Завершить</button>` : ""}
        <button class="btn btn-danger" data-action="delete" data-id="${task.id}">Удалить</button>
      </div>
    `;
    tasksListEl.appendChild(item);
  });
}

function renderLeaderboard(rows) {
  leaderboardListEl.innerHTML = "";

  if (!rows.length) {
    leaderboardListEl.innerHTML = '<div class="leader-item">Пока нет данных.</div>';
    return;
  }

  rows.forEach((row, index) => {
    const item = document.createElement("div");
    item.className = "leader-item";
    if (currentUserId && Number(row.user_id) === Number(currentUserId)) {
      item.classList.add("me");
    }
    const name = row.display_name || (row.username ? `@${row.username}` : `id:${row.user_id}`);
    item.innerHTML = `<strong>#${index + 1}</strong> ${name} — ${row.completed_count} задач`;
    leaderboardListEl.appendChild(item);
  });
}

async function loadTasks() {
  listTitleEl.textContent = tabTitles[currentTab];
  setStatus("Загрузка задач...");
  try {
    const tasks = await apiFetch(`/tasks?filter=${currentTab}`);
    tasks.sort((a, b) => a.deadline - b.deadline);
    renderTasks(tasks);
    setStatus("Готово");
  } catch (err) {
    setStatus(err.message, true);
  }
}

async function loadLeaderboard() {
  setStatus("Загрузка лидерборда...");
  try {
    const rows = await apiFetch("/leaderboard");
    renderLeaderboard(rows.slice(0, 10));
    setStatus("Готово");
  } catch (err) {
    setStatus(err.message, true);
  }
}

function switchTab(tab) {
  currentTab = tab;

  document.querySelectorAll(".tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });

  if (tab === "leaderboard") {
    tasksSection.classList.add("hidden");
    leaderboardSection.classList.remove("hidden");
    loadLeaderboard();
  } else {
    leaderboardSection.classList.add("hidden");
    tasksSection.classList.remove("hidden");
    loadTasks();
  }
}

function toUtcTimestamp(datetimeLocalValue) {
  const date = new Date(datetimeLocalValue);
  return Math.floor(date.getTime() / 1000);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

tabsEl.addEventListener("click", (event) => {
  const btn = event.target.closest(".tab");
  if (!btn) return;
  switchTab(btn.dataset.tab);
});

taskForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const title = document.getElementById("title").value.trim();
  const description = document.getElementById("description").value.trim();
  const deadlineRaw = document.getElementById("deadline").value;

  if (!title || !deadlineRaw) {
    setStatus("Заполните название и дедлайн", true);
    return;
  }

  const deadline = toUtcTimestamp(deadlineRaw);
  setStatus("Создание задачи...");

  try {
    await apiFetch("/tasks", {
      method: "POST",
      body: JSON.stringify({ title, description, deadline }),
    });
    taskForm.reset();
    await loadTasks();
  } catch (err) {
    setStatus(err.message, true);
  }
});

tasksListEl.addEventListener("click", async (event) => {
  const btn = event.target.closest("button[data-action]");
  if (!btn) return;

  const id = btn.dataset.id;
  const action = btn.dataset.action;

  try {
    if (action === "complete") {
      setStatus("Завершаем задачу...");
      await apiFetch(`/tasks/${id}/complete`, { method: "POST" });
      await loadTasks();
    }

    if (action === "delete") {
      setStatus("Удаляем задачу...");
      await apiFetch(`/tasks/${id}`, { method: "DELETE" });
      await loadTasks();
    }
  } catch (err) {
    setStatus(err.message, true);
  }
});

const setupError = getSetupError();
if (setupError) {
  setStatus(setupError, true);
}

switchTab("active");

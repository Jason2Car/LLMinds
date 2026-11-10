let sessionId = null;
let items = [];
let order = [];          // item ids, most important first
let ranking = "initial"; // which ranking the list is currently collecting

const $ = (id) => document.getElementById(id);
const names = {};

async function post(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, ...body }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

function show(section) {
  for (const id of ["consent-section", "rank-section", "chat-section", "confidence-section", "done-section"]) {
    $(id).hidden = id !== section;
  }
}

function renderList() {
  const list = $("rank-list");
  list.innerHTML = "";
  order.forEach((id, i) => {
    const li = document.createElement("li");
    li.draggable = true;
    li.dataset.index = i;
    li.innerHTML = `<strong>${i + 1}.</strong><span class="name">${names[id]}</span>
      <span class="arrows"><button data-d="-1">&uarr;</button> <button data-d="1">&darr;</button></span>`;
    li.querySelectorAll("button").forEach((b) =>
      b.addEventListener("click", () => move(i, i + Number(b.dataset.d))));
    li.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", i);
      li.classList.add("dragging");
    });
    li.addEventListener("dragend", () => li.classList.remove("dragging"));
    li.addEventListener("dragover", (e) => e.preventDefault());
    li.addEventListener("drop", (e) => {
      e.preventDefault();
      move(Number(e.dataTransfer.getData("text/plain")), i);
    });
    list.appendChild(li);
  });
}

function move(from, to) {
  if (to < 0 || to >= order.length || from === to) return;
  order.splice(to, 0, order.splice(from, 1)[0]);
  renderList();
}

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  $("chat-log").appendChild(div);
}

async function start() {
  const data = await post("/api/start", {});
  sessionId = data.session_id;
  items = data.items;
  items.forEach((it) => (names[it.id] = it.name));
  order = items.map((it) => it.id);
  $("scenario").textContent = data.scenario;
  setRemaining(data.max_messages);
  $("rank-title").textContent = "Your ranking";
  $("rank-submit").textContent = "Submit ranking";
  renderList();
  show("rank-section");
}

$("rank-submit").addEventListener("click", async () => {
  try {
    if (ranking === "initial") {
      const data = await post("/api/ranking", { ranking: order });
      addMessage("assistant", data.message);
      show("chat-section");
    } else {
      await post("/api/final", { ranking: order });
      show("confidence-section");
    }
  } catch (e) { alert(e.message); }
});

$("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = $("chat-input").value.trim();
  if (!text) return;
  $("chat-input").value = "";
  addMessage("user", text);
  const bubble = $("chat-log").lastChild;
  try {
    const data = await post("/api/message", { message: text });
    addMessage("assistant", data.message);
    setRemaining(data.remaining);
  } catch (err) {
    bubble.remove();  // the server didn't record it
    $("chat-input").value = text;
    alert(err.message);
  }
});

function setRemaining(n) {
  $("chat-remaining").textContent = n > 0
    ? `${n} message${n === 1 ? "" : "s"} left`
    : "Message limit reached. Please re-rank below.";
  $("chat-input").disabled = n <= 0;
  $("chat-form").querySelector("button").disabled = n <= 0;
}

$("chat-done").addEventListener("click", () => {
  ranking = "final";
  $("rank-title").textContent = "Final ranking: change anything you like";
  $("rank-submit").textContent = "Submit final ranking";
  show("rank-section");
});

for (let n = 1; n <= 7; n++) {
  const b = document.createElement("button");
  b.textContent = n;
  b.addEventListener("click", async () => {
    try {
      await post("/api/confidence", { confidence: n });
      show("done-section");
    } catch (e) { alert(e.message); }
  });
  $("scale").appendChild(b);
}

$("consent-check").addEventListener("change", (e) => {
  $("consent-start").disabled = !e.target.checked;
});

$("consent-start").addEventListener("click", async () => {
  $("consent-start").disabled = true;
  try {
    await start();
  } catch (e) {
    $("consent-error").textContent = e.message === "Failed to fetch"
      ? "Could not reach the server. Please try again later."
      : e.message;
    $("consent-start").disabled = false;
  }
});

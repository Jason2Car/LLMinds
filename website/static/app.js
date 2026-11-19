let sessionId = null;
let items = [];
let picked = [];         // chosen item ids, most important first
let topN = 3;            // how many items to pick (set by the server)
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
  const list = $("picked-list");
  list.innerHTML = "";
  for (let i = 0; i < topN; i++) {
    const li = document.createElement("li");
    const id = picked[i];
    if (id === undefined) {
      li.className = "empty";
      li.innerHTML = `<strong>${i + 1}.</strong><span class="name">Click an item below to add it</span>`;
    } else {
      li.innerHTML = `<strong>${i + 1}.</strong><span class="name">${names[id]}</span>
        <span class="arrows"><button data-d="-1" title="Move up">&uarr;</button>
        <button data-d="1" title="Move down">&darr;</button>
        <button data-remove title="Remove">&times;</button></span>`;
      li.querySelectorAll("button[data-d]").forEach((btn) =>
        btn.addEventListener("click", () => move(i, i + Number(btn.dataset.d))));
      li.querySelector("button[data-remove]").addEventListener("click", () => {
        picked.splice(i, 1);
        renderList();
      });
    }
    list.appendChild(li);
  }

  const pool = $("pool-list");
  pool.innerHTML = "";
  const full = picked.length >= topN;
  items.filter((it) => !picked.includes(it.id)).forEach((it) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.textContent = it.name;
    btn.disabled = full;
    btn.addEventListener("click", () => {
      picked.push(it.id);
      renderList();
    });
    li.appendChild(btn);
    pool.appendChild(li);
  });

  $("rank-submit").disabled = picked.length !== topN;
}

function move(from, to) {
  if (to < 0 || to >= picked.length || from === to) return;
  picked.splice(to, 0, picked.splice(from, 1)[0]);
  renderList();
}

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  $("chat-log").appendChild(div);
  div.scrollIntoView({ block: "end" });
  return div;
}

// Placeholder bubble shown while the crewmate's reply is being generated.
function addThinking() {
  const div = addMessage("assistant", "Thinking");
  div.classList.add("thinking");
  return div;
}

function setBusy(busy) {
  $("chat-input").disabled = busy;
  $("chat-form").querySelector("button").disabled = busy;
  $("chat-done").disabled = busy;
}

async function start() {
  const data = await post("/api/start", {});
  sessionId = data.session_id;
  items = data.items;
  items.forEach((it) => (names[it.id] = it.name));
  topN = data.top_n;
  picked = [];
  $("scenario").textContent = data.scenario;
  setRemaining(data.max_messages);
  $("rank-title").textContent = `Your top ${topN}`;
  $("picked-title").textContent = "Ranked, most important first";
  $("rank-hint").textContent =
    `Click items to add them to your top ${topN}. Use the arrows to reorder or \u00d7 to remove.`;
  $("rank-submit").textContent = "Submit ranking";
  renderList();
  show("rank-section");
}

$("rank-submit").addEventListener("click", async () => {
  try {
    if (ranking === "initial") {
      // Go to the chat right away; the opening message arrives when ready.
      show("chat-section");
      setBusy(true);
      const thinking = addThinking();
      try {
        const data = await post("/api/ranking", { ranking: picked });
        thinking.remove();
        addMessage("assistant", data.message);
        setBusy(false);
        $("chat-input").focus();
      } catch (e) {
        thinking.remove();
        setBusy(false);
        show("rank-section");  // the server kept the stage, so they can resubmit
        throw e;
      }
    } else {
      await post("/api/final", { ranking: picked });
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
  setBusy(true);
  const thinking = addThinking();
  try {
    const data = await post("/api/message", { message: text });
    thinking.remove();
    addMessage("assistant", data.message);
    setBusy(false);
    setRemaining(data.remaining);
    if (data.remaining > 0) $("chat-input").focus();
  } catch (err) {
    thinking.remove();
    bubble.remove();  // the server didn't record it
    $("chat-input").value = text;
    setBusy(false);
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
  $("briefing").open = false;
  $("rank-title").textContent = `Final top ${topN}: change anything you like`;
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

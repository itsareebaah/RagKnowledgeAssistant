const uploadForm = document.getElementById("upload-form");
const queryForm = document.getElementById("query-form");
const uploadStatus = document.getElementById("upload-status");
const queryStatus = document.getElementById("query-status");
const docList = document.getElementById("doc-list");
const answerEl = document.getElementById("answer");
const sourcesEl = document.getElementById("sources");
const sourceList = document.getElementById("source-list");
const metaEl = document.getElementById("meta");

function setStatus(el, message, ok = true) {
  el.textContent = message;
  el.className = `status ${ok ? "ok" : "err"}`;
}

async function parseResponse(res) {
  const text = await res.text();
  try {
    return { data: JSON.parse(text), raw: text };
  } catch {
    return { data: null, raw: text };
  }
}

function errorMessage(res, data, raw, fallback) {
  if (data?.detail) {
    return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
  }
  if (!res.ok) return raw?.trim() || fallback;
  return fallback;
}

async function loadStatus() {
  const res = await fetch("/api/status");
  const data = await res.json();

  docList.innerHTML = "";
  for (const doc of data.documents) {
    const li = document.createElement("li");
    li.innerHTML = `
      <span>${doc.filename} <small>(${doc.chunk_count} chunks)</small></span>
      <button type="button" data-filename="${doc.filename}">Remove</button>
    `;
    docList.appendChild(li);
  }

  docList.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const filename = btn.dataset.filename;
      await fetch(`/api/documents/${encodeURIComponent(filename)}`, {
        method: "DELETE",
      });
      await loadStatus();
      setStatus(uploadStatus, `Removed ${filename}.`, true);
    });
  });

  metaEl.textContent = `${data.total_chunks} chunks indexed · embeddings: ${data.embedding_model} · LLM: ${data.llm_provider}`;
}

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("file-input");
  const file = fileInput.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  const btn = uploadForm.querySelector("button");
  btn.disabled = true;
  setStatus(uploadStatus, "Uploading and indexing…", true);

  try {
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const { data, raw } = await parseResponse(res);
    if (!res.ok) throw new Error(errorMessage(res, data, raw, "Upload failed"));
    setStatus(uploadStatus, data.message, true);
    fileInput.value = "";
    await loadStatus();
  } catch (err) {
    setStatus(uploadStatus, err.message, false);
  } finally {
    btn.disabled = false;
  }
});

queryForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = document.getElementById("question").value.trim();
  if (!question) return;

  const btn = queryForm.querySelector("button");
  btn.disabled = true;
  setStatus(queryStatus, "Searching knowledge base…", true);
  answerEl.classList.add("hidden");
  sourcesEl.classList.add("hidden");

  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const { data, raw } = await parseResponse(res);
    if (!res.ok) throw new Error(errorMessage(res, data, raw, "Query failed"));

    answerEl.textContent = data.answer;
    answerEl.classList.remove("hidden");

    sourceList.innerHTML = "";
    for (const src of data.sources) {
      const div = document.createElement("div");
      div.className = "source-item";
      div.innerHTML = `
        <div class="meta">${src.filename} · relevance ${src.score}</div>
        <div>${src.text}</div>
      `;
      sourceList.appendChild(div);
    }
    sourcesEl.classList.remove("hidden");
    setStatus(queryStatus, `Answer generated via ${data.provider}.`, true);
  } catch (err) {
    setStatus(queryStatus, err.message, false);
  } finally {
    btn.disabled = false;
  }
});

loadStatus();

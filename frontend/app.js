// Talks to the agent backend. window.API_ENDPOINT is set in config.js, which is
// generated at deploy time. For local testing you can hardcode it below.
const API_ENDPOINT =
  window.API_ENDPOINT || "REPLACE_WITH_YOUR_API_ENDPOINT";

const requestForm = document.getElementById("request-form");
const responseEl = document.getElementById("response");
const statusEl = document.getElementById("status");
const generateBtn = document.getElementById("generate-btn");

// Escape HTML so model output is never injected as markup.
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Render the common markdown the agent produces (headings, bold, inline code,
// bulleted and numbered lists, paragraphs) into safe HTML. Everything is
// escaped first, so this only ever adds formatting tags.
function renderMarkdown(text) {
  const escaped = escapeHtml(text);
  const lines = escaped.split("\n");
  const html = [];
  let listType = null; // "ul" or "ol"

  const closeList = () => {
    if (listType) {
      html.push(`</${listType}>`);
      listType = null;
    }
  };

  const inline = (s) =>
    s
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+?)`/g, "<code>$1</code>");

  for (const raw of lines) {
    const line = raw.trim();

    if (!line) {
      closeList();
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      closeList();
      const level = Math.min(heading[1].length + 1, 6); // shift so # -> h2
      html.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      continue;
    }

    const bullet = line.match(/^[-*]\s+(.*)$/);
    if (bullet) {
      if (listType !== "ul") {
        closeList();
        html.push("<ul>");
        listType = "ul";
      }
      html.push(`<li>${inline(bullet[1])}</li>`);
      continue;
    }

    const numbered = line.match(/^\d+\.\s+(.*)$/);
    if (numbered) {
      if (listType !== "ol") {
        closeList();
        html.push("<ol>");
        listType = "ol";
      }
      html.push(`<li>${inline(numbered[1])}</li>`);
      continue;
    }

    closeList();
    html.push(`<p>${inline(line)}</p>`);
  }

  closeList();
  return html.join("\n");
}

function setBusy(busy, message) {
  generateBtn.disabled = busy;
  if (busy) {
    statusEl.innerHTML = `<span class="loading-dots">${message || "Thinking"}</span>`;
  } else {
    statusEl.textContent = message || "";
  }
}

async function callAgent(prompt) {
  if (API_ENDPOINT.includes("REPLACE_WITH")) {
    statusEl.textContent =
      "API endpoint is not configured yet. Deploy the backend and set config.js.";
    return;
  }

  setBusy(true, "Asking the agent");
  responseEl.innerHTML = "";

  try {
    const res = await fetch(API_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });

    const data = await res.json();

    if (!res.ok) {
      statusEl.textContent = data.error || "Something went wrong.";
      return;
    }

    responseEl.innerHTML = data.response
      ? renderMarkdown(data.response)
      : "<p>(no response)</p>";
    setBusy(false, "Done");
  } catch (err) {
    setBusy(false, "");
    statusEl.textContent = "Could not reach the agent. Check your connection.";
    console.error(err);
  }
}

function buildIdeasPrompt() {
  const level = document.getElementById("skill-level").value;
  const background = document.getElementById("background").value.trim();
  const interests = document.getElementById("interests").value.trim();
  const time = document.getElementById("time").value.trim();

  let prompt = `I am a ${level} AWS learner.`;
  if (background) prompt += ` My background: ${background}.`;
  prompt += " Suggest tailored AWS project ideas for me";
  if (interests) prompt += ` focused on ${interests}`;
  if (time) prompt += ` that I can complete in ${time}`;
  prompt +=
    ". For each project include the AWS services involved, the key learning " +
    "outcomes, an estimated time to complete and a real-world application. " +
    "Then for the project you recommend most, add a step by step build plan " +
    "with the security considerations for each step.";

  return prompt;
}

requestForm.addEventListener("submit", (e) => {
  e.preventDefault();
  callAgent(buildIdeasPrompt());
});

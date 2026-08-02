from __future__ import annotations

import asyncio
import json
import sqlite3
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import UUID

from forecasting_assistant.application.dataset_discovery import DatasetDiscoveryService
from forecasting_assistant.application.orchestrator import ElicitationEngine
from forecasting_assistant.config import get_settings
from forecasting_assistant.domain.datasets import SourcePlan
from forecasting_assistant.domain.models import DialogueState, ReadinessReport, TurnResult
from forecasting_assistant.domain.schema import load_schema
from forecasting_assistant.infrastructure.datasets.http import SecureHttpClient
from forecasting_assistant.infrastructure.datasets.object_store import ContentAddressedObjectStore
from forecasting_assistant.infrastructure.datasets.registry import build_default_adapters
from forecasting_assistant.infrastructure.datasets.sqlite_repository import (
    SQLiteDatasetCatalogRepository,
)
from forecasting_assistant.infrastructure.llm.openai_responses import OpenAIResponsesClient
from forecasting_assistant.infrastructure.persistence.sqlite_repository import (
    SQLiteDialogueRepository,
)


def _json_default(value: Any) -> str:
    return str(value)


def _state_payload(state: DialogueState, readiness: ReadinessReport | None = None) -> dict[str, Any]:
    return {
        "dialogue_id": str(state.dialogue_id),
        "intent": state.intent.value,
        "confirmed": state.confirmed,
        "schema_version": state.schema_version,
        "turns": [turn.model_dump(mode="json") for turn in state.turns],
        "slots": [
            slot.model_dump(mode="json")
            for slot in sorted(state.slots.values(), key=lambda item: item.slot_id)
        ],
        "readiness": None if readiness is None else readiness.model_dump(mode="json"),
    }


def _turn_payload(result: TurnResult) -> dict[str, Any]:
    return {
        "assistant_message": result.assistant_message,
        "state": _state_payload(result.state, result.readiness),
    }


def _source_plan_payload(plan: SourcePlan) -> dict[str, Any]:
    return plan.model_dump(mode="json")


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _list_table(db_path: Path, table: str, order_by: str) -> list[dict[str, Any]]:
    if table not in {
        "dialogues",
        "events",
        "specifications",
        "dataset_source_plans",
        "dataset_selections",
        "dataset_versions",
    }:
        raise ValueError("unsupported table")
    with _connect(db_path) as connection:
        rows = connection.execute(f"SELECT * FROM {table} ORDER BY {order_by} DESC LIMIT 100").fetchall()
    return [{key: row[key] for key in row} for row in rows]


def dashboard_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Forecast Elicitation Demo</title>
  <style>
    :root { --bg:#f6f7f2; --ink:#1f2826; --muted:#66706d; --line:#d8ddd4; --panel:#ffffff; --accent:#1f7a66; --warn:#9a5b15; --bad:#a13d3d; }
    * { box-sizing: border-box; }
    body { margin:0; font:14px/1.45 "Segoe UI", sans-serif; background:var(--bg); color:var(--ink); }
    header { padding:16px 22px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:16px; align-items:center; }
    h1 { font-size:20px; margin:0; }
    main { display:grid; grid-template-columns:minmax(320px, 0.95fr) minmax(420px, 1.25fr); gap:14px; padding:14px; height:calc(100vh - 66px); }
    section { background:var(--panel); border:1px solid var(--line); border-radius:8px; min-height:0; overflow:hidden; }
    .toolbar { display:flex; gap:8px; padding:10px; border-bottom:1px solid var(--line); align-items:center; flex-wrap:wrap; }
    button { border:1px solid var(--line); background:#fff; border-radius:6px; padding:8px 11px; cursor:pointer; color:var(--ink); }
    button.primary { background:var(--accent); color:white; border-color:var(--accent); }
    input, textarea { width:100%; border:1px solid var(--line); border-radius:6px; padding:9px; font:inherit; }
    textarea { min-height:76px; resize:vertical; }
    .chat { padding:12px; height:calc(100% - 150px); overflow:auto; }
    .bubble { padding:9px 10px; border-radius:8px; margin:0 0 8px; max-width:92%; white-space:pre-wrap; }
    .user { margin-left:auto; background:#e4f2ed; }
    .assistant { background:#f1f3ef; }
    .compose { padding:10px; border-top:1px solid var(--line); display:grid; gap:8px; }
    .tabs { display:flex; gap:6px; padding:10px; border-bottom:1px solid var(--line); }
    .tabs button.active { background:#eef5f1; border-color:var(--accent); }
    .content { height:calc(100% - 54px); overflow:auto; padding:10px; }
    table { width:100%; border-collapse:collapse; font-size:13px; }
    th, td { border-bottom:1px solid var(--line); text-align:left; padding:7px; vertical-align:top; }
    th { position:sticky; top:0; background:#fbfcfa; z-index:1; }
    .status-provided,.status-confirmed { color:var(--accent); font-weight:600; }
    .status-invalid,.status-conflicting { color:var(--bad); font-weight:600; }
    .status-ambiguous,.status-inferred { color:var(--warn); font-weight:600; }
    code, pre { font-family:Consolas, monospace; }
    pre { background:#f7f8f5; border:1px solid var(--line); border-radius:6px; padding:10px; overflow:auto; }
    .meta { color:var(--muted); font-size:12px; }
    @media (max-width: 900px) { main { grid-template-columns:1fr; height:auto; } section { min-height:520px; } }
  </style>
</head>
<body>
  <header>
    <div><h1>Forecast Requirement Elicitation</h1><div class="meta" id="dialogueMeta">No active dialogue</div></div>
    <div><button onclick="refreshDatabase()">Refresh DB</button><button class="primary" onclick="startDialogue()">Start New</button></div>
  </header>
  <main>
    <section>
      <div class="toolbar"><button onclick="confirmSpec()">Confirm</button><button onclick="showState()">Show State</button></div>
      <div id="chat" class="chat"></div>
      <div class="compose">
        <textarea id="message" placeholder="Describe the forecast or answer the latest question..."></textarea>
        <button class="primary" onclick="sendMessage()">Send</button>
      </div>
    </section>
    <section>
      <div class="tabs">
        <button class="active" onclick="tab('slots')">Slots</button>
        <button onclick="tab('specs')">Saved Specs</button>
        <button onclick="tab('datasets')">Datasets</button>
        <button onclick="tab('events')">Events</button>
        <button onclick="tab('state')">JSON</button>
      </div>
      <div id="panel" class="content"></div>
    </section>
  </main>
<script>
let dialogueId = null;
let state = null;
let currentTab = 'slots';
const chat = document.getElementById('chat');
const panel = document.getElementById('panel');
function esc(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
async function api(path, options={}) {
  const response = await fetch(path, {headers:{'content-type':'application/json'}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
function addBubble(text, cls) {
  const div = document.createElement('div');
  div.className = 'bubble ' + cls;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}
function renderState(next) {
  state = next;
  dialogueId = next.dialogue_id;
  document.getElementById('dialogueMeta').textContent = `Dialogue ${dialogueId} · intent ${next.intent}`;
  chat.innerHTML = '';
  for (const turn of next.turns) {
    addBubble(turn.user_message, 'user');
    if (turn.assistant_message) addBubble(turn.assistant_message, 'assistant');
  }
  renderPanel();
}
async function startDialogue() {
  const data = await api('/api/dialogues', {method:'POST'});
  renderState(data.state);
  addBubble('Describe the time-series forecast you need.', 'assistant');
}
async function sendMessage() {
  if (!dialogueId) await startDialogue();
  const box = document.getElementById('message');
  const message = box.value.trim();
  if (!message) return;
  box.value = '';
  addBubble(message, 'user');
  const data = await api(`/api/dialogues/${dialogueId}/message`, {method:'POST', body:JSON.stringify({message})});
  renderState(data.state);
}
async function confirmSpec() {
  if (!dialogueId) return;
  const data = await api(`/api/dialogues/${dialogueId}/confirm`, {method:'POST'});
  currentTab = 'datasets';
  panel.innerHTML = `<pre>${esc(JSON.stringify(data, null, 2))}</pre>`;
}
async function showState() {
  if (!dialogueId) return;
  const data = await api(`/api/dialogues/${dialogueId}`);
  renderState(data.state);
  currentTab = 'state';
  renderPanel();
}
function tab(name) {
  currentTab = name;
  document.querySelectorAll('.tabs button').forEach(b => b.classList.toggle('active', b.textContent.toLowerCase().includes(name === 'specs' ? 'saved' : name)));
  renderPanel();
}
function renderPanel() {
  if (currentTab === 'slots') renderSlots();
  if (currentTab === 'state') panel.innerHTML = `<pre>${esc(JSON.stringify(state, null, 2))}</pre>`;
  if (currentTab === 'specs') loadTable('specifications');
  if (currentTab === 'datasets') loadTable('dataset_source_plans');
  if (currentTab === 'events') loadTable('events');
}
function renderSlots() {
  if (!state) { panel.innerHTML = '<p class="meta">Start a dialogue to see slots.</p>'; return; }
  panel.innerHTML = `<table><thead><tr><th>Slot</th><th>Status</th><th>Value</th><th>Evidence</th></tr></thead><tbody>${
    state.slots.map(s => `<tr><td><code>${esc(s.slot_id)}</code></td><td class="status-${esc(s.status)}">${esc(s.status)}</td><td>${esc(JSON.stringify(s.value))}</td><td>${esc(s.evidence_text || '')}<br><span class="meta">${esc((s.validation_errors || []).join('; '))}</span></td></tr>`).join('')
  }</tbody></table>`;
}
async function loadTable(name) {
  const data = await api(`/api/${name}`);
  const rows = data.rows || [];
  if (!rows.length) { panel.innerHTML = '<p class="meta">No rows yet.</p>'; return; }
  const keys = Object.keys(rows[0]);
  panel.innerHTML = `<table><thead><tr>${keys.map(k=>`<th>${esc(k)}</th>`).join('')}</tr></thead><tbody>${
    rows.map(r=>`<tr>${keys.map(k=>`<td>${esc(String(r[k] ?? '').slice(0, 900))}</td>`).join('')}</tr>`).join('')
  }</tbody></table>`;
}
async function refreshDatabase() {
  if (currentTab === 'slots') currentTab = 'specs';
  renderPanel();
}
startDialogue().catch(error => { panel.innerHTML = `<pre>${esc(error.message)}</pre>`; });
</script>
</body>
</html>"""


class DashboardServer:
    def __init__(self, host: str, port: int) -> None:
        self.settings = get_settings()
        schema = load_schema(self.settings.schema_version)
        repository = SQLiteDialogueRepository(self.settings.elicitation_db_path)
        repository.initialize()
        catalog_repository = SQLiteDatasetCatalogRepository(self.settings.elicitation_db_path)
        catalog_repository.initialize()
        provider = OpenAIResponsesClient(self.settings.openai_api_key, self.settings.openai_model, schema)
        self.engine = ElicitationEngine(schema, provider, repository)
        http = SecureHttpClient()
        self.catalog_repository = catalog_repository
        self.dataset_service = DatasetDiscoveryService(
            build_default_adapters(http),
            catalog_repository,
            ContentAddressedObjectStore(self.settings.dataset_store_path),
        )
        self.db_path = Path(self.settings.elicitation_db_path)
        self.server = ThreadingHTTPServer((host, port), self._handler_class())

    def _handler_class(self) -> type[BaseHTTPRequestHandler]:
        dashboard = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                return

            def _read_json(self) -> dict[str, Any]:
                size = int(self.headers.get("content-length", "0"))
                if size == 0:
                    return {}
                payload = json.loads(self.rfile.read(size).decode("utf-8"))
                return payload if isinstance(payload, dict) else {}

            def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
                body = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
                self.send_response(status.value)
                self.send_header("content-type", "application/json; charset=utf-8")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_html(self) -> None:
                body = dashboard_html().encode("utf-8")
                self.send_response(HTTPStatus.OK.value)
                self.send_header("content-type", "text/html; charset=utf-8")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _error(self, error: Exception, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
                self._send_json({"error": str(error)}, status)

            def do_GET(self) -> None:
                try:
                    parsed = urlparse(self.path)
                    parts = [part for part in parsed.path.split("/") if part]
                    if parsed.path == "/":
                        self._send_html()
                    elif parts == ["api", "dialogues"]:
                        self._send_json({"rows": _list_table(dashboard.db_path, "dialogues", "updated_at")})
                    elif len(parts) == 3 and parts[:2] == ["api", "dialogues"]:
                        state = dashboard.engine.get_state(UUID(parts[2]))
                        self._send_json({"state": _state_payload(state)})
                    elif parts == ["api", "events"]:
                        rows = _list_table(dashboard.db_path, "events", "event_id")
                        query = parse_qs(parsed.query)
                        dialogue_id = query.get("dialogue_id", [None])[0]
                        if dialogue_id is not None:
                            rows = [row for row in rows if row.get("dialogue_id") == dialogue_id]
                        self._send_json({"rows": rows})
                    elif parts == ["api", "specifications"]:
                        self._send_json({"rows": _list_table(dashboard.db_path, "specifications", "confirmed_at")})
                    elif parts == ["api", "dataset-plans"]:
                        self._send_json(
                            {
                                "rows": _list_table(
                                    dashboard.db_path,
                                    "dataset_source_plans",
                                    "created_at",
                                )
                            }
                        )
                    elif len(parts) == 3 and parts[:2] == ["api", "dataset-plans"]:
                        plan = dashboard.catalog_repository.load_plan(UUID(parts[2]))
                        if plan is None:
                            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                        else:
                            self._send_json({"source_plan": _source_plan_payload(plan)})
                    else:
                        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                except Exception as error:  # noqa: BLE001 - HTTP boundary returns safe JSON errors
                    self._error(error)

            def do_POST(self) -> None:
                try:
                    parts = [part for part in urlparse(self.path).path.split("/") if part]
                    if parts == ["api", "dialogues"]:
                        state = dashboard.engine.start_dialogue()
                        self._send_json({"state": _state_payload(state)})
                    elif len(parts) == 4 and parts[:2] == ["api", "dialogues"] and parts[3] == "message":
                        message = str(self._read_json().get("message", "")).strip()
                        result = asyncio.run(dashboard.engine.handle_user_message(UUID(parts[2]), message))
                        self._send_json(_turn_payload(result))
                    elif len(parts) == 4 and parts[:2] == ["api", "dialogues"] and parts[3] == "confirm":
                        body = self._read_json()
                        specification = dashboard.engine.confirm_specification(UUID(parts[2]), confirm=True)
                        user_id = body.get("user_id")
                        plan = dashboard.dataset_service.discover_for_specification(
                            specification,
                            user_id=str(user_id) if user_id else None,
                        )
                        self._send_json(
                            {
                                "specification": specification.model_dump(mode="json"),
                                "source_plan": _source_plan_payload(plan),
                            }
                        )
                    elif (
                        len(parts) == 4
                        and parts[:2] == ["api", "dataset-plans"]
                        and parts[3] == "confirm"
                    ):
                        body = self._read_json()
                        candidate_id = str(body.get("candidate_id", "")).strip()
                        user_id = body.get("user_id")
                        selection = dashboard.dataset_service.confirm_dataset(
                            UUID(parts[2]),
                            candidate_id,
                            confirm=True,
                            user_id=str(user_id) if user_id else None,
                        )
                        self._send_json({"selection": selection.model_dump(mode="json")})
                    elif (
                        len(parts) == 4
                        and parts[:2] == ["api", "dataset-selections"]
                        and parts[3] == "fetch"
                    ):
                        version = dashboard.dataset_service.fetch_selection(UUID(parts[2]))
                        self._send_json({"version": version.model_dump(mode="json")})
                    else:
                        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                except Exception as error:  # noqa: BLE001 - HTTP boundary returns safe JSON errors
                    self._error(error)

        return Handler

    def serve(self, *, open_browser: bool) -> None:
        host = str(self.server.server_address[0])
        port = int(self.server.server_address[1])
        url = f"http://{host}:{port}/"
        if open_browser:
            webbrowser.open(url)
        print(f"Forecast elicitation web UI running at {url}")
        self.server.serve_forever()


def run_web_server(host: str = "127.0.0.1", port: int = 8765, *, open_browser: bool = True) -> None:
    DashboardServer(host, port).serve(open_browser=open_browser)

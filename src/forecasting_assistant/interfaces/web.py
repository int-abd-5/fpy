from __future__ import annotations

import asyncio
import base64
import binascii
import csv
import io
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
from forecasting_assistant.infrastructure.llm.openai_responses import (
    PersistentOpenAIResponsesClient,
)
from forecasting_assistant.infrastructure.observability.pipeline_logger import JsonlPipelineLogger
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


_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_UPLOAD_SUFFIXES = {".csv", ".json", ".xlsx", ".xls", ".parquet"}


def _safe_upload_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    if not name or name in {".", ".."}:
        raise ValueError("a file name is required")
    if Path(name).suffix.casefold() not in _UPLOAD_SUFFIXES:
        raise ValueError("supported uploads are CSV, JSON, Excel, or Parquet files")
    return name


def _extract_uploaded_columns(filename: str, content: bytes) -> list[str]:
    suffix = Path(filename).suffix.casefold()
    if suffix == ".csv":
        try:
            row = next(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
        except (StopIteration, UnicodeDecodeError, csv.Error):
            return []
        return _unique_columns(row)
    if suffix == ".json":
        try:
            payload = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return []
        if isinstance(payload, list):
            payload = next((item for item in payload if isinstance(item, dict)), {})
        if isinstance(payload, dict):
            return _unique_columns(payload.keys())
    return []


def _unique_columns(columns: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for column in columns:
        value = str(column).strip()
        key = value.casefold()
        if value and key not in seen:
            result.append(value)
            seen.add(key)
    return result


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
  <title>Forecast Studio</title>
  <style>
    :root { --bg:#f8f8f5; --ink:#10294e; --muted:#64758e; --line:#dce2e8; --panel:#fff; --accent:#086a73; --accent-soft:#eaf4f3; --warm:#fff8eb; --warn:#d99317; --bad:#b24b4b; }
    * { box-sizing: border-box; }
    body { margin:0; font:15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:var(--bg); color:var(--ink); }
    header { min-height:78px; padding:18px 32px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:20px; align-items:center; background:#fff; }
    h1 { font-size:24px; letter-spacing:-.03em; margin:0; }
    h2 { font-size:20px; letter-spacing:-.02em; margin:0; }
    p { margin:4px 0 0; color:var(--muted); }
    main { display:grid; grid-template-columns:minmax(420px, 1.05fr) minmax(420px, .95fr); gap:20px; padding:26px 32px; height:calc(100vh - 78px); }
    section { background:var(--panel); border:1px solid var(--line); border-radius:14px; min-height:0; overflow:hidden; box-shadow:0 8px 24px rgba(16,41,78,.04); }
    button { border:1px solid var(--line); background:#fff; border-radius:8px; padding:9px 13px; cursor:pointer; color:var(--ink); font:inherit; transition:all .15s ease; }
    button:hover { border-color:var(--accent); transform:translateY(-1px); }
    button.primary { background:var(--accent); color:white; border-color:var(--accent); }
    button.link { border:0; padding:4px 0; color:var(--accent); background:transparent; }
    .brand { display:flex; align-items:center; gap:12px; }
    .brand-mark { width:34px; height:34px; border-radius:10px; display:grid; place-items:center; color:#fff; background:var(--accent); font-size:22px; font-weight:700; }
    .header-actions { display:flex; gap:10px; align-items:center; }
    .meta { color:var(--muted); font-size:12px; }
    .chat-shell, .insight-shell { display:flex; flex-direction:column; }
    .section-head { padding:26px 28px 16px; }
    .chat { padding:8px 28px 24px; flex:1; overflow:auto; }
    .bubble { padding:14px 16px; border-radius:12px; margin:0 0 14px; max-width:84%; white-space:pre-wrap; }
    .user { margin-left:auto; background:var(--ink); color:#fff; border-bottom-right-radius:4px; }
    .assistant { background:#f1f6f6; color:#1a365b; border-bottom-left-radius:4px; }
    .compose { padding:14px 18px 18px; border-top:1px solid var(--line); display:grid; gap:10px; background:#fcfcfa; }
    textarea { width:100%; min-height:68px; resize:vertical; border:1px solid var(--line); border-radius:10px; padding:12px 14px; font:inherit; color:var(--ink); background:#fff; }
    .compose-actions { display:flex; justify-content:space-between; align-items:center; gap:12px; }
    .upload-label { color:var(--accent); border-color:#9fc8c7; background:var(--accent-soft); }
    .upload-label input { display:none; }
    .tabs { display:flex; gap:8px; padding:18px 24px 0; border-bottom:1px solid var(--line); }
    .tabs button { border:0; border-bottom:2px solid transparent; border-radius:0; padding:10px 4px 12px; color:var(--muted); background:transparent; }
    .tabs button.active { border-bottom-color:var(--accent); color:var(--ink); font-weight:600; }
    .content { flex:1; overflow:auto; padding:22px 24px; }
    .requirement { display:flex; justify-content:space-between; gap:20px; padding:14px 0; border-bottom:1px solid var(--line); }
    .requirement:last-child { border-bottom:0; }
    .requirement-name { font-weight:600; }
    .requirement-value { color:var(--accent); text-align:right; max-width:55%; word-break:break-word; }
    .status { color:var(--accent); font-size:12px; text-transform:capitalize; }
    .empty { padding:24px 0; color:var(--muted); }
    .catalog-card { padding:18px; border:1px solid var(--line); border-radius:12px; margin-bottom:12px; }
    .catalog-card h3 { margin:0 0 5px; font-size:16px; }
    .catalog-card p { margin:0 0 14px; }
    .catalog-footer { display:flex; justify-content:space-between; align-items:center; gap:12px; }
    .notice { padding:16px; background:var(--warm); border:1px solid #f1d79e; border-radius:10px; margin-top:14px; }
    .error { color:var(--bad); }
    @media (max-width: 900px) { header { padding:16px 20px; } main { grid-template-columns:1fr; height:auto; padding:18px 20px; } section { min-height:560px; } }
  </style>
</head>
<body>
  <header>
    <div class="brand"><div class="brand-mark">↗</div><div><h1>Forecast Studio</h1><div class="meta" id="dialogueMeta">A simple conversation for setting up your forecast</div></div></div>
    <div class="header-actions"><button onclick="startDialogue()">New session</button></div>
  </header>
  <main>
    <section>
      <div class="section-head"><h2>Describe the forecast you need</h2><p>I’ll help you shape the request and find useful data.</p></div>
      <div id="chat" class="chat"></div>
      <div class="compose">
        <textarea id="message" placeholder="Describe the forecast or answer the latest question..."></textarea>
        <div class="compose-actions"><label class="upload-label"><input id="fileInput" type="file" accept=".csv,.json,.xlsx,.xls,.parquet" onchange="uploadData(this.files[0])">↥ &nbsp;Upload data</label><span id="uploadStatus" class="meta"></span><button class="primary" onclick="sendMessage()">Send&nbsp; ↗</button></div>
      </div>
    </section>
    <section>
      <div class="tabs">
        <button class="active" onclick="tab('requirements')">Requirements</button>
        <button onclick="tab('catalog')">Data catalog</button>
      </div>
      <div id="panel" class="content"></div>
    </section>
  </main>
<script>
let dialogueId = null;
let state = null;
let currentTab = 'requirements';
let sourcePlan = null;
let selection = null;
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
  sessionStorage.setItem('forecast_dialogue_id', dialogueId);
  document.getElementById('dialogueMeta').textContent = `Session ${dialogueId.slice(0, 8)} · your information is saved locally`;
  chat.innerHTML = '';
  for (const turn of next.turns) {
    addBubble(turn.user_message, 'user');
    if (turn.assistant_message) addBubble(turn.assistant_message, 'assistant');
  }
  renderPanel();
}
async function startDialogue() {
  const data = await api('/api/dialogues', {method:'POST'});
  sourcePlan = null;
  selection = null;
  renderState(data.state);
  addBubble('Hi! Tell me what you want to forecast and any details you already know.', 'assistant');
}
async function sendMessage() {
  if (!dialogueId) await startDialogue();
  const box = document.getElementById('message');
  const message = box.value.trim();
  if (!message) return;
  box.value = '';
  addBubble(message, 'user');
  try {
    const data = await api(`/api/dialogues/${dialogueId}/message`, {method:'POST', body:JSON.stringify({message})});
    renderState(data.state);
  } catch (error) {
    addBubble(`I couldn’t process that yet. ${error.message}`, 'assistant');
  }
}
async function confirmSpec() {
  if (!dialogueId) return;
  try {
    const data = await api(`/api/dialogues/${dialogueId}/confirm`, {method:'POST'});
    sourcePlan = data.source_plan;
    currentTab = 'catalog';
    addBubble('Your requirements are confirmed. I found some data options on the right.', 'assistant');
    renderPanel();
  } catch (error) {
    addBubble(`We need a little more information before confirming. ${error.message}`, 'assistant');
  }
}
function tab(name) {
  currentTab = name;
  document.querySelectorAll('.tabs button').forEach(b => b.classList.toggle('active', b.textContent.toLowerCase().includes(name === 'requirements' ? 'requirements' : 'catalog')));
  renderPanel();
}
function renderPanel() {
  if (currentTab === 'requirements') renderRequirements();
  if (currentTab === 'catalog') renderCatalog();
}
function prettyName(id) {
  return ({problem_statement:'Forecast request', target_description:'What to predict', target_unit:'Unit', forecast_horizon:'How far ahead', output_granularity:'Results shown', source_mode:'Data source', source_reference:'Source', frequency:'Data timing', dataset_type:'Data shape', source_provider:'Data provider', contains_sensitive_data:'Data privacy'}[id] || id.replaceAll('_',' '));
}
function displayValue(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object' && value.periods !== undefined) return `${value.periods} ${value.unit}`;
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
}
function renderRequirements() {
  if (!state) { panel.innerHTML = '<p class="empty">Start a conversation to see your requirements.</p>'; return; }
  const visible = state.slots.filter(s => s.value !== null && s.status !== 'unmentioned' && s.slot_id !== 'source_reference');
  if (!visible.length) { panel.innerHTML = '<p class="empty">Your requirements will appear here as we talk.</p>'; return; }
  panel.innerHTML = `<div class="meta">Your brief is built from the conversation.</div>${visible.map(s => `<div class="requirement"><div><div class="requirement-name">${esc(prettyName(s.slot_id))}</div><div class="status">${esc(s.status)}</div></div><div class="requirement-value">${esc(displayValue(s.value))}</div></div>`).join('')}<div class="notice"><strong>Ready to continue?</strong><br><span class="meta">When the brief looks right, choose Confirm to find matching catalog data.</span><br><button class="primary" onclick="confirmSpec()">Confirm requirements</button></div>`;
}
function renderCatalog() {
  if (!sourcePlan) { panel.innerHTML = '<p class="empty">Confirm your requirements first. Matching datasets will appear here.</p>'; return; }
  const items = sourcePlan.recommendations || [];
  if (!items.length) { panel.innerHTML = '<p class="empty">I couldn’t find an eligible dataset for this request yet.</p><div class="notice">You can go back to the conversation and adjust the forecast details, or upload your own data.</div>'; return; }
  panel.innerHTML = `<div class="meta">Choose one dataset to continue.</div>${items.map(item => { const c=item.candidate, r=item.ranking, url=(c.source_url.startsWith('http://') || c.source_url.startsWith('https://')) ? c.source_url : '#'; return `<div class="catalog-card"><h3>${esc(c.title)}</h3><p>${esc(c.description || 'Catalog dataset from a trusted source.')}</p><div class="meta">${esc(c.publisher)}${c.frequency ? ` · ${esc(c.frequency)}` : ''}${r.total ? ` · Match ${esc(r.total)}/100` : ''}</div><div class="catalog-footer"><a class="link" href="${esc(url)}" target="_blank" rel="noopener">Preview details ↗</a><button class="primary" onclick="selectDataset('${esc(sourcePlan.plan_id)}','${esc(c.candidate_id)}')">Use this dataset</button></div></div>`; }).join('')}${selection ? `<div class="notice"><strong>Dataset selected.</strong><br><span class="meta">It is ready to fetch when you are.</span><br><button class="primary" onclick="fetchDataset('${esc(selection.selection_id)}')">Fetch dataset</button></div>` : ''}`;
}
async function selectDataset(planId, candidateId) {
  try {
    const data = await api(`/api/dataset-plans/${planId}/confirm`, {method:'POST', body:JSON.stringify({candidate_id:candidateId})});
    selection = data.selection;
    renderCatalog();
    addBubble('That dataset is selected. You can fetch it from the catalog panel.', 'assistant');
  } catch (error) { panel.innerHTML = `<p class="error">${esc(error.message)}</p>`; }
}
async function fetchDataset(selectionId) {
  try {
    const data = await api(`/api/dataset-selections/${selectionId}/fetch`, {method:'POST'});
    panel.innerHTML = `<div class="notice"><strong>Your dataset is ready.</strong><br><span class="meta">It has been safely stored for the next forecasting step. Retrieved ${esc(data.version.retrieved_at || 'now')}.</span></div>`;
    addBubble('The dataset is ready for the next step in the forecasting pipeline.', 'assistant');
  } catch (error) { panel.innerHTML = `<p class="error">${esc(error.message)}</p>`; }
}
function uploadData(file) {
  if (!file) return;
  if (!dialogueId) { document.getElementById('uploadStatus').textContent = 'Start a session first.'; return; }
  if (file.size > 10 * 1024 * 1024) { document.getElementById('uploadStatus').textContent = 'Please choose a file under 10 MB.'; return; }
  const reader = new FileReader();
  reader.onload = async () => {
    try {
      document.getElementById('uploadStatus').textContent = 'Uploading…';
      const base64 = String(reader.result).split(',')[1] || '';
      const data = await api(`/api/dialogues/${dialogueId}/upload`, {method:'POST', body:JSON.stringify({filename:file.name, content_base64:base64})});
      renderState(data.state);
      document.getElementById('uploadStatus').textContent = `${data.filename} added`;
      addBubble(`I’ve added ${data.filename}. I can use its columns while we set up the forecast.`, 'assistant');
    } catch (error) { document.getElementById('uploadStatus').textContent = error.message; }
  };
  reader.readAsDataURL(file);
}
async function resumeOrStart() {
  const savedId = sessionStorage.getItem('forecast_dialogue_id');
  if (savedId) {
    try {
      const data = await api(`/api/dialogues/${savedId}`);
      renderState(data.state);
      if (!data.state.turns.length) addBubble('Hi! Tell me what you want to forecast and any details you already know.', 'assistant');
      return;
    } catch (error) {
      sessionStorage.removeItem('forecast_dialogue_id');
    }
  }
  await startDialogue();
}
resumeOrStart().catch(error => { panel.innerHTML = `<p class="error">${esc(error.message)}</p>`; });
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
        pipeline_sink = JsonlPipelineLogger(self.settings.elicitation_log_path)
        provider = PersistentOpenAIResponsesClient(
            self.settings.openai_api_key,
            self.settings.openai_model,
            schema,
            trace_sink=pipeline_sink,
        )
        self.engine = ElicitationEngine(
            schema,
            provider,
            repository,
            trace_sink=pipeline_sink,
        )
        http = SecureHttpClient()
        self.catalog_repository = catalog_repository
        self.dataset_service = DatasetDiscoveryService(
            build_default_adapters(http),
            catalog_repository,
            ContentAddressedObjectStore(self.settings.dataset_store_path),
        )
        self.db_path = Path(self.settings.elicitation_db_path)
        self.server = ThreadingHTTPServer((host, port), self._handler_class())

    def _store_upload(self, dialogue_id: UUID, filename: str, content: bytes) -> dict[str, Any]:
        if len(content) > _MAX_UPLOAD_BYTES:
            raise ValueError("uploads must be 10 MB or smaller")
        safe_name = _safe_upload_filename(filename)
        upload_path = (
            Path(self.settings.dataset_store_path)
            / "uploads"
            / str(dialogue_id)
            / safe_name
        ).resolve()
        upload_path.parent.mkdir(parents=True, exist_ok=True)
        upload_path.write_bytes(content)
        columns = _extract_uploaded_columns(safe_name, content)
        state = self.engine.attach_uploaded_file(
            dialogue_id,
            source_reference=str(upload_path),
            filename=safe_name,
            columns=columns,
        )
        return {
            "filename": safe_name,
            "columns": columns,
            "state": _state_payload(state),
        }

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
                    elif len(parts) == 4 and parts[:2] == ["api", "dialogues"] and parts[3] == "upload":
                        body = self._read_json()
                        filename = str(body.get("filename", "")).strip()
                        encoded = body.get("content_base64")
                        if not isinstance(encoded, str) or not encoded:
                            raise ValueError("uploaded file content is missing")
                        try:
                            content = base64.b64decode(encoded, validate=True)
                        except (ValueError, binascii.Error) as error:
                            raise ValueError("uploaded file content is not valid base64") from error
                        self._send_json(
                            dashboard._store_upload(UUID(parts[2]), filename, content)
                        )
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

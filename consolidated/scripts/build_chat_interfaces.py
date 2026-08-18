#!/usr/bin/env python3
"""Generate self-contained chat interface HTML files from templates and config."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "src" / "templates"
CONFIG_PATH = ROOT / "src" / "chat_pages.json"
DOCUMENT_SAVE_LIB = ROOT / "src" / "lib" / "chat_document_save.js"

TEMPLATE_FILES = {
    "base": "chat_interface.base.html",
    "extended": "chat_interface.extended.html",
    "extended_save": "chat_interface.extended_save.html",
}

USER_ID_TEMPLATE_ONLY = """const userId = '{{USER_ID}}';
        const courseId = '{{COURSE_ID}}';"""

USER_ID_URL_PARAMS = """// URL params for session (iframe: ?user_id=...&course_id=...)
        const urlParams = new URLSearchParams(window.location.search);
        const userId = urlParams.get('user_id') || window.PLATFORM_USER_ID || '{{USER_ID}}' || '';
        const courseId = urlParams.get('course_id') || window.PLATFORM_COURSE_ID || '{{COURSE_ID}}' || '';"""

USER_ID_URL_PARAMS_SIMPLE = """// URL params for session (iframe: ?user_id=...&course_id=...)
        const urlParams = new URLSearchParams(window.location.search);
        const userId = '{{USER_ID}}' || '';
        const courseId = '{{COURSE_ID}}' || '';"""


def escape_js_string(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "\\'")


def build_welcome_message_html(content: str) -> str:
    escaped = escape_js_string(content)
    return (
        "'<div class=\"message assistant\">' +\n"
        "                    '<div class=\"message-avatar\">C<\\/div>' +\n"
        f"                    '<div class=\"message-content\">{escaped}<\\/div>' +\n"
        "                    '<\\/div>'"
    )


def session_storage_key_expr(page: dict) -> str:
    prefix = page["sessionStorageKey"]
    if page.get("sessionKeyIncludesCourseId"):
        return f"'{prefix}'+ courseId"
    return f"'{prefix}'"


def session_id_comment(page: dict) -> str:
    if page.get("template") == "base":
        return "// ── Session ID ───────────────────────────────────────────"
    label = page.get("sessionLabel", page["id"])
    return f"// ── Session ID (separate from chat_interface.html / n8n {label} session) ─"


def session_log_label(page: dict) -> str:
    if "sessionLogLabel" in page:
        return page["sessionLogLabel"]
    label = page.get("sessionLabel", page["id"])
    return f"Session ID ({label}):" if label != "readiness" else "Session ID:"


def user_id_resolution(page: dict) -> str:
    source = page.get("userIdSource", "url_params")
    if source == "template_only":
        return USER_ID_TEMPLATE_ONLY
    if source == "url_params_simple":
        return USER_ID_URL_PARAMS_SIMPLE
    return USER_ID_URL_PARAMS


def build_document_save_block(page: dict) -> str:
    doc = page.get("documentSave")
    if not doc:
        return ""

    trigger = doc["saveTrigger"]
    save_url = doc.get("saveWebhookUrl", "")
    fetch_url = doc.get("fetchWebhookUrl", "")
    save_url_line = (
        f"            saveWebhookUrl: '{save_url}',\n"
        if save_url
        else "            saveWebhookUrl: ChatDocumentSave.DEFAULT_SAVE_WEBHOOK,\n"
    )
    fetch_url_line = (
        f"            fetchWebhookUrl: '{fetch_url}',\n"
        if fetch_url
        else "            fetchWebhookUrl: ChatDocumentSave.DEFAULT_FETCH_WEBHOOK,\n"
    )

    return f"""        // ── Document fetch/save hooks — edit when each n8n webhook runs ──
        // SAVE: documentTypeId — this page's output type
        // FETCH: sourceDocumentTypeId — prior page's output to look up (unique per HTML file)
        const PAGE_SAVE_DOCUMENT_TYPE_ID = '{doc["saveDocumentTypeId"]}';
        const PAGE_FETCH_DOCUMENT_TYPE_ID = '{doc["fetchDocumentTypeId"]}';

        const DOCUMENT_WEBHOOK_CONFIG = {{
{save_url_line}{fetch_url_line}            documentTypeId: ChatDocumentSave.resolveDocumentTypeId(PAGE_SAVE_DOCUMENT_TYPE_ID),
            sourceDocumentTypeId: ChatDocumentSave.resolveSourceDocumentTypeId(PAGE_FETCH_DOCUMENT_TYPE_ID),
            sourceDocumentLabel: '{escape_js_string(doc["sourceDocumentLabel"])}',
            fetchOnStartConversation: {str(doc.get("fetchOnStartConversation", True)).lower()},
            fetchOnSendMessage: {str(doc.get("fetchOnSendMessage", False)).lower()},
            saveOnAgentResponse: {str(doc.get("saveOnAgentResponse", True)).lower()},
            showRetrievedDocumentOnScreen: {str(doc.get("showRetrievedDocumentOnScreen", True)).lower()},
            saveTrigger: ChatDocumentSave.triggers.{trigger}()
        }};

        const documentSave = ChatDocumentSave.create({{
            saveWebhookUrl: DOCUMENT_WEBHOOK_CONFIG.saveWebhookUrl,
            fetchWebhookUrl: DOCUMENT_WEBHOOK_CONFIG.fetchWebhookUrl,
            documentTypeId: DOCUMENT_WEBHOOK_CONFIG.documentTypeId,
            sourceDocumentTypeId: DOCUMENT_WEBHOOK_CONFIG.sourceDocumentTypeId,
            sourceDocumentLabel: DOCUMENT_WEBHOOK_CONFIG.sourceDocumentLabel,
            userId: userId,
            courseId: courseId,
            trigger: DOCUMENT_WEBHOOK_CONFIG.saveTrigger
        }});

        async function applyFetchHooks(payload, chatInput, when) {{
            const shouldFetch = (when === 'start' && DOCUMENT_WEBHOOK_CONFIG.fetchOnStartConversation)
                || (when === 'send' && DOCUMENT_WEBHOOK_CONFIG.fetchOnSendMessage);
            if (shouldFetch) {{
                await documentSave.prepareAgentPayload(payload, chatInput);
            }} else {{
                payload.chatInput = chatInput;
            }}
            return payload;
        }}

        function showRetrievedDocumentSummary() {{
            if (!DOCUMENT_WEBHOOK_CONFIG.showRetrievedDocumentOnScreen) return;
            if (documentSave.hasShownSourceSummary()) return;
            if (!documentSave.hasSourceDocumentContent()) return;
            const summary = ChatDocumentSave.formatDocumentSummary(
                documentSave.getSourceDocument(),
                DOCUMENT_WEBHOOK_CONFIG.sourceDocumentLabel
            );
            if (!summary || ChatDocumentSave.isTrivialEmptyContent(summary)) return;
            documentSave.markSourceSummaryShown();
            addMessage('Here is your retrieved summary from the previous work.\\n\\n' + summary, false);
        }}"""


def build_document_save_lib_tag(page: dict) -> str:
    if page.get("template") != "extended_save":
        return ""
    lib = DOCUMENT_SAVE_LIB.read_text()
    return f"    <script>\n    {lib}    </script>"


def render_page(page: dict) -> str:
    template_name = TEMPLATE_FILES[page["template"]]
    template = (TEMPLATES_DIR / template_name).read_text()

    welcome_js = page.get("welcomeMessageJs") or page["welcomeMessageBody"]
    replacements = {
        "{{WEBHOOK_URL}}": page["webhookUrl"],
        "{{WELCOME_MESSAGE_BODY}}": page["welcomeMessageBody"],
        "{{WELCOME_MESSAGE_HTML}}": build_welcome_message_html(welcome_js),
        "{{USER_ID_RESOLUTION}}": user_id_resolution(page),
        "{{SESSION_STORAGE_KEY_EXPR}}": session_storage_key_expr(page),
        "{{HISTORY_STORAGE_KEY}}": page["historyStorageKey"],
        "{{SESSION_ID_COMMENT}}": session_id_comment(page),
        "{{SESSION_LOG_LABEL}}": session_log_label(page),
        "{{DOCUMENT_SAVE_BLOCK}}": build_document_save_block(page),
        "{{DOCUMENT_SAVE_LIB}}": build_document_save_lib_tag(page),
    }

    output = template
    for key, value in replacements.items():
        output = output.replace(key, value)
    return output


def load_config() -> list[dict]:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("chat_pages.json must be a JSON array")
    return data


def build_all(output_dir: Path | None = None) -> list[tuple[str, Path]]:
    output_dir = output_dir or ROOT
    pages = load_config()
    written: list[tuple[str, Path]] = []

    for page in pages:
        required = ["id", "outputFile", "template", "webhookUrl", "sessionStorageKey", "historyStorageKey", "welcomeMessageBody"]
        missing = [k for k in required if k not in page]
        if missing:
            raise KeyError(f"Page {page.get('id', '?')} missing keys: {missing}")

        if page["template"] not in TEMPLATE_FILES:
            raise ValueError(f"Unknown template {page['template']} for {page['id']}")

        content = render_page(page)
        out_path = output_dir / page["outputFile"]
        out_path.write_text(content, encoding="utf-8")
        written.append((page["id"], out_path))
        print(f"Built {page['outputFile']} ({page['template']})")

    # Keep consolidated copy in sync with src/lib version.
    consolidated_lib = ROOT / "chat_document_save.js"
    if DOCUMENT_SAVE_LIB.exists():
        consolidated_lib.write_text(DOCUMENT_SAVE_LIB.read_text(), encoding="utf-8")

    return written


def main() -> int:
    if not TEMPLATES_DIR.exists():
        print("Templates missing. Run: python scripts/bootstrap_templates.py", file=sys.stderr)
        return 1
    if not DOCUMENT_SAVE_LIB.exists():
        print("chat_document_save.js missing. Run: python scripts/bootstrap_templates.py", file=sys.stderr)
        return 1
    build_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

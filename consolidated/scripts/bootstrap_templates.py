#!/usr/bin/env python3
"""One-time helper to create templates from existing HTML files. Run from repo root."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "src" / "templates"
LIB = ROOT / "src" / "lib"

DEBUG_LOG_PATTERN = re.compile(
    r"\n\s*// #region agent log\n.*?\n\s*// #endregion",
    re.DOTALL,
)


def strip_debug_telemetry(text: str) -> str:
    return DEBUG_LOG_PATTERN.sub("", text)


def extract_document_save_lib(save_html: str) -> str:
    marker_start = "(function (global) {"
    marker_end = "})(typeof window !== 'undefined' ? window : this);"
    start = save_html.index(marker_start)
    end = save_html.index(marker_end, start) + len(marker_end)
    return save_html[start:end] + "\n"


def apply_common_placeholders(text: str) -> str:
    text = strip_debug_telemetry(text)
    text = re.sub(
        r"const WEBHOOK_URL = '[^']*';",
        "const WEBHOOK_URL = '{{WEBHOOK_URL}}';",
        text,
        count=1,
    )
    text = re.sub(
        r"const WELCOME_MESSAGE_HTML = '.*?'\s*\+\s*'<\\/div>';",
        "const WELCOME_MESSAGE_HTML = {{WELCOME_MESSAGE_HTML}};",
        text,
        flags=re.DOTALL,
        count=1,
    )
    text = re.sub(
        r"(<div class=\"message-content\">).*?(</div>\s*</div>\s*</div>\s*<div class=\"input-container\">)",
        r"\1{{WELCOME_MESSAGE_BODY}}\2",
        text,
        count=1,
        flags=re.DOTALL,
    )
    return text


def replace_user_id_block(text: str) -> str:
    patterns = [
        (
            r"// URL params for session \(iframe: \?user_id=\.\.\.&course_id=\.\.\.\)\n"
            r"        const urlParams = new URLSearchParams\(window\.location\.search\);\n"
            r"        const userId = urlParams\.get\('user_id'\) \|\| window\.PLATFORM_USER_ID \|\| '\{\{USER_ID\}\}' \|\| '';\n"
            r"        const courseId = urlParams\.get\('course_id'\) \|\| window\.PLATFORM_COURSE_ID \|\| '\{\{COURSE_ID\}\}' \|\| '';",
            "{{USER_ID_RESOLUTION}}",
        ),
        (
            r"// URL params for session \(iframe: \?user_id=\.\.\.&course_id=\.\.\.\)\n"
            r"        const urlParams = new URLSearchParams\(window\.location\.search\);\n"
            r"        const userId = '\{\{USER_ID\}\}' \|\| '';\n"
            r"        const courseId = '\{\{COURSE_ID\}\}' \|\| '';",
            "{{USER_ID_RESOLUTION}}",
        ),
        (
            r"// URL params for session \(iframe: \?user_id=\.\.\.&course_id=\.\.\.\)\n"
            r"        const urlParams = new URLSearchParams\(window\.location\.search\);\n"
            r"        const userId = '\{\{USER_ID\}\}';\n"
            r"        const courseId = '\{\{COURSE_ID\}\}';",
            "// URL params for session (iframe: ?user_id=...&course_id=...)\n"
            "        const urlParams = new URLSearchParams(window.location.search);\n"
            "        {{USER_ID_RESOLUTION}}",
        ),
    ]
    for pattern, replacement in patterns:
        updated, count = re.subn(pattern, replacement, text, count=1)
        if count:
            return updated
    return text


def apply_session_placeholders(text: str, session_prefix: str, history_key: str, session_comment: str, session_log: str) -> str:
    text = re.sub(
        rf"localStorage\.setItem\('{re.escape(session_prefix)}'(?:\s*\+\s*courseId)?, sessionId\);",
        "localStorage.setItem({{SESSION_STORAGE_KEY_EXPR}}, sessionId);",
        text,
    )
    text = re.sub(
        rf"localStorage\.getItem\('{re.escape(session_prefix)}'(?:\s*\+\s*courseId)?\)",
        "localStorage.getItem({{SESSION_STORAGE_KEY_EXPR}})",
        text,
    )
    text = re.sub(
        rf"localStorage\.removeItem\('{re.escape(history_key)}'\);",
        "localStorage.removeItem('{{HISTORY_STORAGE_KEY}}');",
        text,
    )
    text = re.sub(session_comment, "{{SESSION_ID_COMMENT}}", text, count=1)
    text = text.replace(session_log, "console.log('{{SESSION_LOG_LABEL}}', sessionId);")
    text = re.sub(
        r"// Clear stored conversation if using local storage[^\n]*",
        "// Clear stored conversation if using local storage ({{HISTORY_STORAGE_KEY}})",
        text,
        count=1,
    )
    return text


def make_base_template() -> str:
    text = (ROOT / "chat_interface.html").read_text()
    text = apply_common_placeholders(text)
    text = replace_user_id_block(text)
    return apply_session_placeholders(
        text,
        "chatSessionId",
        "chatHistory",
        r"// ── Session ID ───────────────────────────────────────────",
        "console.log('Session ID:', sessionId);",
    )


def make_extended_template() -> str:
    text = (ROOT / "chat_interface_gpt2_talents.html").read_text()
    text = apply_common_placeholders(text)
    text = replace_user_id_block(text)
    return apply_session_placeholders(
        text,
        "chatSessionId_gpt2",
        "chatHistory_gpt2",
        r"// ── Session ID \(separate from chat_interface\.html / n8n GPT2 session\) ─",
        "console.log('Session ID (GPT2):', sessionId);",
    )


def make_extended_save_template() -> str:
    save_html = (ROOT / "chat_interface_gpt3_needs_save.html").read_text()
    lib = extract_document_save_lib(save_html)
    (LIB / "chat_document_save.js").write_text(lib)

    lib_block = save_html[
        save_html.index("<script>\n    (function (global) {") : save_html.index(
            "})(typeof window !== 'undefined' ? window : this);\n    </script>"
        )
        + len("})(typeof window !== 'undefined' ? window : this);\n    </script>")
    ]
    text = save_html.replace(lib_block, "{{DOCUMENT_SAVE_LIB}}\n")
    text = apply_common_placeholders(text)
    text = replace_user_id_block(text)

    doc_block_start = "        // ── Document fetch/save hooks"
    doc_block_end = "        // ── Conversation starter button"
    start_idx = text.index(doc_block_start)
    end_idx = text.index(doc_block_end)
    text = text[:start_idx] + "{{DOCUMENT_SAVE_BLOCK}}\n\n" + text[end_idx:]

    return apply_session_placeholders(
        text,
        "chatSessionId_gpt3_",
        "chatHistory_gpt3",
        r"// ── Session ID \(separate from chat_interface\.html / n8n GPT3 session\) ─",
        "console.log('Session ID (GPT3):', sessionId);",
    )


def main() -> None:
    TEMPLATES.mkdir(parents=True, exist_ok=True)
    LIB.mkdir(parents=True, exist_ok=True)
    (TEMPLATES / "chat_interface.base.html").write_text(make_base_template())
    (TEMPLATES / "chat_interface.extended.html").write_text(make_extended_template())
    (TEMPLATES / "chat_interface.extended_save.html").write_text(make_extended_save_template())
    print("Templates and chat_document_save.js created.")


if __name__ == "__main__":
    main()

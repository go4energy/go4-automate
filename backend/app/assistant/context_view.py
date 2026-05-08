"""Assistant conversation context view helpers."""


def build_voice_response_context(context: dict) -> dict:
    current_email = None
    email_list = context.get("email_list", [])
    idx = context.get("current_email_index", 0)
    if email_list and 1 <= idx <= len(email_list):
        current_email = email_list[idx - 1]

    return {
        "active_mailbox": context.get("active_mailbox"),
        "active_folder": context.get("active_folder_name"),
        "current_email": current_email,
        "email_count": len(email_list),
        "current_index": idx,
        "pending_draft_id": context.get("pending_draft_id")
        or (context.get("pending_reply") or {}).get("id"),
        "pending_intent_id": context.get("pending_intent_id")
        or (context.get("pending_confirmation") or {}).get("id"),
        "cleanup_preview_summary": (context.get("cleanup_preview") or {}).get(
            "summary"
        ),
    }


def build_context_summary(context: dict) -> str:
    parts = []
    email_list = context.get("email_list", [])
    idx = context.get("current_email_index", 0)
    active_mailbox = context.get("active_mailbox")
    active_folder = context.get("active_folder_name")

    if active_mailbox:
        parts.append(f"Aktives Postfach: {active_mailbox}.")
    if active_folder:
        parts.append(f"Aktiver Ordner: {active_folder}.")

    if email_list and 1 <= idx <= len(email_list):
        current = email_list[idx - 1]
        parts.append(
            f"Aktuelle Email: Von {current.get('sender', '?')} — "
            f"{current.get('subject', '?')}"
        )
        if current.get("has_attachments"):
            parts.append("Hat Anhaenge.")

    pending = context.get("pending_confirmation")
    if pending:
        action = pending.get("action", "?")
        subject = pending.get("subject", "")
        tool_hint = (
            "confirm_and_send mit confirmed=true"
            if action == "send_draft"
            else f"{action} mit confirmed=true"
        )
        parts.append(
            f"AUSSTEHENDE BESTAETIGUNG: {action} fuer '{subject}'. "
            f"Wenn der User 'ja', 'ok', 'mach das' oder aehnlich sagt, "
            f"rufe {tool_hint} auf. "
            f"Bei 'nein' oder 'abbrechen' sage dass es abgebrochen wurde."
        )

    pending_reply = context.get("pending_reply")
    if pending_reply:
        parts.append(
            f"ENTWURF BEREIT fuer {pending_reply.get('sender', '?')}. "
            f"Wenn der User bestaetigt, rufe confirm_and_send mit confirmed=true auf."
        )

    return " ".join(parts)

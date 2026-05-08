"""Assistant conversation policy helpers.

These helpers manage the canonical pending/draft markers inside the
conversation context. They are intentionally small and stateless so
that voice and later chat flows can share them.
"""


def set_pending_intent_context(
    context: dict,
    intent_id: int | None,
    action: str,
    *,
    target_ref: dict | None = None,
    payload: dict | None = None,
) -> None:
    context["pending_intent_id"] = intent_id
    context["pending_confirmation"] = {
        "id": intent_id,
        "action": action,
        **(target_ref or {}),
        **(payload or {}),
    }


def clear_pending_intent_context(context: dict) -> None:
    context["pending_intent_id"] = None
    context.pop("pending_confirmation", None)


def set_pending_draft_context(
    context: dict,
    draft_id: int | None,
    *,
    sender: str,
    subject: str,
    reply_text: str,
    email_id: str | None,
    draft_type: str,
) -> None:
    context["pending_draft_id"] = draft_id
    context["pending_reply"] = {
        "id": draft_id,
        "sender": sender,
        "subject": subject,
        "reply_text": reply_text,
        "email_id": email_id,
        "draft_type": draft_type,
    }


def clear_pending_draft_context(context: dict) -> None:
    context["pending_draft_id"] = None
    context.pop("pending_reply", None)

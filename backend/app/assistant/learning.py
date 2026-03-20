"""Assistant learning service - derives rules from user feedback + LLM classification."""

import json
from collections import defaultdict
from collections.abc import Iterable

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assistant.models import (
    AssistantFeedback,
    AssistantItem,
    AssistantProfile,
    AssistantRule,
    AssistantUndoLog,
)
from app.config import settings


class AssistantLearningService:
    """Analyses feedback patterns and suggests rules using LLM classification."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def suggest_rules(
        self,
        tenant_id: str,
        user_id: int,
        *,
        auto_apply: bool = True,
    ) -> list[dict]:
        """Analyse feedback, auto-activate ready rules, return remaining suggestions."""
        try:
            trust_settings = await self._load_trust_settings(tenant_id, user_id)
            sender_patterns = await self._find_sender_patterns(tenant_id, user_id)
            undo_patterns = await self._find_undo_log_patterns(tenant_id, user_id)
            status_patterns = await self._find_status_patterns(tenant_id, user_id)
            category_patterns = await self._find_category_feedback_patterns(
                tenant_id, user_id
            )
            suggestions = self._finalize_suggestions(
                [
                    *sender_patterns,
                    *undo_patterns,
                    *status_patterns,
                    *category_patterns,
                ],
                trust_settings=trust_settings,
            )

            # Auto-apply rules that are autopilot_ready
            if auto_apply:
                remaining = []
                for suggestion in suggestions:
                    if suggestion.get("autopilot_ready"):
                        try:
                            rule = await self.apply_suggestion(
                                tenant_id, user_id, suggestion
                            )
                            logger.info(
                                "Auto-activated rule: {name} (id={rid})",
                                name=rule.name,
                                rid=rule.id,
                            )
                            suggestion["auto_applied"] = True
                            suggestion["rule_id"] = rule.id
                        except Exception as exc:
                            logger.warning(
                                "Auto-apply failed for '{name}': {err}",
                                name=suggestion.get("name"),
                                err=str(exc),
                            )
                    remaining.append(suggestion)
                suggestions = remaining

            logger.info(
                "Generated {n} rule suggestions for user {uid}",
                n=len(suggestions),
                uid=user_id,
            )
            return suggestions
        except Exception as exc:
            logger.warning(
                "Rule suggestions unavailable, returning empty list: {err}",
                err=str(exc),
            )
            return []

    # ── Undo-Log patterns (move_email / delete_email) ─────────────

    async def _find_undo_log_patterns(self, tenant_id: str, user_id: int) -> list[dict]:
        """Find repeated move/delete actions and classify with LLM."""
        sender_col = AssistantUndoLog.target_ref_json["sender"].as_string()
        subject_col = AssistantUndoLog.target_ref_json["subject"].as_string()
        folder_col = AssistantUndoLog.after_state_json["folder_name"].as_string()

        result = await self.db.execute(
            select(
                sender_col.label("sender"),
                subject_col.label("subject"),
                AssistantUndoLog.action_type,
                folder_col.label("folder_name"),
            )
            .where(
                AssistantUndoLog.tenant_id == tenant_id,
                AssistantUndoLog.user_id == user_id,
                AssistantUndoLog.status.in_(["executed", "undone"]),
                sender_col.isnot(None),
                AssistantUndoLog.action_type.in_(["move_email", "delete_email"]),
            )
            .order_by(AssistantUndoLog.created_at.desc())
            .limit(200)
        )
        rows = result.all()

        # Group by (sender, action_type, folder_name)
        groups: dict[tuple, list[str]] = defaultdict(list)
        for sender, subject, action_type, folder_name in rows:
            key = (sender, action_type, folder_name or "")
            groups[key].append(subject or "")

        suggestions = []

        for (sender, action_type, folder_name), subjects in groups.items():
            if len(subjects) < 3:
                continue
            if await self._rule_exists_for_sender(tenant_id, user_id, sender):
                continue

            # LLM classification
            classification = await self._classify_email_group(
                sender, subjects, action_type, folder_name
            )

            if not classification or not classification.get("should_create_rule"):
                continue

            criteria = self._build_criteria_from_classification(sender, classification)
            count = len(subjects)

            if action_type == "move_email":
                action = "move"
                payload = {"target": folder_name or "Archive"}
                name = classification.get("rule_name", f"Mails von {sender}")
            else:
                action = "delete"
                payload = {}
                name = classification.get("rule_name", f"Mails von {sender} loeschen")

            base_conf = 0.62 if len(criteria) > 1 else 0.55
            suggestions.append(
                {
                    "name": name,
                    "match_criteria": criteria,
                    "action_type": action,
                    "action_payload": payload,
                    "risk_level": "low",
                    "confidence": min(base_conf + count * 0.07, 0.95),
                    "priority": 22 if len(criteria) > 1 else 20,
                    "reason": classification.get("reason", f"{count}x gleiche Aktion"),
                    "source": "undo_log",
                    "evidence_count": count,
                    "email_category": classification.get("category"),
                }
            )

        # Domain-level grouping
        domain_suggestions = await self._find_domain_patterns(groups, set(), "undo_log")
        suggestions.extend(domain_suggestions)

        return suggestions

    # ── Status patterns (move_to_status) ──────────────────────────

    async def _find_status_patterns(self, tenant_id: str, user_id: int) -> list[dict]:
        """Find repeated status moves with LLM classification."""
        sender_col = AssistantUndoLog.target_ref_json["sender"].as_string()
        subject_col = AssistantUndoLog.target_ref_json["subject"].as_string()
        status_col = AssistantUndoLog.after_state_json["status"].as_string()

        result = await self.db.execute(
            select(
                sender_col.label("sender"),
                subject_col.label("subject"),
                status_col.label("status"),
            )
            .where(
                AssistantUndoLog.tenant_id == tenant_id,
                AssistantUndoLog.user_id == user_id,
                AssistantUndoLog.status.in_(["executed", "undone"]),
                AssistantUndoLog.action_type == "move_to_status",
                sender_col.isnot(None),
                status_col.isnot(None),
            )
            .order_by(AssistantUndoLog.created_at.desc())
            .limit(200)
        )
        rows = result.all()

        # Group by (sender, status)
        groups: dict[tuple, list[str]] = defaultdict(list)
        for sender, subject, status in rows:
            key = (sender, status)
            groups[key].append(subject or "")

        suggestions = []

        for (sender, status), subjects in groups.items():
            if len(subjects) < 3:
                continue
            if await self._rule_exists_for_sender(
                tenant_id, user_id, sender, action_type="move_to_status"
            ):
                continue

            classification = await self._classify_email_group(
                sender, subjects, "move_to_status", status
            )

            if not classification or not classification.get("should_create_rule"):
                continue

            criteria = self._build_criteria_from_classification(sender, classification)
            count = len(subjects)

            base_conf = 0.65 if len(criteria) > 1 else 0.58
            suggestions.append(
                {
                    "name": classification.get(
                        "rule_name", f"Mails von {sender} → {status}"
                    ),
                    "match_criteria": criteria,
                    "action_type": "move_to_status",
                    "action_payload": {"status": status},
                    "risk_level": "low",
                    "confidence": min(base_conf + count * 0.07, 0.95),
                    "priority": 27 if len(criteria) > 1 else 25,
                    "reason": classification.get(
                        "reason", f"{count}x nach {status} verschoben"
                    ),
                    "source": "status_history",
                    "evidence_count": count,
                    "email_category": classification.get("category"),
                }
            )

        return suggestions

    # ── LLM Classification ────────────────────────────────────────

    async def _classify_email_group(
        self,
        sender: str,
        subjects: list[str],
        action_type: str,
        target: str,
    ) -> dict | None:
        """Ask LLM to classify a group of emails from one sender.

        Returns dict with:
          - should_create_rule: bool
          - category: str (e.g. "Newsletter", "Automatische Benachrichtigung")
          - rule_name: str (human-readable rule name)
          - reason: str (why this rule makes sense)
          - scope: "all" | "category" (all mails from sender, or only this type)
          - keywords: list[str] (optional distinguishing keywords)
        """
        # Deduplicate subjects for the prompt
        unique_subjects = list(dict.fromkeys(subjects))[:15]

        action_desc = {
            "move_email": f"nach '{target}' verschoben",
            "delete_email": "geloescht",
            "move_to_status": f"nach Status '{target}' verschoben",
        }.get(action_type, action_type)

        prompt = (
            f"Analysiere diese {len(subjects)} Emails vom Absender '{sender}'.\n"
            f"Der User hat sie alle {action_desc}.\n\n"
            f"Betreffzeilen:\n"
        )
        for i, subj in enumerate(unique_subjects, 1):
            prompt += f"  {i}. {subj}\n"

        prompt += (
            "\nBeantworte als JSON:\n"
            "{\n"
            '  "should_create_rule": true/false,  // Ergibt eine Regel Sinn?\n'
            '  "category": "...",  // Email-Kategorie (z.B. "Newsletter", '
            '"Automatische Benachrichtigung", "Meeting-Notification", '
            '"Marketing", "Persoenliche Mail")\n'
            '  "scope": "all" oder "category",  // "all" = alle Mails von '
            "diesem Absender gleich behandeln. "
            '"category" = nur diese Art von Mail\n'
            '  "keywords": [],  // Falls scope="category": Stichwoerter '
            "die diese Art von Mail identifizieren\n"
            '  "rule_name": "...",  // Kurzer Regelname auf Deutsch\n'
            '  "reason": "..."  // Warum diese Regel sinnvoll ist\n'
            "}\n\n"
            "Regeln:\n"
            "- should_create_rule=false wenn die Emails zu unterschiedlich "
            "sind (z.B. persoenliche Mails mit verschiedenen Themen)\n"
            "- scope='all' wenn ALLE Mails von diesem Absender gleich "
            "behandelt werden sollen (z.B. Newsletter, Notifications)\n"
            "- scope='category' wenn nur bestimmte Mails dieses Absenders "
            "betroffen sind\n"
            "- Antworte NUR mit dem JSON, kein anderer Text"
        )

        try:
            response_text = await self._llm_call(prompt)
            if not response_text:
                return None

            # Parse JSON from response (handle markdown code blocks)
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

            result = json.loads(cleaned)
            logger.debug(
                "LLM classification for {sender}: {result}",
                sender=sender,
                result=result,
            )
            return result
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning(
                "LLM classification parse error for {sender}: {err}",
                sender=sender,
                err=str(exc),
            )
            return None
        except Exception as exc:
            logger.warning(
                "LLM classification failed for {sender}: {err}",
                sender=sender,
                err=str(exc),
            )
            return None

    async def _llm_call(self, prompt: str) -> str | None:
        """Make a lightweight LLM call for classification."""
        if settings.anthropic_api_key:
            return await self._llm_call_anthropic(prompt)
        return await self._llm_call_openai_compat(prompt)

    async def _llm_call_anthropic(self, prompt: str) -> str | None:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.llm_model_content,
            max_tokens=300,
            temperature=0.1,
            system=(
                "Du bist ein Email-Klassifikations-Assistent. "
                "Antworte NUR mit validem JSON, kein anderer Text."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()

    async def _llm_call_openai_compat(self, prompt: str) -> str | None:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url=f"{settings.ollama_url}/v1",
            api_key="ollama",
        )
        response = await client.chat.completions.create(
            model=settings.ollama_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Du bist ein Email-Klassifikations-Assistent. "
                        "Antworte NUR mit validem JSON, kein anderer Text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.1,
        )
        return (response.choices[0].message.content or "").strip()

    # ── Build criteria from LLM result ────────────────────────────

    @staticmethod
    def _build_criteria_from_classification(sender: str, classification: dict) -> dict:
        """Convert LLM classification into match_criteria dict."""
        scope = classification.get("scope", "all")
        criteria: dict = {"sender_contains": sender}

        if scope == "category":
            keywords = classification.get("keywords", [])
            if keywords and isinstance(keywords, list):
                # Filter to meaningful keywords
                filtered = [k for k in keywords if isinstance(k, str) and len(k) >= 3]
                if filtered:
                    criteria["keywords"] = filtered[:3]

        return criteria

    # ── Domain-level grouping ─────────────────────────────────────

    async def _find_domain_patterns(
        self,
        groups: dict[tuple, list[str]],
        already_suggested: set[str],
        source: str,
    ) -> list[dict]:
        """Check if multiple senders from the same domain share the same action.

        Uses LLM to decide whether a domain-level rule is appropriate.
        """
        # Collect all subjects per (domain, action, target)
        domain_data: dict[tuple, dict[str, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for key, subjects in groups.items():
            sender = key[0]
            if not sender or "@" not in sender:
                continue
            domain = sender.split("@", 1)[1].lower()
            action_key = key[1] if len(key) >= 2 else ""
            folder_or_status = (
                key[2] if len(key) >= 3 else key[1] if len(key) >= 2 else ""
            )
            domain_group_key = (domain, action_key, folder_or_status)
            domain_data[domain_group_key][sender].extend(subjects)

        suggestions = []
        for (domain, action_key, target), senders_subjects in domain_data.items():
            unique_senders = set(senders_subjects.keys())
            if len(unique_senders) < 2:
                continue

            all_subjects = []
            for sender_subjects in senders_subjects.values():
                all_subjects.extend(sender_subjects)
            total_count = len(all_subjects)

            # Ask LLM whether a domain-level rule makes sense
            classification = await self._classify_domain_group(
                domain, senders_subjects, action_key, target
            )

            if not classification or not classification.get("should_create_rule"):
                continue

            suggestions.append(
                {
                    "name": classification.get(
                        "rule_name", f"Alle Mails von @{domain} → {target}"
                    ),
                    "match_criteria": {"sender_domain": domain},
                    "action_type": "move"
                    if action_key in ("move_email",)
                    else action_key,
                    "action_payload": {"target": target} if target else None,
                    "risk_level": "low",
                    "confidence": min(0.50 + total_count * 0.06, 0.90),
                    "priority": 15,
                    "reason": classification.get(
                        "reason",
                        f"{len(unique_senders)} Absender von @{domain}, "
                        f"{total_count}x gleiche Aktion",
                    ),
                    "source": source,
                    "evidence_count": total_count,
                    "email_category": classification.get("category"),
                }
            )

        return suggestions

    async def _classify_domain_group(
        self,
        domain: str,
        senders_subjects: dict[str, list[str]],
        action_type: str,
        target: str,
    ) -> dict | None:
        """Ask LLM whether a domain-level rule makes sense."""
        action_desc = {
            "move_email": f"nach '{target}' verschoben",
            "delete_email": "geloescht",
            "move_to_status": f"nach Status '{target}' verschoben",
        }.get(action_type, action_type)

        prompt = (
            f"Analysiere Emails von der Domain '@{domain}'.\n"
            f"Der User hat sie alle {action_desc}.\n\n"
        )
        for sender, subjects in senders_subjects.items():
            unique = list(dict.fromkeys(subjects))[:5]
            prompt += f"Absender: {sender}\n"
            for subj in unique:
                prompt += f"  - {subj}\n"
            prompt += "\n"

        prompt += (
            "Frage: Sollen ALLE Mails von @" + domain + " gleich "
            "behandelt werden, oder sind manche Absender anders "
            "(z.B. persoenliche Nachrichten vs. Notifications)?\n\n"
            "Antworte als JSON:\n"
            "{\n"
            '  "should_create_rule": true/false,\n'
            '  "category": "...",  // z.B. "Automatische Benachrichtigungen"\n'
            '  "rule_name": "...",\n'
            '  "reason": "..."\n'
            "}\n\n"
            "should_create_rule=false wenn die Absender verschiedene Arten "
            "von Mails senden (z.B. persoenliche Nachrichten vs. Marketing). "
            "Antworte NUR mit JSON."
        )

        try:
            response_text = await self._llm_call(prompt)
            if not response_text:
                return None
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
                cleaned = cleaned.rsplit("```", 1)[0]
            result = json.loads(cleaned.strip())
            logger.debug(
                "LLM domain classification for @{domain}: {result}",
                domain=domain,
                result=result,
            )
            return result
        except Exception as exc:
            logger.warning(
                "LLM domain classification failed for @{domain}: {err}",
                domain=domain,
                err=str(exc),
            )
            return None

    # ── Category feedback patterns ────────────────────────────────

    async def _find_category_feedback_patterns(
        self, tenant_id: str, user_id: int
    ) -> list[dict]:
        """Find repeated category feedback assignments for one sender."""
        cat_col = AssistantFeedback.feedback_payload_json["category_name"].as_string()
        result = await self.db.execute(
            select(
                AssistantItem.sender,
                cat_col.label("category_name"),
                func.count(AssistantFeedback.id).label("count"),
            )
            .join(AssistantItem, AssistantFeedback.item_id == AssistantItem.id)
            .where(
                AssistantFeedback.tenant_id == tenant_id,
                AssistantFeedback.user_id == user_id,
                AssistantItem.sender.isnot(None),
                cat_col.isnot(None),
            )
            .group_by(
                AssistantItem.sender,
                cat_col,
            )
            .having(func.count(AssistantFeedback.id) >= 3)
        )
        rows = result.all()

        suggestions = []
        for sender, category_name, count in rows:
            if await self._rule_exists_for_sender(
                tenant_id, user_id, sender, action_type="label"
            ):
                continue

            suggestions.append(
                {
                    "name": f"Mails von {sender} als {category_name} markieren",
                    "match_criteria": {"sender_contains": sender},
                    "action_type": "label",
                    "action_payload": {"category": category_name},
                    "risk_level": "low",
                    "confidence": min(0.52 + count * 0.09, 0.92),
                    "priority": 12,
                    "reason": f"{count}x Kategorie {category_name} fuer {sender}",
                    "source": "category_feedback",
                    "evidence_count": count,
                }
            )

        return suggestions

    # ── Sender feedback patterns ──────────────────────────────────

    async def _find_sender_patterns(self, tenant_id: str, user_id: int) -> list[dict]:
        """Find senders with repeated feedback of the same type."""
        result = await self.db.execute(
            select(
                AssistantItem.sender,
                AssistantFeedback.feedback_type,
                func.count(AssistantFeedback.id).label("count"),
            )
            .join(AssistantItem, AssistantFeedback.item_id == AssistantItem.id)
            .where(
                AssistantFeedback.tenant_id == tenant_id,
                AssistantFeedback.user_id == user_id,
                AssistantItem.sender.isnot(None),
            )
            .group_by(AssistantItem.sender, AssistantFeedback.feedback_type)
            .having(func.count(AssistantFeedback.id) >= 3)
        )
        rows = result.all()

        action_map = {
            "ignore": "mute",
            "move": "move",
            "delete": "archive",
            "keep": "prioritize",
        }

        suggestions = []
        for sender, feedback_type, count in rows:
            if await self._rule_exists_for_sender(tenant_id, user_id, sender):
                continue

            action_type = action_map.get(feedback_type, "label")
            suggestions.append(
                {
                    "name": f"Mails von {sender}: {feedback_type}",
                    "match_criteria": {"sender_contains": sender},
                    "action_type": action_type,
                    "risk_level": "low",
                    "confidence": min(0.5 + count * 0.1, 0.95),
                    "priority": 10,
                    "reason": f"{count}x '{feedback_type}' fuer Absender {sender}",
                    "source": "feedback",
                    "evidence_count": count,
                }
            )

        return suggestions

    # ── Apply / Finalize ──────────────────────────────────────────

    async def apply_suggestion(
        self,
        tenant_id: str,
        user_id: int,
        suggestion: dict,
    ) -> AssistantRule:
        """Convert a suggestion into a saved rule. Skips if duplicate."""
        normalized = self._normalize_suggestion(suggestion)
        criteria = normalized.get("match_criteria") or {}
        action_type = normalized.get("action_type", "label")

        # Check for existing rule with same sender + action
        sender = criteria.get("sender_contains") or criteria.get("sender_domain")
        if sender:
            key = (
                "sender_contains" if "sender_contains" in criteria else "sender_domain"
            )
            existing = await self.db.execute(
                select(AssistantRule).where(
                    AssistantRule.tenant_id == tenant_id,
                    AssistantRule.user_id == user_id,
                    AssistantRule.match_criteria_json[key].as_string() == sender,
                    AssistantRule.action_type == action_type,
                )
            )
            found = existing.scalar_one_or_none()
            if found:
                logger.debug(
                    "Rule already exists: {name} (id={rid})",
                    name=found.name,
                    rid=found.id,
                )
                return found

        rule = AssistantRule(
            tenant_id=tenant_id,
            user_id=user_id,
            name=normalized.get("name", "Gelernte Regel"),
            scope="user",
            priority=normalized.get("priority", 10),
            match_criteria_json=criteria,
            action_type=action_type,
            action_payload_json=normalized.get("action_payload"),
            risk_level=normalized.get("risk_level", "low"),
            origin="learned",
            confidence=normalized.get("confidence", 0.7),
        )
        self.db.add(rule)
        await self.db.flush()
        await self.db.refresh(rule)
        logger.info("Applied rule suggestion: {name}", name=rule.name)
        return rule

    def _finalize_suggestions(
        self,
        suggestions: Iterable[dict],
        *,
        trust_settings: dict | None = None,
    ) -> list[dict]:
        """Normalize, deduplicate and sort suggestion candidates."""
        by_key: dict[tuple, dict] = {}
        for raw in suggestions:
            normalized = self._normalize_suggestion(raw, trust_settings=trust_settings)
            if (
                normalized.get("confidence", 0.0)
                < (trust_settings or self._default_trust_settings())[
                    "suggestion_min_confidence"
                ]
            ):
                continue
            dedupe_key = (
                normalized.get("action_type"),
                _hashable_dict(normalized.get("match_criteria") or {}),
                _hashable_dict(normalized.get("action_payload") or {}),
            )
            existing = by_key.get(dedupe_key)
            if not existing or (
                normalized.get("evidence_count", 0),
                normalized.get("confidence", 0.0),
            ) > (
                existing.get("evidence_count", 0),
                existing.get("confidence", 0.0),
            ):
                by_key[dedupe_key] = normalized

        return sorted(
            by_key.values(),
            key=lambda item: (
                item.get("autopilot_ready", False),
                item.get("evidence_count", 0),
                item.get("confidence", 0.0),
                item.get("priority", 0),
            ),
            reverse=True,
        )

    def _normalize_suggestion(
        self, suggestion: dict, *, trust_settings: dict | None = None
    ) -> dict:
        """Ensure suggestion payloads have stable fields."""
        trust = trust_settings or self._default_trust_settings()
        match_criteria = dict(suggestion.get("match_criteria") or {})
        action_payload = dict(suggestion.get("action_payload") or {})
        action_type = str(suggestion.get("action_type") or "label")
        evidence_count = int(suggestion.get("evidence_count") or 0)
        confidence = float(suggestion.get("confidence") or 0.0)
        risk_level = str(suggestion.get("risk_level", "low"))

        autopilot_blockers: list[str] = []
        if action_type in {"move", "archive"} and not action_payload.get("target"):
            autopilot_blockers.append("Kein Zielordner hinterlegt")
        if action_type == "move_to_status" and not action_payload.get("status"):
            autopilot_blockers.append("Kein Assistant-Status hinterlegt")
        if action_type == "label" and not action_payload.get("category"):
            autopilot_blockers.append("Keine Kategorie hinterlegt")
        if action_type == "delete":
            autopilot_blockers.append("Loeschen bleibt manuelle Entscheidung")
        if confidence < trust["autopilot_min_confidence"]:
            autopilot_blockers.append("Confidence unter Autopilot-Schwelle")
        if evidence_count < 4:
            autopilot_blockers.append("Zu wenig Wiederholungen fuer Autopilot")
        if self._risk_rank(risk_level) > self._risk_rank(
            trust["autopilot_max_rule_risk"]
        ):
            autopilot_blockers.append("Risikostufe ueber Autopilot-Limit")
        if confidence < trust["suggestion_min_confidence"]:
            autopilot_blockers.append("Unter Suggestion-Schwelle")

        return {
            "name": suggestion.get("name", "Gelernte Regel"),
            "match_criteria": match_criteria,
            "action_type": action_type,
            "action_payload": action_payload or None,
            "risk_level": risk_level,
            "confidence": confidence,
            "priority": int(suggestion.get("priority") or 10),
            "reason": suggestion.get("reason", "Kein Grund angegeben"),
            "source": suggestion.get("source", "unknown"),
            "evidence_count": evidence_count,
            "email_category": suggestion.get("email_category"),
            "autopilot_ready": len(autopilot_blockers) == 0,
            "autopilot_blockers": autopilot_blockers,
        }

    # ── Helpers ───────────────────────────────────────────────────

    async def _rule_exists_for_sender(
        self,
        tenant_id: str,
        user_id: int,
        sender: str,
        *,
        action_type: str | None = None,
    ) -> bool:
        """Check if a rule already exists for this sender."""
        query = select(AssistantRule.id).where(
            AssistantRule.tenant_id == tenant_id,
            AssistantRule.user_id == user_id,
            AssistantRule.match_criteria_json["sender_contains"].as_string() == sender,
        )
        if action_type:
            query = query.where(AssistantRule.action_type == action_type)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def _load_trust_settings(self, tenant_id: str, user_id: int) -> dict:
        result = await self.db.execute(
            select(AssistantProfile).where(
                AssistantProfile.tenant_id == tenant_id,
                AssistantProfile.user_id == user_id,
            )
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return self._default_trust_settings()
        return {
            "autopilot_min_confidence": float(profile.autopilot_min_confidence or 0.85),
            "autopilot_max_rule_risk": str(profile.autopilot_max_rule_risk or "medium"),
            "suggestion_min_confidence": float(
                profile.suggestion_min_confidence or 0.70
            ),
        }

    @staticmethod
    def _default_trust_settings() -> dict:
        return {
            "autopilot_min_confidence": 0.85,
            "autopilot_max_rule_risk": "medium",
            "suggestion_min_confidence": 0.70,
        }

    @staticmethod
    def _risk_rank(risk_level: str) -> int:
        return {"low": 1, "medium": 2, "high": 3}.get(str(risk_level), 99)


# ── Pure helpers ─────────────────────────────────────────────────


def _hashable_dict(d: dict) -> tuple:
    """Convert a dict with possible list values to a hashable tuple."""
    items = []
    for k, v in sorted(d.items()):
        if isinstance(v, list):
            items.append((k, tuple(v)))
        else:
            items.append((k, v))
    return tuple(items)

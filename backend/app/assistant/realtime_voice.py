"""OpenAI Realtime Voice bridge — WebSocket relay with tool execution."""

import asyncio
import json

import websockets
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from loguru import logger

from app.config import settings

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"
OPENAI_REALTIME_MODEL = "gpt-4o-mini-realtime-preview"

router = APIRouter(tags=["realtime-voice"])


def _build_system_instructions(*, ai_suggestions_enabled: bool = False) -> str:
    """Build the system prompt for the Realtime session — same rules as text chat."""
    from app.assistant.tool_registry import AI_SUGGESTIONS_PROMPT, SYSTEM_PROMPT

    prompt = SYSTEM_PROMPT
    if ai_suggestions_enabled:
        prompt += AI_SUGGESTIONS_PROMPT
    prompt += (
        "\n\nREALTIME VOICE SESSION:"
        "\n- Beim Start: Sage NUR kurz 'Hallo, was kann ich fuer dich tun?' und WARTE."
        "\n- Starte KEINE Aktion von dir aus. Warte IMMER auf den User."
        "\n- Fuehre NICHTS aus bis der User eine Anweisung gibt."
    )
    return prompt


def _build_tools_for_realtime() -> list[dict]:
    """Convert assistant tools to OpenAI Realtime format."""
    from app.assistant.tool_registry import TOOLS

    realtime_tools = []
    for tool in TOOLS:
        fn = tool.get("function", {})
        realtime_tools.append(
            {
                "type": "function",
                "name": fn["name"],
                "description": fn.get("description", ""),
                "parameters": fn.get(
                    "parameters", {"type": "object", "properties": {}}
                ),
            }
        )
    return realtime_tools


@router.websocket("/ws/voice-realtime")
async def voice_realtime_ws(
    ws: WebSocket,
    token: str = Query(default=""),
):
    """WebSocket bridge: Browser ↔ Backend ↔ OpenAI Realtime API.

    The browser sends audio chunks and receives audio + transcript + tool results.
    Tool calls are executed locally against the go4-automate API.
    The OpenAI API key never leaves the server.
    """
    await ws.accept()

    if not settings.openai_api_key:
        await ws.send_json(
            {"type": "error", "message": "OpenAI API Key nicht konfiguriert"}
        )
        await ws.close()
        return

    # Authenticate user from token
    tenant_id, user_id = await _authenticate_ws(token)
    if not tenant_id:
        await ws.send_json({"type": "error", "message": "Nicht authentifiziert"})
        await ws.close()
        return

    logger.info(
        "Realtime voice session: tenant={t} user={u}",
        t=tenant_id,
        u=user_id,
    )

    # Connect to OpenAI Realtime API
    openai_headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "OpenAI-Beta": "realtime=v1",
    }
    openai_url = f"{OPENAI_REALTIME_URL}?model={OPENAI_REALTIME_MODEL}"

    try:
        logger.info("Connecting to OpenAI Realtime: {url}", url=openai_url)
        async with websockets.connect(
            openai_url,
            additional_headers=openai_headers,
            max_size=2**24,
        ) as openai_ws:
            logger.info("OpenAI Realtime connected")

            # Load user profile for settings
            from app.assistant.models import AssistantProfile
            from app.database import async_session

            ai_suggestions = False
            async with async_session() as db:
                from sqlalchemy import select

                result = await db.execute(
                    select(AssistantProfile).where(
                        AssistantProfile.tenant_id == tenant_id,
                        AssistantProfile.user_id == user_id,
                    )
                )
                profile = result.scalar_one_or_none()
                if profile:
                    ai_suggestions = bool(profile.ai_suggestions_enabled)

            # Configure session with full system prompt
            await _configure_session(openai_ws, ai_suggestions_enabled=ai_suggestions)
            logger.info("OpenAI session configured")

            # Notify client that session is ready
            await ws.send_json(
                {"type": "session.ready", "model": OPENAI_REALTIME_MODEL}
            )
            logger.info("Client notified: session.ready")

            # Create tool executor for this session
            executor = await _create_executor(tenant_id, user_id)
            logger.info("Tool executor created, starting relay")

            # Run bidirectional relay — cancel all on first exit
            tasks = [
                asyncio.create_task(_relay_client_to_openai(ws, openai_ws)),
                asyncio.create_task(
                    _relay_openai_to_client(
                        ws, openai_ws, executor, tenant_id, user_id
                    )
                ),
            ]
            try:
                done, pending = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )
                # Log which task finished first
                for t in done:
                    if t.exception():
                        logger.error("Relay task error: {e}", e=t.exception())
                    else:
                        logger.info("Relay task completed normally")
            finally:
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    except (websockets.ConnectionClosed, WebSocketDisconnect):
        logger.info("Realtime voice session ended")
    except Exception:
        logger.exception("Realtime voice session error")
        import contextlib

        with contextlib.suppress(Exception):
            await ws.send_json({"type": "error", "message": "Verbindungsfehler"})


async def _configure_session(
    openai_ws, *, ai_suggestions_enabled: bool = False
) -> None:
    """Send session.update to configure the OpenAI Realtime session."""
    config = {
        "type": "session.update",
        "session": {
            "modalities": ["text", "audio"],
            "instructions": _build_system_instructions(
                ai_suggestions_enabled=ai_suggestions_enabled
            ),
            "voice": "coral",
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {"model": "whisper-1"},
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.5,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 700,
            },
            "tools": _build_tools_for_realtime(),
        },
    }
    await openai_ws.send(json.dumps(config))


async def _relay_client_to_openai(client_ws: WebSocket, openai_ws) -> None:
    """Forward client messages to OpenAI Realtime API."""
    try:
        while True:
            data = await client_ws.receive_text()
            msg = json.loads(data)

            # Only forward allowed event types
            allowed = {
                "input_audio_buffer.append",
                "input_audio_buffer.commit",
                "input_audio_buffer.clear",
                "response.create",
                "response.cancel",
                "conversation.item.create",
            }
            if msg.get("type") in allowed:
                await openai_ws.send(data)
    except WebSocketDisconnect:
        logger.info("Client disconnected during input relay")
    except Exception:
        logger.exception("Client relay error")


async def _relay_openai_to_client(
    client_ws: WebSocket,
    openai_ws,
    executor,
    tenant_id: str,
    user_id: int,
) -> None:
    """Forward OpenAI events to client, intercept tool calls for local execution."""
    # Accumulate function call arguments
    fn_call_args: dict[str, str] = {}
    fn_call_names: dict[str, str] = {}
    fn_call_ids: dict[str, str] = {}

    try:
        async for raw in openai_ws:
            msg = json.loads(raw)
            event_type = msg.get("type", "")

            # Track function call arguments
            if event_type == "response.function_call_arguments.delta":
                item_id = msg.get("item_id", "")
                fn_call_args.setdefault(item_id, "")
                fn_call_args[item_id] += msg.get("delta", "")
                fn_call_ids[item_id] = msg.get("call_id", "")
                # Forward to client for UI display
                await client_ws.send_text(raw)
                continue

            # Function call complete — execute locally
            if event_type == "response.output_item.done":
                item = msg.get("item", {})
                if item.get("type") == "function_call":
                    item_id = item.get("id", "")
                    call_id = item.get("call_id", fn_call_ids.get(item_id, ""))
                    fn_name = item.get("name", "")
                    args_str = fn_call_args.pop(item_id, "{}")

                    try:
                        fn_args = json.loads(args_str)
                    except json.JSONDecodeError:
                        fn_args = {}

                    # Notify client about tool execution
                    await client_ws.send_json(
                        {
                            "type": "tool.executing",
                            "tool_name": fn_name,
                            "tool_args": fn_args,
                        }
                    )

                    # Execute tool locally
                    result = await _execute_tool(
                        executor, fn_name, fn_args, tenant_id, user_id
                    )

                    # Notify client about result
                    await client_ws.send_json(
                        {
                            "type": "tool.result",
                            "tool_name": fn_name,
                            "result": result[:500],
                        }
                    )

                    # Submit result to OpenAI
                    tool_result = {
                        "type": "conversation.item.create",
                        "item": {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": result,
                        },
                    }
                    await openai_ws.send(json.dumps(tool_result))

                    # Trigger continuation
                    await openai_ws.send(json.dumps({"type": "response.create"}))

                    # Clean up
                    fn_call_ids.pop(item_id, None)
                    fn_call_names.pop(item_id, None)
                    continue

            # Forward everything else to client
            # (audio deltas, transcripts, session events, etc.)
            if event_type.startswith("response.audio"):
                logger.debug("Relay to client: {t} (len={l})", t=event_type, l=len(raw))
            elif event_type not in ("response.audio.delta",):
                logger.debug("Relay to client: {t}", t=event_type)
            await client_ws.send_text(raw)

    except WebSocketDisconnect:
        logger.info("Client disconnected during relay")
    except Exception:
        logger.exception("OpenAI relay error")


async def _execute_tool(
    executor, tool_name: str, tool_args: dict, tenant_id: str, user_id: int
) -> str:
    """Execute a tool using the existing VoiceToolExecutor."""
    try:
        result = await executor.execute(tool_name, tool_args)
        logger.info(
            "Realtime tool: {name} → {r}",
            name=tool_name,
            r=result[:100],
        )
        return result
    except Exception as exc:
        logger.exception("Realtime tool error: {name}", name=tool_name)
        return f"Fehler bei {tool_name}: {str(exc)[:200]}"


async def _create_executor(tenant_id: str, user_id: int):
    """Create a VoiceToolExecutor for the realtime session."""
    from app.assistant.service import AssistantService
    from app.assistant.tool_executor import VoiceToolExecutor
    from app.assistant.voice_runtime import DEFAULT_VOICE_CONTEXT, VoiceRuntimeSupport
    from app.database import async_session

    async with async_session() as db:
        svc = AssistantService(db)
        profile = await svc.get_or_create_profile(tenant_id, user_id)

        runtime = VoiceRuntimeSupport(db)
        (
            access_token,
            mailbox,
            connection_id,
            provider,
        ) = await runtime.get_voice_connection(tenant_id, user_id)

        executor = VoiceToolExecutor(
            access_token=access_token,
            mailbox=mailbox,
            context=dict(DEFAULT_VOICE_CONTEXT),
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            provider=provider,
            connection_id=connection_id,
            skip_confirmation=bool(profile.skip_confirmation),
        )
        # Detach executor from this session — it will create its own sessions per call
        executor._detached_db = True
        return executor


async def _authenticate_ws(token: str) -> tuple[str | None, int | None]:
    """Authenticate WebSocket connection from JWT token."""
    if not token:
        return None, None

    try:
        from app.auth.service import AuthService
        from app.database import async_session

        async with async_session() as db:
            auth_svc = AuthService(db)
            user = await auth_svc.get_user_from_token(token)
            if user:
                return user.tenant_id, user.id
    except Exception:
        logger.warning("Realtime WS auth failed")

    return None, None

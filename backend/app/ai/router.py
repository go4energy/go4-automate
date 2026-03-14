"""AI Setup router - endpoints for prompts, context, and onboarding."""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import (
    ContextVariableDelete,
    ContextVariableUpdate,
    ModuleContextResponse,
    ModuleContextUpdate,
    ModuleParameterCreate,
    ModuleParameterResponse,
    ModuleParameterUpdate,
    ModuleParameterValueUpdate,
    OnboardingChatRequest,
    OnboardingChatResponse,
    OnboardingResetResponse,
    OnboardingStartResponse,
    PromptCreate,
    PromptListResponse,
    PromptResponse,
    PromptUpdate,
)
from app.ai.service import AISetupService
from app.database import get_db
from app.exceptions import AppError
from app.utils.dependencies import get_current_tenant_id

router = APIRouter(prefix="/ai", tags=["ai"])


def get_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> AISetupService:
    """Dependency to get AISetupService."""
    return AISetupService(db, tenant_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Module Context Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/modules/{module}/context", response_model=ModuleContextResponse)
async def get_module_context(
    module: str,
    service: AISetupService = Depends(get_service),
):
    """Get the context (extracted parameters) for a module."""
    context = await service.get_or_create_module_context(module)
    return context


@router.get("/modules/{module}/setup-schema")
async def get_module_setup_schema(
    module: str,
    service: AISetupService = Depends(get_service),
):
    """Return unified module metadata for chatbot-driven setup and control."""
    return await service.get_unified_setup_schema(module)


@router.get("/modules/{module}/config")
async def get_module_config(
    module: str,
    service: AISetupService = Depends(get_service),
):
    """Read canonical module config via the module interface."""
    try:
        return await service.get_module_config(module)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.put("/modules/{module}/config")
async def update_module_config(
    module: str,
    updates: dict,
    service: AISetupService = Depends(get_service),
):
    """Update canonical module config via the module interface."""
    try:
        return await service.update_module_config(module, updates)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post("/modules/{module}/actions/{action_key}")
async def invoke_module_action(
    module: str,
    action_key: str,
    payload: dict | None = None,
    service: AISetupService = Depends(get_service),
):
    """Execute a declared module action for chatbot/admin workflows."""
    try:
        return await service.invoke_module_action(module, action_key, payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except AppError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
        ) from e


@router.put("/modules/{module}/context", response_model=ModuleContextResponse)
async def update_module_context(
    module: str,
    data: ModuleContextUpdate,
    service: AISetupService = Depends(get_service),
):
    """Update the context for a module."""
    return await service.update_module_context(module, data)


@router.put("/modules/{module}/context/variable", response_model=ModuleContextResponse)
async def set_context_variable(
    module: str,
    data: ContextVariableUpdate,
    service: AISetupService = Depends(get_service),
):
    """Set a single variable in module context."""
    return await service.set_context_variable(module, data.key, data.value)


@router.delete(
    "/modules/{module}/context/variable", response_model=ModuleContextResponse
)
async def delete_context_variable(
    module: str,
    data: ContextVariableDelete,
    service: AISetupService = Depends(get_service),
):
    """Delete a variable from module context."""
    return await service.delete_context_variable(module, data.key)


# ═══════════════════════════════════════════════════════════════════════════════
# Module Parameter Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/modules/{module}/parameters", response_model=list[ModuleParameterResponse]
)
async def get_module_parameters(
    module: str,
    service: AISetupService = Depends(get_service),
):
    """Get all parameters for a module."""
    return await service.get_module_parameters(module)


@router.post(
    "/modules/{module}/parameters",
    response_model=ModuleParameterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_parameter(
    module: str,
    data: ModuleParameterCreate,
    service: AISetupService = Depends(get_service),
):
    """Create a new parameter for a module."""
    existing = await service.get_parameter(module, data.variable)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Parameter '{data.variable}' already exists",
        )
    return await service.create_parameter(module, data)


@router.put(
    "/modules/{module}/parameters/{variable}", response_model=ModuleParameterResponse
)
async def update_parameter(
    module: str,
    variable: str,
    data: ModuleParameterUpdate,
    service: AISetupService = Depends(get_service),
):
    """Update an existing parameter."""
    param = await service.update_parameter(module, variable, data)
    if not param:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parameter '{variable}' not found",
        )
    return param


@router.patch(
    "/modules/{module}/parameters/{variable}/value",
    response_model=ModuleParameterResponse,
)
async def set_parameter_value(
    module: str,
    variable: str,
    data: ModuleParameterValueUpdate,
    service: AISetupService = Depends(get_service),
):
    """Set just the value of a parameter."""
    param = await service.set_parameter_value(module, variable, data.value)
    if not param:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parameter '{variable}' not found",
        )
    return param


@router.delete(
    "/modules/{module}/parameters/{variable}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_parameter(
    module: str,
    variable: str,
    service: AISetupService = Depends(get_service),
):
    """Delete a parameter."""
    success = await service.delete_parameter(module, variable)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parameter '{variable}' not found",
        )


@router.put("/modules/{module}/parameters/reorder")
async def reorder_parameters(
    module: str,
    order: list[str],
    service: AISetupService = Depends(get_service),
):
    """
    Reorder parameters by providing a list of variable names in the desired order.
    """
    params = await service.get_module_parameters(module)
    param_map = {p.variable: p for p in params}

    for i, variable in enumerate(order):
        if variable in param_map:
            param_map[variable].sort_order = i

    from sqlalchemy.orm.attributes import flag_modified

    for p in params:
        flag_modified(p, "sort_order")

    await service.db.commit()
    return {"success": True, "order": order}


# ═══════════════════════════════════════════════════════════════════════════════
# Prompt Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/modules/{module}/prompts", response_model=PromptListResponse)
async def get_module_prompts(
    module: str,
    service: AISetupService = Depends(get_service),
):
    """Get all prompts for a module, grouped by type."""
    setup_prompts = await service.get_module_prompts(module, "setup")
    productive_prompts = await service.get_module_prompts(module, "productive")
    return PromptListResponse(
        setup=[PromptResponse.model_validate(p) for p in setup_prompts],
        productive=[PromptResponse.model_validate(p) for p in productive_prompts],
    )


@router.get("/modules/{module}/prompts/{slug}", response_model=PromptResponse)
async def get_prompt(
    module: str,
    slug: str,
    service: AISetupService = Depends(get_service),
):
    """Get a specific prompt by slug."""
    prompt = await service.get_prompt_by_slug(module, slug)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{slug}' not found in module '{module}'",
        )
    return prompt


@router.post(
    "/modules/{module}/prompts",
    response_model=PromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt(
    module: str,
    data: PromptCreate,
    service: AISetupService = Depends(get_service),
):
    """Create a new prompt for a module."""
    # Ensure module matches
    data.module = module
    try:
        return await service.create_prompt(data)
    except Exception as e:
        logger.exception("Error creating prompt")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.put("/modules/{module}/prompts/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    module: str,
    prompt_id: int,
    data: PromptUpdate,
    service: AISetupService = Depends(get_service),
):
    """Update an existing prompt."""
    prompt = await service.update_prompt(prompt_id, data)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )
    return prompt


@router.delete(
    "/modules/{module}/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_prompt(
    module: str,
    prompt_id: int,
    service: AISetupService = Depends(get_service),
):
    """Delete a prompt (soft delete)."""
    success = await service.delete_prompt(prompt_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found or is a system prompt",
        )


@router.put("/modules/{module}/prompts/reorder/{prompt_type}")
async def reorder_prompts(
    module: str,
    prompt_type: str,
    order: list[int],
    service: AISetupService = Depends(get_service),
):
    """
    Reorder prompts by providing a list of prompt IDs in the desired order.
    prompt_type should be 'setup' or 'productive'.
    """
    prompts = await service.get_module_prompts(module, prompt_type)
    prompt_map = {p.id: p for p in prompts}

    for i, prompt_id in enumerate(order):
        if prompt_id in prompt_map:
            prompt_map[prompt_id].sort_order = i

    await service.db.commit()
    return {"success": True, "order": order}


# ═══════════════════════════════════════════════════════════════════════════════
# Onboarding Endpoints
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/modules/{module}/onboarding/start", response_model=OnboardingStartResponse
)
async def start_onboarding(
    module: str,
    service: AISetupService = Depends(get_service),
):
    """Start an onboarding conversation for a module."""
    try:
        # Ensure onboarding prompt exists
        await service.ensure_onboarding_prompt(module)

        conversation, first_message = await service.start_onboarding(module)
        return OnboardingStartResponse(
            conversation_id=conversation.id,
            first_message=first_message,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Error starting onboarding")
        # Pass through the actual error message for transparency
        error_message = str(e) if str(e) else "Failed to start onboarding"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message,
        ) from e


@router.post(
    "/modules/{module}/onboarding/{conversation_id}/chat",
    response_model=OnboardingChatResponse,
)
async def onboarding_chat(
    module: str,
    conversation_id: int,
    data: OnboardingChatRequest,
    service: AISetupService = Depends(get_service),
):
    """Continue an onboarding conversation."""
    try:
        return await service.continue_onboarding(module, conversation_id, data.message)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.exception("Error in onboarding chat")
        error_message = str(e) if str(e) else "Failed to process message"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message,
        ) from e


@router.post(
    "/modules/{module}/onboarding/reset", response_model=OnboardingResetResponse
)
async def reset_onboarding(
    module: str,
    service: AISetupService = Depends(get_service),
):
    """Reset onboarding for a module (clears context and status)."""
    await service.reset_onboarding(module)
    return OnboardingResetResponse(
        success=True,
        message=f"Onboarding for {module} has been reset",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Prompt Rendering (for n8n/system use)
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/modules/{module}/prompts/{slug}/render")
async def render_prompt(
    module: str,
    slug: str,
    extra_vars: dict | None = None,
    service: AISetupService = Depends(get_service),
):
    """
    Render a prompt with context variables substituted.
    Can pass extra_vars for additional runtime variables (e.g., lead data).
    """
    result = await service.render_prompt(module, slug, extra_vars)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt '{slug}' not found in module '{module}'",
        )
    system_prompt, user_prompt = result
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }

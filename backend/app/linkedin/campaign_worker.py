"""LinkedIn campaign worker - processes campaign leads and executes steps."""

import asyncio
import random
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Activity logging imports
from app.engagement import (
    LinkedInActivityType,
    log_linkedin_activity,
)
from app.linkedin.models import (
    LinkedInAccount,
    LinkedInCampaign,
    LinkedInCampaignLead,
    LinkedInCampaignStep,
    LinkedInConnection,
    LinkedInMessage,
    LinkedInMessageTemplate,
)
from app.linkedin.safety_service import SafetyService


class CampaignWorker:
    """Processes campaign leads and executes automation steps."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.safety = SafetyService(db)

    async def process_campaign(self, campaign_id: int, tenant_id: str) -> dict:
        """Process a single campaign - execute pending steps for all ready leads.

        Returns:
            dict: Processing results
        """
        # Load campaign with steps
        result = await self.db.execute(
            select(LinkedInCampaign)
            .options(selectinload(LinkedInCampaign.steps))
            .where(
                LinkedInCampaign.id == campaign_id,
                LinkedInCampaign.tenant_id == tenant_id,
            )
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            return {"error": "Campaign not found"}

        if campaign.status != "active":
            return {"error": f"Campaign is not active (status: {campaign.status})"}

        # Get account
        account = await self.safety.get_account(campaign.account_id, tenant_id)
        if not account:
            return {"error": "Account not found"}

        # Get leads ready for action
        leads_ready = await self._get_ready_leads(campaign)
        if not leads_ready:
            return {"processed": 0, "message": "No leads ready for action"}

        processed = 0
        errors = []

        for lead in leads_ready:
            try:
                result = await self._process_lead(campaign, lead, account)
                if result.get("success"):
                    processed += 1
                else:
                    errors.append({
                        "lead_id": lead.id,
                        "error": result.get("error", "Unknown error"),
                    })
            except Exception as e:
                logger.exception(f"Error processing lead {lead.id}")
                errors.append({
                    "lead_id": lead.id,
                    "error": str(e),
                })

            # Random delay between leads
            await asyncio.sleep(random.uniform(2, 5))

        return {
            "processed": processed,
            "errors": len(errors),
            "error_details": errors,
        }

    async def _get_ready_leads(self, campaign: LinkedInCampaign) -> list[LinkedInCampaignLead]:
        """Get leads that are ready for their next action."""
        now = datetime.utcnow()

        result = await self.db.execute(
            select(LinkedInCampaignLead)
            .where(
                LinkedInCampaignLead.campaign_id == campaign.id,
                LinkedInCampaignLead.status.in_(["pending", "active", "waiting"]),
                LinkedInCampaignLead.next_action_at <= now,
            )
            .order_by(LinkedInCampaignLead.next_action_at)
            .limit(50)  # Process max 50 leads per run
        )
        return list(result.scalars().all())

    async def _process_lead(
        self,
        campaign: LinkedInCampaign,
        lead: LinkedInCampaignLead,
        account: LinkedInAccount,
    ) -> dict:
        """Process a single lead - execute their current step."""
        # Get current step
        if lead.current_step_id:
            result = await self.db.execute(
                select(LinkedInCampaignStep).where(
                    LinkedInCampaignStep.id == lead.current_step_id
                )
            )
            step = result.scalar_one_or_none()
        else:
            # Find first step
            step = next((s for s in campaign.steps if s.order == 1), None)

        if not step:
            # No more steps - mark as completed
            lead.status = "completed"
            lead.completed_at = datetime.utcnow()
            await self.db.commit()
            return {"success": True, "action": "completed"}

        # Check safety limits
        action_type = self._get_action_type(step.step_type)
        if action_type:
            can_perform, reason = await self.safety.can_perform_action(account, action_type)
            if not can_perform:
                logger.warning(f"Cannot perform action for lead {lead.id}: {reason}")
                return {"success": False, "error": reason}

        # Execute step
        result = await self._execute_step(campaign, lead, step, account)

        if result.get("success"):
            # Record action
            if action_type:
                await self.safety.record_action(account, action_type)

            # Advance to next step
            await self._advance_lead(campaign, lead, step)

        return result

    def _get_action_type(self, step_type: str) -> str | None:
        """Map step type to action type for limit checking."""
        mapping = {
            "connect": "connection",
            "message": "message",
            "inmail": "message",
            "view_profile": "profile",
        }
        return mapping.get(step_type)

    async def _execute_step(
        self,
        campaign: LinkedInCampaign,
        lead: LinkedInCampaignLead,
        step: LinkedInCampaignStep,
        account: LinkedInAccount,
    ) -> dict:
        """Execute a campaign step."""
        step_type = step.step_type

        if step_type == "wait":
            # Just advance timing
            return {"success": True, "action": "wait"}

        if step_type == "condition":
            # Evaluate condition
            return await self._evaluate_condition(campaign, lead, step)

        if step_type == "connect":
            return await self._execute_connect(campaign, lead, step, account)

        if step_type == "message":
            return await self._execute_message(campaign, lead, step, account)

        if step_type == "view_profile":
            return await self._execute_view_profile(lead, account)

        if step_type == "follow":
            return await self._execute_follow(lead, account)

        return {"success": False, "error": f"Unknown step type: {step_type}"}

    async def _execute_connect(
        self,
        campaign: LinkedInCampaign,
        lead: LinkedInCampaignLead,
        step: LinkedInCampaignStep,
        account: LinkedInAccount,
    ) -> dict:
        """Execute a connection request step."""
        # Get template if specified
        message = None
        if step.template_ids:
            # A/B test - pick random template
            template_id = random.choice(step.template_ids)
            template = await self._get_template(template_id)
            if template:
                context = self._build_template_context(lead)
                message = template.render(context)
                lead.ab_variant = template.variant_name or "A"
        elif step.template_id:
            template = await self._get_template(step.template_id)
            if template:
                context = self._build_template_context(lead)
                message = template.render(context)

        # Create connection record
        connection = LinkedInConnection(
            tenant_id=campaign.tenant_id,
            account_id=account.id,
            contact_id=lead.contact_id,
            linkedin_url=lead.linkedin_url,
            linkedin_id=lead.linkedin_id,
            profile_name=lead.profile_name,
            profile_headline=lead.profile_headline,
            profile_picture_url=lead.profile_picture_url,
            message=message[:300] if message else None,  # Connection note max 300 chars
            template_id=step.template_id,
            status="pending",
            campaign_id=campaign.id,
            campaign_lead_id=lead.id,
        )
        self.db.add(connection)

        # Update lead connection status
        lead.connection_status = "pending"

        # In production, would call browser automation here:
        # await self.browser.send_connection_request(account, lead.linkedin_url, message)

        # For now, simulate success
        connection.status = "sent"
        connection.sent_at = datetime.utcnow()

        # Log activity if contact is linked
        if lead.contact_id:
            try:
                await log_linkedin_activity(
                    db=self.db,
                    tenant_id=campaign.tenant_id,
                    contact_id=lead.contact_id,
                    activity_type=LinkedInActivityType.CONNECTION_REQUEST_SENT,
                    content=message,
                    external_id=str(connection.id),
                    metadata={
                        "linkedin_url": lead.linkedin_url,
                        "campaign_id": campaign.id,
                        "campaign_name": campaign.name,
                        "template_id": step.template_id,
                    },
                    commit=False,
                )
            except Exception as e:
                logger.warning(
                    f"Activity logging failed for connection {connection.id}: {e}"
                )

        await self.db.commit()

        logger.info(f"Connection request sent for lead {lead.id} in campaign {campaign.id}")
        return {"success": True, "action": "connect", "connection_id": connection.id}

    async def _execute_message(
        self,
        campaign: LinkedInCampaign,
        lead: LinkedInCampaignLead,
        step: LinkedInCampaignStep,
        account: LinkedInAccount,
    ) -> dict:
        """Execute a message step."""
        # Check if connected (required for DM)
        if lead.connection_status != "accepted":
            # Check if they actually accepted
            is_connected = await self._check_connection_accepted(lead)
            if not is_connected:
                return {"success": False, "error": "Not connected - cannot send message"}
            lead.connection_status = "accepted"

        # Get template
        if not step.template_ids and not step.template_id:
            return {"success": False, "error": "No template configured for message step"}

        template_id = step.template_id
        if step.template_ids:
            template_id = random.choice(step.template_ids)
            lead.ab_variant = chr(65 + step.template_ids.index(template_id))  # A, B, C...

        template = await self._get_template(template_id)
        if not template:
            return {"success": False, "error": f"Template {template_id} not found"}

        context = self._build_template_context(lead)
        content = template.render(context)

        # Create message record
        message = LinkedInMessage(
            tenant_id=campaign.tenant_id,
            account_id=account.id,
            contact_id=lead.contact_id,
            linkedin_url=lead.linkedin_url,
            profile_name=lead.profile_name,
            message_type="direct",
            content=content,
            template_id=template_id,
            direction="outbound",
            status="pending",
            campaign_id=campaign.id,
            campaign_lead_id=lead.id,
            campaign_step_id=step.id,
        )
        self.db.add(message)

        # In production, would call browser automation:
        # await self.browser.send_message(account, lead.linkedin_url, content)

        # Simulate success
        message.status = "sent"
        message.sent_at = datetime.utcnow()

        # Update template stats
        template.times_used += 1

        # Log activity if contact is linked
        if lead.contact_id:
            try:
                await log_linkedin_activity(
                    db=self.db,
                    tenant_id=campaign.tenant_id,
                    contact_id=lead.contact_id,
                    activity_type=LinkedInActivityType.MESSAGE_SENT,
                    content=content,
                    external_id=str(message.id),
                    metadata={
                        "linkedin_url": lead.linkedin_url,
                        "campaign_id": campaign.id,
                        "campaign_name": campaign.name,
                        "template_id": template_id,
                        "step_id": step.id,
                    },
                    commit=False,
                )
            except Exception as e:
                logger.warning(
                    f"Activity logging failed for message {message.id}: {e}"
                )

        await self.db.commit()

        logger.info(f"Message sent to lead {lead.id} in campaign {campaign.id}")
        return {"success": True, "action": "message", "message_id": message.id}

    async def _execute_view_profile(
        self,
        lead: LinkedInCampaignLead,
        account: LinkedInAccount,
    ) -> dict:
        """Execute a profile view (for warmup/engagement)."""
        # In production: await self.browser.view_profile(account, lead.linkedin_url)
        logger.info(f"Profile view for lead {lead.id}")
        return {"success": True, "action": "view_profile"}

    async def _execute_follow(
        self,
        lead: LinkedInCampaignLead,
        account: LinkedInAccount,
    ) -> dict:
        """Execute a follow action."""
        # In production: await self.browser.follow_profile(account, lead.linkedin_url)
        logger.info(f"Follow action for lead {lead.id}")
        return {"success": True, "action": "follow"}

    async def _evaluate_condition(
        self,
        campaign: LinkedInCampaign,
        lead: LinkedInCampaignLead,
        step: LinkedInCampaignStep,
    ) -> dict:
        """Evaluate a condition step."""
        condition = step.condition_type
        result = False

        if condition == "connected":
            result = lead.connection_status == "accepted"
        elif condition == "replied":
            result = lead.has_replied
        elif condition == "not_replied":
            result = not lead.has_replied
        elif condition == "not_connected":
            result = lead.connection_status != "accepted"

        # The next step will be determined in _advance_lead based on condition result
        return {
            "success": True,
            "action": "condition",
            "condition": condition,
            "result": result,
            "next_step_id": step.condition_true_step_id if result else step.condition_false_step_id,
        }

    async def _advance_lead(
        self,
        campaign: LinkedInCampaign,
        lead: LinkedInCampaignLead,
        completed_step: LinkedInCampaignStep,
    ) -> None:
        """Advance lead to the next step."""
        # Find next step
        next_step = None

        if completed_step.step_type == "condition":
            # Condition determines next step
            condition_result = await self._evaluate_condition(campaign, lead, completed_step)
            next_step_id = condition_result.get("next_step_id")
            if next_step_id:
                result = await self.db.execute(
                    select(LinkedInCampaignStep).where(
                        LinkedInCampaignStep.id == next_step_id
                    )
                )
                next_step = result.scalar_one_or_none()
        else:
            # Find next step by order
            next_order = completed_step.order + 1
            next_step = next(
                (s for s in campaign.steps if s.order == next_order and s.is_active),
                None
            )

        if not next_step:
            # Campaign completed for this lead
            lead.status = "completed"
            lead.completed_at = datetime.utcnow()
            lead.current_step_id = None
            campaign.leads_completed += 1
        else:
            # Set up next step
            lead.current_step_id = next_step.id
            lead.current_step_order = next_step.order
            lead.status = "waiting" if next_step.step_type == "wait" else "active"

            # Calculate next action time
            wait_hours = 0
            if next_step.step_type == "wait":
                wait_hours = (next_step.wait_days or 0) * 24 + (next_step.wait_hours or 0)
            else:
                # Add some delay between actions
                wait_hours = random.uniform(0.5, 2)  # 30 min to 2 hours

            lead.next_action_at = datetime.utcnow() + timedelta(hours=wait_hours)

            # Update step stats
            completed_step.leads_completed += 1
            next_step.leads_entered += 1

        await self.db.commit()

    async def _get_template(self, template_id: int) -> LinkedInMessageTemplate | None:
        """Get a message template by ID."""
        result = await self.db.execute(
            select(LinkedInMessageTemplate).where(
                LinkedInMessageTemplate.id == template_id
            )
        )
        return result.scalar_one_or_none()

    def _build_template_context(self, lead: LinkedInCampaignLead) -> dict:
        """Build context dict for template rendering."""
        # Parse first/last name from full name
        name_parts = (lead.profile_name or "").split(" ", 1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        context = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": lead.profile_name or "",
            "company": lead.company_name or "",
            "headline": lead.profile_headline or "",
            "position": lead.profile_headline or "",  # Often same as headline
        }

        # Merge custom variables
        if lead.custom_variables:
            context.update(lead.custom_variables)

        return context

    async def _check_connection_accepted(self, lead: LinkedInCampaignLead) -> bool:
        """Check if a connection request was accepted."""
        # In production, would check via browser or API
        # For now, check our local records
        result = await self.db.execute(
            select(LinkedInConnection).where(
                LinkedInConnection.campaign_lead_id == lead.id,
                LinkedInConnection.status == "accepted",
            )
        )
        return result.scalar_one_or_none() is not None

    async def check_for_replies(self, campaign_id: int, tenant_id: str) -> dict:
        """Check for replies to messages in a campaign.

        Should be run periodically to detect replies.
        """
        # Get active leads in campaign
        result = await self.db.execute(
            select(LinkedInCampaignLead).where(
                LinkedInCampaignLead.campaign_id == campaign_id,
                LinkedInCampaignLead.status.in_(["active", "waiting"]),
                LinkedInCampaignLead.has_replied.is_(False),
            )
        )
        leads = result.scalars().all()

        # Load campaign
        campaign_result = await self.db.execute(
            select(LinkedInCampaign).where(
                LinkedInCampaign.id == campaign_id,
                LinkedInCampaign.tenant_id == tenant_id,
            )
        )
        campaign = campaign_result.scalar_one_or_none()

        if not campaign:
            return {"error": "Campaign not found"}

        # In production, would check inbox via browser
        # For now, check our message records for inbound messages
        replies_found = 0

        for lead in leads:
            msg_result = await self.db.execute(
                select(LinkedInMessage).where(
                    LinkedInMessage.campaign_lead_id == lead.id,
                    LinkedInMessage.direction == "inbound",
                )
            )
            inbound_msg = msg_result.scalar_one_or_none()

            if inbound_msg:
                lead.has_replied = True
                lead.reply_received_at = inbound_msg.created_at
                replies_found += 1

                # Log activity for reply if contact is linked
                if lead.contact_id:
                    try:
                        await log_linkedin_activity(
                            db=self.db,
                            tenant_id=tenant_id,
                            contact_id=lead.contact_id,
                            activity_type=LinkedInActivityType.MESSAGE_RECEIVED,
                            content=inbound_msg.content,
                            external_id=str(inbound_msg.id),
                            metadata={
                                "linkedin_url": lead.linkedin_url,
                                "campaign_id": campaign_id,
                                "campaign_name": campaign.name,
                            },
                            commit=False,
                        )
                    except Exception as e:
                        logger.warning(
                            f"Activity logging failed for reply: {e}"
                        )

                # Stop campaign for this lead if configured
                if campaign.stop_on_reply:
                    lead.status = "replied"
                    lead.completed_at = datetime.utcnow()
                    campaign.replies_received += 1

        await self.db.commit()
        return {"replies_found": replies_found}


async def run_daily_maintenance(db: AsyncSession) -> dict:
    """Run daily maintenance tasks for LinkedIn automation.

    Should be called once per day, preferably at midnight.
    """
    safety = SafetyService(db)

    # Reset daily counters
    accounts_reset = await safety.reset_daily_counters()

    # Progress warmup
    accounts_warmed = await safety.progress_warmup()

    logger.info(f"Daily maintenance: reset {accounts_reset} accounts, progressed {accounts_warmed} warmups")

    return {
        "accounts_reset": accounts_reset,
        "warmup_progressed": accounts_warmed,
    }

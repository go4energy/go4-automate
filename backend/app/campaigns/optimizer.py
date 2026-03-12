"""Budget optimization engine for ad campaigns."""

from decimal import Decimal

from loguru import logger

from app.campaigns.meta_ads_client import (
    get_campaign_insights,
    pause_campaign,
    update_campaign_budget,
)
from app.campaigns.schemas import OptimizationResult, WeatherData
from app.campaigns.weather_service import get_current_weather
from app.config import settings

# Default location: Vienna, Austria
DEFAULT_LAT = 48.2082
DEFAULT_LON = 16.3738


async def optimize_campaign(
    campaign_config: object,
    access_token: str,
    date_from: str,
    date_to: str,
) -> OptimizationResult:
    """Optimize a single campaign based on performance and weather.

    Rules (in priority order):
    1. Stop:   CPL > max_cpl - pause campaign
    2. Reduce: CPL > 1.5x target_cpl - reduce budget by 20%
    3. Weather Boost: sunny + enabled - multiply budget by weather_boost_factor
    4. Scale:  CPL < 0.8x target_cpl - increase budget by 20%
    5. Maintain: keep current budget
    """
    campaign_id = campaign_config.campaign_id
    campaign_name = campaign_config.campaign_name

    # Fetch current performance
    insights = await get_campaign_insights(
        campaign_id, access_token, date_from, date_to
    )

    leads = insights.get("leads", 0)
    spend = Decimal(str(insights.get("spend", 0)))
    cpl = spend / leads if leads > 0 else Decimal("0")

    target_cpl = campaign_config.target_cpl or Decimal("0")
    max_cpl = campaign_config.max_cpl or Decimal("999999")
    budget_min = campaign_config.daily_budget_min
    budget_max = campaign_config.daily_budget_max

    # Rule 1: Stop - CPL exceeds maximum
    if leads > 0 and cpl > max_cpl:
        await pause_campaign(campaign_id, access_token)
        logger.warning(
            "Kampagne gestoppt: {name} (CPL {cpl} > Max {max})",
            name=campaign_name,
            cpl=cpl,
            max=max_cpl,
        )
        return OptimizationResult(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            action="stopped",
            cpl=cpl,
            leads=leads,
            reason=f"CPL {cpl} ueberschreitet Maximum {max_cpl}",
        )

    # Rule 2: Reduce - CPL too high
    if leads > 0 and target_cpl > 0 and cpl > target_cpl * Decimal("1.5"):
        new_budget = _calc_reduced_budget(spend, budget_min)
        await _apply_budget(campaign_id, access_token, new_budget)
        logger.info(
            "Budget reduziert: {name} (CPL {cpl} > 1.5x{target})",
            name=campaign_name,
            cpl=cpl,
            target=target_cpl,
        )
        return OptimizationResult(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            action="reduced",
            previous_budget=spend,
            new_budget=new_budget,
            cpl=cpl,
            leads=leads,
            reason=f"CPL {cpl} > 1.5x Ziel-CPL {target_cpl}",
        )

    # Rule 3: Weather Boost
    weather: WeatherData | None = None
    if campaign_config.weather_boost_enabled and settings.openweather_api_key:
        weather = await _fetch_weather()

    if weather and weather.is_sunny and campaign_config.weather_boost_enabled:
        factor = campaign_config.weather_boost_factor or Decimal("1.5")
        new_budget = _calc_weather_budget(spend, factor, budget_max)
        await _apply_budget(campaign_id, access_token, new_budget)
        logger.info(
            "Weather-Boost: {name} (x{factor}, {desc})",
            name=campaign_name,
            factor=factor,
            desc=weather.description,
        )
        return OptimizationResult(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            action="weather_boosted",
            previous_budget=spend,
            new_budget=new_budget,
            cpl=cpl,
            leads=leads,
            weather_boosted=True,
            reason=f"Sonnig ({weather.description}), Budget x{factor}",
        )

    # Rule 4: Scale - CPL well below target
    if leads > 0 and target_cpl > 0 and cpl < target_cpl * Decimal("0.8"):
        new_budget = _calc_scaled_budget(spend, budget_max)
        await _apply_budget(campaign_id, access_token, new_budget)
        logger.info(
            "Budget erhoeht: {name} (CPL {cpl} < 0.8x{target})",
            name=campaign_name,
            cpl=cpl,
            target=target_cpl,
        )
        return OptimizationResult(
            campaign_id=campaign_id,
            campaign_name=campaign_name,
            action="scaled",
            previous_budget=spend,
            new_budget=new_budget,
            cpl=cpl,
            leads=leads,
            reason=f"CPL {cpl} < 0.8x Ziel-CPL {target_cpl}",
        )

    # Rule 5: Maintain
    logger.info(
        "Budget beibehalten: {name} (CPL {cpl})",
        name=campaign_name,
        cpl=cpl,
    )
    return OptimizationResult(
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        action="maintained",
        cpl=cpl,
        leads=leads,
        reason="Performance im Zielbereich",
    )


def _calc_reduced_budget(current_spend: Decimal, budget_min: Decimal | None) -> Decimal:
    """Reduce budget by 20%, respecting minimum."""
    new = current_spend * Decimal("0.8")
    if budget_min and new < budget_min:
        new = budget_min
    return new.quantize(Decimal("0.01"))


def _calc_scaled_budget(current_spend: Decimal, budget_max: Decimal | None) -> Decimal:
    """Increase budget by 20%, respecting maximum."""
    new = current_spend * Decimal("1.2")
    if budget_max and new > budget_max:
        new = budget_max
    return new.quantize(Decimal("0.01"))


def _calc_weather_budget(
    current_spend: Decimal, factor: Decimal, budget_max: Decimal | None
) -> Decimal:
    """Apply weather boost factor, respecting maximum."""
    new = current_spend * factor
    if budget_max and new > budget_max:
        new = budget_max
    return new.quantize(Decimal("0.01"))


async def _apply_budget(
    campaign_id: str, access_token: str, budget_euros: Decimal
) -> dict:
    """Convert euros to cents and update campaign budget."""
    budget_cents = int(budget_euros * 100)
    return await update_campaign_budget(campaign_id, access_token, budget_cents)


async def _fetch_weather() -> WeatherData | None:
    """Fetch weather data, returning None on failure."""
    try:
        return await get_current_weather(
            DEFAULT_LAT, DEFAULT_LON, settings.openweather_api_key
        )
    except Exception as e:
        logger.warning("Wetter-Abfrage fehlgeschlagen: {err}", err=str(e))
        return None

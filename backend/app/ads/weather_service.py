"""OpenWeather API client for weather-based budget boosting."""

import httpx
from loguru import logger

from app.ads.schemas import WeatherData
from app.exceptions import ExternalServiceError

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"


async def get_current_weather(lat: float, lon: float, api_key: str) -> WeatherData:
    """Fetch current weather from OpenWeather API."""
    if not api_key:
        raise ExternalServiceError("OpenWeather", "API Key nicht konfiguriert")

    url = f"{OPENWEATHER_BASE_URL}/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            temp = data.get("main", {}).get("temp", 0)
            clouds = data.get("clouds", {}).get("all", 100)
            desc = data.get("weather", [{}])[0].get("description", "")
            is_sunny = clouds < 40 and temp > 10

            logger.info(
                "Wetter: {temp}°C, {clouds}% Wolken, sonnig={sunny}",
                temp=temp,
                clouds=clouds,
                sunny=is_sunny,
            )
            return WeatherData(
                temp=temp,
                description=desc,
                clouds_percent=clouds,
                is_sunny=is_sunny,
            )
        except httpx.HTTPStatusError as e:
            detail = e.response.text if e.response else str(e)
            logger.error("OpenWeather API Fehler: {err}", err=detail)
            raise ExternalServiceError("OpenWeather", detail) from e
        except httpx.RequestError as e:
            logger.error("OpenWeather Verbindungsfehler: {err}", err=str(e))
            raise ExternalServiceError("OpenWeather", str(e)) from e

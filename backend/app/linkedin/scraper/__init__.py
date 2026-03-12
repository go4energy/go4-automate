"""LinkedIn scraper module - Playwright-based Sales Navigator scraping."""

from app.linkedin.scraper.browser import LinkedInBrowser
from app.linkedin.scraper.human_like import (
    human_delay,
    human_scroll,
    micro_pause,
    random_mouse_move,
    short_pause,
    wait_for_rate_limit_recovery,
)
from app.linkedin.scraper.parsers import (
    extract_linkedin_id,
    normalize_linkedin_url,
    parse_connections_list,
    parse_contact_info_modal,
    parse_profile_page,
    parse_search_results,
    split_name,
)
from app.linkedin.scraper.worker import (
    LinkedInWorker,
    get_worker,
    process_job_now,
    start_worker,
    stop_worker,
)

__all__ = [
    "LinkedInBrowser",
    "LinkedInWorker",
    "extract_linkedin_id",
    "get_worker",
    "human_delay",
    "human_scroll",
    "micro_pause",
    "normalize_linkedin_url",
    "parse_connections_list",
    "parse_contact_info_modal",
    "parse_profile_page",
    "parse_search_results",
    "process_job_now",
    "random_mouse_move",
    "short_pause",
    "split_name",
    "start_worker",
    "stop_worker",
    "wait_for_rate_limit_recovery",
]

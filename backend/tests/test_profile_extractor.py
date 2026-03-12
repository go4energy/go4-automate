"""Tests for LinkedIn profile extraction using HTML parsing.

Uses real innerHTML from LinkedIn profile sections (extracted via componentkey)
to verify BeautifulSoup-based parsing works correctly.

Fixtures are stored in tests/fixtures/linkedin_sections.json.
"""

import json
from pathlib import Path

import pytest

from app.linkedin.scraper.profile_extractor import (
    extract_profile_from_sections,
    parse_about_html,
    parse_certifications_html,
    parse_education_html,
    parse_experience_html,
    parse_languages_html,
    parse_skills_html,
    parse_topcard_html,
)

# ========== Load real HTML fixtures ==========

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "linkedin_sections.json"


@pytest.fixture(scope="module")
def fixtures():
    with open(FIXTURES_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def andreas_topcard(fixtures):
    return fixtures["andreas_topcard"]


@pytest.fixture(scope="module")
def andreas_about(fixtures):
    return fixtures["andreas_about"]


@pytest.fixture(scope="module")
def andreas_experience(fixtures):
    return fixtures["andreas_experience"]


@pytest.fixture(scope="module")
def andreas_education(fixtures):
    return fixtures["andreas_education"]


@pytest.fixture(scope="module")
def andreas_skills(fixtures):
    return fixtures["andreas_skills"]


@pytest.fixture(scope="module")
def falko_topcard(fixtures):
    return fixtures["falko_topcard"]


@pytest.fixture(scope="module")
def falko_languages(fixtures):
    return fixtures["falko_language"]


@pytest.fixture(scope="module")
def falko_certifications(fixtures):
    return fixtures["falko_certification"]


# ========== Tests: parse_topcard_html ==========


class TestParseTopcard:
    def test_andreas_name(self, andreas_topcard):
        result = parse_topcard_html(andreas_topcard)
        assert result["name"] == "Andreas Zeidler"

    def test_andreas_headline(self, andreas_topcard):
        result = parse_topcard_html(andreas_topcard)
        assert "Qualit\u00e4ts" in result["headline"]
        assert "Leidenschaft" in result["headline"]

    def test_andreas_location(self, andreas_topcard):
        result = parse_topcard_html(andreas_topcard)
        assert "Magdeburg" in result["location"]

    def test_andreas_company(self, andreas_topcard):
        result = parse_topcard_html(andreas_topcard)
        assert result["company_name"] == "DP World"

    def test_falko_name(self, falko_topcard):
        result = parse_topcard_html(falko_topcard)
        assert result["name"] == "Falko Bretsch"

    def test_falko_headline(self, falko_topcard):
        result = parse_topcard_html(falko_topcard)
        assert "Superheld" in result["headline"]

    def test_falko_location(self, falko_topcard):
        result = parse_topcard_html(falko_topcard)
        assert "Preetz" in result["location"]

    def test_falko_company(self, falko_topcard):
        result = parse_topcard_html(falko_topcard)
        assert result["company_name"] == "LTB Leitungsbau GmbH"

    def test_empty_input(self):
        assert parse_topcard_html("") == {}
        assert parse_topcard_html(None) == {}

    def test_minimal_html(self):
        html = '<h2>John Doe</h2><p class="_5e021eff">Engineer</p>'
        result = parse_topcard_html(html)
        assert result["name"] == "John Doe"
        assert result["headline"] == "Engineer"


# ========== Tests: parse_about_html ==========


class TestParseAbout:
    def test_andreas_summary(self, andreas_about):
        result = parse_about_html(andreas_about)
        assert "Schifffahrt" in result["summary"]
        assert "Appeasement" in result["summary"]

    def test_andreas_top_skills(self, andreas_about):
        result = parse_about_html(andreas_about)
        assert "Projektmanagement" in result["top_skills"]
        assert "Qualit\u00e4tsmanagement" in result["top_skills"]
        assert len(result["top_skills"]) == 5

    def test_summary_not_starts_with_header(self, andreas_about):
        result = parse_about_html(andreas_about)
        assert not result["summary"].startswith("Info")
        assert not result["summary"].startswith("About")

    def test_empty_input(self):
        assert parse_about_html("") == {}
        assert parse_about_html(None) == {}


# ========== Tests: parse_experience_html ==========


class TestParseExperience:
    def test_andreas_has_entries(self, andreas_experience):
        result = parse_experience_html(andreas_experience)
        assert len(result) >= 5

    def test_andreas_first_entry_title(self, andreas_experience):
        result = parse_experience_html(andreas_experience)
        assert result[0]["title"] == "QHSE Engineer"

    def test_andreas_first_entry_company(self, andreas_experience):
        result = parse_experience_html(andreas_experience)
        assert result[0]["company"] == "DP World"

    def test_andreas_first_entry_type(self, andreas_experience):
        result = parse_experience_html(andreas_experience)
        assert result[0].get("employment_type") == "Vollzeit"

    def test_andreas_career_break(self, andreas_experience):
        result = parse_experience_html(andreas_experience)
        breaks = [e for e in result if e.get("is_career_break")]
        assert len(breaks) >= 1
        assert breaks[0]["title"] == "Karriere\u00fcbergang"

    def test_andreas_has_location(self, andreas_experience):
        result = parse_experience_html(andreas_experience)
        first = result[0]
        assert "location" in first
        assert "Halberstadt" in first["location"]

    def test_andreas_has_skills(self, andreas_experience):
        result = parse_experience_html(andreas_experience)
        first = result[0]
        assert "skills" in first
        assert "EHS" in first["skills"]

    def test_empty_input(self):
        assert parse_experience_html("") == []
        assert parse_experience_html(None) == []


# ========== Tests: parse_education_html ==========


class TestParseEducation:
    def test_andreas_has_entries(self, andreas_education):
        result = parse_education_html(andreas_education)
        assert len(result) >= 2

    def test_andreas_first_school(self, andreas_education):
        result = parse_education_html(andreas_education)
        assert result[0]["school"] == "WINGS-Fernstudium"

    def test_andreas_first_degree(self, andreas_education):
        result = parse_education_html(andreas_education)
        assert "Quality Management" in result[0]["degree"]

    def test_andreas_year_range(self, andreas_education):
        result = parse_education_html(andreas_education)
        assert result[0].get("start_year") == 2019
        assert result[0].get("end_year") == 2021

    def test_andreas_second_school(self, andreas_education):
        result = parse_education_html(andreas_education)
        assert "sgd" in result[1]["school"]
        assert result[1].get("start_year") == 2011
        assert result[1].get("end_year") == 2012

    def test_andreas_has_description(self, andreas_education):
        result = parse_education_html(andreas_education)
        desc = result[0].get("description", "")
        assert "Qualit\u00e4tsplanung" in desc

    def test_empty_input(self):
        assert parse_education_html("") == []
        assert parse_education_html(None) == []


# ========== Tests: parse_skills_html ==========


class TestParseSkills:
    def test_andreas_skills(self, andreas_skills):
        result = parse_skills_html(andreas_skills)
        assert "EHS" in result
        assert "Recherche" in result

    def test_filters_ui_elements(self, andreas_skills):
        result = parse_skills_html(andreas_skills)
        for s in result:
            assert "best\u00e4tigen" not in s
            assert "anzeigen" not in s.lower()
            assert s != "Kenntnisse"

    def test_no_duplicates(self, andreas_skills):
        result = parse_skills_html(andreas_skills)
        assert len(result) == len(set(s.lower() for s in result))

    def test_empty_input(self):
        assert parse_skills_html("") == []
        assert parse_skills_html(None) == []


# ========== Tests: parse_languages_html ==========


class TestParseLanguages:
    def test_falko_has_two_languages(self, falko_languages):
        result = parse_languages_html(falko_languages)
        assert len(result) == 2

    def test_falko_german(self, falko_languages):
        result = parse_languages_html(falko_languages)
        german = result[0]
        assert german["language"] == "Deutsch"
        assert german["proficiency"] == "Verhandlungssicher"

    def test_falko_english(self, falko_languages):
        result = parse_languages_html(falko_languages)
        english = result[1]
        assert english["language"] == "Englisch"
        assert english["proficiency"] == "Gute Kenntnisse"

    def test_empty_input(self):
        assert parse_languages_html("") == []
        assert parse_languages_html(None) == []


# ========== Tests: parse_certifications_html ==========


class TestParseCertifications:
    def test_falko_has_cert(self, falko_certifications):
        result = parse_certifications_html(falko_certifications)
        assert len(result) >= 1

    def test_falko_cert_name(self, falko_certifications):
        result = parse_certifications_html(falko_certifications)
        assert "Brandschutzbeauftragter" in result[0]["name"]

    def test_falko_cert_issuer(self, falko_certifications):
        result = parse_certifications_html(falko_certifications)
        assert result[0]["issuer"] == "DEKRA"

    def test_falko_cert_date(self, falko_certifications):
        result = parse_certifications_html(falko_certifications)
        assert "Nov. 2024" in result[0].get("issued_date", "")

    def test_empty_input(self):
        assert parse_certifications_html("") == []
        assert parse_certifications_html(None) == []


# ========== Tests: extract_profile_from_sections (integration) ==========


class TestExtractProfileFromSections:
    def test_andreas_full_extraction(self, fixtures):
        sections = {
            "topcard": fixtures["andreas_topcard"],
            "about": fixtures["andreas_about"],
            "experience": fixtures["andreas_experience"],
            "education": fixtures["andreas_education"],
            "skills": fixtures["andreas_skills"],
            "_is_premium": False,
            "_counters": ["103 Kontakte"],
            "_profile_urn": "urn:li:fsd_profile:ACoAADXeAiwBSfsqLZrX",
        }
        profile = extract_profile_from_sections(sections)

        assert profile["name"] == "Andreas Zeidler"
        assert "Qualit\u00e4ts" in profile["headline"]
        assert "Schifffahrt" in profile["summary"]
        assert len(profile["experience"]) >= 5
        assert len(profile["education"]) >= 2
        assert len(profile["skills"]) >= 2
        assert profile["connection_count"] == 103
        assert profile["profile_urn"] == "urn:li:fsd_profile:ACoAADXeAiwBSfsqLZrX"
        assert profile["position"] == "QHSE Engineer"
        assert profile["company_name"] == "DP World"

    def test_falko_full_extraction(self, fixtures):
        sections = {
            "topcard": fixtures["falko_topcard"],
            "languages": fixtures["falko_language"],
            "certifications": fixtures["falko_certification"],
            "_is_premium": False,
            "_counters": [
                "6.952 Follower:innen",
                "500+ Kontakte",
            ],
        }
        profile = extract_profile_from_sections(sections)

        assert profile["name"] == "Falko Bretsch"
        assert profile["follower_count"] == 6952
        assert profile["connection_count"] == 500
        assert len(profile["languages"]) == 2
        assert profile["languages"][0]["language"] == "Deutsch"
        assert len(profile["certifications"]) >= 1

    def test_activity_hashtags(self):
        sections = {
            "topcard": '<h2>Test User</h2><p class="_5e021eff">Headline</p>',
            "activity": """Aktivit\u00e4ten
Test post with #energiewende and #arbeitsschutz
Another post with #energiewende and #safetyfirst""",
        }
        profile = extract_profile_from_sections(sections)

        assert "hashtags" in profile
        assert "energiewende" in profile["hashtags"]
        assert "arbeitsschutz" in profile["hashtags"]
        assert "safetyfirst" in profile["hashtags"]
        assert profile["hashtags"].count("energiewende") == 1

    def test_empty_sections(self):
        sections = {
            "topcard": '<h2>John Doe</h2><p class="_5e021eff">Software Engineer</p>',
        }
        profile = extract_profile_from_sections(sections)
        assert profile["name"] == "John Doe"
        assert profile.get("experience") is None
        assert profile.get("education") is None

    def test_current_position_from_experience(self, fixtures):
        sections = {
            "topcard": fixtures["andreas_topcard"],
            "experience": fixtures["andreas_experience"],
        }
        profile = extract_profile_from_sections(sections)
        assert profile.get("position") == "QHSE Engineer"
        assert profile.get("company_name") == "DP World"

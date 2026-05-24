"""Tests for app.services.bot module.

Validates BotService operations including query classification,
fallback response generation, conversation history capping, and
LLM integration for relevant queries.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import quote_plus

import pytest

from app.models.profile import UserProfile
from app.models.project import ProjectRecord
from app.models.skill import SkillRecord
from app.services.bot import (
    MAX_HISTORY_MESSAGES,
    RELEVANT_KEYWORDS,
    BotService,
)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_profile(
    user_id: uuid.UUID,
    name: str | None = "Jane Doe",
    bio: str | None = "Full-stack developer",
    contact_email: str | None = "jane@example.com",
    social_links: dict | None = None,
) -> UserProfile:
    """Factory for creating UserProfile instances for testing."""
    return UserProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        bio=bio,
        contact_email=contact_email,
        social_links=social_links or {"github": "https://github.com/jane"},
        picture_url=None,
        updated_at=datetime.now(timezone.utc),
    )


def _make_skill(
    user_id: uuid.UUID,
    name: str = "Python",
    category: str = "Language",
    proficiency_level: str = "advanced",
) -> SkillRecord:
    """Factory for creating SkillRecord instances for testing."""
    return SkillRecord(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        category=category,
        proficiency_level=proficiency_level,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_project(
    user_id: uuid.UUID,
    name: str = "Portfolio Site",
    description: str | None = "My personal portfolio",
    status: str = "completed",
    technology_tags: list[str] | None = None,
) -> ProjectRecord:
    """Factory for creating ProjectRecord instances for testing."""
    return ProjectRecord(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        description=description,
        status=status,
        technology_tags=technology_tags or ["React", "FastAPI"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _mock_llm(response: str = "I'm a helpful bot!") -> AsyncMock:
    """Create a mock LLMProvider."""
    llm = AsyncMock()
    llm.generate_response.return_value = response
    return llm


def _mock_db_with_context(
    profile: UserProfile | None = None,
    skills: list[SkillRecord] | None = None,
    projects: list[ProjectRecord] | None = None,
) -> AsyncMock:
    """Create a mock DB session that returns user context data.

    The mock handles three sequential execute() calls:
    1. Profile query → scalar_one_or_none
    2. Skills query → scalars().all()
    3. Projects query → scalars().all()
    """
    mock_db = AsyncMock()

    # Profile result
    profile_result = MagicMock()
    profile_result.scalar_one_or_none.return_value = profile

    # Skills result
    skills_scalars = MagicMock()
    skills_scalars.all.return_value = skills or []
    skills_result = MagicMock()
    skills_result.scalars.return_value = skills_scalars

    # Projects result
    projects_scalars = MagicMock()
    projects_scalars.all.return_value = projects or []
    projects_result = MagicMock()
    projects_result.scalars.return_value = projects_scalars

    mock_db.execute.side_effect = [profile_result, skills_result, projects_result]

    return mock_db


# ---------------------------------------------------------------------------
# classify_query tests
# ---------------------------------------------------------------------------


class TestClassifyQuery:
    """Tests for BotService.classify_query()."""

    def test_relevant_query_with_skill_keyword(self):
        """classify_query returns 'relevant' when query contains a skill keyword."""
        user_id = uuid.uuid4()
        service = BotService(llm=AsyncMock(), db=AsyncMock(), user_id=user_id)

        assert service.classify_query("What skills do you have?") == "relevant"

    def test_relevant_query_with_project_keyword(self):
        """classify_query returns 'relevant' when query contains a project keyword."""
        user_id = uuid.uuid4()
        service = BotService(llm=AsyncMock(), db=AsyncMock(), user_id=user_id)

        assert service.classify_query("Tell me about your projects") == "relevant"

    def test_relevant_query_with_experience_keyword(self):
        """classify_query returns 'relevant' for experience-related queries."""
        user_id = uuid.uuid4()
        service = BotService(llm=AsyncMock(), db=AsyncMock(), user_id=user_id)

        assert service.classify_query("What is your work experience?") == "relevant"

    def test_relevant_query_with_education_keyword(self):
        """classify_query returns 'relevant' for education-related queries."""
        user_id = uuid.uuid4()
        service = BotService(llm=AsyncMock(), db=AsyncMock(), user_id=user_id)

        assert service.classify_query("Where did you study education?") == "relevant"

    def test_relevant_query_case_insensitive(self):
        """classify_query performs case-insensitive keyword matching."""
        user_id = uuid.uuid4()
        service = BotService(llm=AsyncMock(), db=AsyncMock(), user_id=user_id)

        assert service.classify_query("WHAT SKILLS DO YOU HAVE?") == "relevant"

    def test_unrelated_query(self):
        """classify_query returns 'unrelated' for off-topic queries."""
        user_id = uuid.uuid4()
        service = BotService(llm=AsyncMock(), db=AsyncMock(), user_id=user_id)

        assert service.classify_query("Is it going to rain tomorrow?") == "unrelated"

    def test_unrelated_query_no_keywords(self):
        """classify_query returns 'unrelated' when no keywords match."""
        user_id = uuid.uuid4()
        service = BotService(llm=AsyncMock(), db=AsyncMock(), user_id=user_id)

        assert service.classify_query("How do I cook pasta?") == "unrelated"

    def test_empty_query_is_unrelated(self):
        """classify_query returns 'unrelated' for an empty string."""
        user_id = uuid.uuid4()
        service = BotService(llm=AsyncMock(), db=AsyncMock(), user_id=user_id)

        assert service.classify_query("") == "unrelated"

    def test_relevant_keywords_set_is_not_empty(self):
        """The RELEVANT_KEYWORDS set contains a reasonable number of terms."""
        assert len(RELEVANT_KEYWORDS) > 20


# ---------------------------------------------------------------------------
# build_fallback_response tests
# ---------------------------------------------------------------------------


class TestBuildFallbackResponse:
    """Tests for BotService.build_fallback_response()."""

    def test_fallback_contains_google_link(self):
        """Fallback response contains a Google search link."""
        user_id = uuid.uuid4()
        service = BotService(llm=AsyncMock(), db=AsyncMock(), user_id=user_id)

        result = service.build_fallback_response("best pizza recipe")

        expected_link = f"https://www.google.com/search?q={quote_plus('best pizza recipe')}"
        assert expected_link in result

    def test_fallback_url_encodes_query(self):
        """Fallback response URL-encodes special characters in the query."""
        user_id = uuid.uuid4()
        service = BotService(llm=AsyncMock(), db=AsyncMock(), user_id=user_id)

        result = service.build_fallback_response("what is C++ & Java?")

        expected_link = f"https://www.google.com/search?q={quote_plus('what is C++ & Java?')}"
        assert expected_link in result

    def test_fallback_is_deterministic(self):
        """Same query always produces the same fallback response."""
        user_id = uuid.uuid4()
        service = BotService(llm=AsyncMock(), db=AsyncMock(), user_id=user_id)

        result1 = service.build_fallback_response("random question")
        result2 = service.build_fallback_response("random question")

        assert result1 == result2

    def test_google_link_construction(self):
        """_build_google_link produces the correct URL."""
        link = BotService._build_google_link("hello world")

        assert link == "https://www.google.com/search?q=hello+world"

    def test_google_link_encodes_spaces(self):
        """_build_google_link encodes spaces as plus signs."""
        link = BotService._build_google_link("foo bar baz")

        assert link == "https://www.google.com/search?q=foo+bar+baz"


# ---------------------------------------------------------------------------
# handle_message tests
# ---------------------------------------------------------------------------


class TestHandleMessage:
    """Tests for BotService.handle_message()."""

    @pytest.mark.asyncio
    async def test_unrelated_query_returns_fallback_without_llm_call(self):
        """handle_message returns a fallback for unrelated queries and skips LLM."""
        user_id = uuid.uuid4()
        mock_llm = _mock_llm()
        mock_db = AsyncMock()

        service = BotService(llm=mock_llm, db=mock_db, user_id=user_id)
        result = await service.handle_message("Is it going to rain tomorrow?", [])

        assert result["is_fallback"] is True
        assert "google.com/search" in result["response"]
        mock_llm.generate_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_relevant_query_calls_llm(self):
        """handle_message calls the LLM provider for relevant queries."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        skills = [_make_skill(user_id)]
        projects = [_make_project(user_id)]
        mock_llm = _mock_llm("Jane is a skilled developer.")
        mock_db = _mock_db_with_context(profile, skills, projects)

        service = BotService(llm=mock_llm, db=mock_db, user_id=user_id)
        result = await service.handle_message("What are your skills?", [])

        assert result["is_fallback"] is False
        assert result["response"] == "Jane is a skilled developer."
        mock_llm.generate_response.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_relevant_query_includes_user_query_in_messages(self):
        """handle_message appends the user query to the messages sent to LLM."""
        user_id = uuid.uuid4()
        mock_llm = _mock_llm()
        mock_db = _mock_db_with_context(_make_profile(user_id))

        service = BotService(llm=mock_llm, db=mock_db, user_id=user_id)
        await service.handle_message("Tell me about your background", [])

        call_args = mock_llm.generate_response.call_args
        messages = call_args[0][1]
        assert messages[-1] == {"role": "user", "content": "Tell me about your background"}

    @pytest.mark.asyncio
    async def test_conversation_history_capped_at_max(self):
        """handle_message caps session history at MAX_HISTORY_MESSAGES."""
        user_id = uuid.uuid4()
        mock_llm = _mock_llm()
        mock_db = _mock_db_with_context(_make_profile(user_id))

        # Create history exceeding the cap
        long_history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
            for i in range(30)
        ]

        service = BotService(llm=mock_llm, db=mock_db, user_id=user_id)
        await service.handle_message("What skills do you have?", long_history)

        call_args = mock_llm.generate_response.call_args
        messages = call_args[0][1]
        # Should be MAX_HISTORY_MESSAGES from history + 1 for the current query
        assert len(messages) == MAX_HISTORY_MESSAGES + 1

    @pytest.mark.asyncio
    async def test_conversation_history_preserves_recent_messages(self):
        """handle_message keeps the most recent messages when capping."""
        user_id = uuid.uuid4()
        mock_llm = _mock_llm()
        mock_db = _mock_db_with_context(_make_profile(user_id))

        long_history = [
            {"role": "user", "content": f"msg {i}"}
            for i in range(25)
        ]

        service = BotService(llm=mock_llm, db=mock_db, user_id=user_id)
        await service.handle_message("What about your projects?", long_history)

        call_args = mock_llm.generate_response.call_args
        messages = call_args[0][1]
        # The first message in the capped history should be msg 5 (25 - 20 = 5)
        assert messages[0]["content"] == "msg 5"

    @pytest.mark.asyncio
    async def test_system_prompt_contains_profile_info(self):
        """handle_message builds a system prompt containing the user's profile data."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id, name="Alice", bio="Backend engineer")
        mock_llm = _mock_llm()
        mock_db = _mock_db_with_context(profile)

        service = BotService(llm=mock_llm, db=mock_db, user_id=user_id)
        await service.handle_message("Tell me about yourself", [])

        call_args = mock_llm.generate_response.call_args
        system_prompt = call_args[0][0]
        assert "Alice" in system_prompt
        assert "Backend engineer" in system_prompt

    @pytest.mark.asyncio
    async def test_system_prompt_contains_skills(self):
        """handle_message builds a system prompt containing the user's skills."""
        user_id = uuid.uuid4()
        skills = [
            _make_skill(user_id, name="Python", category="Language"),
            _make_skill(user_id, name="React", category="Framework"),
        ]
        mock_llm = _mock_llm()
        mock_db = _mock_db_with_context(_make_profile(user_id), skills)

        service = BotService(llm=mock_llm, db=mock_db, user_id=user_id)
        await service.handle_message("What are your skills?", [])

        call_args = mock_llm.generate_response.call_args
        system_prompt = call_args[0][0]
        assert "Python" in system_prompt
        assert "React" in system_prompt

    @pytest.mark.asyncio
    async def test_system_prompt_contains_projects(self):
        """handle_message builds a system prompt containing the user's projects."""
        user_id = uuid.uuid4()
        projects = [_make_project(user_id, name="Nexus App", description="A portfolio platform")]
        mock_llm = _mock_llm()
        mock_db = _mock_db_with_context(_make_profile(user_id), projects=projects)

        service = BotService(llm=mock_llm, db=mock_db, user_id=user_id)
        await service.handle_message("Tell me about your projects", [])

        call_args = mock_llm.generate_response.call_args
        system_prompt = call_args[0][0]
        assert "Nexus App" in system_prompt
        assert "A portfolio platform" in system_prompt

    @pytest.mark.asyncio
    async def test_handle_message_with_empty_history(self):
        """handle_message works correctly with an empty session history."""
        user_id = uuid.uuid4()
        mock_llm = _mock_llm("Here are my skills.")
        mock_db = _mock_db_with_context(_make_profile(user_id))

        service = BotService(llm=mock_llm, db=mock_db, user_id=user_id)
        result = await service.handle_message("What skills do you have?", [])

        assert result["is_fallback"] is False
        assert result["response"] == "Here are my skills."
        call_args = mock_llm.generate_response.call_args
        messages = call_args[0][1]
        assert len(messages) == 1  # Just the current query

    @pytest.mark.asyncio
    async def test_handle_message_with_no_profile(self):
        """handle_message works when the user has no profile data."""
        user_id = uuid.uuid4()
        mock_llm = _mock_llm("I don't have much info.")
        mock_db = _mock_db_with_context(profile=None)

        service = BotService(llm=mock_llm, db=mock_db, user_id=user_id)
        result = await service.handle_message("Who are you?", [])

        assert result["is_fallback"] is False
        call_args = mock_llm.generate_response.call_args
        system_prompt = call_args[0][0]
        assert "No profile information available" in system_prompt


# ---------------------------------------------------------------------------
# _build_system_prompt tests
# ---------------------------------------------------------------------------


class TestBuildSystemPrompt:
    """Tests for BotService._build_system_prompt()."""

    def test_prompt_with_full_context(self):
        """System prompt includes profile, skills, and projects."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id, name="Bob", bio="DevOps guru")
        skills = [_make_skill(user_id, name="Docker", category="DevOps")]
        projects = [_make_project(user_id, name="CI Pipeline", description="Automated CI")]

        prompt = BotService._build_system_prompt(profile, skills, projects)

        assert "Bob" in prompt
        assert "DevOps guru" in prompt
        assert "Docker" in prompt
        assert "CI Pipeline" in prompt

    def test_prompt_with_no_profile(self):
        """System prompt handles missing profile gracefully."""
        prompt = BotService._build_system_prompt(None, [], [])

        assert "No profile information available" in prompt
        assert "No skills listed" in prompt
        assert "No projects listed" in prompt

    def test_prompt_includes_social_links(self):
        """System prompt includes social links from the profile."""
        user_id = uuid.uuid4()
        profile = _make_profile(
            user_id,
            social_links={"github": "https://github.com/bob", "twitter": "@bob"},
        )

        prompt = BotService._build_system_prompt(profile, [], [])

        assert "github" in prompt
        assert "https://github.com/bob" in prompt

    def test_prompt_includes_technology_tags(self):
        """System prompt includes project technology tags."""
        user_id = uuid.uuid4()
        projects = [
            _make_project(user_id, name="App", technology_tags=["Python", "FastAPI"])
        ]

        prompt = BotService._build_system_prompt(None, [], projects)

        assert "Python, FastAPI" in prompt

"""About Me Bot service.

Handles query classification, context fetching, LLM interaction,
and fallback response generation for the About Me chat bot.
"""

import uuid
from urllib.parse import quote_plus

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import UserProfile
from app.models.project import ProjectRecord
from app.models.skill import SkillRecord
from app.providers.base import LLMProvider

# Maximum number of messages retained in conversation history.
MAX_HISTORY_MESSAGES: int = 20

# Curated keyword set for classifying queries as relevant to the
# portfolio owner's background. Kept as a module-level constant so
# it is easy to extend without touching business logic.
RELEVANT_KEYWORDS: frozenset[str] = frozenset(
    {
        "skill",
        "skills",
        "project",
        "projects",
        "experience",
        "education",
        "background",
        "work",
        "job",
        "career",
        "portfolio",
        "learn",
        "learning",
        "technology",
        "technologies",
        "programming",
        "code",
        "coding",
        "develop",
        "developer",
        "development",
        "build",
        "building",
        "create",
        "creating",
        "proficiency",
        "proficient",
        "expertise",
        "expert",
        "qualification",
        "qualifications",
        "resume",
        "cv",
        "bio",
        "about",
        "who",
        "what",
        "tell",
        "know",
        "trained",
        "training",
        "certified",
        "certification",
        "degree",
        "university",
        "college",
        "school",
        "study",
        "studied",
        "software",
        "engineer",
        "engineering",
        "frontend",
        "backend",
        "fullstack",
        "stack",
        "framework",
        "language",
        "languages",
        "tool",
        "tools",
        "hobby",
        "hobbies",
        "interest",
        "interests",
        "achievement",
        "achievements",
        "accomplishment",
        "accomplishments",
        "history",
        "role",
        "roles",
        "position",
        "company",
        "employer",
        "hired",
        "hire",
        "intern",
        "internship",
    }
)

# Humorous fallback templates. The service cycles through them based
# on a simple hash of the query so the same question always gets the
# same flavour of humour (deterministic for testability).
_FALLBACK_TEMPLATES: list[str] = [
    "Hmm, that's a bit outside my wheelhouse! I'm really only an expert on the portfolio owner's background. "
    "But hey, Google might know: {link}",
    "Great question — but I'm just a humble portfolio bot, not a search engine! "
    "Try asking Google instead: {link}",
    "I appreciate the curiosity, but that's not in my dataset! "
    "Here's a Google search that might help: {link}",
]


class BotService:
    """Service powering the About Me chat bot.

    Classifies incoming queries, fetches user context from the
    database for relevant questions, and delegates to the configured
    LLM provider. Off-topic queries receive a humorous fallback
    response with a Google search link — no LLM call is made.
    """

    def __init__(
        self,
        llm: LLMProvider,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> None:
        self._llm = llm
        self._db = db
        self._user_id = user_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def handle_message(
        self,
        query: str,
        session_history: list[dict],
    ) -> dict:
        """Process an incoming chat message and return a response.

        Steps:
        1. Classify the query as relevant or unrelated.
        2. If unrelated, return a fallback response (no LLM call).
        3. If relevant, fetch user context, build a system prompt,
           cap the conversation history, and call the LLM provider.

        Args:
            query: The user's chat message.
            session_history: Prior conversation messages, each a dict
                with ``role`` ("user" | "assistant") and ``content`` keys.

        Returns:
            A dict with ``response`` (str) and ``is_fallback`` (bool).
        """
        classification = self.classify_query(query)

        if classification == "unrelated":
            return {
                "response": self.build_fallback_response(query),
                "is_fallback": True,
            }

        # Fetch user context from the database
        profile, skills, projects = await self._fetch_user_context()

        # Build the system prompt with user context
        system_prompt = self._build_system_prompt(profile, skills, projects)

        # Cap conversation history at MAX_HISTORY_MESSAGES
        capped_history = session_history[-MAX_HISTORY_MESSAGES:]

        # Append the current user query
        messages = [*capped_history, {"role": "user", "content": query}]

        # Call the LLM provider
        llm_response = await self._llm.generate_response(system_prompt, messages)

        return {
            "response": llm_response,
            "is_fallback": False,
        }

    def classify_query(self, query: str) -> str:
        """Classify a query as relevant or unrelated using keyword matching.

        Tokenises the query into lowercase words and checks for
        intersection with the curated keyword set.

        Args:
            query: The user's chat message.

        Returns:
            ``"relevant"`` if any keyword matches, ``"unrelated"`` otherwise.
        """
        words = set(query.lower().split())
        if words & RELEVANT_KEYWORDS:
            return "relevant"
        return "unrelated"

    def build_fallback_response(self, query: str) -> str:
        """Generate a humorous fallback message with a Google search link.

        The template is selected deterministically based on the query
        so the same input always produces the same output.

        Args:
            query: The user's original chat message.

        Returns:
            A friendly fallback string containing a Google search URL.
        """
        link = self._build_google_link(query)
        template_index = hash(query) % len(_FALLBACK_TEMPLATES)
        return _FALLBACK_TEMPLATES[template_index].format(link=link)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_google_link(query: str) -> str:
        """URL-encode the query and append to the Google search base URL.

        Args:
            query: Raw query text.

        Returns:
            A full Google search URL string.
        """
        return f"https://www.google.com/search?q={quote_plus(query)}"

    async def _fetch_user_context(
        self,
    ) -> tuple[UserProfile | None, list[SkillRecord], list[ProjectRecord]]:
        """Fetch the user's profile, skills, and projects from the DB.

        Returns:
            A tuple of (profile_or_none, skills_list, projects_list).
        """
        profile_result = await self._db.execute(
            select(UserProfile).where(UserProfile.user_id == self._user_id)
        )
        profile = profile_result.scalar_one_or_none()

        skills_result = await self._db.execute(
            select(SkillRecord)
            .where(SkillRecord.user_id == self._user_id)
            .order_by(SkillRecord.name)
        )
        skills = list(skills_result.scalars().all())

        projects_result = await self._db.execute(
            select(ProjectRecord)
            .where(ProjectRecord.user_id == self._user_id)
            .order_by(ProjectRecord.name)
        )
        projects = list(projects_result.scalars().all())

        return profile, skills, projects

    @staticmethod
    def _build_system_prompt(
        profile: UserProfile | None,
        skills: list[SkillRecord],
        projects: list[ProjectRecord],
    ) -> str:
        """Construct the LLM system prompt from user context data.

        The prompt instructs the LLM to act as a portfolio assistant
        and includes the owner's profile, skills, and projects so the
        model can answer questions accurately.

        Args:
            profile: The user's profile record (may be None).
            skills: The user's skill records.
            projects: The user's project records.

        Returns:
            A system prompt string ready for the LLM provider.
        """
        parts: list[str] = [
            "You are a friendly and professional portfolio assistant. "
            "Your job is to answer questions about the portfolio owner "
            "based on the information provided below. Be concise, "
            "accurate, and personable. If you don't have enough "
            "information to answer a question, say so honestly.",
            "",
            "--- Portfolio Owner Information ---",
        ]

        # Profile section
        if profile:
            if profile.name:
                parts.append(f"Name: {profile.name}")
            if profile.bio:
                parts.append(f"Bio: {profile.bio}")
            if profile.contact_email:
                parts.append(f"Contact: {profile.contact_email}")
            if profile.social_links:
                links = ", ".join(
                    f"{k}: {v}" for k, v in profile.social_links.items()
                )
                parts.append(f"Social Links: {links}")
        else:
            parts.append("No profile information available.")

        # Skills section
        parts.append("")
        parts.append("--- Skills ---")
        if skills:
            for skill in skills:
                parts.append(
                    f"- {skill.name} (Category: {skill.category}, "
                    f"Proficiency: {skill.proficiency_level})"
                )
        else:
            parts.append("No skills listed.")

        # Projects section
        parts.append("")
        parts.append("--- Projects ---")
        if projects:
            for project in projects:
                tags = ", ".join(project.technology_tags) if project.technology_tags else "none"
                desc = project.description or "No description"
                parts.append(
                    f"- {project.name} (Status: {project.status}, "
                    f"Technologies: {tags}): {desc}"
                )
        else:
            parts.append("No projects listed.")

        return "\n".join(parts)

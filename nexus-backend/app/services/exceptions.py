"""Custom exception classes for service layer errors.

Domain-specific exceptions that services raise to communicate
business rule violations to the API layer.
"""


class DuplicateSkillError(Exception):
    """Raised when a user attempts to create a skill with a name that already exists."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"A skill named '{name}' already exists for this user")


class SkillNotFoundError(Exception):
    """Raised when a skill cannot be found by id and user_id."""

    def __init__(self, skill_id: str) -> None:
        self.skill_id = skill_id
        super().__init__(f"Skill with id '{skill_id}' not found")


class ProjectNotFoundError(Exception):
    """Raised when a project cannot be found by id and user_id."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        super().__init__(f"Project with id '{project_id}' not found")


class EntryParentNotFoundError(Exception):
    """Raised when a learning entry references a non-existent skill or project."""

    def __init__(self, parent_type: str, parent_id: str) -> None:
        self.parent_type = parent_type
        self.parent_id = parent_id
        super().__init__(
            f"{parent_type} with id '{parent_id}' not found"
        )


class ProfileNotFoundError(Exception):
    """Raised when a user profile cannot be found for the given user_id."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__(f"Profile for user '{user_id}' not found")


class InvalidMimeTypeError(Exception):
    """Raised when an uploaded file has a MIME type not in the allowlist."""

    def __init__(self, content_type: str) -> None:
        self.content_type = content_type
        self.allowed_types = {"image/jpeg", "image/png", "image/webp"}
        super().__init__(
            f"MIME type '{content_type}' is not allowed. "
            f"Accepted types: {', '.join(sorted(self.allowed_types))}"
        )

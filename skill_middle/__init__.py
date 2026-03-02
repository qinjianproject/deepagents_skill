"""Skills module for deep-agents.

Public API:
- SkillsMiddleware: Middleware for integrating skills into agent execution
- list_skills: List available skills from user and project directories
- SkillMetadata: Type definition for skill metadata
"""

from skill_middle.load import SkillMetadata, list_skills
from skill_middle.middleware import SkillsMiddleware

__all__ = [
    "SkillsMiddleware",
    "SkillMetadata",
    "list_skills",
]

"""
AI Prompts Module
=================
Contains all agent instruction templates and system prompts.
All prompts are stored as Python string constants for version control and easy modification.
"""

from .base_prompts import (
    SYSTEM_PROMPT_BASE,
    ERROR_HANDLING_PROMPT,
    CONTEXT_SUMMARY_PROMPT,
)

__all__ = [
    'SYSTEM_PROMPT_BASE',
    'ERROR_HANDLING_PROMPT',
    'CONTEXT_SUMMARY_PROMPT',
]

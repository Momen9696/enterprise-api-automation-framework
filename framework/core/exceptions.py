"""Framework exceptions. Callers turn these into test failures."""

from __future__ import annotations


class FrameworkError(Exception):
    """Base type for expected framework failures."""


class ConfigError(FrameworkError):
    """Environment profile is missing or invalid."""


class AuthError(FrameworkError):
    """Login failed or no token is available."""


class SchemaValidationError(FrameworkError):
    """A payload does not match its JSON Schema."""


class ResponseValidationError(FrameworkError):
    """Status, field, or JSON assertions failed."""


class TransportError(FrameworkError):
    """The HTTP call could not be completed."""

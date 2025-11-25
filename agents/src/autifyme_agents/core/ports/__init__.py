"""Storage ports - Abstract interfaces for storage operations.

Re-exports StorageInterface for backward compatibility.
Import from here: `from autifyme_agents.core.ports import StorageInterface`
"""

from .storage import StorageInterface

__all__ = ["StorageInterface"]

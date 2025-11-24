"""Universal Data Engine - Modular tool factories for agent data operations.

Three powerful engines providing agent superpowers:
- inspect_schema: Schema discovery, stats, samples
- read_data: Query, search, batch fetch, pagination, counting
- aggregate_data: Analytics with GROUP BY and HAVING
- write_data: Multi-operation atomic transactions with dependencies

Design philosophy:
- Token-efficient (schema fetched on-demand)
- Specialist-scoped access control (table restrictions)
- Agent-centric naming (what agents DO, not database mechanics)
- Intelligence-first (trust agents with rich context)
"""

from autifyme_agents.tools.data_engine.aggregate_data import create_aggregate_data_tool
from autifyme_agents.tools.data_engine.inspect_schema import create_inspect_schema_tool
from autifyme_agents.tools.data_engine.read_data import create_read_data_tool
from autifyme_agents.tools.data_engine.write_data import create_write_data_tool

__all__ = [
    "create_inspect_schema_tool",
    "create_read_data_tool",
    "create_aggregate_data_tool",
    "create_write_data_tool",
]

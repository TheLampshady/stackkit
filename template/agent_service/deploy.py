#!/usr/bin/env python3
"""
Deploy agents to Vertex AI Agent Engine.

Uses vertexai.agent_engines with extra_packages=["."] to package the entire
agent_service/ directory, including gcp_services/ and app_settings.py.

Updates an existing agent if one with the same display_name exists,
otherwise creates a new one.
"""

from agents.agent1 import root_agent as agent1
from agents.agent2 import root_agent as agent2
from app_settings import settings
from vertexai import agent_engines

AGENT_MAP: dict[str, list] = {
    "agent1": ["ConversionAgent", agent1],
    "agent2": ["LayoutAgent", agent2],
}


def get_resource_name(app_name: str) -> str:
    """
    Find the newest existing agent with the given display_name.

    :param app_name: The display_name to search for.
    :return: The resource_name if found, empty string otherwise.
    """
    agent_list = list(agent_engines.list(filter=f'display_name="{app_name}"'))
    if not agent_list:
        return ""
    newest_agent = next(
        iter(
            sorted(
                agent_list,
                key=lambda a: a.update_time or a.create_time,
                reverse=True,
            )
        )
    )
    return newest_agent.resource_name


def run(agent_name: str):
    """
    Deploy or update an agent on Agent Engine.

    :param agent_name: Key from AGENT_MAP (e.g., 'agent1', 'agent2').
    """
    entry = AGENT_MAP.get(agent_name.lower())
    if not entry:
        raise LookupError(f"No agent '{agent_name}': Use {list(AGENT_MAP.keys())}")

    app_name, agent_instance = entry
    resource_name = get_resource_name(app_name)

    # Wrap with AdkApp for tracing support
    app = agent_engines.AdkApp(
        agent=agent_instance,
        enable_tracing=True,
    )

    if resource_name:
        print(f"Updating Agent: {resource_name}")
        resp = agent_engines.update(
            resource_name,
            agent_engine=app,  # type: ignore[arg-type]
            display_name=app_name,
            extra_packages=["."],
            requirements="requirements.txt",
            env_vars={"PROJECT_ID": settings.project_id},
        )
    else:
        print("Creating New Agent")
        resp = agent_engines.create(
            agent_engine=app,  # type: ignore[arg-type]
            display_name=app_name,
            extra_packages=["."],
            requirements="requirements.txt",
            env_vars={"PROJECT_ID": settings.project_id},
        )

    print(resp.resource_name)


if __name__ == "__main__":
    run("agent1")

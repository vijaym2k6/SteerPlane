"""
SteerPlane SDK — Framework Integrations.

Available integrations:
    - LangChain: SteerPlaneCallbackHandler
    - OpenAI Agents SDK: SteerPlaneAgentHooks
    - CrewAI: SteerPlaneCrewMonitor
    - AutoGen: SteerPlaneAutoGenMonitor

Each integration is lazily imported to avoid requiring all framework
dependencies. Import only the integration you need:

    from steerplane.integrations.langchain import SteerPlaneCallbackHandler
    from steerplane.integrations.openai_agents import SteerPlaneAgentHooks
    from steerplane.integrations.crewai import SteerPlaneCrewMonitor
    from steerplane.integrations.autogen import SteerPlaneAutoGenMonitor
"""


def __getattr__(name):
    """Lazy imports to avoid requiring all framework dependencies."""
    if name == "SteerPlaneCallbackHandler":
        from .langchain import SteerPlaneCallbackHandler

        return SteerPlaneCallbackHandler
    if name == "SteerPlaneAgentHooks":
        from .openai_agents import SteerPlaneAgentHooks

        return SteerPlaneAgentHooks
    if name == "SteerPlaneCrewMonitor":
        from .crewai import SteerPlaneCrewMonitor

        return SteerPlaneCrewMonitor
    if name == "SteerPlaneAutoGenMonitor":
        from .autogen import SteerPlaneAutoGenMonitor

        return SteerPlaneAutoGenMonitor
    raise AttributeError(f"module 'steerplane.integrations' has no attribute {name!r}")


__all__ = [
    "SteerPlaneCallbackHandler",
    "SteerPlaneAgentHooks",
    "SteerPlaneCrewMonitor",
    "SteerPlaneAutoGenMonitor",
]

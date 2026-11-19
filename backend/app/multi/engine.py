"""Explicit execution profile selection; never an automatic fallback."""
import os
from app.clinical.access import fail
from app.multi.legacy_v1 import trusted_context  # Backward-compatible trusted read interface.

def run_investigation(actor, request, write):
    profile = os.getenv("MULTI_AGENT_EXECUTION_PROFILE", "optimized")
    if profile == "legacy":
        from app.multi.legacy_v1 import run_investigation as execute
    elif profile == "optimized":
        from app.multi.optimized import run_investigation as execute
    else:
        fail(503, "invalid_multi_agent_configuration", "Choose optimized or legacy execution explicitly.")
    return execute(actor, request, write)

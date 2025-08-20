"""
Deprecated module: smart context system has been removed.

This file remains only to make stale imports fail fast and explicitly. Do not use.
Switch to `sanskara.context_service.assemble_baseline_context` for deterministic context.
"""

raise ImportError(
    "sanskara.context_manager is deprecated and removed. Use sanskara.context_service.assemble_baseline_context instead."
)

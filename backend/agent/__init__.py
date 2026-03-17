"""
agent/__init__.py
──────────────────
Makes agent/ a Python package.
Exports the compiled graph for use in main.py.

Usage:
    from agent import agent_graph
"""

from agent.graph import agent_graph

__all__ = ["agent_graph"]
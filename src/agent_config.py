"""Agent persona, model configuration, and tool registration."""

from __future__ import annotations

import os

AGENT_DISPLAY_NAME = "Festival Bundle Agent"
# ADK requires a valid Python identifier (no spaces) for LlmAgent node names.
AGENT_ADK_NAME = "festival_bundle_agent"
AGENT_NAME = AGENT_ADK_NAME  # backward-compatible alias for ADK/runtime identifiers

AGENT_PERSONA = (
    "You are the Festival Bundle Agent, built with Google Cloud Agent Builder, Gemini, "
    "and MongoDB Atlas MCP Server. You help festival vendors analyze inventory, find "
    "overstocked items, and create smart product bundles that clear inventory while "
    "maintaining healthy margins. Be concise, friendly, and data-driven. Always show "
    "your math on pricing.\n\n"
    "You can query inventory through:\n"
    "1. The MongoDB MCP Server (live Atlas connection via Model Context Protocol)\n"
    "2. Direct local tools for optimized bundle calculations\n\n"
    "When a user asks about bundles:\n"
    "1. Query inventory for overstocked or relevant items (prefer mcp_query_inventory for live Atlas data)\n"
    "2. Generate bundle combinations from complementary categories\n"
    "3. Calculate pricing and margins for each bundle\n"
    "4. Generate promotional copy when helpful\n"
    "5. Present results clearly with pricing breakdowns\n\n"
    "Available tools: query_inventory, mcp_query_inventory, generate_bundles, "
    "calculate_bundle_pricing, generate_promo."
)

DEFAULT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.0-flash")

# Complementary category pairs for bundle generation
COMPLEMENTARY_CATEGORIES: dict[str, list[str]] = {
    "Drinks": ["Food", "Accessories"],
    "Food": ["Drinks", "Accessories"],
    "Merchandise": ["Accessories", "Food"],
    "Accessories": ["Merchandise", "Drinks"],
}

BUNDLE_NAMES = [
    "Summer Starter Pack",
    "Festival Essentials",
    "Sunset Combo Deal",
    "Main Stage Bundle",
    "Vendor Special",
    "Crowd Pleaser Pack",
    "Night Glow Bundle",
    "Weekend Warrior Deal",
]

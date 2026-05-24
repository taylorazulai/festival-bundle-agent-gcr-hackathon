"""Promotional description generator for bundles."""

from __future__ import annotations

from typing import Any, Literal

from src.utils.logging_config import get_logger

logger = get_logger("generate_promo")

Tone = Literal["festival", "professional", "casual"]

_EMOJI = {"festival": "🎪", "professional": "✨", "casual": "😎"}
_HASHTAGS = {
    "festival": "#FestivalVibes #BundleDeal #LiveMusic",
    "professional": "#SpecialOffer #ValueBundle #LimitedTime",
    "casual": "#DealAlert #FestivalSeason #SaveBig",
}


def generate_promo(
    bundle_name: str,
    bundle_items: list[str],
    bundle_price: float,
    original_price: float,
    tone: Tone = "festival",
) -> dict[str, Any]:
    """Generate marketing-ready promotional descriptions for product bundles.

    Creates engaging, festival-themed copy that vendors can use directly in marketing.

    Args:
        bundle_name: Name of the bundle.
        bundle_items: Item names in the bundle.
        bundle_price: Bundle sale price.
        original_price: Original combined retail price.
        tone: Tone — festival, professional, or casual.

    Returns:
        Object with tagline, description, social_caption, savings_amount, savings_percent.
    """
    try:
        savings_amount = round(original_price - bundle_price, 2)
        savings_percent = (
            round((savings_amount / original_price) * 100, 1) if original_price else 0.0
        )
        items_str = ", ".join(bundle_items[:3])
        if len(bundle_items) > 3:
            items_str += f" + {len(bundle_items) - 3} more"
        emoji = _EMOJI.get(tone, "🎪")
        hashtags = _HASHTAGS.get(tone, _HASHTAGS["festival"])

        if tone == "professional":
            tagline = f"{bundle_name}: curated value at ${bundle_price:.2f}."
            description = (
                f"Introducing {bundle_name} — a thoughtfully priced bundle featuring "
                f"{items_str}. Regularly ${original_price:.2f}, now ${bundle_price:.2f}. "
                f"You save ${savings_amount:.2f} ({savings_percent:.0f}% off)."
            )
            social_caption = (
                f"{emoji} {bundle_name} — ${bundle_price:.2f} (save ${savings_amount:.2f}!) {hashtags}"
            )
        elif tone == "casual":
            tagline = f"Grab the {bundle_name} — only ${bundle_price:.2f}!"
            description = (
                f"Hey festival fam! The {bundle_name} packs {items_str} for just "
                f"${bundle_price:.2f}. That's ${savings_amount:.2f} off the usual "
                f"${original_price:.2f}. Don't sleep on this one!"
            )
            social_caption = (
                f"{emoji} {bundle_name} = ${bundle_price:.2f} 🔥 Save ${savings_amount:.2f}! {hashtags}"
            )
        else:
            tagline = f"{bundle_name} — festival favorites for ${bundle_price:.2f}!"
            description = (
                f"Light up your festival day with {bundle_name}! Includes {items_str} "
                f"for just ${bundle_price:.2f} — save ${savings_amount:.2f} "
                f"({savings_percent:.0f}% off the ${original_price:.2f} retail total)."
            )
            social_caption = (
                f"{emoji} {bundle_name} ${bundle_price:.2f} — save ${savings_amount:.2f}! {hashtags}"
            )

        result = {
            "status": "success",
            "bundle_name": bundle_name,
            "tagline": tagline,
            "description": description,
            "social_caption": social_caption,
            "savings_amount": savings_amount,
            "savings_percent": savings_percent,
            "tone": tone,
        }

        logger.info("Generated promo copy", extra={"extra_data": {"bundle": bundle_name, "tone": tone}})
        return result

    except Exception as exc:
        logger.error("generate_promo failed", extra={"extra_data": {"error": str(exc)}})
        return {"status": "error", "message": str(exc)}


def generate_promo_tool(
    bundle_name: str,
    bundle_items: list[str],
    bundle_price: float,
    original_price: float,
    tone: str = "festival",
) -> dict[str, Any]:
    """ADK-compatible wrapper for generate_promo."""
    return generate_promo(
        bundle_name=bundle_name,
        bundle_items=bundle_items,
        bundle_price=bundle_price,
        original_price=original_price,
        tone=tone,  # type: ignore[arg-type]
    )

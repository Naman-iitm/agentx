"""Recycling Agent — category handling recommendations and run-level insights.

MVP mode (per agents_config.md): operator-selected or imported categories.
The optional vision classifier is a documented Phase 10 extension. This agent
never makes unreviewed hazardous-waste decisions.
"""
from app.schemas.domain import HANDLING_RECOMMENDATIONS, WASTE_CATEGORIES

AGENT_NAME = "recycling_agent"
MODEL_VERSION = "rules-v1"

RECYCLABLE = {"PAPER", "PLASTIC", "METAL", "GLASS", "E_WASTE", "ORGANIC"}
BIN_TYPE_DEFAULT_CATEGORY = {
    "general": "MIXED",
    "organic": "ORGANIC",
    "recycling": "MIXED",
}


def handling_for(category: str) -> dict:
    """Recommendation + caution for a waste category."""
    entry = HANDLING_RECOMMENDATIONS.get(category, HANDLING_RECOMMENDATIONS["UNKNOWN"])
    return {"category": category, **entry}


def classify(
    *,
    category: str,
    bin_id: str | None,
    source: str = "operator",
    confidence: float | None = None,
    low_confidence_threshold: float = 0.55,
) -> dict:
    """Validate a classification and derive review status + handling."""
    category = category.strip().upper()
    if category not in WASTE_CATEGORIES:
        return {
            "ok": False,
            "error": f"Unsupported category '{category}'. Supported: {', '.join(WASTE_CATEGORIES)}.",
        }

    review_status = "confirmed"
    warnings: list[str] = []
    if source == "model" and confidence is not None and confidence < low_confidence_threshold:
        category = "UNKNOWN"
        review_status = "review_required"
        warnings.append(
            f"Model confidence {confidence:.2f} below threshold {low_confidence_threshold} "
            "— downgraded to UNKNOWN pending human review."
        )
    if category == "HAZARDOUS":
        review_status = "review_required"
        warnings.append("Hazardous classification always requires human review.")

    rec = handling_for(category)
    return {
        "ok": True,
        "bin_id": bin_id,
        "category": category,
        "confidence": confidence,
        "source": source,
        "model_version": MODEL_VERSION if source == "model" else None,
        "review_status": review_status,
        "recommendation": rec["recommendation"],
        "caution": rec.get("caution"),
        "warnings": warnings,
    }


def run_insights(candidates: list[dict], latest_classifications: dict[str, str]) -> dict:
    """Category distribution + handling recommendations for a collection run.

    latest_classifications: bin_id → latest category (falls back to the bin's
    type default). Distribution counts are labelled estimates.
    """
    distribution: dict[str, int] = {}
    for c in candidates:
        cat = latest_classifications.get(
            c["bin_id"], BIN_TYPE_DEFAULT_CATEGORY.get(c.get("bin_type", "general"), "MIXED")
        )
        distribution[cat] = distribution.get(cat, 0) + 1

    recommendations = [handling_for(cat) for cat in sorted(distribution)]
    recyclable = sum(n for cat, n in distribution.items() if cat in RECYCLABLE)
    total = sum(distribution.values())
    diversion = round(100.0 * recyclable / total, 1) if total else None

    return {
        "distribution": distribution,
        "recommendations": recommendations,
        "diversion_estimate_percent": diversion,
        "note": "Category mix is an estimate from operator classifications and bin types.",
    }

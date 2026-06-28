"""System status check tool."""

from __future__ import annotations

from src.models.schemas import ToolResponse
from src.paths import DATA_DIR
from src.tools.base import fail, load_json, ok

STATUS_FILE = DATA_DIR / "status" / "services.json"


def _load_services() -> list[dict]:
    data = load_json(STATUS_FILE)
    return list(data.get("services", []))


def _format_service(service: dict) -> dict:
    return {
        "service_id": service["service_id"],
        "name": service["name"],
        "health": service["health"],
        "affected_regions": service.get("affected_regions", []),
        "description": service.get("description", ""),
        "eta_resolution": service.get("eta_resolution"),
        "recent_changes": service.get("recent_changes", []),
    }


def status_check(service_id: str | None = None, region: str | None = None) -> ToolResponse:
    try:
        services = _load_services()
    except FileNotFoundError:
        return fail("status_check", "status data unavailable")

    if not service_id:
        summaries = [
            {
                "service_id": s["service_id"],
                "name": s["name"],
                "health": s["health"],
                "affected_regions": s.get("affected_regions", []),
            }
            for s in services
        ]
        if region:
            region_lower = region.lower()
            summaries = [
                s
                for s in summaries
                if region_lower in [r.lower() for r in s.get("affected_regions", [])]
                or s["health"] != "healthy"
            ]
        return ok("status_check", {"services": summaries, "total_found": len(summaries)})

    matched = next((s for s in services if s["service_id"] == service_id), None)
    if not matched:
        return fail("status_check", f"service not found: {service_id}")

    formatted = _format_service(matched)
    if region:
        region_lower = region.lower()
        affected = [r.lower() for r in formatted.get("affected_regions", [])]
        formatted["region_impacted"] = region_lower in affected or formatted["health"] != "healthy"

    return ok("status_check", formatted)

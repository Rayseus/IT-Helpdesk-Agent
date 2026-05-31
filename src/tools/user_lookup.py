"""Employee directory lookup tool."""

from __future__ import annotations

import json
from pathlib import Path

from src.models.schemas import Employee
from src.paths import DATA_DIR
from src.tools.base import fail, ok

USERS_DIR = DATA_DIR / "users"


def _load_all_employees() -> list[Employee]:
    employees: list[Employee] = []
    for path in USERS_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        employees.append(Employee.model_validate(data))
    return employees


def user_lookup(employee_id: str | None = None, email: str | None = None) -> ToolResponse:
    if not employee_id and not email:
        return fail("user_lookup", "employee_id or email is required")

    employees = _load_all_employees()
    match: Employee | None = None

    if employee_id:
        match = next((e for e in employees if e.id == employee_id), None)
    elif email:
        email_lower = email.lower()
        match = next((e for e in employees if e.email.lower() == email_lower), None)

    if not match:
        return fail("user_lookup", "employee_not_found")

    return ok("user_lookup", match.model_dump(mode="json"))

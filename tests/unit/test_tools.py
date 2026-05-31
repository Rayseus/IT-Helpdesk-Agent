"""Unit tests for IT backend tools."""

import pytest

from src.tools.history_search import history_search
from src.tools.kb_search import kb_search
from src.tools.policy_check import policy_check
from src.tools.status_check import status_check
from src.tools.user_lookup import user_lookup


@pytest.mark.unit
def test_kb_search_okta():
    result = kb_search("okta password reset")
    assert result.success
    assert result.data is not None
    assert result.data["total_found"] >= 1
    articles = result.data["articles"]
    assert any("okta" in a["title"].lower() or "okta" in a["id"] for a in articles)
    assert "content" in articles[0]
    assert len(articles[0]["content"]) >= len(articles[0]["snippet"])


@pytest.mark.unit
def test_kb_search_empty_query():
    result = kb_search("")
    assert not result.success
    assert result.error == "query is required"


@pytest.mark.unit
def test_kb_search_category_filter():
    result = kb_search("access", category="access")
    assert result.success
    for article in result.data["articles"]:
        assert article["category"] == "access"


@pytest.mark.unit
def test_status_check_single_service():
    result = status_check(service_id="salesforce")
    assert result.success
    assert result.data["service_id"] == "salesforce"
    assert result.data["health"] == "degraded"


@pytest.mark.unit
def test_status_check_all_services():
    result = status_check()
    assert result.success
    assert result.data["total_found"] == 5


@pytest.mark.unit
def test_status_check_not_found():
    result = status_check(service_id="nonexistent")
    assert not result.success


@pytest.mark.unit
def test_user_lookup_by_id():
    result = user_lookup(employee_id="emp-001")
    assert result.success
    assert result.data["email"] == "jane.doe@company.com"
    assert result.data["location"] == "Chicago"


@pytest.mark.unit
def test_user_lookup_locked_account():
    result = user_lookup(employee_id="emp-locked")
    assert result.success
    assert result.data["account_status"] == "locked"
    assert result.data["lock_reason"]


@pytest.mark.unit
def test_user_lookup_not_found():
    result = user_lookup(employee_id="emp-999")
    assert not result.success
    assert result.error == "employee_not_found"


@pytest.mark.unit
def test_history_search_salesforce():
    result = history_search("salesforce slow chicago")
    assert result.success
    assert result.data["total_found"] >= 1


@pytest.mark.unit
def test_history_search_with_systems_filter():
    result = history_search("pipeline", systems=["jenkins"])
    assert result.success
    assert all("jenkins" in r["systems_involved"] for r in result.data["records"])


@pytest.mark.unit
def test_policy_check_snowflake_prod_denied():
    result = policy_check("grant_snowflake_prod", employee_id="emp-002")
    assert result.success
    assert result.data["agent_can_execute"] is False
    assert result.data["approval_required"] == "manager"


@pytest.mark.unit
def test_policy_check_grafana_allowed_for_data_eng():
    result = policy_check("grant_grafana_readonly", employee_id="emp-002")
    assert result.success
    assert result.data["agent_can_execute"] is True


@pytest.mark.unit
def test_policy_check_unknown_action():
    result = policy_check("unknown_action_xyz", employee_id="emp-001")
    assert not result.success


@pytest.mark.unit
def test_registry_tools_count():
    from src.tools.registry import get_langchain_tools

    tools = get_langchain_tools()
    assert len(tools) == 5
    names = {t.name for t in tools}
    assert names == {"kb_search", "status_check", "user_lookup", "history_search", "policy_check"}

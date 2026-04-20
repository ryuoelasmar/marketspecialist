from chat.tools import DISPATCH, TOOLS


def test_tools_have_required_fields():
    for tool in TOOLS:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"


def test_every_tool_has_dispatcher():
    names = {t["name"] for t in TOOLS}
    assert names == set(DISPATCH.keys())


def test_unknown_tool_returns_error():
    from chat.tools import run_tool

    out = run_tool("doesnotexist", {})
    assert "Unknown tool" in out

"""
Unit tests for Problem 1 fix:
  WorkFlowAgent_Rebuild/lang_graph/main/subgraph.py

Bug: human_feedback() returned early with condition="direct_input" even when
     the last message was a ToolMessage.  That caused go_to_end_or_get_user_input
     to route to "get_user_input" instead of END, making the next subgraph's
     template (e.g. flight query prompt) appear right after a weather result.

Fix: guard the direct_input early-return so it is skipped when the last message
     is a ToolMessage; the ToolMessage branch then sets condition="next_graph_or_end".
"""

import sys
import types

import pytest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Minimal stubs so we can import subgraph without the full project installed
# ---------------------------------------------------------------------------

def _make_stub(name):
    mod = types.ModuleType(name)
    sys.modules.setdefault(name, mod)
    return mod


def _stub_langchain_core():
    lc = _make_stub("langchain_core")
    msgs = _make_stub("langchain_core.messages")

    class _Base:
        def __init__(self, content="", **kw):
            self.content = content
            self.tool_calls = kw.get("tool_calls", [])
            self.type = kw.get("type", "base")

    class AIMessage(_Base):
        type = "ai"

    class HumanMessage(_Base):
        type = "human"

    class SystemMessage(_Base):
        type = "system"

    class ToolMessage(_Base):
        type = "tool"

        def __init__(self, content="", name="", **kw):
            super().__init__(content=content, **kw)
            self.name = name

    msgs.AIMessage = AIMessage
    msgs.HumanMessage = HumanMessage
    msgs.SystemMessage = SystemMessage
    msgs.ToolMessage = ToolMessage
    lc.messages = msgs
    return AIMessage, HumanMessage, SystemMessage, ToolMessage


def _stub_remaining():
    for mod_name in [
        "langchain_ollama",
        "langgraph",
        "langgraph.types",
        "langgraph.graph",
        "lang_graph",
        "lang_graph.main",
        "lang_graph.main.about_file",
        "lang_graph.main.state",
        "lang_graph.main.config",
        "lang_graph.main.tools",
    ]:
        _make_stub(mod_name)

    sys.modules["langgraph.types"].interrupt = lambda msg: msg
    sys.modules["langgraph.graph"].END = "__end__"
    sys.modules["lang_graph.main.about_file"].dynamic_functions_google_schema = []
    sys.modules["lang_graph.main.state"].State = dict
    sys.modules["lang_graph.main.config"].initial_input = {}
    sys.modules["lang_graph.main.tools"].querys = {
        "get_weather_info": "請輸入天氣查詢資訊",
        "get_flight_info": "請輸入航班查詢資訊",
    }

    class _FakeLLM:
        def bind_tools(self, **kw):
            return self
        def invoke(self, msgs):
            m = MagicMock()
            m.content = "fake"
            m.tool_calls = []
            return m
        def with_structured_output(self, schema):
            return self

    sys.modules["langchain_ollama"].ChatOllama = lambda **kw: _FakeLLM()


# Run stubs before importing module under test
_AIMessage, _HumanMessage, _SystemMessage, _ToolMessage = _stub_langchain_core()
_stub_remaining()

import importlib
import WorkFlowAgent_Rebuild.lang_graph.main.subgraph as _sg_module  # noqa: E402

SubGraph = _sg_module.SubGraph
AIMessage = _sg_module.AIMessage
ToolMessage = _sg_module.ToolMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_subgraph():
    fake_tool = MagicMock()
    fake_tool.__name__ = "get_weather_info"
    graph = MagicMock()
    return SubGraph(graph, fake_tool)


def _base_state(**extra):
    state = {
        "messages": [],
        "feedback": "",
        "condition": "",
        "tool_use": [],
        "args_missing_funcname": "",
        "tool_calls_args": {},
        "empty_args": [],
    }
    state.update(extra)
    return state


# ---------------------------------------------------------------------------
# Tests for Problem 1
# ---------------------------------------------------------------------------

class TestHumanFeedbackToolMessageRouting:
    """Ensure ToolMessage is processed even when condition=='direct_input'."""

    def setup_method(self):
        self.sg = _make_subgraph()

    def test_tool_message_sets_condition_next_graph_or_end(self):
        """
        When the last message is a ToolMessage, human_feedback must set
        condition='next_graph_or_end' regardless of any prior condition value.
        """
        tool_msg = ToolMessage(content="晴天，25°C", name="weather_info")
        state = _base_state(
            messages=[tool_msg],
            condition="direct_input",
            feedback="台北天氣",
        )
        result = self.sg.human_feedback(state)
        assert result["condition"] == "next_graph_or_end", (
            "condition should be 'next_graph_or_end' after processing a ToolMessage"
        )

    def test_direct_input_early_return_skipped_for_tool_message(self):
        """
        The direct_input early-return must NOT fire when last message is ToolMessage.
        """
        tool_msg = ToolMessage(content="test content", name="weather_info")
        state = _base_state(
            messages=[tool_msg],
            condition="direct_input",
            feedback="some feedback",
        )
        result = self.sg.human_feedback(state)
        assert result["condition"] != "direct_input", (
            "direct_input early-return must be bypassed when last message is ToolMessage"
        )

    def test_direct_input_early_return_fires_without_tool_message(self):
        """
        When condition=='direct_input', feedback is set, and last message is NOT a
        ToolMessage, the early-return path should still work.
        """
        ai_msg = AIMessage(content="template shown")
        state = _base_state(
            messages=[ai_msg],
            condition="direct_input",
            feedback="some feedback",
        )
        result = self.sg.human_feedback(state)
        assert result["condition"] == "direct_input", (
            "direct_input early-return should fire when there is no pending ToolMessage"
        )

    def test_go_to_end_returns_end_when_condition_next_graph_or_end(self):
        """
        go_to_end_or_get_user_input must return END when condition == 'next_graph_or_end'.
        """
        from langgraph.graph import END
        state = _base_state(condition="next_graph_or_end")
        result = self.sg.go_to_end_or_get_user_input(state)
        assert result == END

    def test_go_to_end_returns_get_user_input_for_other_conditions(self):
        """
        For any other condition, the graph continues to 'get_user_input'.
        """
        for cond in ("", "direct_input", "assistant", "lack_args", "parse_args"):
            state = _base_state(condition=cond)
            result = self.sg.go_to_end_or_get_user_input(state)
            assert result == "get_user_input", (
                f"Expected 'get_user_input' for condition={cond!r}, got {result!r}"
            )

    def test_flight_tool_message_also_sets_next_graph_or_end(self):
        """Any ToolMessage (not just weather) must set condition correctly."""
        tool_msg = ToolMessage(content="BR123, TPE→NRT", name="flight_info")
        state = _base_state(
            messages=[tool_msg],
            condition="direct_input",
            feedback="台北到東京航班",
        )
        result = self.sg.human_feedback(state)
        assert result["condition"] == "next_graph_or_end"

    def test_empty_tool_message_also_routes_to_end(self):
        """Even an empty-content ToolMessage should set condition='next_graph_or_end'."""
        tool_msg = ToolMessage(content="", name="flight_info")
        state = _base_state(
            messages=[tool_msg],
            condition="direct_input",
            feedback="TPE to NRT",
        )
        result = self.sg.human_feedback(state)
        assert result["condition"] == "next_graph_or_end"

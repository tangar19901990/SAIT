from core.agent_loop import AgentLoop, AgentTask


def test_agent_can_call_tool_and_finish():
    calls = []

    def echo(text):
        calls.append(text)
        return {"text": text}

    decisions = iter([
        {"action": "echo", "arguments": {"text": "hello"}},
        {"action": "finish", "output": "done"},
    ])

    agent = AgentLoop(lambda task, history: next(decisions), {"echo": echo})
    result = agent.run(AgentTask("test"))

    assert result.status == "completed"
    assert result.output == "done"
    assert calls == ["hello"]

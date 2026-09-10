from observer.research.reviewer import gpt_reviewer, grok_reviewer, deepseek_reviewer

import pytest


def test_named_reviewers_are_unavailable_not_simulated():
    for reviewer in (gpt_reviewer, grok_reviewer, deepseek_reviewer):
        avail = reviewer.availability()
        assert avail["status"] == "UNAVAILABLE"
        assert avail["adapter"] == "NOT CONFIGURED"
        assert avail["credentials"] == "NOT PRESENT"
        assert avail["last_verified"] == "NEVER"
        result = reviewer.submit_review({"question": "Who benefited?", "evidence": []})
        assert result["status"] == "UNAVAILABLE"
        assert not result.get("analysis")
        assert "reviewed your claim" not in str(result).lower()
        with pytest.raises(RuntimeError):
            reviewer.receive_result("never-ran")

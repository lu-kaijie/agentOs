from agentos.policy import CommandApprovalPolicy


def test_policy_requires_approval_for_destructive_command():
    policy = CommandApprovalPolicy()

    decision = policy.evaluate(["rm", "temp.txt"])

    assert decision.requires_approval is True
    assert decision.matched_rule == "destructive-command"
    assert decision.risk_level == "high"


def test_policy_allows_safe_command():
    policy = CommandApprovalPolicy()

    decision = policy.evaluate(["pwd"])

    assert decision.requires_approval is False
    assert decision.matched_rule == "safe-command"
    assert decision.risk_level == "low"


def test_policy_requires_approval_for_inline_shell_wrapper():
    policy = CommandApprovalPolicy()

    decision = policy.evaluate(["bash", "-lc", "cat README.md"])

    assert decision.requires_approval is True
    assert decision.matched_rule == "shell-wrapper"
    assert decision.risk_level == "medium"


def test_policy_requires_approval_for_absolute_shell_wrapper():
    policy = CommandApprovalPolicy()

    decision = policy.evaluate(["/bin/sh", "-c", "cat README.md"])

    assert decision.requires_approval is True
    assert decision.matched_rule == "shell-wrapper"
    assert decision.risk_level == "medium"

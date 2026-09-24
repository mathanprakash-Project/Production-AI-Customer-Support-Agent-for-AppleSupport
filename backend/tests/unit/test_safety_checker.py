"""
Unit tests for Stage 5: Safety and Policy Checker.
"""

import pytest
from app.agent.safety_checker import SafetyChecker


def test_safety_checker_valid_apple_url():
    checker = SafetyChecker()
    valid_text = "You can verify your coverage status at https://checkcoverage.apple.com to review repair options."
    res = checker.check(valid_text)
    assert res.passed is True
    assert len(res.flags) == 0


def test_safety_checker_flags_hallucinated_url():
    checker = SafetyChecker()
    bad_url_text = "Please download the battery utility from https://unknown-thirdparty-apple-tools.com/fix"
    res = checker.check(bad_url_text)
    assert res.passed is False
    assert any("Unapproved/hallucinated URL" in flag for flag in res.flags)


def test_safety_checker_flags_unauthorized_promise():
    checker = SafetyChecker()
    promise_text = "We promise a 100% free replacement will be sent to your house today."
    res = checker.check(promise_text)
    assert res.passed is False
    assert any("Unauthorized promise" in flag for flag in res.flags)


def test_safety_checker_allows_up_to_469_chars():
    checker = SafetyChecker()
    # 290 chars (the customer scenario) should pass cleanly
    text_290 = "A" * 290
    res_290 = checker.check(text_290, response_type="tweet")
    assert res_290.passed is True
    assert len(res_290.flags) == 0

    # Exactly 469 chars should also pass
    text_469 = "A" * 469
    res_469 = checker.check(text_469, response_type="tweet")
    assert res_469.passed is True
    assert len(res_469.flags) == 0


def test_safety_checker_flags_excessive_length():
    checker = SafetyChecker()
    long_text = "A" * 475
    res = checker.check(long_text, response_type="tweet")
    assert res.passed is False
    assert any("exceeds maximum 469 limit" in flag for flag in res.flags)



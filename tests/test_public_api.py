"""Проверки публичного API, необходимого интеграциям."""

from anycaptcha import CloudflareChallengeType, CloudflareTurnstile, Solver


def test_cloudflare_turnstile_is_exported() -> None:
    captcha = CloudflareTurnstile("site-key", "https://example.com")

    assert captcha.challenge_type is CloudflareChallengeType.TURNSTILE
    assert callable(Solver.solve_cloudflare_turnstile)

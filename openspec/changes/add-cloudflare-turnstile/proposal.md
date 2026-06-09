# Proposal: add-cloudflare-turnstile

## Why

The library currently has no support for Cloudflare captchas at all, while Cloudflare Turnstile (standalone widget, Challenge pages and the `cf_clearance` cookie flow) is one of the most demanded captcha types today. Most solver services already integrated in the library (CapMonster, CapSolver, anti-captcha, 2captcha/ruCaptcha, DeathByCaptcha, cap.guru, AZcaptcha, multibot) document Turnstile support, so the fork needs a unified interface to it.

## What Changes

- New captcha type `CloudflareTurnstile` (with `CloudflareTurnstileSolution`) covering all three Cloudflare variants behind a single dataclass:
  - **Turnstile** — standalone widget → token;
  - **Turnstile Challenge** — Cloudflare Challenge page → token (requires `page_action`/`data`/`page_data` extras);
  - **Challenge Cookie (`cf_clearance`)** — full Cloudflare challenge bypass → `cf_clearance` cookie (proxy + user-agent mandatory; supported only by CapMonster and CapSolver).
- New `CaptchaType.CLOUDFLARE_TURNSTILE` enum member.
- New `Solver.solve_cloudflare_turnstile(...)` high-level method.
- `TurnstileTaskRequest` / `TurnstileSolutionRequest` implementations for every provider with documented support:
  - `capmonster` — `TurnstileTask` (+ `cloudflareTaskType: token | cf_clearance`);
  - `capsolver` — `AntiTurnstileTaskProxyLess` / `AntiCloudflareTask` (cf_clearance);
  - `anti_captcha` — `TurnstileTask` / `TurnstileTaskProxyless` (token only);
  - `twocaptcha`, `rucaptcha`, `captcha_guru`, `azcaptcha`, `multibot_captcha` — legacy `method=turnstile` (token only);
  - `deathbycaptcha` — Turnstile via `type=12` + `turnstile_params` (token only).
- Providers without documented Turnstile support (`cptch_net`, `sctg_captcha`) are intentionally left unchanged — the existing `supported_captchas` mechanism will report the type as unsupported automatically.
- Requesting an unsupported variant (e.g. `cf_clearance` from anti-captcha) raises a clear library error instead of a cryptic service error.

## Capabilities

### New Capabilities

- `cloudflare-turnstile-captcha`: unified captcha model for Cloudflare Turnstile (widget / challenge token / cf_clearance cookie), its solution model, solver entry point, and per-provider task/solution request behavior.

### Modified Capabilities

<!-- none: openspec/specs/ is empty; existing captcha types are unaffected -->

## Impact

- `anycaptcha/enums.py` — new `CaptchaType` member.
- `anycaptcha/captcha/cloudflare_turnstile.py` (new) + `anycaptcha/captcha/__init__.py`, `anycaptcha/__init__.py` exports.
- `anycaptcha/solver.py` — new `solve_cloudflare_turnstile` method.
- `anycaptcha/service/{capmonster,capsolver,anti_captcha,twocaptcha,rucaptcha,captcha_guru,azcaptcha,multibot_captcha,deathbycaptcha}.py` — new request classes + `__all__` updates + polling settings.
- `anycaptcha/errors.py` — no new classes expected; reuse `BadInputDataError`/`AnyCaptchaException` for unsupported variants.
- No breaking changes: existing captcha types and provider APIs stay untouched.

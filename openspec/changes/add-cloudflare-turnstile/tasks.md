# Tasks: add-cloudflare-turnstile

## 1. Core model (captcha type, solution, enums, exports)

- [x] 1.1 Add `CaptchaType.CLOUDFLARE_TURNSTILE = "CloudflareTurnstile"` and the `CloudflareChallengeType` enum (`TURNSTILE`/`CHALLENGE`/`CHALLENGE_COOKIE`) to `anycaptcha/enums.py`
- [x] 1.2 Create `anycaptcha/captcha/cloudflare_turnstile.py` with `CloudflareTurnstile` (site_key, page_url, challenge_type, action, data, page_data, html_page_base64) and `CloudflareTurnstileSolution` (token, cf_clearance, user_agent) per design D1/D2
- [x] 1.3 Export both classes from `anycaptcha/captcha/__init__.py` and add `CloudflareTurnstile`, `CloudflareTurnstileSolution`, `CloudflareChallengeType` to `anycaptcha/__init__.py`
- [x] 1.4 Add `Solver.solve_cloudflare_turnstile(site_key, page_url, **kwargs)` to `anycaptcha/solver.py` with a docstring documenting all variant kwargs (challenge_type, action, data, page_data, html_page_base64, proxy, user_agent, cookies)

## 2. CapMonster (token + challenge + cf_clearance)

- [x] 2.1 Add `CloudflareTurnstileTaskRequest(CreateTaskRequest)` to `anycaptcha/service/capmonster.py`: `TurnstileTask` payload; `CHALLENGE` → `cloudflareTaskType:"token"` + `pageAction`/`data`/`pageData` + required `userAgent`; `CHALLENGE_COOKIE` → `cloudflareTaskType:"cf_clearance"` + `htmlPageBase64` + required `userAgent` + required proxy via `_apply_proxy_to_task`; raise `BadInputDataError` on missing prerequisites
- [x] 2.2 Add `CloudflareTurnstileSolutionRequest(GetTaskResultRequest)` parsing `token`/`cf_clearance`/`userAgent` into `CloudflareTurnstileSolution`
- [x] 2.3 Update `__all__` and `_post_init` polling settings (treat like RECAPTCHAV2/HCAPTCHA bucket) in capmonster module

## 3. CapSolver (token + cf_clearance)

- [x] 3.1 Add `CloudflareTurnstileTaskRequest(CreateTaskRequest)` to `anycaptcha/service/capsolver.py`: `TURNSTILE` → `AntiTurnstileTaskProxyLess` with optional `metadata.action`/`metadata.cdata`; `CHALLENGE_COOKIE` → `AntiCloudflareTask` with required proxy and optional `userAgent`; `CHALLENGE` → `BadInputDataError`
- [x] 3.2 Add `CloudflareTurnstileSolutionRequest(GetTaskResultRequest)` parsing `token` / `cookies.cf_clearance` / `userAgent`
- [x] 3.3 Update `__all__` and `_post_init` polling settings in capsolver module

## 4. anti-captcha (token only)

- [x] 4.1 Add `CloudflareTurnstileTaskRequest(TaskRequest)` to `anycaptcha/service/anti_captcha.py`: `TurnstileTask`/`TurnstileTaskProxyless` split like `HCaptchaTaskRequest`, optional `action`/`cData`/`chlPageData`; `CHALLENGE_COOKIE` → `BadInputDataError`
- [x] 4.2 Extend the shared `SolutionRequest.parse_response` type dispatch with a `CLOUDFLARE_TURNSTILE` branch building the solution from `token` + `userAgent`; add `CloudflareTurnstileSolutionRequest(SolutionRequest)`
- [x] 4.3 Update `__all__` in anti_captcha module

## 5. 2captcha family (token only)

- [x] 5.1 Add `CloudflareTurnstileTaskRequest(TaskRequest)` to `anycaptcha/service/twocaptcha.py`: `method=turnstile`, `sitekey`, `pageurl`, optional `action`/`data`/`pagedata`; `CHALLENGE_COOKIE` → `BadInputDataError`
- [x] 5.2 Extend the shared `SolutionRequest.parse_response` in twocaptcha.py with a `CLOUDFLARE_TURNSTILE` branch (token from `request`, `user_agent` from top-level `useragent` when present); add `CloudflareTurnstileSolutionRequest(SolutionRequest)`
- [x] 5.3 Re-export the two new classes in `rucaptcha.py`, `captcha_guru.py`, `multibot_captcha.py` and update their `__all__`
- [x] 5.4 Add equivalent local `CloudflareTurnstileTaskRequest`/`CloudflareTurnstileSolutionRequest` classes to `azcaptcha.py` (module keeps its own copy of the hierarchy) and update its `__all__`
- [x] 5.5 Update `_post_init` polling settings for the new type in twocaptcha.py and azcaptcha.py

## 6. DeathByCaptcha (widget token only)

- [x] 6.1 Add `CloudflareTurnstileTaskRequest(TaskRequest)` to `anycaptcha/service/deathbycaptcha.py`: POST `type=12` + `turnstile_params` JSON (`sitekey`, `pageurl`, optional `action`, proxy/proxytype) mirroring the existing `token_params` pattern; `CHALLENGE`/`CHALLENGE_COOKIE` → `BadInputDataError`
- [x] 6.2 Add `CloudflareTurnstileSolutionRequest(SolutionRequest)` (token arrives in `text` via the shared parser) and update `__all__` + `_post_init` settings

## 7. Verification

- [x] 7.1 Smoke-check imports and discovery: `from anycaptcha import CloudflareTurnstile, ...` works; `supported_captchas` includes `CLOUDFLARE_TURNSTILE` for the 9 supported services and excludes it for `cptch_net`/`sctg_captcha`
- [x] 7.2 Unit-test payload building per provider (prepare() output for each variant) and fail-fast `BadInputDataError` cases (cf_clearance on token-only providers, missing proxy/user_agent on capmonster/capsolver cookie variant)
- [x] 7.3 Unit-test solution parsing per provider family (createTask JSON, res.php token+useragent, DBC text) using canned responses
- [x] 7.4 Run the full test suite / linter used by the project (`uv run pytest`, pylint) and fix regressions

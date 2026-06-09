# Design: add-cloudflare-turnstile

## Context

The library has a class-name-driven plugin architecture:

- `CaptchaType` enum value == captcha dataclass name (`CaptchaType(cls.__name__)` in `captcha/base.py`).
- A service supports a captcha type iff its module defines `{CaptchaType.value}TaskRequest` (see `BaseService.supported_captchas`).
- Solving = `{Type}TaskRequest.prepare/parse_response` (create task) + `{Type}SolutionRequest.parse_response` (poll result).
- `proxy`, `user_agent`, `cookies` are passed at solve time through `solve_captcha(...)`, not stored in the captcha dataclass.

There are three API families among providers:

1. **JSON `createTask`** — capmonster, capsolver, anti_captcha.
2. **Legacy `in.php`/`res.php` (2captcha clones)** — twocaptcha, rucaptcha, captcha_guru, multibot_captcha, azcaptcha, cptch_net, sctg_captcha.
3. **DeathByCaptcha** — numeric `type` + `*_params` JSON blob.

Researched Turnstile support (verified against official docs, June 2026):

| Provider | Task/method | Challenge token | cf_clearance cookie |
|---|---|---|---|
| capmonster | `TurnstileTask` + `cloudflareTaskType` | yes (`token`: needs `pageAction`, `data`, `pageData`, `userAgent`) | yes (`cf_clearance`: needs `htmlPageBase64`, `userAgent`, **proxy obligatory**) |
| capsolver | `AntiTurnstileTaskProxyLess` / `AntiCloudflareTask` | no separate token product (metadata `action`/`cdata` only) | yes (`AntiCloudflareTask`: **static proxy obligatory**, optional `userAgent`, `html`) |
| anti_captcha | `TurnstileTask(Proxyless)` | yes (`action`, `cData`, `chlPageData`) | no |
| twocaptcha / rucaptcha | `method=turnstile` | yes (`action`, `data`, `pagedata`; response includes `useragent`) | no |
| captcha_guru | `method=turnstile` (BETA) | minimal documented form | no |
| azcaptcha | `method=turnstile` (2captcha clone, params inferred) | undocumented | no |
| multibot_captcha | `method=turnstile` (rucaptcha clone) | yes (clone behavior) | no |
| deathbycaptcha | `type=12` + `turnstile_params` (`sitekey`, `pageurl`, optional `action`, proxy) | no (`data`/`pagedata` not documented) | no |
| cptch_net, sctg_captcha | **no documented support — skip** | — | — |

## Goals / Non-Goals

**Goals:**

- One captcha dataclass + one solution dataclass covering all three Cloudflare variants (widget token, challenge token, cf_clearance cookie) — единый интерфейс.
- Implement Turnstile for every provider with documented support, following each module's existing code style.
- Fail fast (library-side error, no network call) when a provider does not support the requested variant or required inputs are missing.

**Non-Goals:**

- No support for providers without documented Turnstile API (cptch_net, sctg_captcha).
- No migration of 2captcha-family providers to their new `createTask` JSON API — stay on `in.php` like the rest of the module.
- No browser emulation / cookie management on the library side; we only transport what the service returns.
- No sync API (library is async-only).

## Decisions

### D1. Single captcha type `CloudflareTurnstile` with a variant selector (not three CaptchaTypes)

`CaptchaType.CLOUDFLARE_TURNSTILE = "CloudflareTurnstile"`; dataclass `CloudflareTurnstile` in `anycaptcha/captcha/cloudflare_turnstile.py`.

Variant is an explicit enum field (new, in `enums.py`):

```python
class CloudflareChallengeType(StrEnum):
    TURNSTILE = "turnstile"          # standalone widget -> token
    CHALLENGE = "token"              # Cloudflare Challenge page -> token
    CHALLENGE_COOKIE = "cf_clearance"  # full challenge -> cf_clearance cookie
```

```python
@dataclass
class CloudflareTurnstile(BaseCaptcha):
    site_key: str
    page_url: str
    challenge_type: CloudflareChallengeType = CloudflareChallengeType.TURNSTILE
    action: Optional[str] = None        # pageAction / data-action
    data: Optional[str] = None          # cData / data / cdata
    page_data: Optional[str] = None     # chlPageData / pageData / pagedata
    html_page_base64: Optional[str] = None  # capmonster cf_clearance only
```

Rationale: the `supported_captchas` mechanism is per-CaptchaType; three separate types would force every clone module to define three nearly identical request classes, and the matrix above shows variants differ per provider anyway — variant capability is a provider concern, validated in `prepare()`. CapMonster models it the same way (`cloudflareTaskType` inside one task). Alternative (three captcha classes `CloudflareTurnstile`, `CloudflareChallenge`, `CloudflareChallengeCookie`) rejected: 3× boilerplate in 9 modules and `supported_captchas` would still lie about variant support for most providers.

### D2. Single solution dataclass with optional fields

```python
@dataclass
class CloudflareTurnstileSolution(BaseCaptchaSolution):
    token: Optional[str] = None
    cf_clearance: Optional[str] = None
    user_agent: Optional[str] = None
```

`user_agent` is returned because 2captcha/anti-captcha/capmonster explicitly require submitting the token with the worker's UA. Alternative (separate `...CookieSolution` class) rejected: breaks the `{ClassName}Solution` lookup convention in `base.py`.

### D3. Unsupported variant / missing prerequisites → `errors.BadInputDataError` raised in the provider's `TaskRequest.prepare()`

Before building the payload each provider checks `captcha.challenge_type` against its capabilities and raises `BadInputDataError` with an explicit message ("cf_clearance is not supported by anti-captcha.com", "cf_clearance requires proxy and user_agent"). Raising inside `prepare()` keeps `BaseService.create_task` untouched and happens before any HTTP call. Cross-variant prerequisites that don't depend on the provider (e.g. `CHALLENGE_COOKIE` without proxy) are still validated per provider because proxy/user_agent only reach the request object, not the dataclass.

### D4. Per-provider mapping

- **capmonster** (`CloudflareTurnstileTaskRequest(CreateTaskRequest)`): always `type: "TurnstileTask"`; `TURNSTILE` → no `cloudflareTaskType`; `CHALLENGE` → `cloudflareTaskType: "token"` + `pageAction`/`data`/`pageData` + `userAgent` (required); `CHALLENGE_COOKIE` → `cloudflareTaskType: "cf_clearance"` + `htmlPageBase64` + `userAgent` + proxy via `_apply_proxy_to_task` (required). Solution parser reads `token` / `cf_clearance` + `userAgent`.
- **capsolver**: `TURNSTILE` → `AntiTurnstileTaskProxyLess` (+ `metadata.action`/`metadata.cdata` if set); `CHALLENGE_COOKIE` → `AntiCloudflareTask` (proxy required, optional `userAgent`); `CHALLENGE` → `BadInputDataError` (no token product for challenge pages).
- **anti_captcha**: `TurnstileTask` with proxy / `TurnstileTaskProxyless` without (same pattern as its `HCaptchaTaskRequest`); optional `action`/`cData`/`chlPageData` cover both `TURNSTILE` and `CHALLENGE`; `CHALLENGE_COOKIE` → `BadInputDataError`. Extend the type dispatch in the module's shared `SolutionRequest.parse_response` to build the solution from `token` + `userAgent`.
- **twocaptcha**: `method=turnstile`, `sitekey`, `pageurl`, optional `action`/`data`/`pagedata` (+ `useragent` already handled by shared `TaskRequest`); `CHALLENGE_COOKIE` → `BadInputDataError`. Add a `CLOUDFLARE_TURNSTILE` branch to the shared `SolutionRequest.parse_response` building the solution from `request` (token) + top-level `useragent`.
- **rucaptcha, captcha_guru, multibot_captcha**: re-export the twocaptcha classes (existing pattern), update `__all__`; captcha_guru's `_decorator` GET-wrapping applies automatically.
- **azcaptcha**: module has its own copy of the 2captcha hierarchy → add analogous `CloudflareTurnstileTaskRequest`/`SolutionRequest` classes locally, token-only.
- **deathbycaptcha**: `TaskRequest` subclass posting `type=12`, `turnstile_params=json.dumps({sitekey, pageurl, action?, proxy?, proxytype?})` (mirrors its `token_params` pattern); only `TURNSTILE` supported, other variants → `BadInputDataError`. Solution comes through the existing text-based `SolutionRequest` (token in `text`).

### D5. Solver facade

`Solver.solve_cloudflare_turnstile(site_key, page_url, **kwargs)` mirroring the other `solve_*` methods (kwargs: `challenge_type`, `action`, `data`, `page_data`, `html_page_base64`, plus `proxy`/`user_agent`/`cookies` routed by `_solve_captcha_async`). Exports added to `captcha/__init__.py` and `anycaptcha/__init__.py` (`CloudflareTurnstile`, `CloudflareTurnstileSolution`, `CloudflareChallengeType`).

### D6. Polling settings

Add `CaptchaType.CLOUDFLARE_TURNSTILE` to each touched service's `_post_init` with the same bucket as `HCAPTCHA`/`RECAPTCHAV2` where the service distinguishes (challenge solving routinely takes 15–30 s); otherwise the module defaults already apply because settings are keyed by `supported_captchas`.

## Risks / Trade-offs

- [azcaptcha/multibot Turnstile params are inferred from the 2captcha-clone surface, not first-party docs] → implement the standard clone payload; their existing error mapping (`ERROR_*`) will surface anything unsupported; the variant stays token-only.
- [capmonster `pageAction` values for challenge pages are constrained ("managed"/"non-interactive")] → pass user input through unchanged; document expected values in the solver docstring.
- [Single dataclass means `supported_captchas` can't express per-variant support] → mitigated by D3 fail-fast errors with explicit messages.
- [2captcha shared `SolutionRequest` dispatch grows another branch used by 4 modules] → covered by the clones' re-export pattern already in place for GeeTest; keep the branch minimal (token + useragent).
- [Provider docs drift (e.g. capsolver renaming task types)] → task type strings are module-local constants, one-line fixes.

## Open Questions

- None blocking. If cptch.net/sctg later document `method=turnstile`, support is a re-export away.

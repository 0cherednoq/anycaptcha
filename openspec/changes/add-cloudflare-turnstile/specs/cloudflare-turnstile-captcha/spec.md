# Spec: cloudflare-turnstile-captcha

## ADDED Requirements

### Requirement: Unified Cloudflare Turnstile captcha model
The library SHALL provide a `CloudflareTurnstile` captcha dataclass registered as `CaptchaType.CLOUDFLARE_TURNSTILE` (value `"CloudflareTurnstile"`). The dataclass SHALL accept `site_key` and `page_url` as required fields and a `challenge_type` selector (`CloudflareChallengeType` enum: `TURNSTILE`, `CHALLENGE`, `CHALLENGE_COOKIE`, default `TURNSTILE`), plus optional `action`, `data`, `page_data` and `html_page_base64` fields.

#### Scenario: Standalone widget captcha created with defaults
- **WHEN** `CloudflareTurnstile(site_key="0x4AAA...", page_url="https://example.com")` is instantiated
- **THEN** `challenge_type` equals `CloudflareChallengeType.TURNSTILE` and `captcha.get_type()` returns `CaptchaType.CLOUDFLARE_TURNSTILE`

#### Scenario: Challenge page captcha carries Cloudflare extras
- **WHEN** a `CloudflareTurnstile` is created with `challenge_type=CHALLENGE`, `action`, `data` and `page_data`
- **THEN** the dataclass stores all three extras and exposes them via `get_optional_data()`

### Requirement: Unified Turnstile solution model
The library SHALL provide `CloudflareTurnstileSolution` with optional `token`, `cf_clearance` and `user_agent` fields, resolvable from the captcha class via the standard `get_solution_class()` mechanism.

#### Scenario: Token solution
- **WHEN** a provider returns a Turnstile token and a worker user-agent
- **THEN** the solution object contains `token` and `user_agent`, and `cf_clearance` is `None`

#### Scenario: Cookie solution
- **WHEN** a provider solves the `CHALLENGE_COOKIE` variant
- **THEN** the solution object contains `cf_clearance` and `user_agent`

### Requirement: Solver facade method
`Solver` SHALL expose `solve_cloudflare_turnstile(site_key, page_url, **kwargs)` returning a `SolvedCaptcha`, accepting `challenge_type`, `action`, `data`, `page_data`, `html_page_base64` and the standard `proxy`, `user_agent`, `cookies` kwargs.

#### Scenario: Solving via the facade
- **WHEN** `await solver.solve_cloudflare_turnstile("0x4AAA...", "https://example.com")` is called on a service supporting Turnstile
- **THEN** a task is created for `CaptchaType.CLOUDFLARE_TURNSTILE` and the awaited result is a `SolvedCaptcha` whose solution is a `CloudflareTurnstileSolution`

### Requirement: Provider support discovery
Services with documented Turnstile support (capmonster, capsolver, anti_captcha, twocaptcha, rucaptcha, captcha_guru, azcaptcha, multibot_captcha, deathbycaptcha) SHALL define `CloudflareTurnstileTaskRequest`/`CloudflareTurnstileSolutionRequest` so that `CaptchaType.CLOUDFLARE_TURNSTILE` appears in their `supported_captchas`. Services without documented support (cptch_net, sctg_captcha) SHALL NOT define these classes.

#### Scenario: Supported service advertises the type
- **WHEN** `supported_captchas` is read on a CapMonster service instance
- **THEN** it contains `CaptchaType.CLOUDFLARE_TURNSTILE`

#### Scenario: Unsupported service rejects the type
- **WHEN** `solve_captcha(CloudflareTurnstile(...))` is called on a cptch.net service instance
- **THEN** an `AnyCaptchaException` is raised stating the type is not supported

### Requirement: CapMonster Turnstile task mapping
The capmonster module SHALL submit `type: "TurnstileTask"` with: no `cloudflareTaskType` for `TURNSTILE`; `cloudflareTaskType: "token"` plus `pageAction`, `data`, `pageData` and `userAgent` for `CHALLENGE`; `cloudflareTaskType: "cf_clearance"` plus `htmlPageBase64`, `userAgent` and mandatory proxy fields for `CHALLENGE_COOKIE`. The solution parser SHALL map `token`/`cf_clearance`/`userAgent` response fields.

#### Scenario: cf_clearance task requires proxy and user-agent
- **WHEN** a `CHALLENGE_COOKIE` task is created on CapMonster with a proxy and user_agent supplied
- **THEN** the payload contains `cloudflareTaskType: "cf_clearance"`, `htmlPageBase64`, `userAgent` and `proxyType/proxyAddress/proxyPort` fields

#### Scenario: cf_clearance without proxy fails fast
- **WHEN** a `CHALLENGE_COOKIE` task is created on CapMonster without a proxy or without user_agent
- **THEN** `BadInputDataError` is raised before any HTTP request is made

### Requirement: CapSolver Turnstile task mapping
The capsolver module SHALL submit `AntiTurnstileTaskProxyLess` (with optional `metadata.action`/`metadata.cdata`) for `TURNSTILE`, and `AntiCloudflareTask` (mandatory proxy, optional `userAgent`) for `CHALLENGE_COOKIE`. The `CHALLENGE` variant SHALL raise `BadInputDataError`.

#### Scenario: Widget task with metadata
- **WHEN** a `TURNSTILE` task with `action="login"` is created on CapSolver
- **THEN** the payload type is `AntiTurnstileTaskProxyLess` and `metadata.action` equals `"login"`

#### Scenario: Challenge-token variant rejected
- **WHEN** a `CHALLENGE` task is created on CapSolver
- **THEN** `BadInputDataError` is raised explaining the variant is unsupported

### Requirement: anti-captcha Turnstile task mapping
The anti_captcha module SHALL submit `TurnstileTaskProxyless` (no proxy) or `TurnstileTask` (with proxy, IP-resolved address) including `websiteURL`, `websiteKey` and optional `action`, `cData`, `chlPageData`, covering `TURNSTILE` and `CHALLENGE`. `CHALLENGE_COOKIE` SHALL raise `BadInputDataError`. The solution SHALL be built from `token` and `userAgent`.

#### Scenario: Proxyless task
- **WHEN** a `TURNSTILE` task is created on anti-captcha without proxy
- **THEN** the payload type is `TurnstileTaskProxyless`

#### Scenario: Challenge extras forwarded
- **WHEN** a `CHALLENGE` task with `action`, `data`, `page_data` is created on anti-captcha
- **THEN** the payload contains `action`, `cData` and `chlPageData`

### Requirement: 2captcha-family Turnstile task mapping
The twocaptcha module SHALL submit `method=turnstile` with `sitekey`, `pageurl` and optional `action`, `data`, `pagedata` parameters; rucaptcha, captcha_guru and multibot_captcha SHALL reuse these request classes via re-export; azcaptcha SHALL implement the equivalent classes locally. `CHALLENGE_COOKIE` SHALL raise `BadInputDataError` in all of them. The solution SHALL carry the token and the `useragent` field from the poll response when present.

#### Scenario: Legacy in.php payload
- **WHEN** a `TURNSTILE` task is created on 2captcha
- **THEN** the `in.php` form data contains `method=turnstile`, `sitekey` and `pageurl`

#### Scenario: Clone services inherit support
- **WHEN** `supported_captchas` is read on rucaptcha, captcha_guru, azcaptcha and multibot instances
- **THEN** each contains `CaptchaType.CLOUDFLARE_TURNSTILE`

#### Scenario: Worker user-agent propagated
- **WHEN** 2captcha responds with `{"status":1, "request":"<token>", "useragent":"<ua>"}`
- **THEN** the parsed solution has `token="<token>"` and `user_agent="<ua>"`

### Requirement: DeathByCaptcha Turnstile task mapping
The deathbycaptcha module SHALL submit captcha `type=12` with a JSON `turnstile_params` payload containing `sitekey`, `pageurl`, optional `action` and proxy fields. Only `TURNSTILE` SHALL be supported; `CHALLENGE` and `CHALLENGE_COOKIE` SHALL raise `BadInputDataError`.

#### Scenario: Turnstile params payload
- **WHEN** a `TURNSTILE` task with a proxy is created on DeathByCaptcha
- **THEN** the POST contains `type=12` and `turnstile_params` with `sitekey`, `pageurl`, `proxy` and `proxytype`

### Requirement: Fail-fast variant validation
Every provider request class SHALL validate the requested `challenge_type` and its prerequisites inside `prepare()` and raise `errors.BadInputDataError` with a message naming the provider and the unsupported/missing piece, before any HTTP request is sent.

#### Scenario: Unsupported variant produces a library error
- **WHEN** a `CHALLENGE_COOKIE` task is created on any token-only provider (anti-captcha, 2captcha family, DeathByCaptcha)
- **THEN** `BadInputDataError` is raised locally and no network call is made

### Requirement: Public exports
`CloudflareTurnstile`, `CloudflareTurnstileSolution` and `CloudflareChallengeType` SHALL be importable from the top-level `anycaptcha` package and from `anycaptcha.captcha`.

#### Scenario: Top-level import
- **WHEN** `from anycaptcha import CloudflareTurnstile, CloudflareTurnstileSolution, CloudflareChallengeType` is executed
- **THEN** the import succeeds

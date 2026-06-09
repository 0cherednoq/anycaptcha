"""
Demo: solve the Cloudflare "Just a moment" (cf_clearance) challenge on namecheap.com
via CapMonster using the anycaptcha library, then prove the cookie works.

Usage:
    set CAPMONSTER_KEY=your_capmonster_api_key
    set PROXY=http://login:password@host:port
    uv run python examples/solve_namecheap_cf_clearance.py

cf_clearance REQUIRES a proxy: CapMonster solves the challenge through it and
binds the cookie to that proxy's IP, so the same proxy + User-Agent must be
used afterwards for the cookie to be accepted.
"""
import asyncio
import base64
import os
import re

import httpx
from better_proxy import Proxy

from anycaptcha import Solver, Service, CloudflareChallengeType
from anycaptcha.errors import UnableToSolveError, ServiceError

RETRIES = int(os.environ.get("RETRIES", "1"))

PAGE_URL = os.environ.get("TARGET_URL", "https://www.namecheap.com/")
# A real, current Chrome User-Agent. Must stay identical across fetch -> solve -> verify.
USER_AGENT = os.environ.get(
    "UA",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
IMPERSONATE = os.environ.get("IMPERSONATE", "chrome124")

API_KEY = os.environ["CAPMONSTER_KEY"]  # set CAPMONSTER_KEY in the environment
PROXY_STR = os.environ.get("PROXY")


def _extract_site_key(html: str) -> str:
    """Best-effort extraction of the Turnstile sitekey from the challenge page."""
    m = re.search(r'data-sitekey="([^"]+)"', html) or re.search(r'sitekey["\']?\s*[:=]\s*["\']([^"\']+)', html)
    return m.group(1) if m else "0x4AAAAAAA"  # placeholder; CapMonster ignores it for cf_clearance


async def main():
    if not PROXY_STR:
        raise SystemExit(
            "PROXY env var is required for the cf_clearance variant.\n"
            "Example: set PROXY=http://login:password@host:port"
        )

    proxy = Proxy.from_str(PROXY_STR)
    httpx_proxy = proxy.as_url

    # 1. Fetch the challenge page THROUGH the proxy with our fixed UA.
    async with httpx.AsyncClient(proxy=httpx_proxy, headers={"User-Agent": USER_AGENT},
                                 timeout=30, follow_redirects=True) as client:
        resp = await client.get(PAGE_URL)
        html = resp.text
        print(f"[1] Initial fetch: HTTP {resp.status_code}, cf-mitigated={resp.headers.get('cf-mitigated')!r}")

        if resp.status_code != 403 and "challenge" not in (resp.headers.get("cf-mitigated") or ""):
            print("    No Cloudflare challenge served right now — nothing to solve.")
            return

    html_b64 = base64.b64encode(html.encode("utf-8")).decode("ascii")
    site_key = _extract_site_key(html)
    print(f"[2] Challenge page captured ({len(html)} bytes), site_key={site_key!r}")

    # 2. Solve cf_clearance via CapMonster (retry: managed-challenge solving is probabilistic).
    solver = Solver(Service.CAPMONSTER, API_KEY)
    solved = None
    try:
        for attempt in range(1, RETRIES + 1):
            print(f"[3] Submitting cf_clearance task to CapMonster (attempt {attempt}/{RETRIES})...")
            try:
                solved = await solver.solve_cloudflare_turnstile(
                    site_key=site_key,
                    page_url=PAGE_URL,
                    challenge_type=CloudflareChallengeType.CHALLENGE_COOKIE,
                    html_page_base64=html_b64,
                    proxy=PROXY_STR,
                    user_agent=USER_AGENT,
                )
                break
            except (UnableToSolveError, ServiceError) as exc:
                print(f"    attempt {attempt} failed: {type(exc).__name__}: {exc}")
                if attempt == RETRIES:
                    print("[x] Give up: CapMonster could not bypass the challenge with this proxy.")
                    return
    finally:
        await solver.close()

    cf_clearance = solved.solution.cf_clearance
    returned_ua = solved.solution.user_agent or USER_AGENT
    print(f"[4] Solved in {solved.solving_duration.total_seconds():.1f}s")
    print(f"    cf_clearance = {cf_clearance[:40]}... ({len(cf_clearance)} chars)")
    print(f"    userAgent    = {returned_ua}")

    # 3. Prove the cookie works. cf_clearance is bound to IP + UA + the browser's TLS/JA3
    #    fingerprint, so the verify must impersonate Chrome (curl_cffi) over the SAME sticky proxy.
    print("[5] Verifying cf_clearance with Chrome TLS impersonation (curl_cffi)...")
    from curl_cffi import requests as cffi_requests  # noqa: PLC0415

    verify = cffi_requests.get(
        PAGE_URL,
        headers={"User-Agent": returned_ua},
        cookies={"cf_clearance": cf_clearance},
        proxies={"http": httpx_proxy, "https": httpx_proxy},
        impersonate=IMPERSONATE,
        timeout=30,
    )
    ok = verify.status_code == 200 and "challenge" not in (verify.headers.get("cf-mitigated") or "")
    print(f"    Verify with cf_clearance: HTTP {verify.status_code} -> "
          f"{'SUCCESS [OK]' if ok else 'still challenged [FAIL]'}")


if __name__ == "__main__":
    asyncio.run(main())

"""
Demo: solve a STANDALONE Cloudflare Turnstile widget (token variant) via CapMonster
using the anycaptcha library. No proxy required.

    set CAPMONSTER_KEY=your_capmonster_api_key
    uv run python examples/solve_standalone_turnstile.py
"""
import asyncio
import os

from anycaptcha import Solver, Service, CloudflareChallengeType

PAGE_URL = "https://peet.ws/turnstile-test/non-interactive.html"
SITE_KEY = "0x4AAAAAAABS7vwvV6VFfMcD"
API_KEY = os.environ["CAPMONSTER_KEY"]  # set CAPMONSTER_KEY in the environment


async def main():
    solver = Solver(Service.CAPMONSTER, API_KEY)
    try:
        print(f"[1] Submitting standalone Turnstile task (sitekey={SITE_KEY})...")
        solved = await solver.solve_cloudflare_turnstile(
            site_key=SITE_KEY,
            page_url=PAGE_URL,
            challenge_type=CloudflareChallengeType.TURNSTILE,
        )
    finally:
        await solver.close()

    sol = solved.solution
    print(f"[2] Solved in {solved.solving_duration.total_seconds():.1f}s")
    print(f"    token      = {sol.token}")
    print(f"    user_agent = {sol.user_agent}")
    print(f"    token_len  = {len(sol.token) if sol.token else 0}")
    print(f"[3] Result: {'REAL TOKEN RECEIVED [OK]' if sol.token else 'NO TOKEN [FAIL]'}")


if __name__ == "__main__":
    asyncio.run(main())

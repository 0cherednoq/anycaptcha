from dataclasses import dataclass
from typing import Optional

from .base import BaseCaptcha, BaseCaptchaSolution
from ..enums import CloudflareChallengeType


@dataclass
class CloudflareTurnstile(BaseCaptcha):
    """ Cloudflare Turnstile (widget / Challenge page / cf_clearance cookie) """

    site_key: str
    page_url: str
    challenge_type: CloudflareChallengeType = CloudflareChallengeType.TURNSTILE
    action: Optional[str] = None  # pageAction / data-action
    data: Optional[str] = None  # cData
    page_data: Optional[str] = None  # chlPageData / pageData
    html_page_base64: Optional[str] = None  # base64 of the challenge page (cf_clearance only)

    def __post_init__(self):
        self.challenge_type = CloudflareChallengeType(self.challenge_type)


@dataclass
class CloudflareTurnstileSolution(BaseCaptchaSolution):
    """ Cloudflare Turnstile solution """

    token: Optional[str] = None
    cf_clearance: Optional[str] = None
    user_agent: Optional[str] = None

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .base import BaseCaptcha, BaseCaptchaSolution


@dataclass
class GeeTestV4(BaseCaptcha):
    """ GeeTest v4 """

    page_url: str
    captcha_id: str
    risk_type: Optional[str] = None
    geetest_api_server_subdomain: Optional[str] = None
    geetest_get_lib: Optional[str] = None
    init_parameters: Optional[Dict[str, Any]] = None


@dataclass
class GeeTestV4Solution(BaseCaptchaSolution):
    """ GeeTest v4 solution """

    captcha_id: str
    lot_number: str
    pass_token: str
    gen_time: str
    captcha_output: str

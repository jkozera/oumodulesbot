import httpx
import json
import logging
import re

from .ou_utils import MODULE_CODE_RE_TEMPLATE, get_module_url

logger = logging.getLogger(__name__)


class OUModulesBackend:

    MODULE_TITLE_RE = re.compile(
        r"<title>" + MODULE_CODE_RE_TEMPLATE + r" (.*)"
        r" - Open University Digital Archive</title>"
    )

    def __init__(self):
        with open("cache.json", "r") as f:
            self.cache = json.load(f)

    async def get_module_title(self, code):
        code = code.upper()

        # 1. Try cached title:
        if code in self.cache:
            return self.cache[code][0].replace("!", "")

        # 2. Try OUDA:
        logger.info("{} not in cache".format(code))
        try:
            url_template = (
                "http://www.open.ac.uk/library/digital-archive/module/xcri:{}"
            )
            async with httpx.AsyncClient() as client:
                response = await client.get(url_template.format(code))
            html = response.content.decode("utf-8")
        except Exception:
            return
        title = self.MODULE_TITLE_RE.findall(html)
        return title[0].replace("!", "") if title else None

    async def _is_module_url(self, url, code):
        async with httpx.AsyncClient() as client:
            response = await client.head(url, allow_redirects=True)
            correct_redirect = code.lower() in str(response.url).lower()
            return correct_redirect and response.status_code == 200

    async def get_module_url(self, code):
        code = code.upper()

        # 1. Try cached URL
        _, url = self.cache.get(code, (None, None))
        if url:
            return url

        # 2. Try constructing it from code
        try_url = get_module_url(code)
        if await self._is_module_url(try_url, code):
            return try_url

        return None

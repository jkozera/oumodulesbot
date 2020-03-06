import json
import logging
import re
from typing import Mapping, Optional, Tuple

import httpx

from .ou_utils import MODULE_CODE_RE_TEMPLATE, get_module_url

logger = logging.getLogger(__name__)

CacheItem = Tuple[str, Optional[str]]  # title, url


class OUModulesBackend:

    MODULE_TITLE_RE = re.compile(
        r"<title>" + MODULE_CODE_RE_TEMPLATE + r" (.*)"
        r" - Open University Digital Archive</title>"
    )

    def __init__(self):
        with open("cache.json", "r") as f:
            cache_json = json.load(f)
        self.cache: Mapping[str, CacheItem] = {
            k: tuple(v) for k, v in cache_json.items()
        }

    async def get_module_title(self, code: str) -> Optional[str]:
        """
        Returns a module title for given code, if available.

        Tries a lookup in cache, and if it fails then it attempts to query
        the Open University Digital Archive.
        """
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
            return None
        title = self.MODULE_TITLE_RE.findall(html)
        return title[0].replace("!", "") if title else None

    async def _is_module_url(self, url: str, code: str) -> bool:
        """
        Check if given URL looks like a valid URL for a given module code,
        i.e. resolves to 200, and doesn't redirect away to a different page.

        OU redirects to places like /courses/ sometimes which is a masked way
        of saying '404'. However 301 redirects don't always indicate that
        modules aren't available, because they sometimes point to a different
        page for the same module.

        Thus a compromise is used here by allowing redirects, but only if the
        destination page URL includes the module code.
        """
        async with httpx.AsyncClient() as client:
            response = await client.head(url, allow_redirects=True)
            correct_redirect = code.lower() in str(response.url).lower()
            return correct_redirect and response.status_code == 200

    async def get_module_url(self, code: str) -> Optional[str]:
        """
        Return module's URL for given module code, if available.

        Tries to lookup in cache, and if it fails then it tries to provide
        the URL with a well-known template (see get_module_url from ou_utils).

        The template-based URL is returned only if it passes a HTTP check.
        """
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

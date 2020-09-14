import json
import logging
import re
from collections import namedtuple
from typing import Dict, Optional, Tuple

import httpx

from .ou_utils import (
    MODULE_CODE_RE_TEMPLATE,
    MODULE_OR_QUALIFICATION_CODE_RE_TEMPLATE,
    get_possible_urls_from_code,
)

MODULE_TITLE_OUDA_RE = re.compile(
    r"<title>" + MODULE_CODE_RE_TEMPLATE + r" (.*?)"
    r" - Open University Digital Archive</title>"
)
OUDA_URL_TEMPLATE = (
    "http://www.open.ac.uk/library/digital-archive/module/xcri:{}"
)


TITLE_SEPARATORS = [r"\|", "-"]
HTML_TITLE_TEXT_RE_TEMPLATES = [
    fr"{MODULE_OR_QUALIFICATION_CODE_RE_TEMPLATE}"
    # the trailing '.*' allows ' Course' after 'Open University':
    fr"\s*{sep}\s*(.+?)\s*{sep}\s*Open University.*"
    for sep in TITLE_SEPARATORS
]
HTML_TITLE_TAG_RES = [
    re.compile(fr"<title>\s*{template}\s*</title>")
    for template in HTML_TITLE_TEXT_RE_TEMPLATES
]

logger = logging.getLogger(__name__)

CacheItem = Tuple[str, Optional[str]]  # title, url
Result = namedtuple("Result", "code,title,url")


def find_title_in_html(html: str) -> Optional[str]:
    for tag_re in HTML_TITLE_TAG_RES:
        found = tag_re.search(html)
        if found:
            return found.groups()[0]
    return None


class OUModulesBackend:
    def __init__(self):
        with open("cache.json", "r") as f:
            cache_json = json.load(f)
        self.cache: Dict[str, CacheItem] = {
            k: tuple(v) for k, v in cache_json.items()
        }

    async def _try_cache(self, code) -> Optional[Result]:
        if code not in self.cache:
            logger.info(f"{code} not in cache")
            return None
        cached_result = self.cache[code]
        title = cached_result[0]
        url = cached_result[1] or await self._get_url_if_active(code)
        return Result(code, title, url)

    async def _try_url(self, code) -> Optional[Result]:
        if active_url := await self._get_url_if_active(code):
            async with httpx.AsyncClient() as client:
                result = await client.get(active_url, allow_redirects=True)
            if found_title := find_title_in_html(result.text):
                logger.info(f"{code} found via {active_url}")
                self.cache[code] = (found_title, active_url)
                return Result(code, found_title, active_url)
        logger.info(f"{code} can't be found via module URL")
        return None

    async def _try_ouda(self, code) -> Optional[Result]:
        ouda_url = OUDA_URL_TEMPLATE.format(code)
        try:
            logger.info(f"Trying {ouda_url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(ouda_url)
            html = response.content.decode("utf-8")
        except Exception:
            logger.exception(f"Failed fetching {ouda_url}")
            return None

        if titles := MODULE_TITLE_OUDA_RE.findall(html):
            logger.info(f"{code} found via OUDA")
            self.cache[code] = (titles[0], None)
            return Result(code, titles[0], None)
        logger.info(f"{code} can't be found via {ouda_url}")
        return None

    async def find_result_for_code(self, code: str) -> Optional[Result]:
        """
        Returns a module title for given code, if available.

        Tries a lookup in cache, and if it fails then it attempts to query
        the Open University Digital Archive.
        """
        code = code.upper()

        # 1. Try cached title:
        if cached_result := await self._try_cache(code):
            return cached_result

        # 2. Try scraping URL with HTML description
        #    (some results used to be missing from SPARQL results):
        if result := await self._try_url(code):
            return result

        # 3. Try OUDA for old modules:
        if result := await self._try_ouda(code):
            return result

        return None

    async def _is_active_url(self, url: str, code: str) -> bool:
        """
        Check if given URL looks like a valid URL for a given code, i.e.
        resolves to 200, and doesn't redirect away to a different page.

        OU redirects to places like /courses/ sometimes which is a masked way
        of saying '404'. However 301 redirects don't always indicate that
        modules aren't available, because they sometimes point to a different
        page for the same module/qualification.

        Thus a compromise is used here by allowing redirects, but only if the
        destination page URL includes the module code.
        """
        async with httpx.AsyncClient() as client:
            response = await client.head(url, allow_redirects=True)
            correct_redirect = code.lower() in str(response.url).lower()
            return correct_redirect and response.status_code == 200

    async def _get_url_if_active(self, code: str) -> Optional[str]:
        """
        Return module's URL for given module code, if available.

        Tries to lookup in cache, and if it fails then it tries to provide
        the URL with a well-known template (see get_module_url from ou_utils).

        The template-based URL is returned only if it passes a HTTP check.
        """
        # 1. Try cached URL
        _, url = self.cache.get(code.upper(), (None, None))
        if url:
            return url

        # 2. Try constructing it from code
        for try_url in get_possible_urls_from_code(code):
            if await self._is_active_url(try_url, code):
                return try_url

        return None

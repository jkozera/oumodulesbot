import json
import logging
import re
from typing import Dict, Optional, Tuple

import httpx

from .ou_sparql_utils import find_module_or_qualification
from .ou_utils import (
    MODULE_CODE_RE_TEMPLATE,
    MODULE_OR_QUALIFICATION_CODE_RE_TEMPLATE,
    Result,
    get_possible_urls_from_code,
)

MODULE_TITLE_OUDA_RE = re.compile(
    r"<title>" + MODULE_CODE_RE_TEMPLATE + r" (.*?)"
    r" - Open University Digital Archive</title>"
)
OUDA_URL_TEMPLATE = (
    "http://www.open.ac.uk/library/digital-archive/module/xcri:{}"
)


TITLE_SEPARATOR = r"[^\s]"
HTML_TITLE_TEXT_RE_TEMPLATE = (
    fr"{MODULE_OR_QUALIFICATION_CODE_RE_TEMPLATE}"
    # the trailing '.*' allows ' Course' after 'Open University':
    fr"\s*{TITLE_SEPARATOR}\s*(.+?)\s*{TITLE_SEPARATOR}\s*Open University.*"
)
HTML_TITLE_TAG_RE = re.compile(
    fr"<title>\s*{HTML_TITLE_TEXT_RE_TEMPLATE}\s*</title>",
)


logger = logging.getLogger(__name__)

CacheItem = Tuple[str, Optional[str]]  # title, url


def find_title_in_html(html: str) -> Optional[str]:
    if found := HTML_TITLE_TAG_RE.search(html):
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
        url = cached_result[1]
        # try to make sure URL really isn't reachable, by autogenerating one:
        if (not url) and (active_url := await self._get_url_if_active(code)):
            url = active_url
            logger.info(f"{code} has no url in cache, but {url} is reachable")
            self.cache[code] = (title, url)
        return Result(code, title, url)

    async def _try_url(self, code) -> Optional[Result]:
        if active_url := await self._get_url_if_active(code):
            async with httpx.AsyncClient() as client:
                result = await client.get(active_url, allow_redirects=True)
            if found_title := find_title_in_html(result.text):
                logger.info(f"{code} found via {active_url}")
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
        # 2. Try SPARQL queries:
        elif sparql_result := await find_module_or_qualification(code):
            result = sparql_result
        # 3. Try scraping URL with HTML description
        #    (some results used to be missing from SPARQL results):
        elif url_scraping_result := await self._try_url(code):
            result = url_scraping_result
        # 4. Try OUDA for old modules:
        elif ouda_result := await self._try_ouda(code):
            result = ouda_result
        else:
            return None

        self.cache[code] = (result.title, result.url)
        return result

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
            try:
                response = await client.head(
                    url,
                    allow_redirects=True,
                    timeout=3,
                )
            except httpx.ReadTimeout:
                return False
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

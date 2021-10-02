import logging
import time
import urllib.parse
from typing import Optional

import httpx

from .ou_utils import Result

XCRI_QUERY = """
PREFIX xcri: <http://xcri.org/profiles/catalog/1.2/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX mlo: <http://purl.org/net/mlo/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?id ?title ?url ?type
FROM <http://data.open.ac.uk/context/xcri> WHERE {{
  ?course a xcri:course .
  ?course xcri:internalID ?id .
  ?course dc:title ?title .
  ?course mlo:url ?url .
  ?course rdf:type ?type
  FILTER ( STRSTARTS ( STR ( ?type ), "http://data.open.ac.uk/ontology/" ) )
  {addfilter}
}}
"""

OLDCOURSE_QUERY = """
PREFIX aiiso: <http://purl.org/vocab/aiiso/schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?id ?title
FROM <http://data.open.ac.uk/context/oldcourses> WHERE {{
  ?course a aiiso:Module .
  ?course aiiso:code ?id .
  ?course dcterms:title ?title
  {addfilter}
}}
"""

QUERY_FORMAT_DEFAULTS = {"addfilter": ""}

logger = logging.getLogger(__name__)


async def query_data_ac_uk(query, offset, limit):
    q = {"query": "{} offset {} limit {}".format(query, offset, limit)}
    async with httpx.AsyncClient() as client:
        http_result = await client.get(
            f"http://data.open.ac.uk/sparql?{urllib.parse.urlencode(q)}",
            headers={"Accept": "application/sparql-results+json"},
        )
    retval = []
    for result in http_result.json()["results"]["bindings"]:
        item = {}
        for k in result:
            item[k] = result[k]["value"]
        retval.append(item)
    return retval


async def query_xcri(limit=3000, **format_kwargs):
    format_ = dict(QUERY_FORMAT_DEFAULTS, **format_kwargs)
    return await query_data_ac_uk(XCRI_QUERY.format(**format_), 0, limit)


async def query_oldcourses(limit=3000, **format_kwargs):
    format_ = dict(QUERY_FORMAT_DEFAULTS, **format_kwargs)
    return await query_data_ac_uk(OLDCOURSE_QUERY.format(**format_), 0, limit)


async def find_module_or_qualification(code) -> Optional[Result]:
    code = code.upper()
    filter_ = f'FILTER(?id = "{code}")'

    logger.info(f"Querying {code} from xcri")
    if results_xcri := await query_xcri(addfilter=filter_, limit=1):
        result = results_xcri[0]
        logger.info(f"xcri result: {result}")
        return Result(code, result["title"], result.get("url"))

    logger.info(f"Querying {code} from oldcourses")
    if results_old := await query_oldcourses(addfilter=filter_, limit=1):
        result = results_old[0]
        logger.info(f"oldcourses result: {result}")
        return Result(code, result["title"], result.get("url"))

    logger.info(f"Querying {code} from SPARQL returned no results")
    return None


def is_really_active(url, code, retries=2, retry_num=0):
    if not url:
        # no point in checking if API returns it as 'oldcourse'
        return None
    print(f"Trying {url} -> ", end=" ")
    time.sleep(0.1)  # lame rate limiting
    try:
        result = httpx.head(url, allow_redirects=True)
    except Exception as e:
        print("failed (%s)" % e, end=" ")
        retry_num += 1
        if retry_num <= retries:
            print(f"- retrying ({retry_num} / {retries})")
            return is_really_active(url, code, retries, retry_num=retry_num)
        really_active = False
    else:
        correct_redirect = code.lower() in str(result.url).lower()
        really_active = correct_redirect and result.status_code == 200
        print(f"{really_active} ({result.url}, {result.status_code})")
    return really_active

import time
import urllib.parse

import httpx

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


async def query_data_ac_uk(query, offset, limit):
    q = {"query": "{} offset {} limit {}".format(query, offset, limit)}
    async with httpx.AsyncClient() as client:
        http_result = client.get(
            f"http://data.open.ac.uk/sparql?{urllib.parse.urlencode(q)}",
            headers={"Accept": "application/sparql-results+json"},
        )
    retval = []
    for result in (await http_result).json()["results"]["bindings"]:
        item = {}
        for k in result:
            item[k] = result[k]["value"]
        retval.append(item)
    return retval


def query_xcri(limit=3000, **format_kwargs):
    format_kwargs = dict(QUERY_FORMAT_DEFAULTS, **format_kwargs)
    return query_data_ac_uk(XCRI_QUERY.format(**format_kwargs), 0, limit)


def query_oldcourses(limit=3000, **format_kwargs):
    format_kwargs = dict(QUERY_FORMAT_DEFAULTS, **format_kwargs)
    return query_data_ac_uk(OLDCOURSE_QUERY.format(**format_kwargs), 0, limit)


def find_module_or_qualification(code):
    addfilter = f'FILTER(?id = "{code}")'
    results_xcri = query_xcri(addfilter=addfilter, limit=1)
    if results_xcri:
        return results_xcri[0]
    results_oldcourses = query_oldcourses(addfilter=addfilter, limit=1)
    if results_oldcourses:
        return results_oldcourses[0]


def is_really_active(url, code):
    if not url:
        # no point in checking if API returns it as 'oldcourse'
        return None
    print("Trying", url, "->", end=" ")
    try:
        result = httpx.head(url, allow_redirects=True)
    except Exception as e:
        print("(%s)" % e, end=" ")
        really_active = False
    correct_redirect = code.lower() in str(result.url).lower()
    really_active = correct_redirect and result.status_code == 200
    print(f"{really_active} ({result.url}, {result.status_code})")
    time.sleep(0.1)
    return really_active

import json
import re
import sys
import time
import urllib.parse

import httpx


PAGES = 165

NEWCOURSE_QUERY = """
PREFIX xcri: <http://xcri.org/profiles/catalog/1.2/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>
PREFIX mlo: <http://purl.org/net/mlo/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?id ?title ?url ?type
FROM <http://data.open.ac.uk/context/xcri> WHERE {
  ?course a xcri:course .
  ?course xcri:internalID ?id .
  ?course dc:title ?title .
  ?course mlo:url ?url .
  ?course rdf:type ?type
  FILTER ( STRSTARTS ( STR ( ?type ), "http://data.open.ac.uk/ontology/" ) )
}
"""

OLDCOURSE_QUERY = """
PREFIX aiiso: <http://purl.org/vocab/aiiso/schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?id ?title
FROM <http://data.open.ac.uk/context/oldcourses> WHERE {
  ?course a aiiso:Module .
  ?course aiiso:code ?id .
  ?course dcterms:title ?title
}
"""


def query_data_ac_uk(query, offset, limit):
    q = {"query": "{} offset {} limit {}".format(query, offset, limit)}
    results = httpx.get(
        "http://data.open.ac.uk/sparql?{}".format(urllib.parse.urlencode(q)),
        headers={"Accept": "application/sparql-results+json"},
    ).json()["results"]["bindings"]
    retval = []
    for result in results:
        item = {}
        for k in result:
            item[k] = result[k]["value"]
        retval.append(item)
    return retval


def dump_readable_json(dictionary):
    res = ["{"]
    comma = ""  # print comma after first module
    for k, v in sorted(dictionary.items()):
        res.append(
            "%s %s" % (comma or " ", json.dumps({k: [v[0], v[1]]})[1:-1])
        )
        comma = ","
    res.append("}")
    return "\n".join(res + [""])


def is_really_active(url, code):
    if not url:
        # no point in checking if API returns it as 'oldcourse'
        return False
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


def main():
    newcourses = query_data_ac_uk(NEWCOURSE_QUERY, 0, 3000)
    oldcourses = query_data_ac_uk(OLDCOURSE_QUERY, 0, 3000)
    oldcache = json.load(open("cache.json"))

    seen_codes = set()

    for c in oldcourses + newcourses:
        code, title, url = c["id"], c["title"], c.get("url")
        seen_codes.add(code)
        if len(code) > 6:
            if url:
                print((code, title, "active and longer than 6 chars!"))
            # These require the bot to be fixed, to handle names
            # different from [a-zA-Z]{1,3}[0-9]{1,3}
            # (u'SXHL288', u'Practical science: biology and health',
            #  'active and longer than 6 chars!')
            # (u'SXPA288', u'Practical science: physics and astronomy',
            #  'active and longer than 6 chars!')
            # (u'BXFT716',
            #  u'MBA stage 1: management: perspectives and practice
            #    (fast track)',
            #  'active and longer than 6 chars!')
            continue
        if oldcache.get(code, ["", url])[1] != url:
            print(
                '"url" value different:', code, oldcache[code][1], url,
            )
            if not url:
                # Assume that API correctly returns inactive courses.
                print(
                    '"url" value mismatch:',
                    code,
                    oldcache[code][1],
                    url,
                    " - updating.",
                )
                oldcache[code][1] = None
            elif is_really_active(url, code):
                # However, some of the newcourses are in fact not active, so
                # we need the is_really_active check here.
                print(
                    '"url" value mismatch:',
                    code,
                    oldcache[code][1],
                    url,
                    " - updating.",
                )
                oldcache[code] = [title, url]
        elif oldcache.get(code, [title])[0] != title:
            print(
                '"title" value mismatch: ',
                oldcache[code][0],
                "!=",
                title,
                " - updating.",
            )
            oldcache[code] = (
                title,
                is_really_active(url, code) and url,
            )
        elif oldcache.get(code) != [title, url]:
            print(
                code, oldcache.get(code), [title, url], "mismatch - updating",
            )
            oldcache[code] = (title, is_really_active(url, code) and url)

    for code in oldcache:
        _, url = oldcache[code]
        if code in seen_codes or not url:
            continue
        # process unseen which have url set, which may be still valid
        print(code, "missing - trying old url", url)
        if not is_really_active(url, code):
            print(code, "generated url failed - setting null")
            oldcache[code][1] = None

    with open("newcache.json", "w") as f:
        f.write(dump_readable_json(oldcache))
    return

    # old scraping below, disabled for now:
    print("[")
    regex = re.compile(
        r'<a href="/library/digital-archive/xcri:([a-zA-Z]{1,3}[0-9]{1,3})">'
        "(?!\1)(.+?)</a>"
    )
    comma = ""  # print comma after first module
    for i in range(1, PAGES + 1):
        print("Processing page {}/{}...".format(i, PAGES), file=sys.stderr)
        url_template = (
            "http://www.open.ac.uk/library/digital-archive/module/list/page{}"
        )
        html = httpx.get(url_template.format(i)).content
        for (code, module) in regex.findall(html):
            try_url = "http://www.open.ac.uk/courses/modules/{}".format(
                code.lower()
            )
            found = httpx.head(try_url).status_code == 200
            print(
                '%s {"%s": ["%s", %s]}'
                % (comma or " ", code, module, "true" if found else "false",)
            )
            comma = ","
            time.sleep(0.1)
    print("]")


if __name__ == "__main__":
    main()

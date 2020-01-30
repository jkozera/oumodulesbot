import json
import re
import sys
import time
import urllib

import requests

from ou_utils import get_module_url

PAGES = 165

NEWCOURSE_QUERY = '''
PREFIX xcri: <http://xcri.org/profiles/catalog/1.2/>
PREFIX dc: <http://purl.org/dc/elements/1.1/>

SELECT ?course ?title
FROM <http://data.open.ac.uk/context/xcri> WHERE {
  ?course a xcri:course .
  ?course dc:title ?title
}
'''

OLDCOURSE_QUERY = '''
PREFIX aiiso: <http://purl.org/vocab/aiiso/schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?course ?title
FROM <http://data.open.ac.uk/context/oldcourses> WHERE {
  ?course a aiiso:Module .
  ?course dcterms:title ?title
}
'''

def query_data_ac_uk(query, offset, limit):
    q = {
        'query': '{} offset {} limit {}'.format(query, offset, limit)
    }
    results = requests.get(
        'http://data.open.ac.uk/sparql?{}'.format(urllib.urlencode(q)),
        headers={'Accept': 'application/sparql-results+json'}
    ).json()['results']['bindings']
    retval = []
    for result in results:
        item = {}
        for k in result:
            item[k] = result[k]['value']
        retval.append(item)
    return retval

def dump_readable_json(dictionary):
    res = ['[']
    comma = ''  # print comma after first module
    for k, v in sorted(dictionary.items()):
        res.append('%s %s' % (
            comma or ' ',  json.dumps({k: [v[0], v[1]]})
        ))
        comma = ','
    res.append(']')
    return '\n'.join(res + [''])

def main():
    newcourses = query_data_ac_uk(NEWCOURSE_QUERY, 0, 3000)
    oldcourses = query_data_ac_uk(OLDCOURSE_QUERY, 0, 3000)

    oldcache = json.load(open('cache.json'))

    oldcache_dict = {
        k.encode(): (v.encode(), available)
        for d in oldcache
        for k, (v, available) in d.items()
    }

    def is_really_active(active, code):
        if active:
            # no point in checking if API returns it as 'oldcourse'
            try_url = get_module_url(code)
            print 'Trying', try_url, '->',
            try:
                really_active = requests.head(try_url).status_code == 200
            except Exception as e:
                print '(%s)' % e,
                really_active = False
            print really_active
            time.sleep(0.1)
            return really_active
        return active

    for courses, active in [(oldcourses, False), (newcourses, True)]:
        for c in courses:
            if 'course' in c['course']:
                code, title = c['course'].split('/course/')[1].upper(), c['title']
                if len(code) > 6:
                    if active:
                        print(code, title, 'active and longer than 6 chars!')
                        # These require the bot to be fixed, to handle names different from [a-zA-Z]{1,3}[0-9]{1,3}
                        # (u'SXHL288', u'Practical science: biology and health', 'active and longer than 6 chars!')
                        # (u'SXPA288', u'Practical science: physics and astronomy', 'active and longer than 6 chars!')
                        # (u'BXFT716', u'MBA stage 1: management: perspectives and practice (fast track)', 'active and longer than 6 chars!')
                    continue
                if oldcache_dict.get(code, ['', active])[1] != active:
                    print '"active" value different:', code, oldcache_dict[code][1], active
                    if not active:
                        # Assume that API correctly returns inactive courses.
                        print '"active" value mismatch:', code, oldcache_dict[code][1], active, ' - updating.'
                    elif is_really_active(active, code):
                        # However, some of the newcourses are in fact not active.
                        print '"active" value mismatch:', code, oldcache_dict[code][1], active, ' - updating.'
                        oldcache_dict[code] = (title, active)
                elif oldcache_dict.get(code, [title])[0] != title:
                    print '"title" value mismatch: ', oldcache_dict[code][0], '!=', title, ' - updating.'
                    oldcache_dict[code] = (title, is_really_active(active, code))
                elif oldcache_dict.get(code) != (title, active):
                    print code, oldcache_dict.get(code), title, active, 'mismatch - updating'
                    oldcache_dict[code] = (title, is_really_active(active, code))

    with open('newcache.json', 'w') as f:
        f.write(dump_readable_json(oldcache_dict))
    return

    # old scraping below, disabled for now:
    print '['
    regex = re.compile(r'<a href="/library/digital-archive/xcri:([a-zA-Z]{1,3}[0-9]{1,3})">(?!\1)(.+?)</a>')
    comma = ''  # print comma after first module
    for i in range(1, PAGES + 1):
        print >>sys.stderr, 'Processing page {}/{}...'.format(i, PAGES)
        html = requests.get('http://www.open.ac.uk/library/digital-archive/module/list/page{}'.format(i)).content
        for (code, module) in regex.findall(html):
            try_url = 'http://www.open.ac.uk/courses/modules/{}'.format(code.lower())
            found = requests.head(try_url).status_code == 200
            print '%s {"%s": ["%s", %s]}' % (
                comma or ' ',
                code,
                module,
                'true' if found else 'false'
            )
            comma = ','
            time.sleep(0.1)
    print ']'

if __name__ == '__main__':
    main()
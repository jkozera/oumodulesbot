import re

import requests
import sys
import time

PAGES = 165

def main():
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
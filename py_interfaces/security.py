# # Troubleshooting
# I keep getting a CHALLENGE
# Linkedin will throw you a curve ball in the form of a Challenge URL. We currently don't handle this, and so you're kinda screwed. We think it could be only IP-based (i.e. logging in from different location). Your best chance at resolution is to log out and log back in on your browser.

# Known reasons for Challenge include:

# 2FA
# Rate-limit - "It looks like you’re visiting a very high number of pages on LinkedIn.". Note - n=1 experiment where this page was hit after ~900 contiguous requests in a single session (within the hour) (these included random delays between each request), as well as a bunch of testing, so who knows the actual limit.
# Please add more as you come across them.

# Search problems
# Mileage may vary when searching general keywords like "software" using the standard search method. They've recently added some smarts around search whereby they group results by people, company, jobs etc. if the query is general enough. Try to use an entity-specific search method (i.e. search_people) where possible.

#!/usr/bin/env python
print('If you get error "ImportError: No module named \'six\'" install six:\n'+\
    '$ sudo pip install six');
print('To enable your free eval account and get CUSTOMER, YOURZONE and ' + \
    'YOURPASS, please contact sales@brightdata.com')
import sys
if sys.version_info[0]==2:
    import six
    from six.moves.urllib import request
    opener = request.build_opener(
        request.ProxyHandler(
            {'http': 'http://brd-customer-hl_9b9a1599-zone-residential_proxy1-country-us:4n5gx0fg0qax@brd.superproxy.io:33335',
            'https': 'http://brd-customer-hl_9b9a1599-zone-residential_proxy1-country-us:4n5gx0fg0qax@brd.superproxy.io:33335'}))
    print(opener.open('https://geo.brdtest.com/welcome.txt?product=resi&method=native').read())
if sys.version_info[0]==3:
    import urllib.request
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(
            {'http': 'http://brd-customer-hl_9b9a1599-zone-residential_proxy1-country-us:4n5gx0fg0qax@brd.superproxy.io:33335',
            'https': 'http://brd-customer-hl_9b9a1599-zone-residential_proxy1-country-us:4n5gx0fg0qax@brd.superproxy.io:33335'}))
    print(opener.open('https://geo.brdtest.com/welcome.txt?product=resi&method=native').read())
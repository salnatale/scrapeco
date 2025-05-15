# # Troubleshooting
# I keep getting a CHALLENGE
# Linkedin will throw you a curve ball in the form of a Challenge URL. We currently don't handle this, and so you're kinda screwed. We think it could be only IP-based (i.e. logging in from different location). Your best chance at resolution is to log out and log back in on your browser.

# Known reasons for Challenge include:

# 2FA
# Rate-limit - "It looks like you're visiting a very high number of pages on LinkedIn.". Note - n=1 experiment where this page was hit after ~900 contiguous requests in a single session (within the hour) (these included random delays between each request), as well as a bunch of testing, so who knows the actual limit.
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

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from pydantic import BaseModel
from typing import Optional, Dict
import os
from datetime import datetime, timedelta

# API key security
API_KEY_NAME = "X-API-Key"
API_KEY_HEADER = APIKeyHeader(name=API_KEY_NAME)

# OAuth2 components
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Define valid API keys (in a real app, store these securely)
API_KEYS = {
    "dev_key_123": {"app_name": "Development App", "app_id": "dev_app_1", "rate_limit": 100},
    "test_key_456": {"app_name": "Test App", "app_id": "test_app_1", "rate_limit": 50}
}

# Define users (in a real app, store these securely in a database)
USERS = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "email": "admin@example.com",
        "hashed_password": "fakehashedpassword",
        "disabled": False,
        "permissions": ["read", "write", "admin"]
    },
    "user": {
        "username": "user",
        "full_name": "Regular User",
        "email": "user@example.com",
        "hashed_password": "fakehashedpassword2",
        "disabled": False,
        "permissions": ["read"]
    }
}

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    permissions: list = []

def verify_api_key(api_key: str = Depends(API_KEY_HEADER)) -> Dict:
    """
    Verifies the API key and returns the associated app information.
    Raises an HTTPException if the API key is invalid.
    """
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "APIKey"},
        )
    return API_KEYS[api_key]

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Gets the current user based on the provided token.
    In a real implementation, this would validate JWT tokens.
    For this example, we're using simplified logic.
    """
    # This is a simplified authentication - in production use proper JWT validation
    username = "admin" if token == "admin_token" else "user"
    
    if username not in USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_data = USERS[username]
    if user_data["disabled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return User(**user_data)
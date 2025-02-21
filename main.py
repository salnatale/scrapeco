from linkedin_api import *
from models import LinkedInProfile
from models import APIStatus

import requests
# create local handler for linkedin api
# define username ID class based off string

# fetch environment variables
import os
from dotenv import load_dotenv
load_dotenv(override=True)
import urllib.parse

LINKEDIN_USER = os.getenv("LINKEDIN_USER_1")
LINKEDIN_PASS = os.getenv("LINKEDIN_PASS_1")

# get proxy info from environment variables
linkedin_logins = {}
for key, value in os.environ.items():
    if "LINKEDIN_USER" in key and key not in linkedin_logins:
        iter = key[-1]
        linkedin_logins[key] = {"username": value, "password": os.getenv(f"LINKEDIN_PASS_{iter}")}
print(linkedin_logins)


customer = os.getenv('BRIGHTDATA_CUSTOMER')
zone = os.getenv('BRIGHTDATA_ZONE')
password = os.getenv('BRIGHTDATA_PASSWORD')
host = os.getenv('BRIGHTDATA_HOST')
port = os.getenv('BRIGHTDATA_PORT')
# no ssl cert needed if using datacenter proxies, change if using residential
# create proxy url
proxy_url = f"{customer}-zone-{zone}:{password}@{host}:{port}"
proxies = {
    'http': proxy_url,
    'https': proxy_url
}
print(proxies)
# test proxy

try: 
    response = requests.get("https://httpbin.org/ip", proxies=proxies)
    print(response.json())
except Exception as e:
    print(e)
    print("Proxy failed")
    proxies = None
    response = requests.get("https://httpbin.org/ip")
    print(response.json())
# test proxy

class LinkedInAPI:
    def __init__(self):
        # define LINKEDIN_USER and LINKEDIN_PASS frmo environment variables
        try:
            self.api = Linkedin(LINKEDIN_USER, LINKEDIN_PASS,proxies=proxies)
        except Exception as init_err:
            print("Failed to initialize LinkedIn client:", init_err)
            self.api = None
        self.curr_info = APIStatus()
    def check_curr_safety(self):
        """
        Check if, by determined metrics, a call is safe to make with current environment
        """
        # check if current account is safe to use
        #rate limit ds  = {"x-ratelimit-limit": "1000", "x-ratelimit-remaining": "999", "x-ratelimit-reset": "1633660800"}

    def attempt_safe_call(self, func,err_msg = None,bad_return = None, *args, **kwargs, ):
        # attempt safe call to linkedin api
        #default msg
        if not err_msg:
            err_msg = "Error calling linkedInAPI method:"
    
        try:
            self.check_curr_safety()
            return func(*args, **kwargs)
        except Exception as call_err:
            print(err_msg, call_err)
            return bad_return
            
    def switch_active_account(self, username, password):
        # switch active account
        try:
            self.api = Linkedin(username, password,proxies=proxies)
            return True
        except Exception as switch_err:
            print("Failed to switch active account:", switch_err)
            return
    # function to grab the profile of a user
    def get_profile_from_public_ID(self, public_uid):
        if not self.api:
            print("LinkedIn API client is not initialized.")
            return None
        return self.attempt_safe_call(self.api.get_profile, public_uid)
        

    # function to grab the connections of a user
    def get_connections(self, uid)->list:
        if not self.api:
            print("LinkedIn API client is not initialized.")
            return None
        # attempt to get connections
        self.attempt_safe_call(self.api.get_profile_connections,err_msg="Error fetching connections",bad_return = [], urn_id = uid)


    # function to grab the companies a user is following
    def get_profile_experiences(self, username):
        if not self.api:
            print("LinkedIn API client is not initialized.")
            return None
        return self.attempt_safe_call(self.api.get_profile_experiences,username, err_msg= f"Error fetching experiences for username '{username}':",)
    
    def test_all(self):
        # Test the complete flow with careful error handling
        try:
            profile = self.get_profile_from_public_ID("salnatale")
            if not profile:
                print("No profile returned.")
                return
            try:
                # Parse the raw profile using your model parser
                linkedin_profile = LinkedInProfile.parse_raw_profile(LinkedInProfile, profile)
                print("Parsed profile:", linkedin_profile)
            except Exception as parse_err:
                print("Error parsing profile data:", parse_err)
        except Exception as test_err:
            print("Error in test_all method:", test_err)


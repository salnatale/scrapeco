from linkedin_api import *
from models import LinkedInProfile
import requests
# create local handler for linkedin api
# define username ID class based off string

# fetch environment variables
import os
from dotenv import load_dotenv
load_dotenv(override=True)
import urllib.parse

LINKEDIN_USER = os.getenv("LINKEDIN_USER")
LINKEDIN_PASS = os.getenv("LINKEDIN_PASS")
# get proxy info from environment variables
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
response = requests.get("https://httpbin.org/ip", proxies=proxies)
print(response.json())


class LinkedInAPI:
    def __init__(self):
        # define LINKEDIN_USER and LINKEDIN_PASS frmo environment variables
        self.api = Linkedin(LINKEDIN_USER, LINKEDIN_PASS,proxies=proxies)
            
    # function to grab the profile of a user
    def get_profile_from_public_ID(self, public_uid):
        # ensure profile found
        try:
            return self.api.get_profile(public_uid)
        except Exception as e:
            print(e)
            return None

    # function to grab the connections of a user
    def get_connections(self, uid)->list:
        return self.api.get_profile_connections(urn_id=uid)

    # function to grab the companies a user is following
    def get_profile_experiences(self, username):
        return self.api.get_profile_experiences(username)

    def test_all(self):
        profile = self.get_profile_from_public_ID("")
        Linkedin_profile = LinkedInProfile.parse_raw_profile(LinkedInProfile, profile)
        print(profile)

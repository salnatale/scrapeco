from linkedin_api import *
from models import LinkedInProfile
# create local handler for linkedin api
# define username ID class based off string

# fetch environment variables
import os
from dotenv import load_dotenv
load_dotenv()
LINKEDIN_USER = os.getenv("LINKEDIN_USER")
LINKEDIN_PASS = os.getenv("LINKEDIN_PASS")


class LinkedInAPI:
    def __init__(self):
        # define LINKEDIN_USER and LINKEDIN_PASS frmo environment variables
        self.api = Linkedin(LINKEDIN_USER, LINKEDIN_PASS)
            
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
        profile = self.get_profile_from_public_ID("christiaaneikeboom")
        Linkedin_profile = LinkedInProfile.parse_raw_profile(LinkedInProfile, profile)
        print(profile)
        return Linkedin_profile

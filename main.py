from linkedin_api import *
from models import LinkedInProfile, LinkedInCompany
from models import APIStatus, AccountStatus
from datetime import datetime, timedelta
import requests
import time
import itertools
import asyncio
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
        self.status = APIStatus(last_call =datetime.now(),total_calls=0, account_statuses = {})
        self.account_cycle = itertools.cycle(linkedin_logins)
        self.status.account_statuses = {id: AccountStatus(rate_limit=1000, remaining_calls=1000, reset_time=datetime.now()  
) for id in linkedin_logins}
        
        self.active_account = LINKEDIN_USER
    def check_curr_safety(self):
        """
        Check if, by determined metrics, a call is safe to make with current environment
        """
        # check if current account is safe to use
        # TODO: set unusable account limit, to cut out. 
        curr_status = self.status.account_statuses[self.active_account]
        if curr_status.usable == True:
            if curr_status.remaining_calls <= 0:
                print("Warning: Account has run out of calls.")

                curr_status.usable = False
                self.reset_account_usability(self.active_account)

                # switch account
                # get next account
                next_account = next(self.account_cycle)
                # switch active account
                self.switch_active_account(linkedin_logins[next_account]["username"], linkedin_logins[next_account]["password"])
                self.active_account = next_account
                # check if account is safe to use
                return self.check_curr_safety()
            else:
                return True
        else: 
            print("Warning: Account is not usable.")
            # switch account
            # get next account
            next_account = next(self.account_cycle)
            # switch active account
            self.switch_active_account(linkedin_logins[next_account]["username"], linkedin_logins[next_account]["password"])
            self.active_account = next_account
            # check if account is safe to use
            return self.check_curr_safety()
        
    async def reset_account_usability(self, account_id):
        """
        Asynchronously wait until the reset time for an account, then mark it as usable again.
        
        Args:
            account_id: The ID of the account to reset
        """
        curr_status = self.status.account_statuses[account_id]
        
        # Calculate how long to wait until reset time
        now = datetime.now()
        if curr_status.reset_time > now:
            wait_seconds = (curr_status.reset_time - now).total_seconds()
            print(f"Account {account_id} will be reset after {wait_seconds:.2f} seconds")
            
            # Wait until the reset time
            await asyncio.sleep(wait_seconds)
            
            # Reset the account status
            curr_status.usable = True
            curr_status.remaining_calls = curr_status.rate_limit
            print(f"Account {account_id} has been reset and is now usable")
        else:
            # If reset time has already passed, immediately reset
            curr_status.usable = True
            curr_status.remaining_calls = curr_status.rate_limit
            print(f"Account {account_id} has been immediately reset and is now usable")

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
        # return self.attempt_safe_call(self.api.get_profile, public_uid)
        return self.api.get_profile(public_uid)
        

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
            profile = self.get_profile_from_public_ID("alexandra-gier")
            if not profile:
                print("No profile returned.")
                return
            try:
                # Parse the raw profile using your model parser
                linkedin_profile = LinkedInProfile.parse_raw_profile(profile)
                print("Parsed profile:", linkedin_profile)
            except Exception as parse_err:
                print("Error parsing profile data:", parse_err)
        except Exception as test_err:
            print("Error in test_all method:", test_err)
    def find_company(self,profile_id):
        # find a profile by id
        print(self.api.get_company(public_id=profile_id))
        return LinkedInCompany.parse_raw_model(self.api.get_company(public_id=profile_id))
    
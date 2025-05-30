from linkedin_api import *
from models import LinkedInProfile, LinkedInCompany
from models import APIStatus, AccountStatus
from datetime import datetime, timedelta
import requests
import time
import itertools
import asyncio
from scipy.stats import lognorm
from druid_database import send_to_druid
from mock import *
import random

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
    # response = requests.get("https://httpbin.org/ip")
    # print(response.json()) # httpbin not working for some reason
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
        
        self.active_account = "LINKEDIN_USER_1"
    def ensure_curr_safety(self) -> bool:
        """
        Check if, by determined metrics, a call is safe to make with current environment.
        If it is not, switch accounts to a valid one, else return false. 
        Returns: 
            True if account is switched
            False otherwise
        """
        print("entering safety check")

        if self.count_usable() == 0: 
            print("no active account ready for querying")
            return False
        print("checking account safety")
        print("self.active_account",self.active_account)
        print("self.status",self.status)
        print("self.status.account_statuses",self.status.account_statuses)
        print("active account in statuses",self.active_account in self.status.account_statuses)
        curr_status = self.status.account_statuses[self.active_account]
        print("checked account safety")

        if curr_status.usable == True:
            print("Account is usable")
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
                return self.ensure_curr_safety()
            else:
                print("returning true")
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
            return self.ensure_curr_safety()
        
    def count_usable(self): 
        """
        count the number of usable accounts reamaining from the account statuses usable field
        """
        # check the usable field for all entries within the account statuses dictionary
        return sum([entry.usable for entry in self.status.account_statuses.values()])

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

    def attempt_safe_call(self, func,*args,err_msg = None,bad_return = None, **kwargs):
    # Method implementation

        # attempt safe call to linkedin api
        #default msg
        print("entering safe call")
        if not err_msg:
            err_msg = "Error calling linkedInAPI method:"

        # last call, use log normal frequency for time between calls
        # last call, use log normal frequency for time between calls
        delay = lognorm.rvs(1, loc=1.2)
        time_since_last_call = datetime.now() - self.status.last_call
        
        if time_since_last_call < timedelta(seconds=delay):
            to_wait = (delay - time_since_last_call.total_seconds())
            print(f"Waiting {to_wait:.2f} seconds before next call")
            time.sleep(to_wait)

        
        try:
            if not self.ensure_curr_safety():
                print("No safe accounts available.")
                print(err_msg, call_err)
                return bad_return
            
            #update api status
            print("updating statuses")
            self.status.last_call = datetime.now()
            self.status.total_calls += 1
            self.status.account_statuses[self.active_account].remaining_calls -= 1

            print(f"Calling {func.__name__} with args={args} kwargs={kwargs}")
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
        print("Getting profile for", public_uid)
        if not self.api:
            print("LinkedIn API client is not initialized.")
            return None
        return self.attempt_safe_call(self.api.get_profile, public_uid)
        # return self.api.get_profile(public_uid)
        

    # function to grab the connections of a user
    def get_connections(self, uid)->list:
        if not self.api:
            print("LinkedIn API client is not initialized.")
            return None
        # attempt to get connections
        return self.attempt_safe_call(self.api.get_profile_connections,err_msg="Error fetching connections",bad_return = [], urn_id = uid)


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
            print("Profile:", profile)
            if not profile:
                print("No profile returned.")
                return
            try:
                # Parse the raw profile using your model parser
                linkedin_profile = LinkedInProfile.parse_raw_profile(LinkedInProfile,profile)
                print("Parsed profile:", linkedin_profile)
            except Exception as parse_err:
                print("Error parsing profile data:", parse_err)
        except Exception as test_err:
            print("Error in test_all method:", test_err)
    def find_company(self,profile_id):
        # find a profile by id
        print(self.api.get_company(public_id=profile_id))
        return LinkedInCompany.parse_raw_model(self.api.get_company(public_id=profile_id))
    
    # perform a api linkedin search with a set of kwargs, return the list of profiles
    def search_profiles(self, **kwargs):
        """
        Perform a search of LinkedIn profiles based on the provided criteria.
        Args:
            keywords: str | None = None,
            connection_of: str | None = None,
            network_depths: List[Literal['F', 'S', 'O']] | None = None,
            current_company: List[str] | None = None,
            past_companies: List[str] | None = None,
            nonprofit_interests: List[str] | None = None,
            profile_languages: List[str] | None = None,
            regions: List[str] | None = None,
            industries: List[str] | None = None,
            schools: List[str] | None = None,
            contact_interests: List[str] | None = None,
            service_categories: List[str] | None = None,
            include_private_profiles: bool = False,
            keyword_first_name: str | None = None,
            keyword_last_name: str | None = None,
            keyword_title: str | None = None,
            keyword_company: str | None = None,
            keyword_school: str | None = None,
            network_depth: Literal['F', 'S', 'O'] | None = None,
            title: str | None = None,
        Returns:
            List[dict] - A list of LinkedIn profiles
        """
        if not self.api:
            print("LinkedIn API client is not initialized.")
            return None
        return self.attempt_safe_call(self.api.search_people, err_msg="Error searching profiles",bad_return = [], **kwargs)
    



    

    def find(self,kwargs,description) -> List[LinkedInProfile]:
        """
        Find LinkedIn profiles based on the provided criteria and description.
        Args:
            kwargs: dict - A dictionary of search criteria (see search_profiles)
            description: str - A description of the desired profile(s)
        Returns:
            List[LinkedInProfile] - The LinkedIn profiles that match the description
        """

        # find a profile or set of profiles by description
        # perform a search of linkedin profiles based on criterion found via description
        # (optional) create linkedin profile search via description 
        # ->    return a list of profiles
        # determine (LLM) which (if any) of the returned profiles are the desired profile from the query
        # ->    return the desired profile(s)
        # parse the raw profile(s) into the LinkedInProfile model
        # load the profile(s) (correct model) into the database
        # ->    return the loaded profile(s) models
        profiles = self.search_profiles(**kwargs)
        print("Profiles:", profiles)
        if not profiles:
            print("No profiles found.")
            return []
        # Filter the profiles using the LLM filter
        filtered_profiles = llm_filter_profile_list(profiles, description)
        
        print("Filtered profiles:", filtered_profiles)
        if not filtered_profiles:
            print("No profiles matched the description.")
            return []
        
        return filtered_profiles


# create and upload 1000 intelligently created mock profiles with unique ids
def create_and_upload_mock_profiles(num):
    # iterate through unique id's
    profiles = []
    for i in range(num):
        # create unique mock urn_id using i
        urn_id = f"urn:li:mock_profile:{i}"
        # create a bank of companies to assign to profiles, along with their mock urn_id's. Model on real companies
        companies = [
            {"name": "Google", "urn_id": "urn:li:Google:1"},
            {"name": "Facebook", "urn_id": "urn:li:Facebook:2"},
            {"name": "Microsoft", "urn_id": "urn:li:Microsoft:3"},
            {"name": "Apple", "urn_id": "urn:li:Apple:4"},
            {"name": "Amazon", "urn_id": "urn:li:Amazon:5"},
            {"name": "Netflix", "urn_id": "urn:li:Netflix:6"},
            {"name": "Tesla", "urn_id": "urn:li:Tesla:7"},
            {"name": "SpaceX", "urn_id": "urn:li:SpaceX:8"},
            {"name": "Twitter", "urn_id": "urn:li:Twitter:9"},
            {"name": "LinkedIn", "urn_id": "urn:li:LinkedIn:10"}
        ]
        first_names = ["Archie", "Betty", "Charlie", "Daisy", "Ella", "Finn", "Grace", "Henry", "Ivy", "Jack", "Katie", "Liam", "Mia", "Noah", "Olivia", "Parker", "Quinn", "Riley", "Sophia", "Theo", "Uma", "Violet", "Wyatt", "Xander", "Yara", "Zara"]
        last_names = ["Adams", "Baker", "Chen", "Diaz", "Evans", "Fisher", "Garcia", "Hernandez", "Ito", "Jones", "Kim", "Lee", "Martinez", "Nguyen", "O'Connor", "Patel", "Quinn", "Rodriguez", "Smith", "Taylor", "Ueda", "Vasquez", "Wang", "Xu", "Yang", "Zhang"]
        university = ["Harvard University", "Stanford University", "Massachusetts Institute of Technology", "Cornell University","California Institute of Technology", "University of California, Berkeley", "University of California, Los Angeles", "University of Michigan", "University of Texas at Austin", "University of Washington", "University of Wisconsin-Madison"]
        # generate random urn_id
        id = random.randint(1000000000, 9999999999)
        # create mock profile, using intelligent mock profile creation, unique urn_id and randomly chosen company
        while True:
            try: 
                mock_profile = LinkedInProfile(**create_intelligent_mock_profile(first_name = random.choice(first_names),last_name = random.choice(last_names), school = random.choice(university), company = random.choice(companies),urn_id = random.randint(1000000000, 9999999999)))
                break
            except Exception as mock_err:
                print("Error creating mock profile:", mock_err)
            # retry
            continue
        # progress updates
        if i % 5 == 1:
            print(f"Created {i} mock profiles / 100")
            most_recent :LinkedInProfile = profiles[-1] 
            print("Most Recent:",most_recent.first_name,most_recent.last_name,most_recent.experience[0].company.name)

        profiles.append(mock_profile)
    
    # upload mock necessary data to druid db
    # send_to_druid(profiles = profiles, companies = [])
    # upload mock necessary data to neo4j db

    # 
    return profiles

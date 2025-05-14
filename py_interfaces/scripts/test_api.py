#!/usr/bin/env python
"""
API Testing Script for the LinkedIn Data API

This script runs a series of tests against the API endpoints to ensure they are functioning correctly.
It also generates sample data for development purposes.
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime
import random

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mock_enhanced import LinkedInDataGenerator

API_BASE_URL = "http://localhost:8000/api"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check endpoint...")
    response = requests.get(f"{API_BASE_URL}/")
    
    if response.status_code == 200:
        print("✅ Health check passed")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False

def generate_mock_data(num_profiles=50, num_companies=10):
    """Generate mock data for testing"""
    print(f"Generating {num_profiles} mock profiles and {num_companies} companies...")
    
    generator = LinkedInDataGenerator()
    
    # Generate profiles
    profiles = generator.generate_profile_dataset(num_profiles)
    
    # Generate companies
    companies = generator.generate_company_dataset(num_companies)
    
    # Generate transitions between profiles and companies
    transitions = generator.generate_transitions(profiles, 100)
    
    print(f"✅ Generated {len(profiles)} profiles, {len(companies)} companies, and {len(transitions)} transitions")
    
    return profiles, companies, transitions

def test_store_data(profiles, companies, transitions):
    """Test storing data in the database"""
    print("Testing data storage endpoints...")
    
    success_count = 0
    total_count = len(profiles) + len(transitions)
    
    # Store profiles
    for profile in profiles:
        try:
            response = requests.post(f"{API_BASE_URL}/db/store_profile", json=profile)
            if response.status_code == 200:
                success_count += 1
            else:
                print(f"Failed to store profile: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error storing profile: {e}")
    
    # Store transitions
    for transition in transitions:
        try:
            response = requests.post(f"{API_BASE_URL}/db/store_transition", json=transition)
            if response.status_code == 200:
                success_count += 1
            else:
                print(f"Failed to store transition: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error storing transition: {e}")
    
    success_rate = (success_count / total_count) * 100
    print(f"✅ Data storage tests completed: {success_count}/{total_count} successful ({success_rate:.1f}%)")
    
    return success_count > 0

def test_graph_algorithms():
    """Test graph algorithm endpoints"""
    print("Testing graph algorithm endpoints...")
    
    # Build projection
    projection_request = {
        "graph_name": "test_graph",
        "weight_scheme": "count",
        "delete_existing": True
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/graph/projection", json=projection_request)
        if response.status_code != 200:
            print(f"Failed to build projection: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error building projection: {e}")
        return False
    
    # Run PageRank
    pagerank_request = {
        "graph_name": "test_graph",
        "damping": 0.85,
        "iterations": 10
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/graph/pagerank", json=pagerank_request)
        if response.status_code != 200:
            print(f"Failed to run PageRank: {response.status_code} - {response.text}")
            return False
            
        pagerank_results = response.json()
        print(f"PageRank returned {len(pagerank_results.get('results', []))} results")
    except Exception as e:
        print(f"Error running PageRank: {e}")
        return False
    
    # Run BiRank
    birank_request = {
        "graph_name": "test_graph",
        "alpha": 0.85,
        "beta": 0.85,
        "max_iter": 10
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/graph/birank", json=birank_request)
        if response.status_code != 200:
            print(f"Failed to run BiRank: {response.status_code} - {response.text}")
            return False
            
        birank_results = response.json()
        print(f"BiRank returned {len(birank_results.get('results', []))} results")
    except Exception as e:
        print(f"Error running BiRank: {e}")
        return False
    
    print("✅ Graph algorithm tests passed")
    return True

def test_vc_analytics():
    """Test VC analytics endpoints"""
    print("Testing VC analytics endpoints...")
    
    # Test company search
    filters = {
        "mode": "research",
        "industries": ["AI", "Fintech"],
        "funding_stages": ["Seed", "Series A"]
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/vc/companies/search", json=filters)
        if response.status_code != 200:
            print(f"Failed to search companies: {response.status_code} - {response.text}")
            return False
            
        search_results = response.json()
        print(f"Company search returned {len(search_results.get('companies', []))} companies")
    except Exception as e:
        print(f"Error searching companies: {e}")
        return False
    
    # Test trending skills
    try:
        response = requests.get(f"{API_BASE_URL}/vc/skills/trending")
        if response.status_code != 200:
            print(f"Failed to get trending skills: {response.status_code} - {response.text}")
            return False
            
        skills_results = response.json()
        print(f"Trending skills endpoint returned {len(skills_results.get('skills', []))} skills")
    except Exception as e:
        print(f"Error getting trending skills: {e}")
        return False
    
    print("✅ VC analytics tests passed")
    return True

def test_advanced_analytics():
    """Test advanced analytics endpoints"""
    print("Testing advanced analytics endpoints...")
    
    # Test talent flow network
    try:
        response = requests.get(f"{API_BASE_URL}/analytics/talent-flow-network?min_transitions=2")
        if response.status_code != 200:
            print(f"Failed to get talent flow network: {response.status_code} - {response.text}")
            return False
            
        network_results = response.json()
        print(f"Talent flow network has {len(network_results.get('nodes', []))} nodes and {len(network_results.get('links', []))} links")
    except Exception as e:
        print(f"Error getting talent flow network: {e}")
        return False
    
    # Test geographic talent density
    try:
        response = requests.get(f"{API_BASE_URL}/analytics/geographic-talent-density")
        if response.status_code != 200:
            print(f"Failed to get geographic talent density: {response.status_code} - {response.text}")
            return False
            
        geo_results = response.json()
        print(f"Geographic talent density returned {len(geo_results)} locations")
    except Exception as e:
        print(f"Error getting geographic talent density: {e}")
        return False
    
    # Test company scores
    score_request = {
        "company_urns": [],  # Empty to get top companies
        "include_pagerank": True,
        "include_birank": True,
        "include_talent_flow": True
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/analytics/company-scores", json=score_request)
        if response.status_code != 200:
            print(f"Failed to get company scores: {response.status_code} - {response.text}")
            return False
            
        score_results = response.json()
        print(f"Company scores returned for {len(score_results)} companies")
    except Exception as e:
        print(f"Error getting company scores: {e}")
        return False
    
    print("✅ Advanced analytics tests passed")
    return True

def main():
    parser = argparse.ArgumentParser(description="Test the LinkedIn Data API")
    parser.add_argument("--generate", type=int, default=0, help="Generate this many mock profiles (default: 0)")
    parser.add_argument("--company-count", type=int, default=10, help="Number of companies to generate (default: 10)")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--url", type=str, default="http://localhost:8000/api", help="Base URL for the API")
    
    args = parser.parse_args()
    
    global API_BASE_URL
    API_BASE_URL = args.url
    
    print(f"Testing API at {API_BASE_URL}")
    
    # Health check
    if not test_health_check():
        print("Health check failed. Make sure the API is running.")
        return 1
    
    # Generate mock data if requested
    if args.generate > 0:
        profiles, companies, transitions = generate_mock_data(args.generate, args.company_count)
        test_store_data(profiles, companies, transitions)
    
    # Run tests if not skipped
    if not args.skip_tests:
        tests_passed = True
        
        tests_passed = tests_passed and test_graph_algorithms()
        tests_passed = tests_passed and test_vc_analytics()
        tests_passed = tests_passed and test_advanced_analytics()
        
        if tests_passed:
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Some tests failed.")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
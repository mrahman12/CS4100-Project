#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import requests
import json
import time
import random
from cdg_client import CDGClient

api_key = 'Jq9Uy2kgbNouvTJfoixzEYYQQJ88FAjM3D5HFPne'
parse_xml = lambda data: ET.fromstring(data)  # from bytes, more accurately

def get_bills(client):
    """
    Returns a list of tuples for each of the bills information collected.

    RETURNS a list of 6-tuples (see desc below)
    """
    all_bills = []
    endpoint = "bill"
    data, _ = client.get(endpoint)
    root = parse_xml(data)
    count = 0
    full_count = 0
    for bill in root.findall(".//bills/bill"):
        time.sleep(random.uniform(0,3))
        bill_congress = bill.find("congress").text.strip()
        bill_type = bill.find("type").text.strip()
        bill_num = bill.find("number").text.strip()
        bill_type = bill_type.lower()
        full_count += 1

        # Only count actual house and senate bills, not resolutions
        if bill_type != 'hr' and bill_type != 's':
            continue

        # Get bill specific data
        print(full_count)
        bill_data = get_bill_data(client, bill_congress, bill_type, bill_num)
        if bill_data is not None and (bill_data[4] or bill_data[5]):
            count += 1
            print(bill_data[0], 'Vote found')
            all_bills.append(bill_data)
    print(count)
    return all_bills

def get_bill_data(client, congress, b_type, b_num):
    try:
        client = CDGClient(api_key, response_format="xml")
        
        """
        Given a bill to lookup, returns a dictionary of each legislator ID
        to their vote on the bill.

        RETURNS a 6-tuple (bill_code, bill_name, bill_policy_area, bill_summary, dict_house(leg_id -> vote), dict_senate(leg_id -> vote)) if vote present OTHERWISE None
        """


        """
        Get VOTES if present in the actions of a bill...otherwise returns None and save API calls
        """
        endpoint = f"bill/{congress}/{b_type}/{b_num}/actions"
        data, _ = client.get(endpoint)
        root = parse_xml(data)

        house_vote = ''
        senate_vote = ''
        for vote in root.findall(".//actions/item/recordedVotes/recordedVote"):
            chamber = vote.find('chamber').text.strip()
            url = vote.find('url')

            if url is None:
                continue
            else:
                url = url.text.strip()
                print(url)

            # Only takes most recent votes if multiple present
            if chamber == 'Senate' and not senate_vote:
                senate_vote = url
            elif chamber == 'House' and not house_vote:
                house_vote = url
            
            # If we have found a link for both houses
            if house_vote and senate_vote:
                break

        """
        Handles HOUSE voting
        """
        house_votes = {}
        if house_vote:
            # Gets the XML data from the recorded vote
            response = requests.get(house_vote)
            tree = ET.ElementTree(ET.fromstring(response.content))
            root = tree.getroot()

            # Extracts each legislator and their vote for the bill
            for recorded_vote in root.findall('.//recorded-vote'):
                legislator_id = recorded_vote.find('legislator').get('name-id')
                # legislator_name = recorded_vote.find('legislator').get('sort-field')
                vote = recorded_vote.find('vote').text
                house_votes[legislator_id] = vote

        """
        Handles SENATE voting
        """
        senate_votes = {}
        if senate_vote:
            # Gets the XML data from the recorded vote
            response = requests.get(senate_vote)
            tree = ET.ElementTree(ET.fromstring(response.content))
            root = tree.getroot()

            # Extracts each legislator and their vote for the bill
            members = root.find('members')
            for member in members.findall('member'):
                legislator_id = member.find('lis_member_id').text
                # legislator_name = member.find('legislator').get('sort-field')
                vote = member.find('vote_cast').text
                senate_votes[legislator_id] = vote

        if not house_votes and not senate_votes:
            print(b_type + str(b_num), 'No vote.')
            return None

        """
        Get the bill title and policy area
        """
        endpoint = f"bill/{congress}/{b_type}/{b_num}"
        data, _ = client.get(endpoint)
        root = parse_xml(data)
        bill_title = root.find(".//bill/title").text.strip()
        bill_policy_area = root.find(".//bill/policyArea/name").text.strip()

        """
        Get the bill summary
        """
        endpoint = f"bill/{congress}/{b_type}/{b_num}/summaries"
        data, _ = client.get(endpoint)
        root = parse_xml(data)
        bill_summ = root.find(".//summaries/summary/text").text.strip()

        bill_code = str(b_type).upper() + str(b_num)
        return (bill_code, bill_title, bill_policy_area, bill_summ, house_votes, senate_votes)
    except AttributeError as err:
        return None

if __name__ == "__main__":
    """
    Runs through 1 year latest bills by action date
    """

    master_list = []
    
    round_cnt = 108
    while round_cnt <= 1000:
        client = CDGClient(api_key, response_format="xml", offset=(round_cnt * 250))
        print(f"Contacting Congress.gov, at {client.base_url} ...")
        
        data = get_bills(client)
        
        # Merge list
        for i in data:
            master_list.append(i)
        
        print('** ROUND ' + str(round_cnt) + ' OVER **')

        try:
            # Write data to JSON file
            with open("votes-round-" + str(round_cnt) + ".json", "w") as json_file:
                json.dump(master_list, json_file, indent=6)

        except OSError as err:
            print('Error:', err)
        
        round_cnt += 1

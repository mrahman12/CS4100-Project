#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import requests
import json
from datetime import datetime, timedelta
from cdg_client import CDGClient

api_key = 'Jq9Uy2kgbNouvTJfoixzEYYQQJ88FAjM3D5HFPne'

parse_xml = lambda data: ET.fromstring(data)  # from bytes, more accurately

def get_bills(client):
    """
    Returns a list of tuples for each of the bills information collected.

    RETURNS a list of 4-tuples (see desc below)
    """
    all_bills = []
    endpoint = "bill"
    data, _ = client.get(endpoint)
    root = parse_xml(data)
    count = 0
    for bill in root.findall(".//bills/bill"):
        bill_congress = bill.find("congress").text.strip()
        bill_type = bill.find("type").text.strip()
        bill_num = bill.find("number").text.strip()
        bill_type = bill_type.lower()

        # Only count actual house and senate bills, not resolutions
        if bill_type != 'hr' and bill_type != 's':
            continue

        # Get bill specific data
        bill_data = get_bill_data(client, bill_congress, bill_type, bill_num)
        if bill_data is not None and (bill_data[4] or bill_data[5]):
            count += 1
            print(bill_data[0], 'Vote found')
            all_bills.append(bill_data)
    print(count)
    return all_bills


def get_bill_data(client, congress, b_type, b_num):
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

if __name__ == "__main__":
    """
    Runs through 1 year latest bills by action date
    """
    today = datetime.today()
    today_fmt = today.strftime('%Y-%m-%dT00:00:00Z')
    today_str = str(today_fmt)

    one_yr_ago = today - timedelta(days=365)
    one_yr_ago_fmt = one_yr_ago.strftime('%Y-%m-%dT00:00:00Z')
    one_yr_ago_str = str(one_yr_ago_fmt)

    client = CDGClient(api_key, response_format="xml", date_to=today_str, date_from=one_yr_ago_str)
    print(f"Contacting Congress.gov, at {client.base_url} ...")

    try:
        # print(get_bill_data(client, 118, 'hr', 6009))
        # exit()
        data = get_bills(client)

        # Write data to JSON file
        with open("votes.json", "w") as json_file:
            json.dump(data, json_file, indent=6)

    except OSError as err:
        print('Error:', err)

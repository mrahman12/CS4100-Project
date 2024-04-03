#!/usr/bin/env python3
"""
    CDG Examples

    Below are some examples of using the Bill endpoint with XML parsing.

    @copyright: 2022, Library of Congress
    @license: CC0 1.0
"""
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
    endpoint = f"bill"
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

        
        bill_data = get_bill_data(client, bill_congress, bill_type, bill_num)
        if bill_data is not None:
            count += 1
            print('Vote found')
            all_bills.append(bill_data)
    print(count)
    return all_bills


def get_bill_data(client, congress, b_type, b_num):
    client = CDGClient(api_key, response_format="xml")
    bill_votes = {}
    """
    Given a bill to lookup, returns a dictionary of each legislator ID
    to their vote on the bill.

    RETURNS a 4-tuple (bill_name, bill_policy_area, bill_summary, dict(leg_id -> vote)) if vote present OTHERWISE None
    """


    """
    Get VOTES if present in the actions of a bill...otherwise returns None and save API calls
    """
    endpoint = f"bill/{congress}/{b_type}/{b_num}/actions"
    data, _ = client.get(endpoint)
    root = parse_xml(data)

    vote_url = root.find(".//actions/item/recordedVotes/recordedVote/url")
    if vote_url is None: # If a bill does not have a vote
        print('Bill does not have a vote')
        return None
    url = vote_url.text.strip()

    # Gets the XML data from the recorded vote
    response = requests.get(url)
    tree = ET.ElementTree(ET.fromstring(response.content))
    root = tree.getroot()

    # Extracts each legislator and their vote for the bill
    for recorded_vote in root.findall('.//recorded-vote'):
        legislator_id = recorded_vote.find('legislator').get('name-id')
        # legislator_name = recorded_vote.find('legislator').get('sort-field')
        vote = recorded_vote.find('vote').text
        bill_votes[legislator_id] = vote

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

    return (bill_title, bill_policy_area, bill_summ, bill_votes)

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
        json_data = json.dumps(get_bills(client))
        print(json_data)

        with open('data.json', 'w') as file:
            file.write(json_data)

    except OSError as err:
        print('Error:', err)
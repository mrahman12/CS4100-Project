import numpy as np
import csv

headers = ['Name', 'Chamber', 'Party', 'State', 'Years in Current Role']

data = []
with open('active_congress_members.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        name = row['Name'].split(' - ')[0]
        chamber = row['Name'].split(' - ')[1].split(':')[0]
        party = row['Party']
        state = row['State']
        terms = row['Terms'].split('|')
        start_year = int(terms[0].split(':')[1].split('-')[0])
        years_in_current_role = 2024-start_year
        data.append([name, chamber, party, state, years_in_current_role])

active_members = np.array(data)
print(active_members)


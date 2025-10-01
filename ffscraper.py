import requests
from bs4 import BeautifulSoup
import pandas as pd

url = "https://www.pro-football-reference.com/years/2023/passing.htm"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Find the player table by its HTML ID or class
table = soup.find('table', {'id': 'passing'})

rows = table.find_all('tr')
data = []

for row in rows[2:]:  # skipping header rows
    cols = row.find_all('td')
    if len(cols) > 0:
        player_data = [ele.text.strip() for ele in cols]
        data.append(player_data)

# Convert to a DataFrame
df = pd.DataFrame(data, columns=['Player', 'Team', 'Age', ...])  # Use appropriate column names

# Save to a CSV or database
df.to_csv('nfl_player_stats.csv', index=False)

import nfl_data_py as nfl
weekly = nfl.import_weekly_data([2023])
defenders = weekly[weekly['position_group'].isin(['DB', 'LB', 'DL'])]
print(defenders[['player_display_name', 'position_group', 'sacks', 'interceptions', 'fantasy_points']].head())

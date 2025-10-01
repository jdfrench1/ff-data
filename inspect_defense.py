import nfl_data_py as nfl
weekly = nfl.import_weekly_data([2023])
defense = weekly[weekly['position_group'] == 'DEF']
print(defense[['player_display_name', 'position', 'sacks', 'interceptions']].head())

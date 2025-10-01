import nfl_data_py as nfl
weekly = nfl.import_weekly_data([2023])
qbs = weekly[weekly['position_group'] == 'QB']
print(qbs[['player_display_name', 'sacks']].head())

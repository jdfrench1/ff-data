import nfl_data_py as nfl
weekly = nfl.import_weekly_data([2023])
print(len(weekly.columns))
print(weekly.columns.tolist())

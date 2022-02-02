import pandas as pd

# get kick return raw tracking data from NFL Big Data Bowl 2022 kaggle:
#   https://www.kaggle.com/c/nfl-big-data-bowl-2022/data?select=plays.csv
track2018 = pd.read_csv('data/kr_data/tracking2018.csv')
track2019 = pd.read_csv('data/kr_data/tracking2019.csv')
track2020 = pd.read_csv('data/kr_data/tracking2020.csv')
plays = pd.read_csv('data/kr_data/plays.csv')

track = pd.concat([track2018, track2019, track2020])
##del(track2018); del(track2019); del(track2020);

### get dataframe of tracking data of all kick returns from 2018-2020
kr_idxs = plays.query('specialTeamsPlayType == "Kickoff" & specialTeamsResult == "Return"')
kr_idxs1 = kr_idxs[["gameId", "playId"]]
kr_idxs1 = kr_idxs1.assign(kr = True)
track = track.merge(kr_idxs1, on=['gameId', 'playId'], how='left')
track = track.assign(kr = track["kr"].fillna(value=False))
all_KR = track.query('kr == True')
all_KR = all_KR.drop(columns='kr')
### write csv
all_KR.to_csv('data/kr_data/all_KR.csv',index=False)
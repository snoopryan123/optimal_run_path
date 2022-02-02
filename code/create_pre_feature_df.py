import pandas as pd
import numpy as np

# pd.set_option('display.max_columns', None) # Display any number of columns
# pd.set_option('display.max_rows', None) # Display any number of rows
# pd.reset_option('display.max_columns')
# pd.reset_option('display.max_rows')

all_KR = pd.read_csv('data/kr_data/all_KR.csv')

### select relevant columns
all_KR = all_KR.sort_values(['gameId', 'playId','frameId'])
all_KR = all_KR.reset_index(drop=True)
all_KR = all_KR[['gameId','playId',"frameId","playDirection",
                 "x","y","s","a","o","dis","dir",
                 "event","nflId","displayName","jerseyNumber", "position","team"]]

### NOTE: playDirection == 'right' MEANS the kick returner moves 'left'
### make sure all kick returner movement is RIGHT (from small x to large x).
### equivalently, make sure all playDirection == 'left',
###    so we need to change all playDirection == 'right'.

all_KR['x'] = np.where(all_KR['playDirection']=='right',
                       120-all_KR['x'],
                       all_KR['x'])
all_KR['y'] = np.where(all_KR['playDirection']=='right',
                       53.3-all_KR['y'],
                       all_KR['y'])
all_KR['dir'] = np.where(all_KR['playDirection']=='right',
                         (180+all_KR['dir']) % 360,
                         all_KR['dir'])
all_KR['o'] = np.where(all_KR['playDirection']=='right',
                       (180+all_KR['o']) % 360,
                       all_KR['o'])

### get rid of "playDirection", since now all plays are going LEFT
all_KR = all_KR.drop(columns=["playDirection"])

### check. make sure to look only after the row with. event == 'kick_received'.
# pd.set_option('max_rows', 200)
# all_KR[(all_KR["gameId"] == 2021010300) & (all_KR["playId"] == 395) & (all_KR["displayName"] == "Isaiah McKenzie")]
# all_KR[(all_KR["gameId"] == 2021010300) & (all_KR["playId"] == 395) & (all_KR["displayName"] == "football")]
# pd.reset_option('display.max_rows')

### keep only the KICKOFF RETURN portion of the kickoff
###   from the time the offense catches the ball, until tackle/out of bounds/
print(set(all_KR["event"]))

ko_beg_events = ["kick_received"] #FIXME
ret_first = all_KR[all_KR['event'].isin(ko_beg_events)][["gameId","playId","frameId"]].drop_duplicates().rename(columns={"frameId":"frameId_0"})
ko_end_events = ["tackle", "out_of_bounds", "touchdown"] #FIXME: should this include touchdown?
ret_last = all_KR[all_KR['event'].isin(ko_end_events)][["gameId","playId","frameId"]].drop_duplicates().rename(columns={"frameId":"frameId_1"})
ret_boundaries = ret_first.merge(ret_last, on=['gameId', 'playId'], how='left')
ret_boundaries = ret_boundaries.assign(valid_return = True)
all_KR = all_KR.merge(ret_boundaries, on=['gameId', 'playId'], how='left')
all_KR = all_KR.assign(valid_return = all_KR["valid_return"].fillna(value=False))
all_KR = all_KR.query('valid_return')
all_KR = all_KR.query('frameId_0 <= frameId & frameId <= frameId_1')
all_KR = all_KR.drop(columns=["frameId_0", "frameId_1","valid_return"])

### "f_dist" distance from the football to the given player
football = all_KR.query('displayName == "football"')[["gameId","playId","frameId","x","y"]]
football = football.rename(columns={"x": "fx", "y": "fy"})
all_KR = all_KR.merge(football, on=['gameId', 'playId', 'frameId'], how='left')
all_KR["f_dist"] = np.sqrt((all_KR["x"] - all_KR["fx"])**2 + (all_KR["y"] - all_KR["fy"])**2)

### "returner", "returnTeam", "isFootball"
all_KR = all_KR.sort_values(by=['gameId', 'playId', 'frameId','team','f_dist'])
all_KR = all_KR.reset_index().drop(columns=["index"])
# all_KR[(all_KR["gameId"] == 2021010300) & (all_KR["playId"] == 395) & (all_KR["frameId"] == 56)]

returner = all_KR.loc[all_KR.query('displayName != "football"')\
                      .groupby(by=["gameId","playId","frameId"])\
                      .f_dist.idxmin()]
returner = returner.groupby(by=["gameId","playId"]).first().reset_index()[["gameId","playId","displayName","team"]].rename(columns={"displayName":"returner","team":"returnTeam"})


all_KR = all_KR.merge(returner, on=["gameId","playId"])
all_KR["returner"] = (all_KR["returner"] == all_KR["displayName"])
all_KR["returnTeam"] = (all_KR["returnTeam"] == all_KR["team"])
all_KR["isFootball"] = (all_KR["displayName"] == "football")
all_KR["f_dist"] = np.where(all_KR["returner"], 0, all_KR["f_dist"])
all_KR = all_KR.sort_values(by=['gameId', 'playId', 'frameId','team','f_dist'])
# all_KR[(all_KR["gameId"] == 2021010300) & (all_KR["playId"] == 395) & (all_KR["frameId"] == 56)]

### player index "p_idx" column:
###   d01 = closest defender,..., d11 = farthest defender
###   kr == returner, o02 = closest offender,..., o11 = farthest offender
### also, remove rows for football
all_KR = all_KR[~(all_KR["isFootball"])].drop(columns=["isFootball"])
all_KR['p_idx'] = (all_KR.groupby(by=["gameId","playId","frameId","returnTeam"]).cumcount()+1).apply(str)
all_KR['p_idx'] = np.where(all_KR['p_idx'].apply(len) >= 2, all_KR['p_idx'], '0'+all_KR['p_idx'])
all_KR['p_idx'] = np.where(all_KR['returnTeam'], 'o'+all_KR['p_idx'], 'd'+all_KR['p_idx'],)
all_KR['p_idx'] = np.where(all_KR['p_idx'] == 'o01', 'kr', all_KR['p_idx'])
# all_KR[(all_KR["gameId"] == 2021010300) & (all_KR["playId"] == 395) & (all_KR["frameId"] == 56)]

### DEPRECATED: use JERSEYNUMBER instead of p_tag.
# ### player tag "p_tag" column:
# ###      player tag p_tag is different from player index p_idx because
# ###      we need d1 to be the SAME person for the ENTIRE kick
# ###      in order for the KR animations to make sense later on.
# ###   d01 = 1st defender,..., d11 = 11th defender
# ###   kr == returner, o02 = 2nd offender,..., o11 = 11th offender
# all_KR['notReturner'] = ~all_KR['returner']
# all_KR = all_KR.sort_values(by=['gameId','playId','frameId','returnTeam','notReturner','displayName'])
# all_KR['p_tag'] = (all_KR.groupby(by=['gameId','playId','frameId','returnTeam','notReturner']).cumcount()+1)
# all_KR['p_tag'] = np.where(all_KR['returnTeam'], all_KR['p_tag']+1, all_KR['p_tag'])
# all_KR['p_tag'] = all_KR['p_tag'].apply(str)
# all_KR['p_tag'] = np.where(all_KR['p_tag'].apply(len) >= 2, all_KR['p_tag'], '0'+all_KR['p_tag'])
# all_KR['p_tag'] = np.where(all_KR['returnTeam'], 'o'+all_KR['p_tag'], 'd'+all_KR['p_tag'])
# all_KR['p_tag'] = np.where(all_KR['returner'], 'kr', all_KR['p_tag'])

# all_KR[(all_KR["gxameId"] == 2021010300) & (all_KR["playId"] == 395) & (all_KR["frameId"] >= 56) &  (all_KR["frameId"] <= 57)]
###print(sorted(set(all_KR["p_idx"]))); print(sorted(set(all_KR["p_tag"])));


### PRE FEATURE DATAFRAME
pre_feature_df = all_KR[['gameId','playId','frameId',
                         'displayName','nflId','jerseyNumber','position',
                         'x','y','s','a','o','dir','dis',
                         'returnTeam','p_idx']]

pre_feature_df = pre_feature_df.set_index(['gameId', 'playId','frameId', 'p_idx']).unstack().sort_index(axis=1, level=1)
pre_feature_df.columns = ['_'.join(col).strip() for col in pre_feature_df.columns.values]
pre_feature_df = pre_feature_df.reset_index()
### write csv
pre_feature_df.to_csv('data/kr_data/pre_feature_df.csv',index=False)

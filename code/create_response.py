import pandas as pd
import numpy as np

# pd.set_option('display.max_columns', None) # Display any number of columns
# pd.set_option('display.max_rows', None) # Display any number of rows
# pd.reset_option('display.max_columns')
# pd.reset_option('display.max_rows')

### read value_of first down dataset
V_df = pd.read_csv('value_of_first_down/value_of_first_down_df.csv')
V_df = V_df.drop(columns=["ydl","v"])
V_df = V_df.rename(columns={"v_smoothed": "V"})

### function to compute the value of yarldine x
def V(x):
    """given yardline x \in [0,120], return the Value of yardline x.
        if x is not an integer, linearly interpolate.
        if x <= 11, use x=11. if x>=110, use x=109."""
    x0 = np.floor(x)
    x1 = np.ceil(x)
    if x0 < 11:
        x0 = 11
        x1 = 11
    elif x1 > 109:
        x0 = 109
        x1 = 109
    V0 = float(V_df.query(f'x=={x0}')["V"])
    V1 = float(V_df.query(f'x=={x1}')["V"])
    Vx = V0 + (x - x0) * (V1 - V0)
    return Vx

### check
# print([V(13), V(13.1), V(13.9), V(14)])
# print([V(108), V(108.2), V(108.8), V(109)])

### load pre_feature_df
pre_feature_df = pd.read_csv('data/kr_data/pre_feature_df.csv')

### curr_V = value of the x yardline of the current frame
### Vs = value of the starting x yardline of this kick return
### Vf = value of the final x yardline of this kick return
### potential reponse columns:
###     (Vf, Vf_minus_Vs, Vf_minus_Vcurr)
V_mat = pre_feature_df[["gameId", "playId", "frameId", "x_kr"]]
V_mat["curr_V"] = V_mat["x_kr"].apply(V) ### takes ~7 minutes
x_endOfPlay = V_mat.groupby(by=["gameId","playId"]).last()["curr_V"].reset_index()
x_endOfPlay = x_endOfPlay.rename(columns={"curr_V":"Vf"})
x_startOfPlay = V_mat.groupby(by=["gameId","playId"]).first()["curr_V"].reset_index()
x_startOfPlay = x_startOfPlay.rename(columns={"curr_V":"Vs"})
Vf_minus_Vs = x_startOfPlay.merge(x_endOfPlay, how='left')
Vf_minus_Vs["Vf_minus_Vs"] = Vf_minus_Vs["Vf"] - Vf_minus_Vs["Vs"]
V_mat = V_mat.merge(Vf_minus_Vs, how='left')
V_mat["Vf_minus_Vcurr"] = V_mat["Vf"] - V_mat["curr_V"]
V_mat1 = V_mat.drop(columns=["x_kr","curr_V","Vs"]) #FIXME?
### save the potential response columns
V_mat1.to_csv('data/kr_data/V_response.csv',index=False)


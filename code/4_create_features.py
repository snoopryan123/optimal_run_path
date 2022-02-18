import pandas as pd
import numpy as np

# pd.set_option('display.max_columns', None) # Display any number of columns
# pd.set_option('display.max_rows', None) # Display any number of rows
# pd.reset_option('display.max_columns')
# pd.reset_option('display.max_rows')

pre_feature_df = pd.read_csv('data/kr_data/pre_feature_df.csv')

#FIXME

#####################
### x_kr Feature ####
#####################

def create_F1(pre_feature_df):
  return pd.concat([pre_feature_df["x_kr"]], axis=1, keys=["x_kr"])

F1 = create_F1(pre_feature_df)
F1

#################################
### Joey's Projection Feature ###
#################################

def create_F3(pre_feature_df):
  all_cols = pre_feature_df.columns.values
  def_x_cols = np.array([col for col in all_cols if col.count('x_d')])
  def_y_cols = np.array([col for col in all_cols if col.count('y_d')])
  x_dist = (pre_feature_df[def_x_cols].mean(1) - pre_feature_df['x_kr'])
  y_proj = pre_feature_df['y_kr'] + x_dist * np.tan(-(np.radians(pre_feature_df['dir_kr'] - 90)))
  # clip projected values to limits of field - necessary?
  y_proj = np.clip(y_proj, 0, 53.3)
  F3 = pd.DataFrame()
  F3[[f"proj_y_d0{j}" if j < 10 else f"proj_y_d{j}" for j in range(1, 12)]] = pre_feature_df[def_y_cols].sub(y_proj, axis='index')
  return F3

# F3 = create_F3(pre_feature_df)
# F3

################################################
### Indicator: is the j^th defender blocked? ###
################################################

import warnings
warnings.simplefilter('ignore')
pd.set_option('display.width', 3000)
pd.set_option('display.max_columns', 500)
from collections import defaultdict
from queue import PriorityQueue
from tqdm import tqdm

def line_coefs(x1, y1, dir, length=150):
    """
    length is arbitrarily long, so 150
    return coefs (A, B, C) of line equation by two points provided
    """
    x2 = x1 + length * np.cos(dir)
    y2 = y1 + length * np.sin(dir)
    A = (y1 - y2)
    B = (x2 - x1)
    C = (x1 * y2 - x2 * y1)
    return A, B, -C


def intersection(L1, L2):
    """
    line L is tuple size 3
    return intersection point (x, y) between blocker line, defender line
    """
    D = L1[0] * L2[1] - L1[1] * L2[0]
    Dx = L1[2] * L2[1] - L1[1] * L2[2]
    Dy = L1[0] * L2[2] - L1[2] * L2[0]
    if D != 0:
        x = Dx / D
        y = Dy / D
        return x, y
    else:
        return False


def to_intersec_first(b_xy, d_xy, i_xy, b_speed, d_speed):
    """
    we assume player takes fastest path to their intersection
    return True if d player takes less or equal time to intersection compared to b
    """
    blk_dis_to_intersec = np.sqrt((b_xy[0] - i_xy[0]) ** 2 + (b_xy[1] - i_xy[1]) ** 2)
    def_dis_to_intersec = np.sqrt((d_xy[0] - i_xy[0]) ** 2 + (d_xy[1] - i_xy[1]) ** 2)

    return (blk_dis_to_intersec / b_speed >= def_dis_to_intersec / d_speed)

# # test
# def_line = line_coefs(73.89, 18.69, 135.45, 100)
# blocker_line = line_coefs(99.19, 16.89, 244.88, 100)
# intersec_xy = intersection(def_line, blocker_line)
# to_intersec_first(b_xy=(89.21, 13.91), d_xy=(73.89, 18.69), i_xy=intersec_xy, b_speed=2.14, d_speed=5.90)

def create_F4(pre_feature_df):
    # init F4 df
    F4 = pd.DataFrame()
    # CLEANUP: Don't need first two columns
    # for i in range(1, 12): # blocked_dj
    #     i = "%02d" % i
    #     F4["blocked_d"+i] = []
    # for i in range(1, 12):
    #     i = "%02d" % i
    #     F4["cant_catch_kr_d"+i] = [] # cant_catch_kr_dj
    for i in range(1, 12):
        i = "%02d" % i
        F4["master_block_d"+i] = [] # master_block_dj

    # loop through frames
    for idx, row in tqdm(pre_feature_df.iterrows(), desc="Blocking features iteration"):
        defenders = ["d%02d" % d for d in range(1, 12)]
        blockers = ["o%02d" % d for d in range(2, 12)] # minus kr

        # available player arrays to be modified
        defenders_blocked = defenders.copy()
        defenders_behind_kr = defenders.copy()  # defenders who cannot catch kr
        possible_blockers = defaultdict(list)

        for d in defenders:
            d_line = line_coefs(row["x_"+d], row["y_"+d], row["dir_"+d])
            kr_line = line_coefs(row["x_kr"], row["y_kr"], row["dir_kr"])

            intersec_kr_xy = intersection(kr_line, d_line)

            # if intersection exists between kr and defender
            if intersec_kr_xy:
              if not to_intersec_first(kr_line, d_line, intersec_kr_xy, row["s_kr"], row["s_"+d]):
                defenders_behind_kr.remove(d)

            for b in blockers:
              b_line = line_coefs(row["x_"+b], row["y_"+b], row["dir_"+b])
              intersec_blocked_xy = intersection(d_line, b_line)

              # if intersection exists between blocker and defender
              if intersec_blocked_xy:
                if to_intersec_first(d_line, b_line, intersec_blocked_xy, row["s_"+b], row["s_"+d]):
                  possible_blockers[d].append(b)

        # continue for feature dj_is_blocked
        # priority queue to check defenders with fewest possible blockers first (not perfect)
        queue = PriorityQueue()
        for d in defenders_blocked:
            queue.put((len(possible_blockers[d]), d))
        while not queue.empty():
            d = queue.get()[1]
            for b in possible_blockers[d]:
                if b in blockers: # if possible blocker is still available, then remove the match up
                    defenders_blocked.remove(d)
                    blockers.remove(b)
                    break

        # write
        bj = np.array([1 if ("d%02d" % i) in defenders_blocked else 0 for i in range(1, 12)])
        cj = np.array([1 if ("d%02d" % i) in defenders_behind_kr else 0 for i in range(1, 12)])
        aj = cj*(1-bj)  # product of the 2 indicator vars
        # new_row = np.concatenate((bj, cj, aj), axis=None)
        new_row = aj
        F4.loc[idx] = new_row

    return F4

# sample = pre_feature_df.copy()[:200]
# F4 = create_F4(sample)
# F4.head()

##################################################
### Segmented Distance to jth closest defender ###
##################################################

### load Tai's pre-run big feature matrix and isolate the desired variables
Tai = pd.read_csv('drive/My Drive/kaggle/BDB22/Tai_big_matrix.csv')
### relevant columns: all 11 MASTER_BLOCK_DJ columns
Tai = Tai[[col for col in Tai.columns if col.startswith("master_block_")]]

def create_F2(pre_feature_df):
  lambda_1 = 2; lambda_2 = 2;
  F2_data = []
  for j in range(1,12):
    #print(j)
    x_dj = pre_feature_df[f"x_d0{j}" if j < 10 else f"x_d{j}"]
    y_dj = pre_feature_df[f"y_d0{j}" if j < 10 else f"y_d{j}"]
    x_kr = pre_feature_df["x_kr"]
    y_kr = pre_feature_df["y_kr"]
    M_j = Tai[f"master_block_d0{j}" if j < 10 else f"master_block_d{j}"] #FIXME
    # distance
    ##dist = np.sqrt((x_kr - x_dj)**2 + (y_kr - y_dj)**2)
    d = np.sqrt((x_kr - x_dj)**2 + (y_kr - y_dj)**2) #1/( (x_kr - x_dj)**2 + (y_kr - y_dj)**2 )
    x_diff = x_kr - x_dj
    # how x-close is dj to kr
    seg1 = x_diff > lambda_1
    seg2 = np.logical_and(0 < x_diff, x_diff <= lambda_1)
    seg3 = np.logical_and(-lambda_2 < x_diff, x_diff <= 0)
    seg4 = x_diff <= -lambda_2
    # feature: segmented distance
    F2_data.append(seg1*d*M_j)
    F2_data.append(seg1*d*(1-M_j))
    F2_data.append(seg2*d*M_j)
    F2_data.append(seg2*d*(1-M_j))
    F2_data.append(seg3*d*M_j)
    F2_data.append(seg3*d*(1-M_j))
    F2_data.append(seg4*d*M_j)
    F2_data.append(seg4*d*(1-M_j))
    # F2_data.append(seg1*d)
    # F2_data.append(seg2*d)
    # F2_data.append(seg3*d)
    # F2_data.append(seg4*d)

  F2 = pd.concat(F2_data, axis=1)
  del(F2_data)
  # F2.columns = [f"segD{k}_d0{j}" if j < 10 else f"segD{k}_d{j}" for j in range(1,12) for k in range(1,5)]
  F2.columns = [f"segD{k}_d0{j}" if j < 10 else f"segD{k}_d{j}" for j in range(1,12) for k in range(1,9)]
  return(F2)


# F2 = create_F2(pre_feature_df)
# F2

### create and store full feature matrix
def create_feature_matrix(pre_feature_df):
  return pd.concat(
    [create_F1(pre_feature_df), # x_kr
     ############create_F1a(pre_feature_df), # distance to sideline
     create_F3(pre_feature_df), # joey projection feature
     create_F2(pre_feature_df)], # segmented distance (interacted with is_blocked)
     axis=1
  )

# feature_matrix = create_feature_matrix(pre_feature_df)
# feature_matrix.to_csv('drive/My Drive/kaggle/BDB22/feature_matrix.csv', index=False)
# feature_matrix
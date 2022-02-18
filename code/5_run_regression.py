import pandas as pd
import numpy as np

##################
### Load Data ####
##################

### training set: all 2018 & 2019 kick returns
### testing set: all 2020 kick returns
pre_feature_df = pd.read_csv('data/kr_data/pre_feature_df.csv')
g = pre_feature_df[['gameId', 'playId', 'frameId']]
year = np.array([int(str(n)[:4]) for n in g['gameId']])
train_ind = np.logical_or(year == 2018, year == 2019)
g['train'] = train_ind
### check ~2/3 training data
g.query('train').shape[0]/g.shape[0]

### load response column
response = pd.read_csv('data/kr_data/V_response.csv')
V = response['Vf']
V.name='V'

### load feature_matrix
feature_matrix = pd.read_csv('data/kr_data/feature_matrix.csv')

### TRAINING & TESTING MATRICES: dat_train & dat_test
dat = pd.concat([g, V, feature_matrix], axis=1)
dat_train = dat.query('train')
dat_test = dat.query('~train')

#############################
### 1. Linear Regression ####
#############################

### regression formula
def ols_formula(df, dependent_var, *excluded_cols):
    '''
    Generates the R style formula for statsmodels (patsy) given
    the dataframe, dependent variable and optional excluded columns
    as strings
    '''
    df_columns = list(df.columns.values)
    df_columns.remove(dependent_var)
    for col in excluded_cols:
        df_columns.remove(col)
    return dependent_var + ' ~ ' + ' + '.join(df_columns)

formula = ols_formula(dat_train, "V", "gameId", "playId", "frameId", "train")
formula

### take care of inf/na rows
# dat_train.isin([np.inf, -np.inf, np.nan]).values.sum() # number of inf or na values
# dat_train_1 = dat_train[~dat_train.isin([np.nan, np.inf, -np.inf]).any(1)]
# dat_test.isin([np.inf, -np.inf, np.nan]).values.sum() # number of inf or na values
# dat_test_1 = dat_test[~dat_test.isin([np.nan, np.inf, -np.inf]).any(1)]

### Regression: OLS
import statsmodels.formula.api as sm
model_ols = sm.ols(formula=formula, data=dat_train) ## FIXME dat_train_1...
fit = model_ols.fit()
fit.summary()

########################
### Model Selection ####
########################

### out-of-sample model RMSE.
### use as a basis of comparison between models.
def rmse(x,y):
  return np.sqrt(np.mean((x - y)**2))

Vpred_train = fit.predict(dat_train)
Vpred_test = fit.predict(dat_test)
rmse(Vpred_train, dat_train['V'])
rmse(Vpred_test, dat_test['V'])

###########################
### Choose Final Model ####
###########################

def f_hat(dat):
  '''return the Value of each row (frame) of this kick-return dataframe dat'''
  return fit.predict(dat) #FIXME



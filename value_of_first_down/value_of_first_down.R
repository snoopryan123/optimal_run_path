library(tidyverse)
library(splines)
library(xgboost)
theme_set(theme_bw())

library(matrixcalc)
library(cowplot)
library(kableExtra)
library(gt)
library(paletteer)
options(scipen = 50)


# read data
E0 <- read_csv("pbp_yardline_data.csv")

# cleaned dataframe
E <- E0 %>% 
  filter(down==1) %>% # first down only
  filter(!startsWith(ydl,"k")) %>% # no kickoff returns, for now
  mutate(ydl = as.numeric(ydl)) # numeric yardline column

# check no NA problems
#sum(is.na(E$P2)); sum(is.na(E$ydl)); 

##############################
########### PLOTS ############
##############################
LOWER_LIM = 0; UPPER_LIM = 6;

smooth_me <- function(df) {
  v_y = df$v[1:99]
  v_spline = smooth.spline(99:1, v_y)
  rev(v_spline$y)
  temp = tibble(ydl=1:99,v_smoothed=rev(v_spline$y))
  left_join(df,temp)
}

make_plot_non_smoothed <- function(df) {
  df %>% ggplot() +
    geom_point(aes(x=ydl,y=v)) + 
    scale_x_continuous(trans = "reverse", breaks=seq(0,100,10)) +
    scale_y_continuous(limits=c(LOWER_LIM,UPPER_LIM),breaks=seq(-2,8,1)) + 
    xlab("yard line") + 
    ylab("expected points until next score") + 
    labs(title="Value of a first down at each yard line")
}

make_plot_smoothed <- function(df) {
  df %>% ggplot(aes(x=ydl,y=v_smoothed)) +
    geom_line() +
    scale_x_continuous(trans = "reverse", breaks=seq(0,100,10)) +
    scale_y_continuous(limits=c(LOWER_LIM,UPPER_LIM),breaks=seq(-2,8,1)) + 
    xlab("yard line") + 
    ylab("expected points until next score") + 
    labs(title="Value of a first down at each yard line")
}

make_plot_both <- function(df,modelName="") {
  df %>% ggplot() +
    geom_point(aes(x=ydl,y=v)) + 
    geom_line(aes(x=ydl,y=v_smoothed), color="firebrick",size=1) +
    scale_x_continuous(trans = "reverse", breaks=seq(0,100,10)) +
    scale_y_continuous(limits=c(LOWER_LIM,UPPER_LIM), breaks=seq(-2,8,1)) + 
    xlab("yard line z") + 
    ylab("expected points until next score if you have a 1st down") + 
    labs(title=paste0("Value of a first down at each yard line ", modelName))
}

############################################
########### TRAINING/TESTING DATA ##########
############################################

# training matrices
test_yrs = seq(2010,2018,by=2) #c(2010,2013,2015,2018)
train_yrs = setdiff(2010:2019, test_yrs)
E <- E %>% mutate(test = season %in% test_yrs)
E <- E %>% mutate(train1 = !test) 
train_idx = E$train1

############################################
########### AVG. EVERY OCCURRENCE ##########
############################################

avg_ydl = E %>% ##filter(train1) %>%
  group_by(ydl) %>% 
  summarise(v = mean(P2)) %>%
  arrange(ydl)
avg_ydl = smooth_me(avg_ydl)

# make_plot_non_smoothed(avg_ydl)
# make_plot_smoothed(avg_ydl)
avg_ydl_plot = make_plot_both(avg_ydl, modelName="avg_ydl")
avg_ydl_plot

##############################
########### xgBoost ##########
##############################

# E_train = E %>%
#   filter(train1) %>%
#   select(ydl, P2)
# x_train = matrix(E_train$ydl, ncol=1)
# y_train = matrix(E_train$P2, ncol=1)
x_train = matrix(E$ydl, ncol=1)
y_train = matrix(E$P2, ncol=1)

xgb1 <- xgboost(
  data = x_train,
  label = y_train,
  nrounds = 1000,
  objective = "reg:squarederror",
  early_stopping_rounds = 3,
  max_depth = 6,
  eta = .25
)

xgb_v = tibble(ydl=1:99, v=predict(xgb1, matrix(1:99,ncol=1)))
xgb_v = smooth_me(xgb_v)
xgb_plot = make_plot_both(xgb_v, modelName="xgBoost")
xgb_plot

############################################
########### AVG. EVERY OCCURRENCE ##########
########### grouoed by team  ##########
############################################

avg_ydl2 = E %>% ##filter(train1) %>%
  group_by(posteam, ydl) %>% 
  summarise(v = mean(P2)) %>%
  group_by(ydl) %>%
  summarise(v = mean(v)) %>%
  arrange(ydl)
avg_ydl2 = smooth_me(avg_ydl2)

avg_ydl_plot2 = make_plot_both(avg_ydl2, modelName="avg_ydl2")
avg_ydl_plot2

cowplot::plot_grid(avg_ydl_plot,avg_ydl_plot2)

############################################
### randomly sample 1 per drive (chunk) ####
############################################

sample_1_per_drive = E %>% ##filter(train1) %>%
  group_by(chunk) %>%
  slice_sample(n=1) %>%
  ungroup() %>%
  group_by(ydl) %>% 
  summarise(v = mean(P2)) %>%
  arrange(ydl)
sample_1_per_drive = smooth_me(sample_1_per_drive)

sample_1_per_drive_plot = make_plot_both(sample_1_per_drive, modelName="sample_1_per_drive_plot")
sample_1_per_drive_plot

############################################
### randomly sample 4 per drive (chunk) ####
############################################

sample_4_per_drive = E %>% ##filter(train1) %>%
  group_by(chunk) %>%
  slice_sample(n=4) %>%
  ungroup() %>%
  group_by(ydl) %>% 
  summarise(v = mean(P2)) %>%
  arrange(ydl)
sample_4_per_drive = smooth_me(sample_4_per_drive)

sample_4_per_drive_plot = make_plot_both(sample_4_per_drive, modelName="sample_4_per_drive_plot")
sample_4_per_drive_plot

####################################
### randomly sample 20% of rows ####
####################################

sample_rand_rows = E %>% ##filter(train1) %>%
  slice_sample(n=floor(0.2 * nrow(E))) %>%
  group_by(ydl) %>% 
  summarise(v = mean(P2)) %>%
  arrange(ydl)
sample_rand_rows = smooth_me(sample_rand_rows)

sample_rand_rows_plot = make_plot_both(sample_rand_rows, modelName="sample_rand_rows")
sample_rand_rows_plot

####################################
######## plot comparison ###########
####################################

cowplot::plot_grid(avg_ydl_plot,avg_ydl_plot2,
                   sample_1_per_drive_plot,sample_4_per_drive_plot,
                   sample_rand_rows_plot, xgb_plot)

#############################################
### final selection: VALUE OF A YARD LINE ###
#############################################

FINAL_V_DF = avg_ydl #FIXME
FINAL_V_PLOT = make_plot_both(FINAL_V_DF, modelName="")
FINAL_V_PLOT
FINAL_V_DF = FINAL_V_DF %>% mutate(x = 120 - (ydl + 10))
# View(FINAL_V_DF)

cowplot::save_plot("value_of_first_down_plot.png", FINAL_V_PLOT, base_width = 8, base_height = 8)
write_csv(FINAL_V_DF, "value_of_first_down_df.csv")

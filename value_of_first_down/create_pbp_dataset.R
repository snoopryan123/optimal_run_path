library(tidyverse)

###### read data
pbp <- nflfastR::load_pbp(2010:2019)

###### select relevant columns
E <- pbp %>% select(game_id, game_date, season, season_type, desc,
                    home_team, away_team, total_home_score, total_away_score,
                    drive, posteam, defteam, posteam_score, defteam_score, posteam_score_post, defteam_score_post,
                    touchdown, field_goal_attempt, field_goal_result, safety,
                    extra_point_attempt, two_point_attempt, extra_point_result, two_point_conv_result,
                    #defensive_extra_point_attempt, defensive_two_point_attempt, defensive_extra_point_conv, defensive_two_point_conv,
                    yardline_100, yrdln, ydstogo, yards_gained, down, goal_to_go, qtr,
                    kickoff_attempt, punt_attempt,
                    game_seconds_remaining,posteam
                    )
rm(pbp)

#########################################
########### CLEAN THE DATASET ###########
#########################################

#View(E %>% filter(game_id == "2015_01_BAL_DEN"))

# remove rows with NA in certain columns
E1 <- E %>% drop_na(posteam_score_post, defteam_score_post, yardline_100)

###### create P
E2 <- E1 %>% 
  mutate(
    H = home_team == posteam,
  ) %>% 
  relocate(H, .after = total_away_score) %>%
  group_by(game_id) %>%
  mutate(
    home_score_diff = total_home_score - lag(total_home_score, default=0),
    away_score_diff = total_away_score - lag(total_away_score, default=0),
    after_td_play = replace_na(extra_point_attempt | two_point_attempt, FALSE), # replace NA's with False...
    home_score_diff = if_else(
      lead(after_td_play, default=FALSE),
      home_score_diff + lead(home_score_diff, default=0),
      home_score_diff
    ),
    away_score_diff = ifelse(
      lead(after_td_play, default=FALSE),
      away_score_diff + lead(away_score_diff, default=0),
      away_score_diff
    ),
    P = case_when(
      H ~ home_score_diff - away_score_diff,
      !H ~ away_score_diff - home_score_diff,
    ),
  ) %>%
  ungroup() %>%
  relocate(home_score_diff, .after = total_away_score) %>%
  relocate(away_score_diff, .after = home_score_diff) %>%
  relocate(after_td_play, .after = away_score_diff) %>%
  relocate(P, .after = total_away_score) %>%
  filter(!after_td_play) # ignore after_td_play !!!
#View(E2 %>% filter(game_id == "2019_01_TEN_CLE"))
#View(E2 %>% filter(game_id == "2010_01_MIN_NO"))


#View(E2 %>% filter(game_id == "2015_01_GB_CHI", H))
#View(E2 %>% filter(game_id == "2015_01_GB_CHI"))
#View(E2 %>% filter(game_id == "2015_01_BAL_DEN", H))
#View(E2 %>% filter(game_id == "2015_01_BAL_DEN", drive==18 | drive == 19))
#View(E2 %>% filter(game_id == "2015_01_BAL_DEN"))

###### YDL yardline (+ kickoff yardline)
E3 <- E2 %>% 
  relocate(desc, .before = yardline_100)  %>%
  mutate(kickoff_attempt = replace_na(kickoff_attempt, 0)) %>% # replace NA with 0...
  mutate(ydl = ifelse(
    !kickoff_attempt,
    yardline_100,
    ifelse(yardline_100 >= 35, "k>=35", "k<35")
  )) %>%
  relocate(ydl, .before = yardline_100) 
#View(E3 %>% filter(game_id == "2019_01_TEN_CLE"))
#View(E3 %>% filter(game_id == "2010_01_CLE_TB"))
sum(is.na(E3$ydl))

###### turnover B, not-score S, chunk is a drive, chunk_bool is end-of-chunk(drive)
E4 <- E3 %>%
  relocate(desc, .before = H)  %>%
  group_by(game_id) %>%
  mutate(B = ifelse(H == lead(H), 1, -1),
         B = replace_na(B,0)) %>% # replace NA with 0...
  ungroup() %>%
  relocate(B, .after = H) %>%
  mutate(S = as.numeric(!P)) %>%
  relocate(S, .after = B) %>%
  mutate(chunk_bool = replace_na(as.numeric(S == 0 | B == -1),0)) %>%
  relocate(chunk_bool, .after = S) %>%
  mutate(chunk = lag(cumsum(chunk_bool), default=0)) %>%
  relocate(chunk, .after = chunk_bool) %>%
  relocate(qtr, .after = chunk)
#View(E4 %>% filter(game_id == "2019_01_TEN_CLE"))
#View(E4 %>% filter(game_id == "2010_01_ATL_PIT"))



##### create P2 = value of next score
E4a <- E4 %>% group_by(chunk) %>% mutate(P2 = P[n()]) %>% ungroup() 
#View(E4a %>% select(chunk, P, P2))

##### keep all first down plays only!
# E5a <- E4a %>% filter(down == 1)

# ##### keep full qtr's 1 & 3, first chunk of qtr 2 & 4 so as to not cut drives off
E5 <- E4a %>%
  group_by(game_id, qtr) %>%
  slice_head() %>%
  select(game_id, qtr, chunk) %>%
  rename(first_chunk_of_qtr = chunk) %>%
  right_join(E4a) %>%
  relocate(qtr, .after = chunk) %>%
  relocate(first_chunk_of_qtr, .after = qtr) %>%
  mutate(first_chunk_of_qtr = as.numeric(first_chunk_of_qtr == chunk)) %>%
  relocate(P, .after = S) %>%
  relocate(P2, .after = P)
#View(E5 %>% filter(game_id == "2019_01_TEN_CLE"))
E5a <- E5 %>%
  group_by(game_id, qtr) %>%
  filter( (qtr %% 2 == 1) | first_chunk_of_qtr ) %>%
  ungroup()

#View(E5a[!complete.cases(E5a$B),])
#sum(is.na(E5a$B)); sum(is.na(E5a$S)); sum(is.na(E5a$P)); sum(is.na(E5a$P2)); sum(is.na(E5a$ydl)); 

### select relevant columns
E6 = E5a %>% select(
  game_id, game_date, season,
  posteam, chunk, chunk_bool, P2, ydl,
  ydstogo,down,goal_to_go,game_seconds_remaining,kickoff_attempt
)

write_csv(E6, "pbp_yardline_data.csv")



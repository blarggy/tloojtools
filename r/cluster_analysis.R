set.seed(123)
source("r/packages.R")
purrr::walk(packages, library, character.only = TRUE, warn.conflicts = FALSE)
options(max.print = 1000000)
remove(packages)

database <- read.csv("data/test_new_scoring.json_as_csv.csv")
database <- database[!database$Week == "null",]

get_column_names <- function(position) {
  rb_wr_te_columns <- c("player_name", "display_name", "team_name", "position", "sleeper_player_id",
                        "height", "weight", "G.", "Off..Snaps_Num", "Off..Snaps_Pct", "Receiving_Tgt",
                        "Receiving_Rec", "Receiving_Yds", "Receiving_Y.R", "Receiving_TD",
                        "Receiving_Ctch.", "Receiving_Y.Tgt", "Scoring_2PM", "Scoring_TD",
                        "Scoring_Pts", "Fumbles_Fmb", "Fumbles_FL", "Rushing_Att", "Rushing_Yds",
                        "Rushing_Y.A", "Rushing_TD", "Passing_Cmp", "fantasy_points")

  qb_columns <- c("player_name", "display_name", "team_name", "position", "sleeper_player_id",
                  "height", "weight", "G.", "Off..Snaps_Num", "Off..Snaps_Pct", "Scoring_2PM",
                  "Scoring_TD", "Scoring_Pts", "Fumbles_Fmb", "Fumbles_FL", "Rushing_Att",
                  "Rushing_Yds", "Rushing_Y.A", "Rushing_TD", "Passing_Cmp", "Passing_Att",
                  "Passing_Cmp.", "Passing_Yds", "Passing_TD", "Passing_Int", "Passing_Rate",
                  "Passing_Sk", "Passing_Yds.1", "Passing_Y.A", "Passing_AY.A", "fantasy_points")

  db_lb_dl_columns <- c("player_name", "display_name", "team_name", "position", "sleeper_player_id",
                        "height", "weight", "G.", "Def..Snaps_Num", "Def..Snaps_Pct", "Scoring_Pts",
                        "Fumbles_Fmb", "Fumbles_FL", "Fumbles_FF", "Fumbles_FR", "Fumbles_Yds",
                        "Fumbles_TD", "fantasy_points", "Sk", "Tackles_Solo", "Tackles_Ast",
                        "Tackles_Comb", "Tackles_TFL", "Tackles_QBHits", "Def.Interceptions_Int",
                        "Def.Interceptions_Yds", "Def.Interceptions_TD", "Def.Interceptions_PD",
                        "Scoring_Sfty")

  if (position %in% c("RB", "WR", "TE")) {
    return(rb_wr_te_columns)
  } else if (position == "QB") {
    return(qb_columns)
  } else if (position %in% c("DB", "LB", "DL")) {
    return(db_lb_dl_columns)
  } else {
    stop("Invalid position")
  }
}

clean_data <- function(database, position, columns, snap_pct_col, catch_pct_col = NULL) {
    if (position == "DL") {
    data <- database[database$position %in% c("DL", "DE", "LB DL"), ]
  } else if (position == "DB") {
    data <- database[database$position %in% c("DB", "LB DB"), ]
  } else if (position == "TE") {
    data <- database[database$position %in% c("TE", "TE QB"), ]
  } else {
    data <- database[database$position == position, ]
  }
  data <- data[, columns]
  data[is.na(data)] <- 0
  data[data == "null"] <- 0
  data[data == "Inactive"] <- NA
  data[data == "Did Not Play"] <- NA
  colnames(data)[8] <- "game"

  if (nrow(data) > 0 && snap_pct_col %in% colnames(data)) {
    data[[snap_pct_col]] <- gsub("%", "", data[[snap_pct_col]])
    data[[snap_pct_col]] <- as.numeric(data[[snap_pct_col]]) / 100
  }

  if (!is.null(catch_pct_col) && catch_pct_col %in% colnames(data)) {
    data[[catch_pct_col]] <- gsub("%", "", data[[catch_pct_col]])
    data[[catch_pct_col]] <- as.numeric(data[[catch_pct_col]]) / 100
  }
  # select the 6th column onwards and convert to numeric
  data[, 6:length(data)] <- lapply(data[, 6:length(data)], as.numeric)
  data <- data[!data$game == 0,]
  data <- data[]
  return(data)
}

summarize_data <- function(data, position) {
  if (position %in% c("QB")) {
    data <- data %>%
      group_by(sleeper_player_id) %>%
      reframe(
        ID = max(sleeper_player_id, na.rm = TRUE),
        playerName = max(player_name, na.rm = TRUE),
        human = max(display_name, na.rm = TRUE),
        team = max(team_name, na.rm = TRUE),
        totalSnaps = sum(Off..Snaps_Num, na.rm = TRUE),
        avgSnaps = mean(Off..Snaps_Num, na.rm = TRUE),
        avgSapsPct = mean(Off..Snaps_Pct, na.rm = TRUE),
        weight = max(weight, na.rm = TRUE),
        height = max(height, na.rm = TRUE),
        totalFP = sum(fantasy_points, na.rm = TRUE),
        totalFumble = sum(Fumbles_Fmb, na.rm = TRUE),
        avgFumble = mean(Fumbles_Fmb, na.rm = TRUE),
        totalFumbleTO = sum(Fumbles_FL, na.rm = TRUE),
        avgFumbleTO = mean(Fumbles_FL, na.rm = TRUE),
        totalRushingAtt = sum(Rushing_Att, na.rm = TRUE),
        avgRushingAtt = mean(Rushing_Att, na.rm = TRUE),
        totalRushingYds = sum(Rushing_Yds, na.rm = TRUE),
        avgRushingYds = mean(Rushing_Yds, na.rm = TRUE),
        totalRushingTd = sum(Rushing_TD, na.rm = TRUE),
        avgRushingTd = mean(Rushing_TD, na.rm = TRUE),
        avgRushingYA = mean(Rushing_Y.A, na.rm = TRUE),
        totalPasses = sum(Passing_Cmp, na.rm = TRUE),
        avgPasses = mean(Passing_Cmp, na.rm = TRUE),
        totalPassAtt = sum(Passing_Att, na.rm = TRUE),
        avgPassAtt = mean(Passing_Att, na.rm = TRUE),
        avgCompPct = mean(Passing_Cmp., na.rm = TRUE),
        totalPassYds = sum(Passing_Yds, na.rm = TRUE),
        avgPassYds = mean(Passing_Yds, na.rm = TRUE),
        totalPassingTd = sum(Passing_TD, na.rm = TRUE),
        avgPassingTd = mean(Passing_TD, na.rm = TRUE),
        totalPassingInt = sum(Passing_Int, na.rm = TRUE),
        avgPassingInt = mean(Passing_Int, na.rm = TRUE),
        avg = mean(Passing_Rate, na.rm = TRUE),
        avgsackedPct = mean(Passing_Sk, na.rm = TRUE),
        avgAdjAYdsAtt = mean(Passing_AY.A, na.rm = TRUE)
      )
  } else if (position %in% c("TE", "WR", "RB")) {
    data <- data %>%
      group_by(sleeper_player_id) %>%
      reframe(
        ID = max(sleeper_player_id, na.rm = TRUE),
        playerName = max(player_name, na.rm = TRUE),
        human = max(display_name, na.rm = TRUE),
        team = max(team_name, na.rm = TRUE),
        totalSnaps = sum(Off..Snaps_Num, na.rm = TRUE),
        avgSnaps = mean(Off..Snaps_Num, na.rm = TRUE),
        avgSapsPct = mean(Off..Snaps_Pct, na.rm = TRUE),
        weight = max(weight, na.rm = TRUE),
        height = max(height, na.rm = TRUE),
        totalFP = sum(fantasy_points, na.rm = TRUE),
        totalTargets = sum(Receiving_Tgt, na.rm = TRUE),
        avgTargets = mean(Receiving_Tgt, na.rm = TRUE),
        totalReceptions = sum(Receiving_Rec, na.rm = TRUE),
        avgReceptions = mean(Receiving_Rec, na.rm = TRUE),
        totalYards = sum(Receiving_Yds, na.rm = TRUE),
        avgYards = mean(Receiving_Yds, na.rm = TRUE),
        `avgY/R` = mean(Receiving_Y.R, na.rm = TRUE),
        totalPts = sum(Scoring_Pts, na.rm = TRUE),
        avgCatchPct = mean(Receiving_Ctch., na.rm = TRUE),
        `avgY/Tgt` = mean(Receiving_Y.Tgt, na.rm = TRUE),
        totalFl = sum(Fumbles_FL, na.rm = TRUE),
        avgRushingAtt = mean(Rushing_Att, na.rm = TRUE),
        totalRushingYds = sum(Rushing_Yds, na.rm = TRUE),
        avgRushingYds = mean(Rushing_Yds, na.rm = TRUE),
        avgRushingYA = mean(Rushing_Y.A, na.rm = TRUE)
      )
  } else if (position %in% c("DL", "LB", "DB")) {
    data <- data %>%
      group_by(sleeper_player_id) %>%
      reframe(
        ID = max(sleeper_player_id, na.rm = TRUE),
        playerName = max(player_name, na.rm = TRUE),
        human = max(display_name, na.rm = TRUE),
        team = max(team_name, na.rm = TRUE),
        totalSnaps = sum(Def..Snaps_Num, na.rm = TRUE),
        avgSnaps = mean(Def..Snaps_Num, na.rm = TRUE),
        avgSapsPct = mean(Def..Snaps_Pct, na.rm = TRUE),
        weight = max(weight, na.rm = TRUE),
        height = max(height, na.rm = TRUE),
        totalFP = sum(fantasy_points, na.rm = TRUE),
        totalSacks = sum(Sk, na.rm = TRUE),
        totalTFL = sum(Tackles_TFL, na.rm = TRUE),
        totalQbHit = sum(Tackles_QBHits, na.rm = TRUE),
        totalFF = sum(Fumbles_FF, na.rm = TRUE),
        totalFR = sum(Fumbles_FR, na.rm = TRUE),
        totalYds = sum(Fumbles_Yds, na.rm = TRUE),
        totalFTd = sum(Fumbles_TD, na.rm = TRUE),
        totalTackSolo = sum(Tackles_Solo, na.rm = TRUE),
        avgTackSolo = mean(Tackles_Solo, na.rm = TRUE),
        totalTackAst = sum(Tackles_Ast, na.rm = TRUE),
        avgTackAst = mean(Tackles_Ast, na.rm = TRUE),
        totalInt = sum(Def.Interceptions_Int, na.rm = TRUE),
        totalIntYds = sum(Def.Interceptions_Yds, na.rm = TRUE),
        totalTd = sum(Def.Interceptions_TD, na.rm = TRUE),
        totalPd = sum(Def.Interceptions_PD, na.rm = TRUE),
        totalSaf = sum(Scoring_Sfty, na.rm = TRUE)
      )
  }

  return(data)
}

perform_clustering <- function(data, num_clusters) {
  data_ <- data[, 6:length(data)]
  # methodtest <- function(x) { agnes(data_, method = x)$ac }
  # m <- c("average", "single", "complete", "ward")
  # map_dbl(m, methodtest)
  clust <- agnes(data_, method = "ward")
  subgrp <- cutree(clust, k = num_clusters)
  data <- data %>% mutate(cluster = subgrp)
  # pltree(clust, cex = 0.6, hang = -1, main = paste("Dendrogram of", position, "s"), labels = data$playerName)
  # rect.hclust(clust, k = num_clusters, border = 2:5)
  # fviz_nbclust(data, FUN = hcut, method = "wss")
  # fviz_nbclust(data, FUN = hcut, method = "silhouette")

  return(data)
}

plot_data <- function(data, title) {
  plot <- ggplot(data, aes(x = totalFP, y = avgSnaps, color = factor(index))) +
    geom_smooth(method = "lm", se = TRUE, linetype = "dashed", color = "black") +
    theme_minimal() +
    labs(
      title = title,
      x = "Fantasy Points",
      y = "Average Snaps",
      color = "Clusters"
    ) +
    theme(
      panel.grid.major = element_line(color = "grey80"),
      panel.grid.minor = element_line(color = "grey90"),
      plot.title = element_text(hjust = 0.5)
    ) +
    geom_text_repel(size = 4, label = data$playerName) +
    scale_color_discrete()
  return(plot)
}

snap_pct_col <- "Off..Snaps_Pct"
def_snap_pct_col <- "Def..Snaps_Pct"
receiving_ctch_col <- "Receiving_Ctch."
passing_cmp_col <- "Passing_Cmp."

# Process each position group
positions <- list(
  list(position = "WR", columns = get_column_names("WR"), snap_pct_col = snap_pct_col, catch_pct_col = receiving_ctch_col, num_clusters = 4),
  list(position = "RB", columns = get_column_names("RB"), snap_pct_col = snap_pct_col, catch_pct_col = receiving_ctch_col, num_clusters = 5),
  list(position = "QB", columns = get_column_names("QB"), snap_pct_col = snap_pct_col, catch_pct_col = passing_cmp_col, num_clusters = 5),
  list(position = "TE", columns = get_column_names("TE"), snap_pct_col = snap_pct_col, catch_pct_col = receiving_ctch_col, num_clusters = 4),
  list(position = "DL", columns = get_column_names("DL"), snap_pct_col = def_snap_pct_col, num_clusters = 4),
  list(position = "LB", columns = get_column_names("LB"), snap_pct_col = def_snap_pct_col, num_clusters = 4),
  list(position = "DB", columns = get_column_names("DB"), snap_pct_col = def_snap_pct_col, num_clusters = 6)
)

plots <- list()
for (pos in positions) {
  data <- clean_data(database, pos$position, pos$columns, pos$snap_pct_col, pos$catch_pct_col)
  data <- summarize_data(data, pos$position)
  clustering_result <- perform_clustering(data, pos$num_clusters)
  data_out <- clustering_result%>%select(playerName,avgSnaps,totalFP,cluster)

  if (pos$position=="WR")
    data_out$index<-ifelse(data_out$cluster==2,1,ifelse(data_out$cluster==2,2,ifelse(data_out$cluster==3,2,data_out$cluster)))
  if (pos$position=="QB")
    data_out$index<-ifelse(data_out$cluster==2,1,ifelse(data_out$cluster==1,5,ifelse(data_out$cluster==5,4,ifelse(data_out$cluster==4,2,data_out$cluster))))
  if (pos$position=="RB")
    data_out$index<-ifelse(data_out$cluster==4,1,ifelse(data_out$cluster==1,2,ifelse(data_out$cluster==2,3,ifelse(data_out$cluster==3,5,ifelse(data_out$cluster==5,4,data_out$cluster)))))
  if (pos$position=="TE")
    data_out$index<-ifelse(data_out$cluster==1,3,ifelse(data_out$cluster==3,2,ifelse(data_out$cluster==2,1,data_out$cluster)))
  if (pos$position=="DL")
    data_out$index<-ifelse(data_out$cluster==1,3,ifelse(data_out$cluster==3,4,ifelse(data_out$cluster==4,2,ifelse(data_out$cluster==2,1,data_out$cluster))))
  if (pos$position=="LB")
    data_out$index <- ifelse(data_out$cluster == 3,4, ifelse(data_out$cluster == 4,3,data_out$cluster))
  if (pos$position=="DB")
    data_out$index <- ifelse(data_out$cluster == 5,6, ifelse(data_out$cluster == 6,5,data_out$cluster))

  plot <- plot_data(data_out, paste(pos$position, "Cluster Analysis"))
  plots[[pos$position]] <- plot

  # for debugging
  file_path <- "data/cluster_output.csv"
  if (file.exists(file_path)) {
    existing_data <- read.csv(file_path)
    combined_data <- rbind(existing_data, data_out)
    write.csv(combined_data, file_path, row.names = FALSE)
  } else {
    write.csv(data_out, file_path, row.names = FALSE)
  }
}

# Save plots
ggsave("data/WR_Cluster.svg", plot = plots$WR, device = "svg", width = 22, height = 13)
ggsave("data/RB_Cluster.svg", plot = plots$RB, device = "svg", width = 22, height = 13)
ggsave("data/QB_Cluster.svg", plot = plots$QB, device = "svg", width = 22, height = 13)
ggsave("data/TE_Cluster.svg", plot = plots$TE, device = "svg", width = 22, height = 13)
ggsave("data/DL_Cluster.svg", plot = plots$DL, device = "svg", width = 22, height = 13)
ggsave("data/DB_Cluster.svg", plot = plots$DB, device = "svg", width = 22, height = 13)
ggsave("data/LB_Cluster.svg", plot = plots$LB, device = "svg", width = 22, height = 13)
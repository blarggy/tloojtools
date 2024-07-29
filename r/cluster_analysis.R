set.seed(123)
source("r/packages.R")
purrr::walk(packages, library, character.only = TRUE, warn.conflicts = FALSE)
options(max.print = 1000000)
remove(packages)

database <- read.csv("data/test_new_scoring.json_as_csv.csv")
database <- database[!database$Week == "null",]

clean_data <- function(database, position, columns, snap_pct_col, catch_pct_col = NULL) {
  # if (position == "DL") {
  #   data <- database[database$position|database$position == "DE"|database$position == "LB DL",]
  # } else if (position == "DB") {
  #   data <- database[database$position|database$position == "LB DB",]
  # }
  #   else if (position == "TE") {
  #   data <- database[database$position|database$position == "TE QB",]
  # }
  #   else {
  #   data <- database[database$position == position,]
  # }
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
  return(data)
}

summarize_data <- function(data, position) {
  data <- data %>%
    group_by(sleeper_player_id) %>%
    summarize(
      ID = max(sleeper_player_id, na.rm = TRUE),
      playerName = max(player_name, na.rm = TRUE),
      human = max(display_name, na.rm = TRUE),
      team = max(team_name, na.rm = TRUE),
      totalSnaps = sum(ifelse(position %in% c("QB", "TE", "TE QB", "RB", "WR"), Off..Snaps_Num, Def..Snaps_Num), na.rm = TRUE),
      avgSnaps = mean(ifelse(position %in% c("QB", "TE", "TE QB", "RB", "WR"), Off..Snaps_Num, Def..Snaps_Num), na.rm = TRUE),
      avgSapsPct = mean(ifelse(position %in% c("QB", "TE", "TE QB", "RB", "WR"), Off..Snaps_Pct, Def..Snaps_Pct), na.rm = TRUE),
      weight = max(weight, na.rm = TRUE),
      height = max(height, na.rm = TRUE),
      totalFP = sum(fantasy_points, na.rm = TRUE)
    )
  return(data)
}

perform_clustering <- function(data, num_clusters, position) {
  data_ <- data[, 6:length(data)]
  methodtest <- function(x) { agnes(data_, method = x)$ac }
  m <- c("average", "single", "complete", "ward")
  map_dbl(m, methodtest)
  clust <- agnes(data_, method = "ward")
  subgrp <- cutree(clust, k = num_clusters)
  data <- data %>% mutate(cluster = subgrp)
  pltree(clust, cex = 0.6, hang = -1, main = paste("Dendrogram of", position, "s"), labels = data$playerName)
  rect.hclust(clust, k = num_clusters, border = 2:5)
  fviz_nbclust(data, FUN = hcut, method = "wss")
  fviz_nbclust(data, FUN = hcut, method = "silhouette")

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
  list(position = "WR", columns = c(1:7, 10, 18, 19, 25:31, 36:38, 40, 45), snap_pct_col = snap_pct_col, catch_pct_col = receiving_ctch_col, num_clusters = 4),
  list(position = "RB", columns = c(1:7, 10, 18, 19, 25:31, 36:40, 56:60, 45), snap_pct_col = snap_pct_col, catch_pct_col = receiving_ctch_col, num_clusters = 5),
  list(position = "QB", columns = c(1:7, 10, 18, 19, 36:40, 56:70, 45), snap_pct_col = snap_pct_col, catch_pct_col = passing_cmp_col, num_clusters = 5),
  list(position = "TE", columns = c(1:7, 10, 18, 19, 25:31, 36:40, 45), snap_pct_col = snap_pct_col, catch_pct_col = receiving_ctch_col, num_clusters = 4),
  list(position = "DL", columns = c(1:7, 10, 20, 21, 38:55, 75), snap_pct_col = def_snap_pct_col, num_clusters = 4),
  list(position = "LB", columns = c(1:7, 10, 20, 21, 38:55, 75), snap_pct_col = def_snap_pct_col, num_clusters = 4),
  list(position = "DB", columns = c(1:7, 10, 20, 21, 38:55, 75), snap_pct_col = def_snap_pct_col, num_clusters = 6)
)

plots <- list()
for (pos in positions) {
  data <- clean_data(database, pos$position, pos$columns, pos$snap_pct_col, pos$catch_pct_col)
  data <- summarize_data(data, pos$position)
  clustering_result <- perform_clustering(data, pos$num_clusters, pos$position)
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
  # print(data_out)
  plot <- plot_data(data_out, paste(pos$position, "Cluster Analysis"))
  plots[[pos$position]] <- plot
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
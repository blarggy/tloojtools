set.seed(123)
packages<-c("tidyverse","haven","purrr","psych","jsonlite","foreign","sas7bdat","ggplot2","lubridate","psych",
            "openxlsx","odbc","DBI","nflverse","cluster","factoextra","dendextend","colorspace","ggrepel","svglite")
purrr::walk(packages,library,character.only=T,warn.conflicts=F)
remove(packages)
options(max.print=1000000)

test<-read.csv("C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/use.csv")
test<-test[!test$Week=="null",]
m<-c("average","single","complete","ward")

#defensive backs
db<-test[test$position=="DB"|test$position=="LB DB",]
db<-db[,c(1:7,10,20,21,38:55,75)]
db[is.na(db)]<-0
db[db=="null"]<-0
db[db=="Inactive"]<-NA
db[db=="Did Not Play"]<-NA
colnames(db)[19]<-"sacks"
colnames(db)[8]<-"game"
db$Def..Snaps_Pct<-gsub("%","",db$Def..Snaps_Pct)
db[,c(6:length(db))]<-lapply(db[,c(6:length(db))], as.numeric)
db$Def..Snaps_Pct<-db$Def..Snaps_Pct/100
db<-db[!db$game==0,]
#db<-na.omit(db)

db<-db%>%
  group_by(sleeper_player_id)%>%
  reframe(ID=max(sleeper_player_id),
          playerName=max(player_name),
          human=max(display_name),
          team=max(team_name),
          totalSnaps=sum(Def..Snaps_Num,na.rm = T),
          avgSnaps=mean(Def..Snaps_Num,na.rm = T),
          avgSapsPct=mean(Def..Snaps_Pct,na.rm = T),
          totalSacks=sum(sacks,na.rm = T),
          totalTFL=sum(Tackles_TFL,na.rm = T),
          totalQbHit=sum(Tackles_QBHits,na.rm = T),
          totalFF=sum(Fumbles_FF,na.rm = T),
          totalFR=sum(Fumbles_FR,na.rm = T),
          totalYds=sum(Fumbles_Yds,na.rm = T),
          totalFTd=sum(Fumbles_TD,na.rm = T),
          totalTackSolo=sum(Tackles_Solo,na.rm = T),
          avgTackSolo=mean(Tackles_Solo,na.rm = T),
          totalTackAst=sum(Tackles_Ast,na.rm = T),
          avgTackAst=mean(Tackles_Ast,na.rm = T),
          totalInt=sum(Def.Interceptions_Int,na.rm = T),
          totalIntYds=sum(Def.Interceptions_Yds,na.rm = T),
          totalTd=sum(Def.Interceptions_TD,na.rm = T),
          totalPd=sum(Def.Interceptions_PD,na.rm = T),
          totalSaf=sum(Scoring_Sfty,na.rm = T),
          totalpoints=sum(Scoring_Pts,na.rm = T),
          weight=max(weight),
          height=max(height),
          totalFP=sum(fantasy_points,na.rm = T)
  )
db1<-db[,c(6:27)]

m<-c("average","single","complete","ward")
#solo and assisted tackles
methodtest<-function(x) {agnes(db1,method=x)$ac}
map_dbl(m,methodtest)
clustDB<-agnes(db1,method="ward")
subgrpDB<-cutree(clustDB,k=6)
db<-db%>%mutate(cluster=subgrpDB)
pltree(clustDB,cex=0.6,hang=-1,main="Dendrogram of DBs",labels = db$playerName)
rect.hclust(clustDB, k = 6, border = 2:5)
fviz_nbclust(db,FUN=hcut,method="wss")
fviz_nbclust(db,FUN=hcut,method="silhouette")

#Wide Receiver
wr<-test[test$position=="WR",]
wr<-wr[,c(1:7,10,18,19,25:31,36:38,40,45)]
wr[is.na(wr)]<-0
wr[wr=="null"]<-0
wr[wr=="Inactive"]<-NA
wr[wr=="Did Not Play"]<-NA
colnames(wr)[8]<-"game"
wr$Off..Snaps_Pct<-gsub("%","",wr$Off..Snaps_Pct)
wr$Receiving_Ctch.<-gsub("%","",wr$Receiving_Ctch.)
wr[,c(6:length(wr))]<-lapply(wr[,c(6:length(wr))], as.numeric)
wr$Off..Snaps_Pct<-wr$Off..Snaps_Pct/100
wr$Receiving_Ctch.<-wr$Receiving_Ctch./100
wr<-wr[!wr$game==0,]
#wr<-na.omit(wr)

wr<-wr%>%
  group_by(sleeper_player_id)%>%
  reframe(ID=max(sleeper_player_id,na.rm = T),
          playerName=max(player_name,na.rm = T),
          human=max(display_name,na.rm = T),
          team=max(team_name,na.rm = T),
          totalSnaps=sum(Off..Snaps_Num,na.rm = T),
          avgSnaps=mean(Off..Snaps_Num,na.rm = T),
          avgSapsPct=mean(Off..Snaps_Pct,na.rm = T),
          totalTargets=sum(Receiving_Tgt,na.rm = T),
          avgTargets=mean(Receiving_Tgt,na.rm = T),
          totalReceptions=sum(Receiving_Rec,na.rm = T),
          avgReceptions=mean(Receiving_Rec,na.rm = T),
          totalYards=sum(Receiving_Yds,na.rm = T),
          avgYards=mean(Receiving_Yds,na.rm = T),
          `avgY/R`=mean(Receiving_Y.R,na.rm = T),
          totalPts=sum(Scoring_Pts,na.rm = T),
          avgCatchPct=mean(Receiving_Ctch.,na.rm = T),
          `avgY/Tgt`=mean(Receiving_Y.Tgt,na.rm = T),
          totalFl=sum(Fumbles_FL,na.rm = T),
          weight=max(weight),
          height=max(height),
          totalFP=sum(fantasy_points)
  )
wr1<-wr[,c(6:21)]
methodtest<-function(x) {agnes(wr1,method=x)$ac}
map_dbl(m,methodtest)
clustwr<- agnes(wr1,method="ward")
subgrpwr<-cutree(clustwr,k=4)
wr<-wr%>%mutate(cluster=subgrpwr)
pltree(clustwr,cex=0.6,hang=-1,main="Dendrogram of wrs",labels = wr$playerName)
rect.hclust(clustwr, k = 4, border = 2:5)
fviz_nbclust(wr,FUN=hcut,method="wss")
fviz_nbclust(wr,FUN=hcut,method="silhouette")

#Tight Ends
te<-test[test$position=="TE"|test$position=="TE QB",]
te<-te[,c(1:7,10,18,19,25:31,36:40,45)]
te[is.na(te)]<-0
te[te=="null"]<-0
te[te=="Inactive"]<-NA
te[te=="Did Not Play"]<-NA
colnames(te)[8]<-"game"
te$Off..Snaps_Pct<-gsub("%","",te$Off..Snaps_Pct)
te$Receiving_Ctch.<-gsub("%","",te$Receiving_Ctch.)
te[,c(6:length(te))]<-lapply(te[,c(6:length(te))], as.numeric)
te$Off..Snaps_Pct<-te$Off..Snaps_Pct/100
te$Receiving_Ctch.<-te$Receiving_Ctch./100
te<-te[!te$game==0,]
#te<-na.omit(te)

te<-te%>%
  group_by(sleeper_player_id)%>%
  reframe(ID=max(sleeper_player_id,na.rm = T),
          playerName=max(player_name,na.rm = T),
          human=max(display_name,na.rm = T),
          team=max(team_name,na.rm = T),
          totalSnaps=sum(Off..Snaps_Num,na.rm = T),
          avgSnaps=mean(Off..Snaps_Num,na.rm = T),
          avgSapsPct=mean(Off..Snaps_Pct,na.rm = T),
          totalTargets=sum(Receiving_Tgt,na.rm = T),
          avgTargets=mean(Receiving_Tgt,na.rm = T),
          totalReceptions=sum(Receiving_Rec,na.rm = T),
          avgReceptions=mean(Receiving_Rec,na.rm = T),
          totalYards=sum(Receiving_Yds,na.rm = T),
          avgYards=mean(Receiving_Yds,na.rm = T),
          `avgY/R`=mean(Receiving_Y.R,na.rm = T),
          totalPts=sum(Scoring_Pts,na.rm = T),
          avgCatchPct=mean(Receiving_Ctch.,na.rm = T),
          `avgY/Tgt`=mean(Receiving_Y.Tgt,na.rm = T),
          totalFl=sum(Fumbles_FL,na.rm = T),
          weight=max(weight),
          height=max(height),
          totalFP=sum(fantasy_points)
  )
te1<-te[,c(6:21)]
methodtest<-function(x) {agnes(te1,method=x)$ac}
map_dbl(m,methodtest)
clustte<- agnes(te1,method="ward")
subgrpte<-cutree(clustte,k=4)
te<-te%>%mutate(cluster=subgrpte)
pltree(clustte,cex=0.6,hang=-1,main="Dendrogram of tes",labels = te$playerName)
rect.hclust(clustte, k = 4, border = 2:5)
fviz_nbclust(te,FUN=hcut,method="wss")
fviz_nbclust(te,FUN=hcut,method="silhouette")


#Running Backs
rb<-test[test$position=="RB",]
rb<-rb[,c(1:7,10,18,19,25:31,36:40,56:60,45)]
rb[is.na(rb)]<-0
rb[rb=="null"]<-0
rb[rb=="Inactive"]<-NA
rb[rb=="Did Not Play"]<-NA
colnames(rb)[8]<-"game"
rb$Off..Snaps_Pct<-gsub("%","",rb$Off..Snaps_Pct)
rb$Receiving_Ctch.<-gsub("%","",rb$Receiving_Ctch.)
rb[,c(6:length(rb))]<-lapply(rb[,c(6:length(rb))], as.numeric)
rb$Off..Snaps_Pct<-rb$Off..Snaps_Pct/100
rb$Receiving_Ctch.<-rb$Receiving_Ctch./100
rb<-rb[!rb$game==0,]
#rb<-na.omit(rb)

rb<-rb%>%
  group_by(sleeper_player_id)%>%
  reframe(ID=max(sleeper_player_id,na.rm = T),
          playerName=max(player_name,na.rm = T),
          human=max(display_name,na.rm = T),
          team=max(team_name,na.rm = T),
          totalSnaps=sum(Off..Snaps_Num,na.rm = T),
          avgSnaps=mean(Off..Snaps_Num,na.rm = T),
          avgSapsPct=mean(Off..Snaps_Pct,na.rm = T),
          totalTargets=sum(Receiving_Tgt,na.rm = T),
          avgTargets=mean(Receiving_Tgt,na.rm = T),
          totalReceptions=sum(Receiving_Rec,na.rm = T),
          avgReceptions=mean(Receiving_Rec,na.rm = T),
          totalYards=sum(Receiving_Yds,na.rm = T),
          avgYards=mean(Receiving_Yds,na.rm = T),
          `avgY/R`=mean(Receiving_Y.R,na.rm = T),
          totalPts=sum(Scoring_Pts,na.rm = T),
          avgCatchPct=mean(Receiving_Ctch.,na.rm = T),
          `avgY/Tgt`=mean(Receiving_Y.Tgt,na.rm = T),
          totalFl=sum(Fumbles_FL,na.rm = T),
          totalRushingAtt=sum(Rushing_Att,na.rm = T),
          avgRushingAtt=mean(Rushing_Att,na.rm = T),
          totalRushingYds=sum(Rushing_Yds,na.rm = T),
          avgRushingYds=mean(Rushing_Yds,na.rm = T),
          avgRushingYA=mean(Rushing_Y.A,na.rm = T),
          weight=max(weight),
          height=max(height),
          totalFP=sum(fantasy_points)
  )
rb1<-rb[,c(6:26)]
methodtest<-function(x) {agnes(rb1,method=x)$ac}
map_dbl(m,methodtest)
clustrb<- agnes(rb1,method="ward")
subgrprb<-cutree(clustrb,k=5)
rb<-rb%>%mutate(cluster=subgrprb)
pltree(clustrb,cex=0.6,hang=-1,main="Dendrogram of rbs",labels = rb$playerName)
rect.hclust(clustrb, k = 5, border = 2:5)
fviz_nbclust(rb,FUN=hcut,method="wss")
fviz_nbclust(rb,FUN=hcut,method="silhouette")

#quarterbacks
qb<-test[test$position=="QB",]
qb<-qb[,c(1:7,10,18,19,36:40,56:70,45)]
qb[is.na(qb)]<-0
qb[qb=="null"]<-0
qb[qb=="Inactive"]<-NA
qb[qb=="Did Not Play"]<-NA
colnames(qb)[8]<-"game"
qb$Off..Snaps_Pct<-gsub("%","",qb$Off..Snaps_Pct)
qb$`Passing_Cmp.`<-gsub("%","",qb$`Passing_Cmp.`)
qb[,c(6:length(qb))]<-lapply(qb[,c(6:length(qb))], as.numeric)
qb$Off..Snaps_Pct<-qb$Off..Snaps_Pct/100
qb$`Passing_Cmp.`<-qb$`Passing_Cmp.`/100
qb<-qb[!qb$game==0,]
#qb<-na.omit(qb)

qb<-qb%>%
  group_by(sleeper_player_id)%>%
  reframe(ID=max(sleeper_player_id,na.rm = T),
          playerName=max(player_name,na.rm = T),
          human=max(display_name,na.rm = T),
          team=max(team_name,na.rm = T),
          totalSnaps=sum(Off..Snaps_Num,na.rm = T),
          avgSnaps=mean(Off..Snaps_Num,na.rm = T),
          avgSapsPct=mean(Off..Snaps_Pct,na.rm = T),
          totalFumble=sum(Fumbles_Fmb,na.rm = T),
          avgFumble=mean(Fumbles_Fmb,na.rm = T),
          totalFumbleTO=sum(Fumbles_FL,na.rm = T),
          avgFumbleTO=sum(Fumbles_FL,na.rm = T),
          totalRushingAtt=sum(Rushing_Att,na.rm = T),
          avgRushingAtt=mean(Rushing_Att,na.rm = T),
          totalRushingYds=sum(Rushing_Yds,na.rm = T),
          avgRushingYds=mean(Rushing_Yds,na.rm = T),
          totalRushingTd=sum(Rushing_TD,na.rm = T),
          avgRushingTd=mean(Rushing_TD,na.rm = T),
          avgRushingYA=mean(Rushing_Y.A,na.rm = T),
          totalPasses=sum(Passing_Cmp,na.rm = T),
          avgPasses=mean(Passing_Cmp,na.rm = T),
          totalPassAtt=sum(Passing_Att,na.rm = T),
          avgPassAtt=mean(Passing_Att,na.rm = T),
          avgCompPct=mean(Passing_Cmp.,na.rm = T),
          totalPassYds=sum(Passing_Yds,na.rm = T),
          avgPassYds=mean(Passing_Yds,na.rm = T),
          totalPassingTd=sum(Passing_TD,na.rm = T),
          avgPassingTd=mean(Passing_TD,na.rm = T),
          totalPassingInt=sum(Passing_Int,na.rm = T),
          avgPassingInt=mean(Passing_Int,na.rm = T),
          avg=mean(Passing_Rate,na.rm = T),
          avgsackedPct=mean(Passing_Sk,na.rm = T),
          avgAdjAYdsAtt=mean(Passing_AY.A,na.rm = T),
          weight=max(weight),
          height=max(height),
          totalFP=sum(fantasy_points)
  )
qb1<-qb[,c(6:35)]
methodtest<-function(x) {agnes(qb1,method=x)$ac}
map_dbl(m,methodtest)
clustqb<- agnes(qb1,method="ward")
subgrpqb<-cutree(clustqb,k=5)
qb<-qb%>%mutate(cluster=subgrpqb)
pltree(clustqb,cex=0.6,hang=-1,main="Dendrogram of qbs",labels = qb$playerName)
rect.hclust(clustqb, k = 5, border = 2:5)
fviz_nbclust(qb,FUN=hcut,method="wss")
fviz_nbclust(qb,FUN=hcut,method="silhouette")

#dline
#solo and assisted tackles
dl<-test[test$position=="DL"|test$position=="LB DL",]
dl<-dl[,c(1:7,10,20,21,38:55,75)]
dl[is.na(dl)]<-0
dl[dl=="null"]<-0
dl[dl=="Inactive"]<-NA
dl[dl=="Did Not Play"]<-NA
colnames(dl)[19]<-"sacks"
colnames(dl)[8]<-"game"
dl$Def..Snaps_Pct<-gsub("%","",dl$Def..Snaps_Pct)
dl[,c(6:length(dl))]<-lapply(dl[,c(6:length(dl))], as.numeric)
dl$Def..Snaps_Pct<-dl$Def..Snaps_Pct/100
dl<-dl[!dl$game==0,]
#dl<-na.omit(dl)

dl<-dl%>%
  group_by(sleeper_player_id)%>%
  reframe(ID=max(sleeper_player_id,na.rm = T),
          playerName=max(player_name,na.rm = T),
          human=max(display_name,na.rm = T),
          team=max(team_name,na.rm = T),
          totalSnaps=sum(Def..Snaps_Num,na.rm = T),
          avgSnaps=mean(Def..Snaps_Num,na.rm = T),
          avgSapsPct=mean(Def..Snaps_Pct,na.rm = T),
          totalSacks=sum(sacks,na.rm = T),
          totalTFL=sum(Tackles_TFL,na.rm = T),
          totalQbHit=sum(Tackles_QBHits,na.rm = T),
          totalFF=sum(Fumbles_FF,na.rm = T),
          totalFR=sum(Fumbles_FR,na.rm = T),
          totalYds=sum(Fumbles_Yds,na.rm = T),
          totalFTd=sum(Fumbles_TD,na.rm = T),
          totalTackSolo=sum(Tackles_Solo,na.rm = T),
          avgTackSolo=mean(Tackles_Solo,na.rm = T),
          totalTackAst=sum(Tackles_Ast,na.rm = T),
          avgTackAst=mean(Tackles_Ast,na.rm = T),
          totalInt=sum(Def.Interceptions_Int,na.rm = T),
          totalIntYds=sum(Def.Interceptions_Yds,na.rm = T),
          totalTd=sum(Def.Interceptions_TD,na.rm = T),
          totalPd=sum(Def.Interceptions_PD,na.rm = T),
          totalSaf=sum(Scoring_Sfty,na.rm = T),
          weight=max(weight),
          height=max(height),
          totalFP=sum(fantasy_points)
      )
dl1<-dl[,c(6,26)]
methodtest<-function(x) {agnes(dl1,method=x)$ac}
map_dbl(m,methodtest)
clustdl<- agnes(dl1,method="ward")
subgrpdl<-cutree(clustdl,k=4)
dl<-dl%>%mutate(cluster=subgrpdl)
pltree(clustdl,cex=0.6,hang=-1,main="Dendrogram of dls",labels = dl$playerName)
rect.hclust(clustdl, k = 4, border = 2:5)
fviz_nbclust(dl,FUN=hcut,method="wss")
fviz_nbclust(dl,FUN=hcut,method="silhouette")

#linebackers
#solo and assisted tackles
lb<-test[test$position=="LB",]
lb<-lb[,c(1:7,10,20,21,38:55,75)]
lb[is.na(lb)]<-0
lb[lb=="null"]<-0
lb[lb=="Inactive"]<-NA
lb[lb=="Did Not Play"]<-NA
colnames(lb)[19]<-"sacks"
colnames(lb)[8]<-"game"
lb$Def..Snaps_Pct<-gsub("%","",lb$Def..Snaps_Pct)
lb[,c(6:length(lb))]<-lapply(lb[,c(6:length(lb))], as.numeric)
lb$Def..Snaps_Pct<-lb$Def..Snaps_Pct/100
lb<-lb[!lb$game==0,]
#lb<-na.omit(lb)

lb<-lb%>%
  group_by(sleeper_player_id)%>%
  reframe(ID=max(sleeper_player_id,na.rm = T),
          playerName=max(player_name,na.rm = T),
          human=max(display_name,na.rm = T),
          team=max(team_name,na.rm = T),
          totalSnaps=sum(Def..Snaps_Num,na.rm = T),
          avgSnaps=mean(Def..Snaps_Num,na.rm = T),
          avgSapsPct=mean(Def..Snaps_Pct,na.rm = T),
          totalSacks=sum(sacks,na.rm = T),
          totalTFL=sum(Tackles_TFL,na.rm = T),
          totalQbHit=sum(Tackles_QBHits,na.rm = T),
          totalFF=sum(Fumbles_FF,na.rm = T),
          totalFR=sum(Fumbles_FR,na.rm = T),
          totalYds=sum(Fumbles_Yds,na.rm = T),
          totalFTd=sum(Fumbles_TD,na.rm = T),
          totalTackSolo=sum(Tackles_Solo,na.rm = T),
          avgTackSolo=mean(Tackles_Solo,na.rm = T),
          totalTackAst=sum(Tackles_Ast,na.rm = T),
          avgTackAst=mean(Tackles_Ast,na.rm = T),
          totalInt=sum(Def.Interceptions_Int,na.rm = T),
          totalIntYds=sum(Def.Interceptions_Yds,na.rm = T),
          totalTd=sum(Def.Interceptions_TD,na.rm = T),
          totalPd=sum(Def.Interceptions_PD,na.rm = T),
          totalSaf=sum(Scoring_Sfty,na.rm = T),
          weight=max(weight),
          height=max(height),
          totalFP=sum(fantasy_points)
  )
lb1<-lb[,c(6,26)]
methodtest<-function(x) {agnes(lb1,method=x)$ac}
map_dbl(m,methodtest)
clustlb<- agnes(lb1,method="ward")
subgrplb<-cutree(clustlb,k=4)
lb<-lb%>%mutate(cluster=subgrplb)
pltree(clustlb,cex=0.6,hang=-1,main="Dendrogram of lbs",labels = lb$playerName)
rect.hclust(clustlb, k = 4, border = 2:5)
fviz_nbclust(lb,FUN=hcut,method="wss")
fviz_nbclust(lb,FUN=hcut,method="silhouette")


#write.csv(wr[,c(3,20)],"C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/wr.csv")
#write.csv(rb[,c(3,25)],"C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/rb.csv")
#write.csv(qb[,c(3,34)],"C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/qb.csv")
#write.csv(te[,c(3,20)],"C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/te.csv")
#write.csv(dl[,c(3,25)],"C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/dl.csv")
#write.csv(lb[,c(3,25)],"C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/lb.csv")
#write.csv(db[,c(3,25)],"C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/db.csv")


#graphs
wr_out<-wr%>%select(playerName,avgSnaps,totalFP,cluster)
wr_out$position<-"WR"
wr_out$index<-ifelse(wr_out$cluster==1,3,
                 ifelse(wr_out$cluster==2,1,
                        ifelse(wr_out$cluster==3,2,wr_out$cluster)))

wrplot<-ggplot(wr_out,aes(x=totalFP,y=avgSnaps,color=factor(index)))+
  geom_smooth(method="lm",se=T,linetype="dashed",color="black")+  
  theme_minimal()+                         
  labs(
    title="Wide Receivers",
    x="Fantasy Points",
    y="Average Snaps",
    color="Clusters")+
  theme(
    panel.grid.major=element_line(color="grey80"),  
    panel.grid.minor=element_line(color="grey90"),  
    plot.title = element_text(hjust=0.5))+
    geom_text_repel(size=4,label=wr$playerName)+  
  scale_color_discrete()


qb_out<-qb%>%select(playerName,avgSnaps,totalFP,cluster)
qb_out$position<-"QB"
qb_out$index<-ifelse(qb_out$cluster==2,1,ifelse(qb_out$cluster==1,5,ifelse(qb_out$cluster==5,4,ifelse(qb_out$cluster==4,2,qb_out$cluster))))
qbplot<-ggplot(qb_out,aes(x=totalFP,y=avgSnaps,color=factor(index)))+
  geom_smooth(method="lm",se=T,linetype="dashed",color="black")+  
  theme_minimal()+                         
  labs(
    title="QuarterBacks",
    x="Fantasy Points",
    y="Average Snaps",
    color="Clusters") +
  theme(
    panel.grid.major=element_line(color="grey80"),  
    panel.grid.minor=element_line(color="grey90"),  
    plot.title=element_text(hjust=0.5))+
  geom_text_repel(size=4,label=qb$playerName)+
  scale_color_discrete()

rb_out<-rb%>%select(playerName,avgSnaps,totalFP,cluster)
rb_out$position<-"RB"
rb_out$index<-ifelse(rb_out$cluster==4,1,ifelse(rb_out$cluster==1,2,ifelse(rb_out$cluster==2,3,ifelse(rb_out$cluster==3,5,ifelse(rb_out$cluster==5,4,rb_out$cluster)))))
rbplot<-ggplot(rb_out,aes(x=totalFP,y=avgSnaps,color=factor(index)))+
  geom_smooth(method="lm",se=T,linetype="dashed",color="black")+  
  theme_minimal()+                         
  labs(
    title="Running Backs",
    x="Fantasy Points",
    y="Average Snaps",
    color="Clusters")+
  theme(
    panel.grid.major=element_line(color="grey80"),  
    panel.grid.minor=element_line(color="grey90"), 
    plot.title=element_text(hjust=0.5),)+
    geom_text_repel(size=4,label=rb$playerName)+
    scale_colour_discrete()

te_out<-te%>%select(playerName,avgSnaps,totalFP,cluster)
te_out$position<-"TE"
te_out$index<-ifelse(te_out$cluster==1,3,ifelse(te_out$cluster==3,2,ifelse(te_out$cluster==2,1,te_out$cluster)))
#teplot<-
  ggplot(te_out, aes(x=totalFP,y=avgSnaps,color=factor(index)))+
  geom_smooth(method="lm",se=T,linetype="dashed",color="black")+  
  theme_minimal()+                         
  labs(
    title="Tight Ends",
    x="Fantasy Points",
    y="Average Snaps",
    color="Clusters") +
  theme(
    panel.grid.major=element_line(color="grey80"),  
    panel.grid.minor=element_line(color="grey90"),  
    plot.title=element_text(hjust=0.5))+
    geom_text_repel(size=4,label=te$playerName)+
  scale_colour_discrete()

dl_out<-dl%>%select(playerName,avgSnaps,totalFP,cluster)
dl_out$position<-"DL"
dl_out$index<-ifelse(dl_out$cluster==1,3,ifelse(dl_out$cluster==3,4,ifelse(dl_out$cluster==4,2,ifelse(dl_out$cluster==2,1,dl_out$cluster))))
dlplot<-ggplot(dl_out,aes(x=totalFP,y=avgSnaps,color=factor(index)))+
  geom_smooth(method="lm",se=T,linetype="dashed",color="black")+  
  theme_minimal() +                         
  labs(
    title="Defensive Linemen",
    x="Fantasy Points",
    y="Average Snaps",
    color="Clusters")+
  theme(
    panel.grid.major=element_line(color="grey80"),  
    panel.grid.minor=element_line(color="grey90"),  
    plot.title=element_text(hjust=0.5)              
  )+geom_text_repel(size=4,label=dl$playerName)+
  scale_colour_discrete()

lb_out<-lb%>%select(playerName,avgSnaps,totalFP,cluster)
lb_out$position<-"LB"
lb_out$index<-ifelse(lb_out$cluster==3,4,ifelse(lb_out$cluster==4,3,lb_out$cluster))
lbplot<-ggplot(lb_out,aes(x=totalFP,y=avgSnaps,color=factor(index)))+
  geom_smooth(method="lm",se=T,linetype="dashed",color="black")+  
  theme_minimal()+                         
  labs(
    title="Line Backers",
    x="Fantasy Points",
    y="Average Snaps",
    color="Clusters")+
  theme(
    panel.grid.major=element_line(color="grey80"),  
    panel.grid.minor=element_line(color="grey90"),
    plot.title=element_text(hjust=0.5)              
  )+geom_text_repel(size=4,label=lb$playerName)+
  scale_colour_discrete()

db_out<-db%>%select(playerName,avgSnaps,totalFP,cluster)
db_out$position<-"DB"
db_out$index<-ifelse(db_out$cluster==5,6,ifelse(db_out$cluster==6,5,db_out$cluster))
dbplot<-ggplot(db_out,aes(x=totalFP,y=avgSnaps,color=factor(index)))+
  geom_smooth(method="lm",se=T,linetype="dashed",color="black")+  
  theme_minimal()+                         
  labs(
    title="Defensive Backs",
    x="Fantasy Points",
    y="Average Snaps",
    color="Clusters")+
  theme(
    panel.grid.major=element_line(color="grey80"),
    panel.grid.minor=element_line(color="grey90"),  
    plot.title=element_text(hjust=0.5))+
    geom_text_repel(size=4,label=db$playerName)+
    scale_colour_discrete()

#exporting 
out<-rbind(wr_out,qb_out,rb_out,te_out,dl_out,lb_out,db_out)
write.csv(out,"C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/to share/playerData.csv",row.names = F)

ggsave("C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/to share/WR_Cluster.svg",plot=wrplot,device="svg",width=22, height=13)
ggsave("C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/to share/RB_Cluster.svg",plot=rbplot,device="svg",width=22, height=13)
ggsave("C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/to share/QB_Cluster.svg",plot=qbplot,device="svg",width=22, height=13)
ggsave("C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/to share/TE_Cluster.svg",plot=teplot,device="svg",width=22, height=13)
ggsave("C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/to share/DL_Cluster.svg",plot=dlplot,device="svg",width=22, height=13)
ggsave("C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/to share/LB_Cluster.svg",plot=lbplot,device="svg",width=22, height=13)
ggsave("C:/Users/zimza/OneDrive/Documents/Fantasy Football stats/to share/DB_Cluster.svg",plot=dbplot,device="svg",width=22, height=13)

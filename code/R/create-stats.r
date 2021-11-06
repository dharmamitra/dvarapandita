library("jsonlite")
library('igraph')
library('network')
library('ggraph')
library(tidyverse)
library(hrbrthemes)
library(circlize)
library(kableExtra)
options(knitr.table.format = "html")
library(viridis)
library(igraph)
library(ggraph)
library(colormap)
library(circlize)
library(viridis)
library(stringi)


# read our json file
# akbh_data <- fromJSON(file ="../../output/T07vakobhau-0.json")
akbh_data <- jsonlite::fromJSON("../../output/T07vakobhau-0.json")
segments = akbh_data[1][[1]]
parallels = akbh_data[2][[1]]


list_of_source = c()
list_of_target = c()
weights = c()





for (i in  1:nrow(parallels)) {
  root_segnr = parallels[i,]$root_segnr[[1]][1]
  par_segnr = parallels[i,]$par_segnr[[1]][1]
  score = parallels[i,]$par_segnr[[1]][1]
  source = stri_extract(root_segnr,regex="VAkK_[0-9]")
  target = stri_extract(par_segnr,regex="VAkK_[0-9]")
  if (score > 50) {
    
    weight = parallels[i,]$par_length[[1]]

    list_of_source[[source+""]] <- list_of_source[['source']] + # blah blah blah
    list_of_target[['target']] <- list_of_target[['target']] + target 
    weights <- c(weights,weight)
  }
}
edges_source = 

graph_frame <- data.frame("from"=list_of_source,"to"=list_of_target,"weight"=weights)

circos.clear()
circos.par(start.degree = 90, gap.degree = 4, track.margin = c(-0.1, 0.1), points.overflow.warning = FALSE)
par(mar = rep(0, 4))

# color palette
mycolor <- viridis(10, alpha = 1, begin = 0, end = 1, option = "D")
mycolor <- mycolor[sample(1:10)]

# Base plot
chordDiagram(
  x = graph_frame, 
  #grid.col = mycolor,
  transparency = 0.25,
  directional = 1,
  direction.type = c("arrows", "diffHeight"), 
  diffHeight  = -0.04,
  annotationTrack = "grid", 
  annotationTrackHeight = c(0.05, 0.1),
  link.arr.type = "big.arrow", 
  link.sort = TRUE, 
  link.largest.ontop = TRUE)

# # Add text and axis
# circos.trackPlotRegion(
#   track.index = 1, 
#   bg.border = NA, 
#   panel.fun = function(x, y) {
#     
#     xlim = get.cell.meta.data("xlim")
#     sector.index = get.cell.meta.data("sector.index")
#     
#     # Add names to the sector. 
#     circos.text(
#       x = mean(xlim), 
#       y = 3.2, 
#       labels = sector.index, 
#       facing = "bending", 
#       cex = 0.8
#     )
#     
#     # Add graduation on axis
#     circos.axis(
#       h = "top", 
#       major.at = seq(from = 0, to = xlim[2], by = ifelse(test = xlim[2]>10, yes = 2, no = 1)), 
#       minor.ticks = 1, 
#       major.tick.percentage = 0.5,
#       labels.niceFacing = FALSE)
#   }
# )

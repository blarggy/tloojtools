packages <- c("tidyverse", "haven", "purrr", "psych", "jsonlite", "foreign", "sas7bdat", "ggplot2", "lubridate", "psych",
              "openxlsx", "odbc", "DBI", "nflverse", "cluster", "factoextra", "dendextend", "colorspace", "ggrepel", "svglite")

for (pkg in packages) {
  if (!require(pkg, character.only = TRUE)) {
    install.packages(pkg, dependencies = TRUE)
    library(pkg, character.only = TRUE)
  }
}
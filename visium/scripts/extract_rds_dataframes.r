#!/usr/bin/env Rscript
library(Seurat)
library(stringr)

get_image_path <- function(input_file) {
  input_file_path <- unlist(str_split(input_file,'/'))
  input_file_path <- paste(input_file_path[1:length(input_file_path)-1],collapse='/')
  print(paste("input_file_path:",input_file_path,sep=""))
  return(input_file_path)
}

get_cell_labels <- function(read_input_file, key_list, input_file_path){
  # Extracting dataframes from RDS file and saving as csvs in the temporary directory
  for (k in key_list){
    print(paste("key:",k,sep=""))
    if (k %in% names(read_input_file@assays)){
      save_path <- paste(input_file_path, paste(gsub("\\.","_",k), ".csv", sep=""), sep="/")
      print(paste("save_path:", save_path, sep=""))
      write.csv(read_input_file[[k]]@data, save_path)
    }
  }
}

get_spotfile <- function(read_input_file, input_file_path) {
  # Writing spot coordinates
  spot_save_path <- paste(input_file_path,"spot_coordinates.csv",sep='/')

  
  if ("coordinates" %in% slotNames(read_input_file@images$slice1)){
    print("Working with VisiumV1 format")
    write.csv(read_input_file@images[["slice1"]]@coordinates, spot_save_path)
  } else if ("centroids" %in% names(read_input_file@images$slice1)){
    print("Working with VisiumV2 format")
    
    centroids <- as.data.frame(read_input_file@images$slice1$centroids@coords)
    rownames(centroids) <- read_input_file@images$slice1$centroids@cells
    write.csv(centroids, spot_save_path)
  }
  print(paste("Spots saved at:", spot_save_path, sep=' '))
}

extract_dataframes <- function(input_file, key_list) {
  read_input_file <- readRDS(input_file)
  input_file_path <- get_image_path(input_file)
  
  get_cell_labels(read_input_file, key_list, input_file_path)
  
  get_spotfile(read_input_file, input_file_path)
  print("All dataframes extracted")
}


key_list <- commandArgs(trailingOnly=TRUE)
input_file <- key_list[1]
key_list <- key_list[2:length(key_list)]
extract_dataframes(input_file, key_list)
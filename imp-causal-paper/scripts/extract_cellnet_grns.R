#!/usr/bin/env Rscript
# extract_cellnet_grns.R
#
# Extract per-cell-type GRN edge lists from CellNet/PACNet grnAll objects.
#
# Each grnAll.rda file contains ctGRNs$graphLists — a named list of
# cell-type-specific igraph objects. We extract the canonical one for
# each cell type from its matching grnAll file if available, otherwise
# from the heart grnAll (which contains all 14 cell types).
#
# Output: one CSV per cell type in data/processed/cellnet/
#   columns: TF, TG (target gene), undirected edge
# Also writes network_stats.csv with node/edge counts for BDM input.

suppressPackageStartupMessages(library(igraph))

base_dir <- file.path(dirname(dirname(normalizePath(sys.frames()[[1]]$ofile))),
                      "imp-causal-paper") |> suppressWarnings()
# Allow running from project root or scripts/
if (!dir.exists(file.path(base_dir, "data"))) {
  base_dir <- dirname(dirname(normalizePath(commandArgs(trailingOnly = FALSE)[4])))
  base_dir <- sub("--file=", "", base_dir)
  base_dir <- dirname(dirname(base_dir))
}

# Accept base_dir from command line for reliability
args <- commandArgs(trailingOnly = TRUE)
if (length(args) >= 1) base_dir <- args[1]

grnAll_dir <- file.path(base_dir, "data/raw/cellnet/grnAll")
out_dir    <- file.path(base_dir, "data/processed/cellnet")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

# Available grnAll files
available_files <- list.files(grnAll_dir, pattern = "_grnAll\\.rda$", full.names = TRUE)
cell_types_available <- sub("_grnAll\\.rda$", "", basename(available_files))
cat(sprintf("Found %d grnAll files: %s\n", length(available_files),
            paste(cell_types_available, collapse = ", ")))

# Load heart_grnAll as the universal source (contains all 14 ct-GRNs)
universal_file <- file.path(grnAll_dir, "heart_grnAll.rda")
cat(sprintf("Loading universal source: %s\n", universal_file))
env <- new.env()
load(universal_file, envir = env)
grnAll_universal <- env$grnAll

all_ct_names <- names(grnAll_universal$ctGRNs$graphLists)
cat(sprintf("Cell types available in universal grnAll: %s\n",
            paste(all_ct_names, collapse = ", ")))

# For each cell type, prefer its own grnAll if available
extract_graph <- function(ct) {
  own_file <- file.path(grnAll_dir, sprintf("%s_grnAll.rda", ct))
  if (file.exists(own_file)) {
    env2 <- new.env()
    load(own_file, envir = env2)
    g <- env2$grnAll$ctGRNs$graphLists[[ct]]
    source_label <- sprintf("%s_grnAll (canonical)", ct)
  } else {
    g <- grnAll_universal$ctGRNs$graphLists[[ct]]
    source_label <- "heart_grnAll (proxy)"
  }
  list(graph = g, source = source_label)
}

stats_rows <- list()

for (ct in all_ct_names) {
  cat(sprintf("Processing %s ...\n", ct))
  result <- extract_graph(ct)
  g <- result$graph

  # Upgrade old igraph format silently
  g <- igraph::upgrade_graph(g)

  n_nodes <- vcount(g)
  n_edges <- ecount(g)
  cat(sprintf("  nodes=%d  edges=%d  source=%s\n", n_nodes, n_edges, result$source))

  # Extract edge list
  el <- as_edgelist(g, names = TRUE)
  el_df <- data.frame(TF = el[, 1], TG = el[, 2], stringsAsFactors = FALSE)

  out_file <- file.path(out_dir, sprintf("%s_edgelist.csv", ct))
  write.csv(el_df, out_file, row.names = FALSE, quote = FALSE)

  stats_rows[[ct]] <- data.frame(
    cell_type  = ct,
    n_nodes    = n_nodes,
    n_edges    = n_edges,
    source     = result$source,
    edge_file  = basename(out_file),
    stringsAsFactors = FALSE
  )
}

stats_df <- do.call(rbind, stats_rows)
stats_file <- file.path(out_dir, "network_stats.csv")
write.csv(stats_df, stats_file, row.names = FALSE, quote = FALSE)

cat(sprintf("\nDone. Wrote %d edge list files + network_stats.csv to %s\n",
            length(all_ct_names), out_dir))
print(stats_df[, c("cell_type", "n_nodes", "n_edges")])

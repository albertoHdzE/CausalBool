# screen_boolnet_reconstruct.R -- BoolNet reconstruction, run as its own software.
#
# Called by screen_s1_full_table.py and screen_s2_queries.py.  Reads a binary
# file of state-successor pairs (one byte per bit, each row = n state bits then
# n successor bits), calls BoolNet::reconstructNetwork, and writes the chosen
# network in BoolNet's own file format.  Only the reconstructNetwork call is
# timed; building the input list is not.
#
# Args: pairs.bin n n_pairs maxK method reps out.bnet names_csv
args <- commandArgs(trailingOnly = TRUE)
.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
suppressMessages(library(BoolNet))
path <- args[1]; n <- as.integer(args[2]); m <- as.integer(args[3])
maxK <- as.integer(args[4]); method <- args[5]; reps <- as.integer(args[6])
out <- args[7]; genes <- strsplit(args[8], ",")[[1]]

raw <- readBin(path, "raw", n = m * 2 * n)
M <- matrix(as.integer(raw), nrow = m, ncol = 2 * n, byrow = TRUE)
meas <- lapply(seq_len(m), function(i) {
  x <- matrix(M[i, ], nrow = n, ncol = 2)
  rownames(x) <- genes
  x
})

times <- c()
res <- NULL
for (r in seq_len(reps)) {
  t <- system.time(res <- reconstructNetwork(meas, method = method, maxK = maxK,
                                            readableFunctions = FALSE))[["elapsed"]]
  times <- c(times, t)
}
nfun <- sapply(res$interactions, length)
status <- "ok"
dontcare <- any(sapply(res$interactions, function(g)
  length(g) > 0 && any(g[[1]]$func < 0)))
if (any(nfun == 0)) {
  status <- "no_consistent_function"
} else if (dontcare) {
  # The chosen function has input combinations never observed ("don't care"
  # entries): the data do not determine it, so it is not an identification.
  status <- "unobserved_input_combinations"
} else {
  net <- chooseNetwork(res, rep(1, n))
  saveNetwork(net, out)
}
cat(sprintf("STATUS\t%s\nTIMES\t%s\nAMBIGUOUS_GENES\t%d\nMAX_FUNCTIONS\t%d\n",
            status, paste(times, collapse = ","), sum(nfun > 1), max(nfun)))

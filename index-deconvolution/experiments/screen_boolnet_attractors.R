# screen_boolnet_attractors.R -- BoolNet attractor search, run as its own software.
#
# Called by screen_s3b_multi_step.py.  Loads a frozen .bnet with loadNetwork and
# answers one question:
#   fixed   all fixed points      getAttractors(type="synchronous", method="sat.restricted", maxAttractorLength=1)
#   attr    all attractors        getAttractors(type="synchronous", method="sat.exhaustive")
# Only the getAttractors call is timed.  Each attractor is written as its
# states (one bit string per state, genes in file order, bit i = gene i).
#
# Args: net.bnet question reps
args <- commandArgs(trailingOnly = TRUE)
.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
suppressMessages(library(BoolNet))
net <- loadNetwork(args[1]); q <- args[2]; reps <- as.integer(args[3])
times <- c(); a <- NULL
for (r in seq_len(reps)) {
  t <- system.time({
    a <- tryCatch(if (q == "fixed") {
      getAttractors(net, type = "synchronous", method = "sat.restricted",
                    maxAttractorLength = 1, returnTable = FALSE)
    } else {
      getAttractors(net, type = "synchronous", method = "sat.exhaustive",
                    returnTable = FALSE)
    }, error = function(e) {
      # BoolNet raises, rather than returning an empty list, when a complete
      # search finds no attractor of the admitted length.
      if (grepl("not able to identify any attractors", conditionMessage(e)))
        list(attractors = list(), none_found = TRUE) else stop(e)
    })
  })[["elapsed"]]
  times <- c(times, t)
}
cat(sprintf("TIMES\t%s\n", paste(times, collapse = ",")))
for (i in seq_along(a$attractors)) {
  s <- as.matrix(getAttractorSequence(a, i))
  st <- apply(s, 1, function(row) paste(row, collapse = ""))
  cat(sprintf("ATTR\t%s\n", paste(st, collapse = ",")))
}

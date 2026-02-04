#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(DBI)
  library(RPostgres)
  library(glue)
  library(yaml)
  library(jsonlite)
})

`%||%` <- function(lhs, rhs) {
  if (is.null(lhs) || (is.character(lhs) && identical(lhs, "")) || (is.logical(lhs) && length(lhs) == 0)) {
    rhs
  } else {
    lhs
  }
}

compact_list <- function(x) {
  if (is.null(x) || length(x) == 0) {
    return(list())
  }
  x[!vapply(x, is.null, logical(1))]
}

merge_lists <- function(base, override) {
  if (is.null(base)) {
    base <- list()
  }
  if (is.null(override)) {
    return(base)
  }
  for (name in names(override)) {
    if (is.list(base[[name]]) && is.list(override[[name]])) {
      base[[name]] <- merge_lists(base[[name]], override[[name]])
    } else {
      base[[name]] <- override[[name]]
    }
  }
  base
}

read_yaml_config <- function(path) {
  if (is.null(path)) {
    return(list())
  }
  if (!file.exists(path)) {
    stop(sprintf("Config file not found: %s", path), call. = FALSE)
  }
  yaml::read_yaml(path)
}

parse_params_json <- function(param_json) {
  if (is.null(param_json) || param_json == "") {
    return(list())
  }
  parsed <- jsonlite::fromJSON(param_json, simplifyVector = FALSE)
  if (!is.list(parsed)) {
    stop("Parsed query parameters must form a JSON object (key/value pairs).", call. = FALSE)
  }
  parsed
}

validate_connection <- function(conn_cfg) {
  required <- c("host", "dbname", "user")
  missing <- setdiff(required, names(conn_cfg))
  if (length(missing) > 0) {
    stop(sprintf(
      "Database connection missing required fields: %s",
      paste(missing, collapse = ", ")
    ), call. = FALSE)
  }
  invisible(conn_cfg)
}

run_parameterized_query <- function(conn_cfg, query_text, params = list()) {
  validate_connection(conn_cfg)
  if (is.null(query_text) || query_text == "") {
    stop("A SQL query text is required to fetch predictions.", call. = FALSE)
  }
  conn <- DBI::dbConnect(
    RPostgres::Postgres(),
    host = conn_cfg$host,
    port = conn_cfg$port %||% 5432,
    dbname = conn_cfg$dbname,
    user = conn_cfg$user,
    password = conn_cfg$password %||% ""
  )
  on.exit(DBI::dbDisconnect(conn), add = TRUE)
  sql_statement <- if (length(params) > 0) {
    glue::glue_data_sql(params, query_text, .con = conn)
  } else {
    DBI::SQL(query_text)
  }
  DBI::dbGetQuery(conn, sql_statement)
}

ensure_columns <- function(df, required_cols) {
  missing <- setdiff(required_cols, names(df))
  if (length(missing) > 0) {
    stop(sprintf("Input data is missing required columns: %s", paste(missing, collapse = ", ")), call. = FALSE)
  }
  df
}

cache_raw_inputs <- function(df, cache_dir, prefix = "analysis") {
  if (is.null(cache_dir) || cache_dir == "") {
    return(NULL)
  }
  if (!dir.exists(cache_dir)) {
    dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)
  }
  timestamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
  file_name <- sprintf("%s_%s.csv", prefix, timestamp)
  path <- file.path(cache_dir, file_name)
  write.csv(df, path, row.names = FALSE)
  message("Raw inputs cached to: ", path)
  path
}

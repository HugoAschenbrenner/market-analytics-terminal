options(stringsAsFactors = FALSE)

input_path <- "data/portfolio_returns_sample.csv"
output_dir <- "r_analytics/outputs"

if (!dir.exists(output_dir)) {
  dir.create(output_dir, recursive = TRUE)
}

returns_df <- read.csv(input_path)
returns_df$date <- as.Date(returns_df$date)

asset_columns <- setdiff(names(returns_df), "date")
returns_matrix <- as.matrix(returns_df[, asset_columns])
mode(returns_matrix) <- "numeric"

weights <- rep(1 / length(asset_columns), length(asset_columns))
portfolio_returns <- as.numeric(returns_matrix %*% weights)

periods_per_year <- 252
risk_free_rate <- 0.02

annualized_return <- mean(portfolio_returns, na.rm = TRUE) * periods_per_year
annualized_volatility <- sd(portfolio_returns, na.rm = TRUE) * sqrt(periods_per_year)

if (annualized_volatility == 0) {
  sharpe_ratio <- 0
} else {
  sharpe_ratio <- (annualized_return - risk_free_rate) / annualized_volatility
}

cumulative_index <- cumprod(1 + portfolio_returns)
running_max <- cummax(cumulative_index)
drawdown <- cumulative_index / running_max - 1

historical_var_95 <- max(0, -as.numeric(quantile(portfolio_returns, probs = 0.05, na.rm = TRUE)))
tail_returns <- portfolio_returns[portfolio_returns <= -historical_var_95]

if (length(tail_returns) == 0) {
  historical_cvar_95 <- historical_var_95
} else {
  historical_cvar_95 <- max(0, -mean(tail_returns, na.rm = TRUE))
}

performance_summary <- data.frame(
  metric = c(
    "number_of_assets",
    "number_of_observations",
    "annualized_return",
    "annualized_volatility",
    "sharpe_ratio",
    "max_drawdown",
    "historical_var_95",
    "historical_cvar_95",
    "best_daily_return",
    "worst_daily_return"
  ),
  value = c(
    length(asset_columns),
    length(portfolio_returns),
    annualized_return,
    annualized_volatility,
    sharpe_ratio,
    min(drawdown, na.rm = TRUE),
    historical_var_95,
    historical_cvar_95,
    max(portfolio_returns, na.rm = TRUE),
    min(portfolio_returns, na.rm = TRUE)
  )
)

write.csv(performance_summary, file.path(output_dir, "performance_summary.csv"), row.names = FALSE)

drawdown_series <- data.frame(
  date = returns_df$date,
  portfolio_return = portfolio_returns,
  cumulative_index = cumulative_index,
  drawdown = drawdown
)

write.csv(drawdown_series, file.path(output_dir, "drawdown_series.csv"), row.names = FALSE)

rolling_window <- 63
rolling_volatility <- rep(NA, length(portfolio_returns))
rolling_sharpe <- rep(NA, length(portfolio_returns))

for (i in seq_along(portfolio_returns)) {
  if (i >= rolling_window) {
    window_returns <- portfolio_returns[(i - rolling_window + 1):i]
    window_return <- mean(window_returns, na.rm = TRUE) * periods_per_year
    window_vol <- sd(window_returns, na.rm = TRUE) * sqrt(periods_per_year)

    rolling_volatility[i] <- window_vol

    if (!is.na(window_vol) && window_vol != 0) {
      rolling_sharpe[i] <- (window_return - risk_free_rate) / window_vol
    } else {
      rolling_sharpe[i] <- 0
    }
  }
}

rolling_risk_metrics <- data.frame(
  date = returns_df$date,
  rolling_window = rolling_window,
  rolling_volatility = rolling_volatility,
  rolling_sharpe = rolling_sharpe
)

write.csv(rolling_risk_metrics, file.path(output_dir, "rolling_risk_metrics.csv"), row.names = FALSE)

returns_df$month <- format(returns_df$date, "%Y-%m")

monthly_returns <- aggregate(
  portfolio_returns,
  by = list(month = returns_df$month),
  FUN = function(x) prod(1 + x, na.rm = TRUE) - 1
)

names(monthly_returns) <- c("month", "portfolio_monthly_return")
write.csv(monthly_returns, file.path(output_dir, "monthly_returns.csv"), row.names = FALSE)

correlation_matrix <- cor(returns_matrix, use = "pairwise.complete.obs")
write.csv(correlation_matrix, file.path(output_dir, "correlation_matrix.csv"), row.names = TRUE)

png(file.path(output_dir, "cumulative_performance.png"), width = 1000, height = 600)
plot(returns_df$date, cumulative_index, type = "l", main = "R Companion - Cumulative Performance", xlab = "Date", ylab = "Cumulative Return Index", lwd = 2)
grid()
dev.off()

png(file.path(output_dir, "drawdown_chart.png"), width = 1000, height = 600)
plot(returns_df$date, drawdown, type = "l", main = "R Companion - Portfolio Drawdown", xlab = "Date", ylab = "Drawdown", lwd = 2)
grid()
dev.off()

png(file.path(output_dir, "rolling_volatility.png"), width = 1000, height = 600)
plot(returns_df$date, rolling_volatility, type = "l", main = "R Companion - 63-Day Rolling Volatility", xlab = "Date", ylab = "Annualized Volatility", lwd = 2)
grid()
dev.off()

cat("R portfolio analytics companion complete.\n")
cat("Outputs written to:", output_dir, "\n")

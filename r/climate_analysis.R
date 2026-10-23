# EarthScape – statistical analysis in RStudio
# install.packages(c("tidyverse","lubridate","forecast","corrplot","trend"))
library(tidyverse); library(lubridate); library(corrplot)
df <- read_csv("../data/sample_dataset.csv") %>% mutate(date = ymd(date), year = year(date), month = month(date))

# 1. Annual mean temperature and linear warming trend per region
annual <- df %>% group_by(region, year) %>% summarise(temp = mean(temperature_c, na.rm = TRUE), co2 = mean(co2_ppm), .groups = "drop")
trend <- annual %>% group_by(region) %>% summarise(c_per_decade = coef(lm(temp ~ year))[2] * 10)
print(trend)
ggplot(annual, aes(year, temp, colour = region)) + geom_line() + geom_smooth(method = "lm", se = FALSE, linetype = 2) +
  labs(title = "Annual mean temperature by region", y = "°C")

# 2. Mann-Kendall test for monotonic trend (Karachi)
if (requireNamespace("trend", quietly = TRUE)) print(trend::mk.test(annual$temp[annual$region == "Sindh"]))

# 3. Correlation matrix
m <- df %>% select(temperature_c, humidity_pct, precipitation_mm, wind_speed_kmh, pressure_hpa, co2_ppm, pm25_ugm3, ndvi, soil_moisture_pct) %>% cor(use = "pairwise.complete.obs")
corrplot(m, method = "color", type = "upper", addCoef.col = "black", number.cex = .6)

# 4. Seasonal ARIMA forecast for Lahore monthly temperature
library(forecast)
lhr <- df %>% filter(station_id == "ST04") %>% group_by(year, month) %>% summarise(t = mean(temperature_c, na.rm = TRUE), .groups = "drop")
fit <- auto.arima(ts(lhr$t, start = c(2016, 1), frequency = 12)); plot(forecast(fit, h = 12), main = "Lahore – 12-month SARIMA outlook")

# 5. Extreme-event frequency
df %>% filter(event_type != "none") %>% count(year, event_type) %>% ggplot(aes(year, n, fill = event_type)) + geom_col() + labs(title = "Extreme-event days per year")

# SF 311 Poop Analysis

Analyzes San Francisco 311 "Human or Animal Waste" reports to visualize weekly trends: report volume, resolution time, and whether the city actually cleaned it up vs. it wasn't there when they arrived.

## Usage

```bash
pip install -r requirements.txt
python fetch_data.py    # downloads data to data/sf_311_poop.csv
python analyze.py       # generates output/weekly_poop_chart.png
```

## Data Source

[311 Cases](https://data.sfgov.org/City-Infrastructure/311-Cases/vw6y-z8j6) from DataSF, filtered to `service_subtype = 'Human or Animal Waste'`.

# Government Travel Cost Analysis — SQL & Data Engineering

Database and analytics project built from **Brazilian government travel data** from the Portal da Transparência. The project combines relational database design, ETL, MySQL programming and analytical SQL to investigate travel expenses, daily allowances, destinations, public agencies and transportation patterns.

This repository is a cleaned portfolio version of an academic database project. The original report and MySQL Workbench model are included for traceability.

## Project Scope

The project analyzes 2024 government travel expenditures, including:

- monthly distribution of travel expenses;
- total and average costs by superior government agency;
- travel allowances and travel profiles by public employee;
- costs by final destination country;
- ticket costs by Brazilian state (UF);
- most frequently used transportation modes.

## Data Engineering Workflow

```text
Portal da Transparência CSV exports
              ↓
      Python / Pandas ETL
              ↓
 Cleaning, normalization and
 artificial traveler identifiers
              ↓
       Normalized CSV tables
              ↓
             MySQL
              ↓
  Views / Procedures / Triggers
              ↓
       Analytical SQL queries
```

## Relational Model

The final model is normalized to **Third Normal Form (3NF)** and contains eight core tables:

```text
pais
  └── uf
       └── cidade

orgao_superior
  └── orgao_solicitante
       └── viagem
            └── trecho
       servidor ─┘
```

Important modeling decisions include:

- `trecho` is identified by the composite primary key `(seq_trecho, viagem_id_viagem)`;
- `trecho` references `cidade` twice, for origin and destination;
- `viagem` references both the traveler (`servidor`) and requesting agency (`orgao_solicitante`);
- geographic entities are normalized into country, state and city tables.

## Repository Structure

```text
government-travel-analysis/
├── README.md
├── PORTFOLIO_REFACTOR.md
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   ├── raw/
│   └── processed/
├── etl/
│   ├── transform_data.py
│   └── load_mysql.py
├── sql/
│   ├── schema/
│   │   └── schema.sql
│   ├── database_objects/
│   │   ├── view_travel_cost.sql
│   │   ├── calculate_travel_cost.sql
│   │   └── validate_travel_dates_trigger.sql
│   └── analysis/
│       ├── 01_monthly_expenses.sql
│       ├── 02_expenses_by_agency.sql
│       ├── 03_employee_allowances.sql
│       ├── 04_costs_by_destination_country.sql
│       └── 05_costs_by_state_transport.sql
├── examples/
├── model/
│   └── government_travel_model.mwb
└── docs/
    └── government_travel_database_project.pdf
```

## ETL

`etl/transform_data.py` transforms the source travel and segment exports into normalized CSV files matching the database schema.

Main ETL operations include:

- encoding-tolerant CSV import;
- column normalization;
- Brazilian decimal conversion;
- date conversion;
- duplicate removal;
- artificial traveler IDs;
- generation of surrogate IDs for country, state and city entities;
- normalization into relational tables.

Raw data are intentionally excluded from Git because the exports can be large and may contain personal identifiers.

### Run the transformation

```bash
python etl/transform_data.py \
  --travel data/raw/2024_Viagem.csv \
  --segments data/raw/2024_Trecho.csv \
  --output-dir data/processed
```

## Database Setup

Create the environment:

```bash
python -m venv .venv
```

Activate it and install dependencies:

```bash
pip install -r requirements.txt
```

Create the database:

```bash
mysql -u your_user -p < sql/schema/schema.sql
```

Create database objects:

```bash
mysql -u your_user -p projeto_fbd < sql/database_objects/view_travel_cost.sql
mysql -u your_user -p projeto_fbd < sql/database_objects/calculate_travel_cost.sql
mysql -u your_user -p projeto_fbd < sql/database_objects/validate_travel_dates_trigger.sql
```

Copy the example environment file:

```bash
cp .env.example .env
```

Fill in your local MySQL credentials and load the processed data:

```bash
python etl/load_mysql.py --data-dir data/processed
```

Use `--truncate` if you intentionally want to clear the target tables before loading:

```bash
python etl/load_mysql.py --data-dir data/processed --truncate
```

## Database Objects

### View — `view_viagem_custo`

Provides one compact record per trip with:

- start and end dates;
- origin and final destination cities;
- superior government agency;
- number of travel legs;
- number of daily allowances;
- total net trip cost.

### Stored Procedure — `CalcularCustoViagemTemp`

Accepts one or more comma-separated trip IDs and returns traveler, requesting agency and detailed cost components through a temporary table.

### Trigger — `BeforeInsertTrecho`

Rejects invalid travel legs when the departure date is later than the arrival date.

## Analytical SQL

### 1. Monthly Expenses

Analyzes the distribution of ticket, daily-allowance and other costs across 2024.

Because costs are stored at trip level and dates at leg level, costs are proportionally allocated across the number of legs to prevent duplicated totals.

### 2. Expenses by Government Agency

Calculates:

- total trips;
- net total cost;
- average cost per trip;
- number and percentage of urgent trips.

### 3. Employee Allowances

Summarizes:

- total trips per employee;
- daily-allowance value;
- net allowance/other-cost value;
- total legs;
- total daily-allowance units;
- domestic and international trips.

### 4. Costs by Destination Country

Assigns each trip once to the country of its **final destination** and compares total and average costs across destinations.

### 5. Costs by UF and Transportation Mode

Assigns ticket cost to the trip's final Brazilian state and identifies the three most common transport modes among legs ending in each UF.

See `sql/analysis/README.md` for the aggregation conventions used to avoid double-counting trip-level costs.

## Technologies

- SQL
- MySQL 5.7
- MySQL Workbench
- Python
- Pandas
- mysql-connector-python
- Relational Data Modeling
- ETL
- Data Cleaning
- Data Normalization
- Stored Procedures
- SQL Views
- Triggers
- Analytical SQL
- Relational Algebra

## Skills Demonstrated

- relational database design and normalization;
- primary, composite and foreign key modeling;
- ETL development with Python and Pandas;
- large-volume CSV processing;
- database loading in batches;
- data-quality rules at database level;
- advanced SQL joins, aggregation and subqueries;
- analytical metric design;
- documentation of data assumptions and aggregation semantics.

## Original Project Artifacts

- 📄 [`docs/government_travel_database_project.pdf`](docs/government_travel_database_project.pdf) — original academic report with model, implementation and documented results.
- 🗂️ [`model/government_travel_model.mwb`](model/government_travel_model.mwb) — final MySQL Workbench model.

## Notes

The original academic results were produced from the 2024 data snapshot used during the project. Exact query outputs can differ if the source data are updated or if a different Portal da Transparência export is used.

The cleaned SQL files in this repository intentionally make cost-allocation rules explicit to avoid double counting when trip-level costs are joined to multi-leg travel records. See [`PORTFOLIO_REFACTOR.md`](PORTFOLIO_REFACTOR.md) for the changes made before publication.

## Author

**Nicola Defonte**

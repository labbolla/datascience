# Data Science Portfolio

Welcome to my Data Science portfolio.

I'm **Nicola Defonte**, a Data & Technology professional with experience in **data analysis, statistical modeling, Machine Learning, ETL, databases, APIs, automation and software development**.

This repository brings together applied Data Science projects and academic research covering **Machine Learning, statistical analysis, SQL and Data Engineering, Natural Language Processing, graph analytics, Big Data and Operations Research**.

My background combines analytical methods with software engineering, allowing me to approach data problems from both the **modeling** and **implementation** perspectives.

---

## Portfolio Overview

| Area                          | Project                                                                                         | Main Topics                                              |
| ----------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Machine Learning              | [Hotel Booking Cancellation Prediction](machine-learning/hotel-booking-logistic-regression/)    | Logistic Regression, SMOTE, RFE, Classification          |
| Machine Learning              | [Real Estate Price Prediction](machine-learning/real-estate-linear-regression/)                 | Linear Regression, OLS, VIF, Model Diagnostics           |
| Statistical Analysis          | [Retail Sales Statistical Analysis](statistical-analysis/retail-sales-anova/)                   | ANOVA, Tukey HSD, Kruskal-Wallis, Hypothesis Testing     |
| SQL & Data Engineering        | [Government Travel Analysis](sql-data-engineering/government-travel-analysis/)                  | MySQL, ETL, Python, Relational Modeling, Advanced SQL    |
| Operations Research           | [Linear Programming Visualizer](operations-research/linear-programming-visualizer/)             | Linear Programming, Optimization, Computational Geometry |
| Research                      | [Parallel NLP Processing](research/parallel-nlp-pdf-processing/)                                | NLP, Dask, Multiprocessing, Graph Analysis               |
| Research                      | [Graph-Based Fraud Detection](research/graph-based-fraud-detection/)                            | Neo4j, PageRank, Louvain, Fraud Detection                |
| Academic Statistical Research | [Musculoskeletal Disorders in Musicians](research/musicians-musculoskeletal-statistical-study/) | Factorial ANOVA, Sampling, Hypothesis Testing            |

---

# Machine Learning

## Hotel Booking Cancellation Prediction

[View Project →](machine-learning/hotel-booking-logistic-regression/)

Machine Learning analysis focused on predicting hotel booking cancellations using **Logistic Regression**.

The project covers the complete modeling workflow:

* data cleaning and exploratory analysis;
* categorical feature encoding;
* class imbalance treatment with **SMOTE**;
* feature selection with **Recursive Feature Elimination (RFE)**;
* statistical modeling with `statsmodels`;
* predictive modeling with `scikit-learn`;
* confusion matrix, classification metrics and ROC analysis.

**Main technologies:**
`Python` `Pandas` `scikit-learn` `statsmodels` `SMOTE` `Matplotlib` `Seaborn`

---

## Real Estate Price Prediction

[View Project →](machine-learning/real-estate-linear-regression/)

Regression analysis for estimating residential property prices.

The project combines predictive modeling with statistical diagnostics, including:

* Exploratory Data Analysis;
* Linear Regression;
* Ordinary Least Squares;
* logarithmic transformations;
* dummy-variable encoding;
* multicollinearity analysis using **VIF**;
* influential observation detection with **Cook's Distance**;
* residual analysis;
* Breusch-Pagan test;
* model validation using training and validation datasets.

**Main technologies:**
`Python` `Pandas` `NumPy` `SciPy` `statsmodels` `scikit-learn`

---

# Statistical Analysis

## Retail Sales Analysis with ANOVA

[View Project →](statistical-analysis/retail-sales-anova/)

Statistical analysis of a large retail transaction dataset to investigate differences in **prices and purchased quantities across countries**.

The project includes:

* descriptive statistics;
* hypothesis testing;
* One-Way ANOVA;
* Tukey HSD post-hoc analysis;
* normality testing;
* homogeneity-of-variance testing;
* non-parametric validation with **Kruskal-Wallis**.

The analysis emphasizes the importance of verifying statistical assumptions before interpreting parametric test results.

**Main technologies:**
`Python` `Pandas` `SciPy` `statsmodels` `Matplotlib` `Seaborn`

---

# SQL & Data Engineering

## Government Travel Analysis

[View Project →](sql-data-engineering/government-travel-analysis/)

Relational database and Data Engineering project based on Brazilian government travel expenditure data.

The project implements an end-to-end workflow:

```text
Public CSV Data
      ↓
Python / Pandas ETL
      ↓
Data Cleaning & Transformation
      ↓
Relational Modeling
      ↓
MySQL
      ↓
Views / Procedures / Triggers
      ↓
Advanced SQL Analytics
```

The relational model was normalized to **Third Normal Form (3NF)** and includes analysis of:

* monthly government travel expenditure;
* expenses by government agency;
* employee travel allowances;
* international destinations;
* costs by Brazilian state;
* transportation patterns.

The repository also includes:

* Python ETL scripts;
* MySQL database schema;
* analytical SQL queries;
* View;
* Stored Procedure;
* Trigger;
* MySQL Workbench model;
* complete project documentation.

**Main technologies:**
`Python` `Pandas` `MySQL` `SQL` `ETL` `MySQL Workbench`

---

# Operations Research

## Linear Programming Visualizer

[View Project →](operations-research/linear-programming-visualizer/)

Interactive Python tool for modeling, solving and visualizing **two-variable Linear Programming problems**.

The application:

* receives objective-function coefficients;
* supports maximization and minimization;
* accepts multiple linear constraints;
* calculates constraint intersections;
* identifies feasible vertices;
* evaluates the objective function;
* determines the optimal solution;
* visualizes the feasible region.

**Main technologies:**
`Python` `NumPy` `SciPy` `Matplotlib`

---

# Research & Academic Work

## Parallel NLP Processing of Historical PDF Collections

[View Research →](research/parallel-nlp-pdf-processing/)

Research project focused on parallelizing a large-scale **Natural Language Processing pipeline** for collections of heterogeneous academic PDF documents.

The workflow combines:

```text
PDF Extraction
      ↓
Language Detection
      ↓
Text Cleaning
      ↓
Bigram Extraction
      ↓
Lemmatization
      ↓
Co-occurrence Graph
      ↓
PageRank
      ↓
Theme Extraction
```

Two parallel-processing strategies were evaluated:

* Python **Multiprocessing**
* **Dask**

The research includes execution-time benchmarking, speedup analysis, parallel efficiency, CPU utilization and memory-consumption evaluation.

**Main technologies:**
`Python` `NLP` `Dask` `Multiprocessing` `spaCy` `NetworkX` `PageRank`

---

## Graph-Based Fraud Detection

[View Research →](research/graph-based-fraud-detection/)

Research project investigating financial fraud detection through **graph analytics and graph databases**.

A synthetic dataset containing more than two million financial transaction records was modeled as a graph connecting entities such as:

* users;
* cards;
* transactions;
* IP addresses;
* devices;
* products.

The analytical pipeline combines:

```text
Transactional Data
      ↓
Data Normalization
      ↓
PostgreSQL
      ↓
Neo4j
      ↓
Graph Modeling
      ↓
Graph Algorithms
      ↓
Structural Risk Analysis
```

Algorithms evaluated include:

* Personalized PageRank;
* Louvain Community Detection;
* Label Propagation.

The research explores centrality, communities, structural risk propagation and the possibility of generating graph-derived features for supervised Machine Learning.

**Main technologies:**
`Neo4j` `Graph Analytics` `Personalized PageRank` `Louvain` `PostgreSQL` `Python`

---

## Statistical Study of Musculoskeletal Disorders in Musicians

[View Research →](research/musicians-musculoskeletal-statistical-study/)

Academic experimental research investigating relationships between **physical activity, gender, musical instrument type and musculoskeletal disability**.

The study involved survey data collection, stratified sampling and a:

```text
2 × 2 × 2 Factorial Design
```

Statistical methods included:

* descriptive statistics;
* Student's t-test;
* Shapiro-Wilk test;
* Levene's test;
* factorial ANOVA;
* interaction analysis;
* Welch ANOVA;
* Kruskal-Wallis;
* adjusted R² and effect-size interpretation.

This project represents an early application of statistical research design and inferential analysis to real-world survey data.

**Main tools:**
`JMP / SAS` `Excel` `Statistical Analysis` `Factorial ANOVA`

---

# Technical Skills Demonstrated

### Data Science & Machine Learning

`Python` · `Pandas` · `NumPy` · `SciPy` · `scikit-learn` · `statsmodels`

`Regression` · `Classification` · `Feature Engineering` · `Model Evaluation`

### Statistics

`Hypothesis Testing` · `ANOVA` · `Factorial ANOVA` · `Kruskal-Wallis`

`Regression Diagnostics` · `Effect Size` · `Sampling` · `Exploratory Data Analysis`

### Data Engineering & Databases

`SQL` · `MySQL` · `PostgreSQL` · `MongoDB` · `Neo4j`

`ETL` · `Data Cleaning` · `Relational Modeling` · `Graph Databases`

### Big Data & Parallel Processing

`Dask` · `Multiprocessing` · `Parallel Computing` · `Large-Scale Data Processing`

### Natural Language Processing

`NLP` · `Text Mining` · `spaCy` · `NetworkX` · `PageRank`

### Visualization

`Matplotlib` · `Seaborn` · `Plotly` · `Power BI`

### Development & Infrastructure

`Git` · `GitHub` · `Linux` · `REST APIs` · `JavaScript / Node.js` · `PHP`

---

# Repository Structure

```text
datascience/
│
├── machine-learning/
│   ├── hotel-booking-logistic-regression/
│   └── real-estate-linear-regression/
│
├── statistical-analysis/
│   └── retail-sales-anova/
│
├── sql-data-engineering/
│   └── government-travel-analysis/
│
├── operations-research/
│   └── linear-programming-visualizer/
│
├── research/
│   ├── parallel-nlp-pdf-processing/
│   ├── graph-based-fraud-detection/
│   └── musicians-musculoskeletal-statistical-study/
│
└── README.md
```

---

# About Me

I'm interested in building solutions at the intersection of **Data Science, analytics and software engineering**.

My work combines data analysis with practical implementation, including data pipelines, databases, APIs, automation, predictive models and production-oriented software systems.

I am particularly interested in:

* Machine Learning and predictive analytics;
* statistical modeling;
* Data Engineering;
* AI and intelligent automation;
* Natural Language Processing;
* Big Data;
* graph analytics;
* data-driven software products.

---

## Contact

**Nicola Defonte**

📍 Brasília, DF — Brazil
📧 [nicola.defonte@gmail.com](mailto:nicola.defonte@gmail.com)
🌐 [LinkedIn](https://www.linkedin.com/in/nicola-defonte-0086269b/)
💻 [GitHub](https://github.com/labbolla)

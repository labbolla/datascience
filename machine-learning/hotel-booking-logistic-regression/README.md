# Hotel Booking Cancellation Prediction

Machine Learning project focused on predicting **hotel booking cancellations**
using Logistic Regression.

The analysis covers the complete workflow from data cleaning and exploratory
data analysis to class balancing, feature selection, statistical modeling and
classification performance evaluation.

## Project Objective

The objective is to analyze hotel reservation data and build a predictive model
capable of estimating whether a booking will be canceled.

The target variable is:

- `is_canceled = 0` → booking not canceled
- `is_canceled = 1` → booking canceled

The project also investigates which variables are most relevant to the
probability of cancellation.

## Dataset

The original dataset contains:

- **119,390 observations**
- **32 variables**

After removing duplicated observations:

- **87,396 observations** remained

The dataset includes information about reservations such as:

- hotel type
- lead time
- arrival date
- length of stay
- number of guests
- country
- market segment
- distribution channel
- previous cancellations
- deposit type
- travel agent
- customer type
- average daily rate (ADR)
- special requests
- reservation status

## Data Preparation

The preprocessing workflow included:

- duplicate detection and removal;
- missing-value analysis and treatment;
- removal of variables with excessive missing data;
- conversion of date variables;
- identification of numerical and categorical variables;
- correlation analysis;
- categorical feature encoding;
- feature selection.

The `company` variable was removed because most observations were missing.

Missing values in `country` and `agent` were assigned to a `not_defined`
category, while missing values in `children` were replaced with zero.

## Exploratory Data Analysis

The exploratory analysis investigated relationships between booking
cancellations and several reservation characteristics.

The analysis included:

- descriptive statistics;
- cancellation frequency;
- correlation heatmap;
- hotel type;
- country of origin;
- market segment;
- distribution channel;
- deposit type;
- customer type;
- travel agents;
- lead time;
- ADR;
- previous cancellations;
- special requests;
- frequency distributions and outliers.

After duplicate removal, the target variable showed:

| Booking status | Percentage |
|---|---:|
| Not canceled | 72.51% |
| Canceled | 27.49% |

This class imbalance motivated the use of a balancing technique before model
development.

## Class Balancing

**SMOTE (Synthetic Minority Oversampling Technique)** was applied to balance
the target classes.

After resampling:

| Class | Observations |
|---|---:|
| Not canceled | 44,435 |
| Canceled | 44,435 |

The resulting balanced dataset contained **88,870 observations**.

## Feature Engineering

Categorical variables were transformed into dummy variables, including
information related to:

- hotel;
- arrival month;
- market segment;
- distribution channel;
- deposit type;
- customer type;
- country;
- travel agent.

This allowed categorical information to be incorporated into the logistic
regression model.

## Feature Selection

**Recursive Feature Elimination (RFE)** with Logistic Regression was used to
identify the most relevant predictors.

The procedure selected **55 features** from the candidate feature set.

Feature selection was combined with statistical analysis of the logistic
regression coefficients.

## Logistic Regression

Logistic Regression was selected because the target variable is binary:
a reservation can either be canceled or not canceled.

Two complementary approaches were used:

- `statsmodels.Logit` for statistical interpretation of the model;
- `scikit-learn.LogisticRegression` for predictive modeling and evaluation.

The statistical model produced a **Pseudo R² of 0.484**, with an LLR p-value
below 0.05, indicating that the predictors collectively provide statistically
significant information for the model.

## Relevant Predictors

The analysis highlighted several variables associated with booking
cancellation probability.

Among the variables with stronger effects were characteristics related to:

- distribution channel;
- customer type;
- deposit type;
- country of origin;
- travel agents;
- previous cancellations;
- lead time;
- average daily rate (ADR).

Distribution channels, particularly travel agency / tour operator and direct
channels, showed strong relevance in the fitted model.

## Model Evaluation

The predictive model was evaluated using a **70/30 train-test split** of the
balanced modeling dataset.

### Accuracy

**84%**

### Classification Report

| Class | Precision | Recall | F1-score |
|---|---:|---:|---:|
| Not canceled | 0.82 | 0.88 | 0.84 |
| Canceled | 0.87 | 0.80 | 0.83 |
| **Overall** | **0.84** | **0.84** | **0.84** |

### Confusion Matrix

```text
[[11596  1655]
 [ 2626 10784]]

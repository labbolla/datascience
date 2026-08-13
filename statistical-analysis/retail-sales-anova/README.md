# Retail Sales Statistical Analysis with ANOVA

Statistical analysis project focused on comparing **product prices and quantities across different countries** using exploratory analysis, hypothesis testing and parametric/non-parametric statistical methods.

The project evaluates the assumptions required for ANOVA and compares its results with a non-parametric alternative when those assumptions are violated.

## Project Objective

The main objectives are to:

* perform descriptive and graphical analysis of retail transaction data;
* compare product **Price** across countries;
* compare purchased **Quantity** across countries;
* apply Analysis of Variance (ANOVA);
* verify ANOVA assumptions;
* identify specific differences between country groups;
* apply a non-parametric alternative when the assumptions of ANOVA are not satisfied.

## Dataset

The dataset was created by combining retail data from two periods:

* 2009–2010
* 2010–2011

The combined dataset contains:

* **1,067,371 observations**
* **8 original variables**

Original variables include:

* Invoice
* StockCode
* Description
* Quantity
* InvoiceDate
* Price
* Customer ID
* Country

For the statistical analysis, the dataset was reduced to the variables:

* `Quantity`
* `Price`
* `Country`

The original dataset contains transactions from **43 countries**.

## Data Preparation

The preprocessing workflow included:

* concatenation of the two annual datasets;
* missing-value inspection;
* duplicate detection;
* selection of relevant variables;
* analysis of country frequencies;
* removal of zero-price observations;
* transformation of `Price` and `Quantity`;
* organization of observations by country.

The original dataset contained **34,335 duplicated rows**, which were identified during the exploratory phase.

## Exploratory Data Analysis

The exploratory analysis included:

* descriptive statistics;
* country frequency analysis;
* grouped means;
* Q-Q plots;
* boxplots;
* visual inspection of price distributions;
* visual inspection of quantity distributions.

The data showed a highly unbalanced geographical distribution, with the United Kingdom representing the largest number of transactions.

## Hypothesis Testing

The analysis investigates whether average values differ between country groups.

The null hypothesis is:

**H₀: the group means are equal**

The alternative hypothesis is:

**H₁: at least one group differs from the others**

A significance level of:

`α = 0.05`

was used throughout the statistical analysis.

## ANOVA

Separate ANOVA models were created for:

* **Price**
* **Quantity**

using Ordinary Least Squares models with `statsmodels`.

### ANOVA Results

| Variable | F-statistic |          p-value | Result    |
| -------- | ----------: | ---------------: | --------- |
| Price    |   **12.31** | **3.01 × 10⁻⁵⁶** | Reject H₀ |
| Quantity |  **225.87** |      **< 0.001** | Reject H₀ |

The ANOVA results indicate statistically significant differences between country groups for both variables.

This means that at least one country group differs from the others in terms of price and quantity.

## Post-hoc Analysis — Tukey HSD

A **Tukey HSD test** was applied to investigate pairwise differences between country groups.

The post-hoc analysis identified specific country combinations with statistically significant differences.

For price, countries such as:

* Hong Kong
* Singapore
* Norway

were among the groups showing significant differences relative to several other countries.

Differences in quantity were also identified among multiple country groups.

## ANOVA Assumption Analysis

Because ANOVA relies on assumptions about the underlying data, additional diagnostic tests were conducted.

### Normality

Normality was investigated using:

* Q-Q plots;
* Shapiro-Wilk test;
* Kolmogorov-Smirnov test.

The residuals did **not** satisfy the normality assumption.

For example:

* Price residuals: Kolmogorov-Smirnov p-value < 0.001
* Quantity residuals: Kolmogorov-Smirnov p-value < 0.001

Therefore, the null hypothesis of normality was rejected.

## Homogeneity of Variance

The **Levene test** was used to evaluate whether the variance was homogeneous across country groups.

### Results

| Variable | Levene statistic |     p-value |
| -------- | ---------------: | ----------: |
| Price    |       **12.402** | **< 0.001** |
| Quantity |      **192.499** | **< 0.001** |

The results indicate **heteroscedasticity**, meaning that group variances are not equal.

Because both normality and homogeneity-of-variance assumptions were violated, the ANOVA results were complemented with a non-parametric analysis.

## Non-Parametric Analysis

### Kruskal-Wallis Test

The **Kruskal-Wallis test** was used as a non-parametric alternative for comparing country groups.

### Results

| Variable | Kruskal-Wallis statistic |     p-value |
| -------- | -----------------------: | ----------: |
| Price    |              **2149.47** | **< 0.001** |
| Quantity |             **52315.55** | **< 0.001** |

The Kruskal-Wallis test also rejects the null hypothesis.

Therefore, the non-parametric analysis confirms the main ANOVA result: **the distributions of price and quantity differ significantly across countries**.

## Main Findings

The analysis produced several important conclusions:

* price distributions vary significantly across countries;
* quantity distributions also vary significantly across countries;
* ANOVA detects statistically significant differences;
* Tukey HSD identifies specific pairwise differences;
* residuals do not follow a normal distribution;
* group variances are heterogeneous;
* Kruskal-Wallis confirms the presence of significant differences without relying on ANOVA's normality assumption.

The agreement between the parametric and non-parametric approaches strengthens the evidence that geographical groups exhibit different purchasing patterns.

## Technologies

* Python
* Pandas
* NumPy
* SciPy
* statsmodels
* Matplotlib
* Seaborn
* Plotly
* Jupyter Notebook / Google Colab

## Statistical Methods

* Exploratory Data Analysis
* Descriptive Statistics
* Hypothesis Testing
* One-Way ANOVA
* Ordinary Least Squares
* Tukey HSD
* Q-Q Plots
* Shapiro-Wilk Test
* Kolmogorov-Smirnov Test
* Levene Test
* Kruskal-Wallis Test
* Parametric vs Non-Parametric Analysis

## Conclusions

The project demonstrates the importance of **checking statistical assumptions rather than relying only on the initial ANOVA result**.

Although ANOVA indicated significant differences between countries for both price and quantity, the diagnostic analysis showed violations of normality and homogeneity of variance.

For this reason, the analysis was complemented with the **Kruskal-Wallis non-parametric test**, which confirmed statistically significant differences between country groups.

This workflow illustrates a practical approach to hypothesis testing in real-world data, where theoretical assumptions may not always be satisfied.

## Files

* 📓 [Jupyter Notebook](retail_sales_anova.ipynb)
* 🌐 [HTML version with outputs and visualizations](retail_sales_anova.html)

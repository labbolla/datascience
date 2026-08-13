# Real Estate Price Prediction with Linear Regression

Data Science project focused on analyzing the factors associated with residential property prices and developing a **Linear Regression model** for real estate price estimation.

The project combines **Exploratory Data Analysis, statistical modeling, regression diagnostics, feature engineering and predictive validation**.

## Project Objective

The objective is to investigate the relationship between property characteristics and sale prices and develop a regression model capable of estimating real estate values.

The analysis places particular emphasis on:

* identifying variables associated with property prices;
* evaluating the statistical assumptions of Linear Regression;
* detecting influential observations and outliers;
* reducing multicollinearity;
* improving model specification;
* evaluating predictive performance on unseen validation data.

## Dataset

The analysis contains **21,613 residential property observations**.

The dataset includes several characteristics related to the properties, such as:

* price;
* living area;
* property grade;
* location / ZIP code;
* bedrooms;
* bathrooms;
* floors;
* waterfront information;
* condition;
* construction and renovation characteristics;
* other structural attributes.

The dependent variable used in the regression analysis is:

`price`

## Exploratory Data Analysis

The initial analysis includes:

* descriptive statistics;
* frequency distributions;
* boxplots for outlier identification;
* countplots for categorical/discrete variables;
* correlation analysis;
* pairwise scatter plots;
* analysis of the relationship between property characteristics and price.

Particular attention was given to:

### Property Grade

The relationship between `grade` and `price` was analyzed to determine how the quality rating of a property is associated with its market value.

### Location

The relationship between `zipcode` and `price` was also analyzed to investigate the influence of geographic location on property prices.

## Initial Linear Regression Analysis

Initial regression models were developed using variables with strong relationships with property prices, including:

* `sqft_living`
* `grade`

The models were evaluated statistically and graphically to assess the assumptions underlying Linear Regression.

## Regression Diagnostics

Several diagnostic techniques were applied to investigate the validity of the regression model.

### Influential Observations

**Cook's Distance** was used to identify observations with a strong influence on the fitted regression model.

Highly influential observations were subsequently considered during model adjustment.

### Homoscedasticity

The **Breusch-Pagan test** was used to evaluate whether the variance of the residuals remained approximately constant.

### Normality

Residual normality was investigated using statistical and graphical techniques, including:

* Shapiro-Wilk test;
* Kolmogorov-Smirnov test;
* Anderson-Darling test;
* residual distribution plots.

The diagnostic analysis indicated that the normality assumption was not fully satisfied, while the adjusted model provided better results for linearity and homoscedasticity.

## Model Adjustment

Because the initial regression assumptions were not sufficiently satisfied, the model was reformulated.

Based on the exploratory analysis, two main predictors were selected:

* `grade`
* `zipcode`

`zipcode` was transformed into dummy variables so that geographic information could be incorporated into the regression model.

## Multicollinearity Analysis

The **Variance Inflation Factor (VIF)** was calculated to identify variables contributing to multicollinearity.

Variables with stronger multicollinearity effects were evaluated and removed during model refinement.

## Logarithmic Transformation

A logarithmic transformation was applied to the dependent variable:

```python
log10(price)
```

The transformation was introduced to improve model behavior and the relationship between predictors and the dependent variable.

## OLS Regression

The adjusted model was estimated using **Ordinary Least Squares (OLS)** with `statsmodels`.

Main predictors:

* property `grade`;
* geographic location represented by `zipcode` dummy variables.

### Model Results

| Metric             |    Result |
| ------------------ | --------: |
| Observations       |    21,613 |
| R²                 | **0.729** |
| Adjusted R²        | **0.728** |
| F-statistic        |     920.5 |
| Model significance | p < 0.001 |

The model explains approximately **72.9% of the variability** in the transformed property price using property grade and geographic location.

The regression coefficients also highlight the importance of location: different ZIP codes show substantial positive or negative associations with estimated property values.

## Outlier Treatment

Cook's Distance was applied again to the adjusted model to identify highly influential observations.

Observations with stronger influence were removed and the regression was subsequently re-estimated.

The adjusted data were then used for additional diagnostic evaluation.

## Final Model Validation

A Machine Learning validation step was performed using `scikit-learn`.

The dataset was divided into:

* **80% training data**
* **20% validation data**

A Linear Regression model was trained on the training dataset and evaluated on both training and validation samples.

### Performance

| Metric | Training |  Validation |
| ------ | -------: | ----------: |
| MSE    |  0.01096 | **0.01077** |
| R²     |   0.7636 |  **0.7654** |

The similar performance between training and validation datasets indicates that the model maintained comparable predictive behavior on unseen validation observations.

Residual plots were also used to compare prediction errors across both datasets.

## Statistical Findings

The final diagnostic analysis showed that:

* the assumption of **normality of residuals was rejected**;
* the assumptions related to **linearity** were not rejected;
* the assumptions related to **homoscedasticity** were not rejected.

Therefore, the analysis also illustrates the practical limitations and assumptions that must be considered when applying Linear Regression to real-world data.

## Technologies

* Python
* Pandas
* NumPy
* SciPy
* statsmodels
* scikit-learn
* Matplotlib
* Seaborn
* Jupyter Notebook / Google Colab

## Statistical & Machine Learning Methods

* Exploratory Data Analysis
* Correlation Analysis
* Linear Regression
* Ordinary Least Squares (OLS)
* Logarithmic Transformation
* Dummy Variables
* Variance Inflation Factor (VIF)
* Cook's Distance
* Breusch-Pagan Test
* Shapiro-Wilk Test
* Kolmogorov-Smirnov Test
* Anderson-Darling Test
* Residual Analysis
* Train / Validation Split
* Mean Squared Error
* R² Evaluation

## Conclusions

The analysis demonstrates how real estate prices can be modeled using a combination of **property quality and geographic location**.

The project also illustrates that building a regression model involves more than fitting an algorithm: statistical assumptions, outliers, multicollinearity, variable transformations and model validation all need to be evaluated.

After model adjustment and validation, the Linear Regression model achieved approximately **76.5% R² on the validation dataset**, with very similar performance between training and validation samples.

## Files

* 📓 [Jupyter Notebook](real_estate_linear_regression.ipynb)
* 🌐 [HTML version with outputs and visualizations](real_estate_linear_regression.html)

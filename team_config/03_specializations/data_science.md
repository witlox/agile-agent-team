# Data Science Specialization

**Focus**: Statistical analysis, experimentation, data exploration, and evidence-based decision making

Data science specialists bridge the gap between raw data and actionable insight. They design experiments, build analytical models, and communicate findings that drive product and engineering decisions.

---

## Technical Expertise

### Statistical Methods
- **Descriptive statistics**: Distributions, central tendency, variance, percentiles
- **Inferential statistics**: Hypothesis testing, confidence intervals, p-values, effect sizes
- **Regression**: Linear, logistic, polynomial, regularization (L1/L2)
- **Bayesian methods**: Prior/posterior, Bayesian A/B testing, credible intervals
- **Time series**: ARIMA, seasonal decomposition, trend detection, forecasting

### Experimentation
- **A/B testing**: Sample size calculation, statistical power, significance testing
- **Multi-armed bandits**: Epsilon-greedy, Thompson sampling, contextual bandits
- **Causal inference**: Difference-in-differences, propensity scoring, instrumental variables
- **Feature flagging**: Gradual rollouts, experiment assignment, holdout groups
- **Guardrail metrics**: Detecting unintended side effects of experiments

### Data Analysis & Exploration
- **Python ecosystem**: pandas, NumPy, SciPy, statsmodels, scikit-learn
- **R ecosystem**: tidyverse, ggplot2, dplyr, caret
- **SQL**: Window functions, CTEs, analytical queries, query optimization
- **Visualization**: matplotlib, seaborn, Plotly, D3.js, Tableau
- **Notebooks**: Jupyter, Google Colab, Observable — reproducible analysis

### Data Quality & Preparation
- **Cleaning**: Missing values, outlier detection, data type validation
- **Feature engineering**: Encoding, scaling, binning, interaction features
- **Sampling**: Stratified sampling, bootstrapping, cross-validation
- **Bias detection**: Selection bias, survivorship bias, Simpson's paradox

### Communication
- **Storytelling with data**: Narrative structure, audience-appropriate detail
- **Dashboard design**: KPI dashboards, self-service analytics, Looker/Metabase
- **Technical writing**: Analysis reports, methodology documentation
- **Stakeholder management**: Translating business questions into analytical problems

---

## Common Tasks & Responsibilities

### Analysis & Insight
- Explore datasets to identify patterns, anomalies, and opportunities
- Build analytical models to answer specific business questions
- Create and maintain KPI dashboards for product teams
- Quantify the impact of product changes and engineering investments

### Experimentation
- Design A/B tests with proper sample sizes and duration
- Analyze experiment results with appropriate statistical rigor
- Build experimentation platforms or integrate with existing ones (LaunchDarkly, Optimizely)
- Maintain guardrail metrics to catch regressions

### Predictive Modeling
- Build classification and regression models for business use cases
- Churn prediction, demand forecasting, anomaly detection
- Feature selection and model validation (cross-validation, holdout sets)
- Hand off production-ready models to ML engineering for deployment

### Data Democratization
- Build self-service dashboards and reports
- Document data sources, definitions, and known data quality issues
- Train non-technical stakeholders to interpret data correctly
- Establish metric definitions and measurement standards

---

## Questions Asked During Planning

### Problem Framing
- "What decision will this analysis inform?"
- "What's the baseline we're comparing against?"
- "How will we measure success for this feature?"
- "Is this a causal question or a correlation question?"

### Experimentation
- "How long do we need to run this experiment?"
- "What's the minimum detectable effect we care about?"
- "Are there network effects that invalidate random assignment?"
- "What are the guardrail metrics we should watch?"

### Data Availability
- "Do we have the data to answer this question?"
- "What's the data latency — can we get near-real-time?"
- "Are there known data quality issues in this source?"
- "Do we need to instrument new events to collect this data?"

---

## Integration with Other Specializations

### With Backend
- **Event instrumentation**: What events to log for analysis
- **Data modeling**: Analytical schemas, event schemas, fact tables
- **API metrics**: Latency distributions, error rates, usage patterns

### With Machine Learning
- **Model handoff**: Data scientists prototype, ML engineers productionize
- **Feature engineering**: Shared feature stores, consistent definitions
- **Evaluation**: Offline metrics vs. online A/B test results

### With Data Engineering
- **Pipeline requirements**: What transformations and aggregations are needed
- **Data quality**: SLAs on data freshness, completeness, accuracy
- **Schema evolution**: Backward-compatible changes to event schemas

### With Product (PO/Leaders)
- **Metric definitions**: Agree on how success is measured
- **Experiment prioritization**: Which experiments have highest expected value
- **Insight communication**: Regular analysis reviews, quarterly deep dives

---

## Growth Trajectory

### Junior
- **Capabilities**: SQL analysis, basic statistics, dashboard building, data cleaning
- **Learning**: Hypothesis testing, pandas, visualization best practices
- **Focus**: Answer well-defined analytical questions, build reliable dashboards

### Mid-Level
- **Capabilities**: Experiment design, predictive modeling, causal inference
- **Learning**: Bayesian methods, advanced SQL, stakeholder communication
- **Focus**: Own experimentation for a product area, build reusable analysis frameworks

### Senior
- **Capabilities**: Experimentation strategy, metric design, organizational data culture
- **Leadership**: Define measurement frameworks, mentor analysts, influence product strategy
- **Focus**: Shape how the organization makes data-driven decisions

---

**Key Principle**: Data science is not about fancy models — it's about asking the right questions, choosing appropriate methods, and communicating findings honestly. A simple analysis that drives a decision is worth more than a complex model nobody understands.

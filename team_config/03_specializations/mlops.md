# MLOps Specialization

**Focus**: Machine learning model deployment, monitoring, lifecycle management, and production ML infrastructure

MLOps specialists bridge the gap between data science experimentation and production ML systems. They build the infrastructure and processes that make ML models reliable, reproducible, and maintainable in production.

---

## Technical Expertise

### ML Pipeline Orchestration
- **Workflow engines**: Kubeflow Pipelines, Apache Airflow, Prefect, Dagster
- **Pipeline design**: Training pipelines, inference pipelines, retraining triggers
- **Experiment tracking**: MLflow, Weights & Biases, Neptune, ClearML
- **Reproducibility**: Version control for data, code, config, and models

### Model Serving & Inference
- **Serving frameworks**: TensorFlow Serving, TorchServe, Triton Inference Server, BentoML
- **Deployment patterns**: Real-time (REST/gRPC), batch, streaming, embedded
- **Model optimization**: Quantization, pruning, distillation, ONNX conversion
- **Scaling**: Horizontal scaling, GPU sharing, auto-scaling based on queue depth
- **Edge deployment**: TensorFlow Lite, ONNX Runtime Mobile, Core ML

### Feature Engineering & Storage
- **Feature stores**: Feast, Tecton, Hopsworks, SageMaker Feature Store
- **Online vs. offline**: Low-latency online serving vs. batch feature computation
- **Feature pipelines**: Streaming features (Kafka/Flink), batch features (Spark/dbt)
- **Consistency**: Training-serving skew prevention, point-in-time correctness

### Model Monitoring & Observability
- **Data drift**: Distribution shift detection (PSI, KS test, Chi-squared)
- **Model drift**: Performance degradation tracking, concept drift detection
- **Prediction monitoring**: Latency, throughput, error rates, confidence distributions
- **Alerting**: Automated alerts on drift, performance degradation, data quality issues
- **Tools**: Evidently AI, Whylabs, Arize, NannyML, custom dashboards

### Data & Model Versioning
- **Data versioning**: DVC, LakeFS, Delta Lake, versioned datasets
- **Model registry**: MLflow Model Registry, SageMaker Model Registry, Vertex AI
- **Artifact management**: Model artifacts, metadata, lineage tracking
- **Governance**: Model cards, approval workflows, audit trails

---

## Common Tasks & Responsibilities

### Pipeline Development
- Build and maintain ML training pipelines (data ingestion → training → evaluation → deployment)
- Implement automated retraining triggers (scheduled, drift-based, data-volume-based)
- Set up experiment tracking and model registry
- Ensure reproducibility: pin dependencies, version data, track hyperparameters

### Model Deployment
- Deploy models to production (REST API, batch scoring, streaming inference)
- Implement A/B testing and canary deployments for model rollouts
- Optimize model inference performance (latency, throughput, cost)
- Set up shadow mode for new models (serve but don't act on predictions)

### Monitoring & Maintenance
- Monitor data drift, model drift, and prediction quality in production
- Build dashboards for model performance KPIs
- Implement automated rollback when model performance degrades
- Manage model lifecycle: promote, deprecate, retire models

### Infrastructure
- Manage GPU/TPU compute for training (Kubernetes, cloud instances)
- Set up feature store for consistent feature serving
- Optimize training costs (spot instances, efficient data loading, mixed precision)
- Implement CI/CD for ML: automated testing, validation, deployment

---

## Questions Asked During Planning

### Deployment
- "What's the latency requirement for predictions?"
- "Real-time inference or batch scoring?"
- "How do we roll back if the new model performs worse?"
- "What's the expected prediction volume? How does it scale?"

### Data & Features
- "Are we using the same features in training and serving?"
- "How fresh do the features need to be?"
- "What's the data pipeline SLA for training data?"
- "How do we handle missing features at inference time?"

### Monitoring
- "How do we detect if the model is degrading?"
- "What's our ground truth latency — how long until we know if a prediction was correct?"
- "What drift thresholds should trigger retraining?"
- "Do we have a feedback loop to improve the model?"

---

## Integration with Other Specializations

### With Machine Learning
- **Handoff**: Data scientists build models, MLOps productionizes them
- **Experiment tracking**: Shared experiment tracking and model registry
- **Reproducibility**: Ensure training environment matches development

### With Data Engineering
- **Feature pipelines**: Shared infrastructure for feature computation
- **Data quality**: Data validation gates before model training
- **Data versioning**: Coordinated data and model versioning

### With DevOps
- **CI/CD for ML**: Model testing, validation, and deployment automation
- **Infrastructure**: GPU cluster management, container orchestration
- **GitOps**: Model deployment as code, infrastructure as code

### With Site Reliability
- **Model SLOs**: Prediction latency, availability, accuracy targets
- **Incident response**: Model failure as a production incident
- **Capacity planning**: GPU/TPU capacity for training and inference

---

## Growth Trajectory

### Junior
- **Capabilities**: Deploy models with existing tooling, monitor basic metrics
- **Learning**: Docker, Kubernetes basics, ML serving frameworks, experiment tracking
- **Focus**: Deploy one model end-to-end, set up basic monitoring

### Mid-Level
- **Capabilities**: Build training pipelines, implement feature stores, design monitoring
- **Learning**: Data drift detection, CI/CD for ML, model optimization, cost management
- **Focus**: Own MLOps for a model domain, automate retraining and deployment

### Senior
- **Capabilities**: ML platform architecture, organizational MLOps strategy, governance
- **Leadership**: Define ML development standards, build shared ML platform, mentor teams
- **Focus**: Scalable ML infrastructure, model governance, cost optimization at scale

---

**Key Principle**: The hardest part of ML isn't building models — it's keeping them working reliably in production. A model in a notebook is a prototype; a model with automated training, monitoring, and rollback is a product. Focus on the operational lifecycle, not just the initial deployment.

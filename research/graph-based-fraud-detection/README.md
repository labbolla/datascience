# Graph-Based Fraud Detection in Financial Transactions

Research project focused on **fraud detection in financial transaction networks** using graph analytics, graph databases and structural risk analysis.

The study explores a hybrid approach based on **Personalized PageRank (PPR)**, **Louvain Community Detection** and **Label Propagation**, using **Neo4j** to model relationships between users, cards, IP addresses, devices, products and transactions.

## Project Objective

Traditional fraud detection approaches based only on static rules or tabular analysis may fail to identify complex relationships between apparently independent transactions.

The objective of this research is to investigate whether **graph-based analysis** can reveal hidden patterns associated with coordinated or distributed financial fraud.

The approach aims to:

- represent financial transactions as a graph;
- identify structurally relevant entities;
- detect highly connected communities;
- identify suspicious relationships between users, cards, IPs and devices;
- propagate structural risk through the transaction network;
- compare alternative graph algorithms for fraud detection;
- generate risk indicators that could later be integrated into supervised Machine Learning models.

## Dataset

The experiment uses a **synthetic dataset containing more than 2 million financial transaction records** from an e-commerce environment.

The transactions cover the period:

```text
January 2023 – December 2024
```

The dataset contains information related to:

- transaction identifiers;
- users;
- cards;
- IP addresses;
- geographic information;
- devices;
- products;
- transaction values;
- authentication methods;
- transaction status;
- risk indicators;
- timestamps.

The analysis also considers approximately **200,000 unique users**.

> The dataset used in this research is synthetic and does not contain real customer financial information.

## Data Preparation

Before graph construction, the transactional dataset was preprocessed and normalized.

The preparation process included:

- removal of duplicated entities;
- treatment of missing and inconsistent values;
- normalization of categorical information;
- standardization of products and geographic attributes;
- organization of users, cards, devices and other entities;
- preparation of relational structures for graph export.

Sensitive identifiers were anonymized as part of the experimental methodology.

## Data Architecture

The project uses a two-stage data architecture.

```text
Transactional Data
       ↓
Data Cleaning & Normalization
       ↓
PostgreSQL
       ↓
Graph Export
       ↓
Neo4j
       ↓
Graph Analytics
       ↓
Risk Scores & Fraud Detection
```

The raw transactional information is initially structured and normalized in **PostgreSQL**.

The resulting relational data are then exported to **Neo4j**, where the entities are represented as nodes and their relationships as directed edges.

## Graph Model

The transaction network contains several entity types.

### Nodes

```text
User
Card
IP Address
Device
Product
Transaction
```

### Relationships

Examples of graph relationships include:

```text
USOU_CARTAO
ACESSOU_DE_IP
COMPROU_PRODUTO
ENTREGOU_EM
UTILIZOU_DISPOSITIVO
```

This structure makes it possible to analyze relationships that are difficult to identify through isolated transaction records.

For example, multiple users sharing the same:

- credit card;
- device;
- IP address;
- product patterns;
- transactional paths

may indicate coordinated or anomalous behavior.

## Graph Analytics Approach

Three main graph algorithms were evaluated:

1. **Personalized PageRank**
2. **Louvain Community Detection**
3. **Label Propagation**

These algorithms address different aspects of the transaction network.

## Personalized PageRank

Personalized PageRank extends traditional PageRank by introducing a preference or seed vector.

Instead of distributing probability uniformly across the graph, the algorithm gives additional importance to selected nodes associated with suspicious or fraudulent behavior.

Conceptually:

```text
Known / Suspicious Entities
          ↓
Personalized PageRank
          ↓
Structural Risk Propagation
          ↓
Related High-Risk Entities
```

This allows the system to identify entities that may not be directly connected to known fraud cases but occupy structurally important positions within suspicious transaction networks.

Examples include:

- users connected to multiple suspicious transactions;
- cards shared across different users;
- repeated devices;
- shared IP addresses;
- central entities within fraudulent transaction chains.

## Community Detection with Louvain

The **Louvain algorithm** was used to identify communities with high internal connectivity.

Dense communities can reveal groups of entities that interact more frequently with each other than with the rest of the network.

In a fraud-detection context, these communities may expose:

- coordinated users;
- shared cards;
- reused devices;
- repeated IP addresses;
- organized fraud structures.

One analyzed sample identified communities with different structural characteristics.

| Community | Nodes | Average Degree | Suspicious Entities | Confirmed Fraud |
|---|---:|---:|---:|---:|
| 1 | 168 | 3.2 | 12 | 7 |
| 2 | 84 | 2.1 | 4 | 2 |
| 3 | 129 | 2.7 | 0 | 0 |

Community 1 showed the strongest concentration of entities associated with fraudulent behavior.

## Label Propagation

**Label Propagation** was also evaluated as an unsupervised community-detection technique.

The algorithm propagates labels through neighboring nodes based on local connectivity.

This makes it useful for detecting:

- temporary communities;
- weakly connected structures;
- evolving transaction patterns;
- distributed relationships.

Its adaptive behavior can be useful when transaction networks change rapidly and only limited labeling information is available.

## Risk Analysis

Graph-derived information was used to identify entities exhibiting structural indicators of anomalous behavior.

The study analyzed approximately:

```text
200,000 users
```

and identified around:

```text
18,300 users
```

with strong indicators of potentially fraudulent behavior.

This corresponds to approximately:

```text
9.15%
```

of the analyzed users.

The study also reports an average of approximately:

```text
25 suspicious attempts per anomalous user
```

and a potentially compromised value exceeding:

```text
R$ 3.95 million
```

during the analyzed period.

Because the experiment uses synthetic data, these values represent results from the experimental dataset rather than real financial losses.

## Behavioral Patterns

Several recurring structural patterns were identified among suspicious entities.

These included:

- multiple cards associated with the same user;
- repeated use of IP addresses;
- shared devices;
- high transaction frequency;
- unusual transaction timing;
- highly connected transactional structures;
- recurring combinations of financial entities.

Among the 100 users with the highest suspicious transaction activity, the study observed recurring use of multiple cards and different card brands.

These patterns complement the graph-based centrality and community analysis.

## Algorithm Evaluation

The algorithms were evaluated using simulated fraud labels.

### Classification Metrics

| Algorithm | Precision | Recall | F1-score | Accuracy | AUC |
|---|---:|---:|---:|---:|---:|
| **PageRank + Threshold** | **0.87** | **0.68** | **0.76** | **0.92** | **0.89** |
| Louvain | 0.75 | 0.54 | 0.63 | 0.86 | 0.76 |
| Label Propagation | 0.69 | 0.51 | 0.59 | 0.83 | 0.68 |

**Personalized PageRank with thresholding achieved the strongest overall performance.**

Its AUC of approximately:

```text
0.89
```

indicates better discrimination between normal and structurally suspicious entities than the other evaluated graph algorithms.

## ROC Analysis

ROC curves were generated to compare the discriminative performance of the three approaches.

The reported AUC values were:

```text
Personalized PageRank → 0.89
Louvain               → 0.76
Label Propagation     → 0.68
```

The results suggest that centrality and structural influence provide particularly useful signals for identifying suspicious entities in the analyzed transaction network.

## Main Findings

The research indicates several potential advantages of graph-based fraud analysis:

- detection of indirect relationships between suspicious entities;
- identification of coordinated fraud structures;
- discovery of dense transactional communities;
- analysis of shared cards, devices and IP addresses;
- structural risk propagation;
- reduction of irrelevant alerts through relational context;
- improved interpretability through graph visualization;
- generation of graph-derived features for future Machine Learning models.

The results also indicate that **Personalized PageRank provided the strongest performance among the evaluated graph algorithms**.

## Hybrid Machine Learning Potential

An important outcome of the graph analysis is the possibility of generating new predictive features.

Examples include:

```text
PageRank Score
Node Degree
Community Membership
Neighborhood Risk
Number of Shared Devices
Number of Shared Cards
Structural Centrality
```

These graph-derived variables could be incorporated into supervised Machine Learning models.

A future hybrid architecture could therefore follow:

```text
Transaction Data
      ↓
Graph Analytics
      ↓
Structural Features
      ↓
Supervised Machine Learning
      ↓
Fraud Probability
```

## Technologies

- Neo4j
- Neo4j Graph Data Science (GDS)
- PostgreSQL
- Python
- Google Colab
- Graph Databases
- Graph Analytics
- Data Mining

## Algorithms & Methods

- Personalized PageRank
- PageRank
- Louvain Community Detection
- Label Propagation
- Graph Centrality
- Community Detection
- Modular Analysis
- Neighborhood Analysis
- Risk Propagation
- ROC Analysis
- Classification Metrics

## Research Areas

`Fraud Detection` · `Graph Analytics` · `Graph Databases` · `Neo4j` · `Personalized PageRank` · `Community Detection` · `Big Data` · `Data Mining` · `Financial Analytics` · `Anomaly Detection`

## Limitations

The study has several important limitations.

The transaction dataset is **synthetic**, meaning that the experimental results cannot be interpreted as direct performance measurements on real banking transactions.

The evaluation also relies on simulated fraud labels rather than complete real-world fraud annotations.

In addition:

- real-time labeling remains challenging;
- very large dynamic graphs may introduce scalability constraints;
- graph algorithms can be sensitive to network topology;
- real production deployment would require validation on regulated financial datasets.

## Future Work

Future research proposed in the study includes:

- combining graph features with supervised Machine Learning models;
- integration with models such as XGBoost and neural networks;
- deployment using Neo4j GDS pipelines;
- real-time fraud monitoring;
- investigation of Graph Neural Networks;
- graph explainability techniques such as GNNExplainer and SubgraphX;
- applications to account manipulation, self-fraud and money laundering detection.

## Research Paper

📄 **[Read the full paper](graph_based_fraud_detection.pdf)**

## Authors

**Alexon Amaro de Oliveira, Nicola Defonte and Félix Garcia**

Postgraduate Program in Applied Computing  
University of Brasília (UnB)  
Brasília, Brazil

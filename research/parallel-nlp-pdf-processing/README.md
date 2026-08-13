# Parallel NLP Processing of Historical PDF Collections

Research project focused on the parallelization and performance evaluation of an **NLP and text-mining pipeline** for large-scale processing of academic PDF collections.

The study compares **Python Multiprocessing** and **Dask** as parallelization strategies for accelerating the extraction of themes and representative keywords from heterogeneous, unstructured Portuguese-language documents.

## Project Overview

The project was developed in the context of the **Oxossi** research initiative at the University of Brasília (UnB), which processes collections of academic and historical documents to identify relevant themes and keywords.

The complete corpus contains approximately **9,365 PDF documents**, including files with heterogeneous sizes, scanned content, irregular structures and noisy formatting.

The main objectives were to:

* process large collections of unstructured PDF documents;
* extract and preprocess textual information;
* identify representative themes and keywords;
* construct semantic co-occurrence graphs;
* parallelize CPU-intensive NLP workloads;
* compare alternative parallel-processing strategies;
* evaluate execution time, CPU utilization, memory consumption and scalability.

## NLP Processing Pipeline

The processing workflow includes:

```text
PDF Documents
      ↓
Text Extraction
      ↓
File Validation
      ↓
Language Detection
      ↓
Text Cleaning
      ↓
Bigram Extraction
      ↓
Lemmatization & POS Tagging
      ↓
Co-occurrence Graph Construction
      ↓
PageRank
      ↓
Theme / Keyword Extraction
```

### Main Technologies

* **Python**
* **Dask**
* **Multiprocessing**
* **spaCy**
* **NetworkX**
* **PyMuPDF / PyPDF2**
* **Lingua**
* **PageRank**
* **Natural Language Processing (NLP)**
* **Text Mining**
* **Graph Analysis**
* **Parallel Computing**
* **CRISP-DM**

## Parallel Processing

Two parallelization approaches were evaluated.

### Python Multiprocessing

Files are distributed across independent worker processes using Python's native multiprocessing capabilities.

This approach is particularly suitable for file-level CPU-bound workloads where individual documents can be processed independently.

### Dask

Dask uses a task-scheduling architecture based on directed acyclic graphs (DAGs), allowing more flexible management of computational workflows and providing potential scalability toward more complex or distributed processing scenarios.

## Performance Evaluation

The main benchmark used a stratified sample of **500 PDF documents** processed on a single-node environment with **7 workers**.

| Approach        | Execution Time |   Speedup | Parallel Efficiency |
| --------------- | -------------: | --------: | ------------------: |
| Sequential      |     3h 58m 34s |     1.00× |                   — |
| Multiprocessing |        43m 38s | **5.47×** |          **78.14%** |
| Dask            |     1h 07m 38s | **3.53×** |          **50.39%** |

For this file-level workload, **Python Multiprocessing achieved the best overall performance**, combining higher speedup with lower memory consumption.

Dask introduced greater scheduling and memory overhead in the tested single-node environment, while retaining potential advantages for more complex task graphs, intra-document parallelization and distributed workloads.

## My Contribution

My work on the project included:

* design and implementation of the parallel processing architecture;
* integration and adaptation of the NLP preprocessing pipeline;
* implementation of the **Python Multiprocessing** solution;
* implementation of the **Dask** solution;
* design of the PDF-processing workflow;
* performance benchmarking;
* analysis of execution time, CPU utilization, memory consumption and parallel efficiency.

## Research Areas

`Natural Language Processing` · `Text Mining` · `Unstructured Data` · `Parallel Computing` · `Dask` · `Multiprocessing` · `Graph Analysis` · `PageRank` · `Data Mining` · `Performance Benchmarking`

## Research Paper

📄 **[Read the full paper](parallel_nlp_processing_historical_pdfs.pdf)**

### Authors

**Nicola Defonte**, Claudio Henrique M. de Oliveira, Marcelo Ladeira and Gustavo van Erven
University of Brasília (UnB), Brasília, Brazil

# Parallel NLP Processing of Historical PDF Collections

Research project developed at the University of Brasília (UnB) focusing on
the parallelization of an NLP pipeline for large-scale processing of
Portuguese-language academic PDF collections.

## Overview

The project evaluates two parallel processing strategies — Python
Multiprocessing and Dask — for accelerating an NLP pipeline designed
to extract themes and representative keywords from unstructured
academic documents.

The pipeline combines PDF text extraction, linguistic preprocessing,
bigram detection, semantic graph construction and PageRank-based
keyword extraction.

## Technologies

- Python
- Dask
- Multiprocessing
- spaCy
- NetworkX
- PyMuPDF / PyPDF2
- NLP
- Text Mining
- PageRank
- CRISP-DM
- Parallel Computing

## Pipeline

PDF Extraction
→ Validation
→ Language Detection
→ Text Cleaning
→ Bigram Extraction
→ Lemmatization
→ Co-occurrence Graph
→ PageRank
→ Theme Extraction

## Parallel Processing

Two approaches were compared:

- Python Multiprocessing
- Dask

In the benchmark with 500 PDF documents and 7 workers:

- Multiprocessing: 5.47× speedup and 78.14% parallel efficiency
- Dask: 3.53× speedup and 50.39% parallel efficiency

Multiprocessing demonstrated better performance for file-level
parallelism on the evaluated single-node environment.

## My Contribution

I designed and implemented the parallel processing architecture,
including the Multiprocessing and Dask implementations and the
performance benchmarking.

I also adapted and integrated the NLP preprocessing module into the
parallel processing pipeline.

## Research Areas

Natural Language Processing · Text Mining · Big Data · Parallel
Computing · Unstructured Data · Graph Analysis · Data Mining

## Paper

[Read the full paper](paper/parallel_nlp_processing_historical_pdfs.pdf)

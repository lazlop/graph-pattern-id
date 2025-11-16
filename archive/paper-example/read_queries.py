#!/usr/bin/env python3
"""
Script to read and extract queries from CSV files in the react_kgqa_results directory.
"""

import csv
import os
from pathlib import Path


def read_queries_from_csv(csv_path):
    """
    Read queries from a CSV file.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        List of dictionaries containing query information
    """
    queries = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query_info = {
                'query_id': row.get('query_id', ''),
                'question': row.get('question', ''),
                'generated_sparql': row.get('generated_sparql', ''),
                'model': row.get('model', ''),
                'source_file': os.path.basename(csv_path)
            }
            queries.append(query_info)
    
    return queries


def main():
    """Main function to process all CSV files in the directory."""
    # Directory containing the CSV files
    results_dir = Path('examples/react_kgqa_results')
    
    # Find all CSV files
    csv_files = list(results_dir.glob('*.csv'))
    
    print(f"Found {len(csv_files)} CSV files in {results_dir}\n")
    
    all_queries = []
    
    # Process each CSV file
    for csv_file in csv_files:
        print(f"Processing: {csv_file.name}")
        queries = read_queries_from_csv(csv_file)
        all_queries.extend(queries)
        print(f"  - Found {len(queries)} queries\n")
    
    # Display summary
    print(f"\n{'='*80}")
    print(f"SUMMARY: Total queries extracted: {len(all_queries)}")
    print(f"{'='*80}\n")
    
    # Display each query
    for i, query in enumerate(all_queries, 1):
        print(f"\n{'='*80}")
        print(f"Query {i}/{len(all_queries)}")
        print(f"{'='*80}")
        print(f"Source File: {query['source_file']}")
        print(f"Query ID: {query['query_id']}")
        print(f"Model: {query['model']}")
        print(f"Question: {query['question']}")
        print(f"\nGenerated SPARQL Query:")
        print(f"{'-'*80}")
        print(query['generated_sparql'])
        print(f"{'-'*80}")
    
    return all_queries


if __name__ == '__main__':
    queries = main()

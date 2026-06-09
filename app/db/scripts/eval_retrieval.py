# app/db/scripts/eval_retrieval.py

import sys
import os
from pathlib import Path

# Setup Python path to include project root
project_root = Path(__file__).resolve().parents[3]
sys.path.append(str(project_root))

from app.db.connection import get_connection
from app.services.retrievel_normalised import retrieve_context

# Target evaluations: queries and expected documents
BENCHMARK_CASES = [
    {
        "query": "What projects use Redis?",
        "expected_titles": ["CollabWrite", "Workforce and Event Management Platform"]
    },
    {
        "query": "Which project demonstrates distributed systems?",
        "expected_titles": ["CollabWrite"]
    },
    {
        "query": "Tell me about DocuMind.",
        "expected_titles": ["DocuMind"]
    },
    {
        "query": "What AI-related projects has Abhinav built?",
        "expected_titles": ["DocuMind", "QRGuard: AI-Powered QR Security Scanner", "Portfolio Backend & AI Chatbot"]
    },
    {
        "query": "Which projects use FastAPI?",
        "expected_titles": ["CollabWrite", "DocuMind", "Portfolio Backend & AI Chatbot"]
    }
]


def run_evaluation():
    conn = get_connection()
    try:
        print("=" * 60)
        print("RUNNING RETRIEVAL EVALUATION BENCHMARK")
        print("=" * 60)

        total_precision = 0.0
        total_recall = 0.0
        total_reciprocal_rank = 0.0
        queries_run = 0

        for case in BENCHMARK_CASES:
            query = case["query"]
            expected = [title.lower() for title in case["expected_titles"]]
            
            # Retrieve top 5 chunks
            results = retrieve_context(query, conn, limit=5)
            retrieved_titles = [r["title"].lower() for r in results]

            # Calculate metrics
            hit_count = 0
            reciprocal_rank = 0.0
            
            for rank, title in enumerate(retrieved_titles):
                # Check for substring match in case titles differ slightly
                matched = False
                for exp in expected:
                    if exp in title or title in exp:
                        matched = True
                        break
                
                if matched:
                    hit_count += 1
                    if reciprocal_rank == 0.0:
                        reciprocal_rank = 1.0 / (rank + 1)

            # Precision@5 = hits / retrieved
            precision = hit_count / len(results) if results else 0.0
            # Recall@5 = hits / expected
            recall = hit_count / len(expected) if expected else 0.0

            total_precision += precision
            total_recall += recall
            total_reciprocal_rank += reciprocal_rank
            queries_run += 1

            print(f"\nQuery: '{query}'")
            print(f"  Expected:  {case['expected_titles']}")
            print(f"  Retrieved: {[r['title'] for r in results]}")
            print(f"  Precision@5: {precision:.2f} | Recall@5: {recall:.2f} | MRR: {reciprocal_rank:.2f}")

        # Compute aggregate metrics
        avg_precision = total_precision / queries_run if queries_run else 0.0
        avg_recall = total_recall / queries_run if queries_run else 0.0
        mrr = total_reciprocal_rank / queries_run if queries_run else 0.0

        print("\n" + "=" * 60)
        print("AGGREGATE RETRIEVAL METRICS")
        print("=" * 60)
        print(f"Total Benchmark Queries: {queries_run}")
        print(f"Average Precision@5:    {avg_precision:.4f} (Target > 0.50)")
        print(f"Average Recall@5:       {avg_recall:.4f} (Target > 0.80)")
        print(f"Mean Reciprocal Rank:   {mrr:.4f} (Target > 0.80)")
        print("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    run_evaluation()

import os
import pandas as pd
import ast
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# Attempt to load .env variables if running as a standalone script
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def run_evaluation():
    # 0. Check API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables.")
        return

    print("--- Setting up RAGAS with Gemini Judge ---")

    # 1. Configure the "Judge" (LLM) and Embeddings
    # RAGAS uses this LLM to read your bot's answers and grade them.
    # We use temperature=0 for consistent grading.
    gemini_judge = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        google_api_key=api_key,
        temperature=0
    )

    # RAGAS needs embeddings to calculate vector similarity for relevance metrics.
    gemini_embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=api_key
    )

    # 2. Load the generated data
    csv_path = "ragas_dataset.csv"
    try:
        print(f"Loading data from {csv_path}...")
        df = pd.read_csv(csv_path)
        
        # CRITICAL STEP: 
        # CSV saves lists as strings like "['text1', 'text2']". 
        # We must convert them back to actual Python lists.
        df['contexts'] = df['contexts'].apply(ast.literal_eval)
        
        # Convert to HuggingFace Dataset format required by RAGAS
        dataset = Dataset.from_pandas(df)
        print(f"✅ Loaded {len(dataset)} test samples.")
        
    except FileNotFoundError:
        print(f"❌ Error: {csv_path} not found.")
        print("   Please run: python manage.py generate_ragas_data <doc_id>")
        return
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return

    # 3. Define Metrics
    # - Faithfulness: Is the answer derived from the context? (Avoids hallucinations)
    # - Answer Relevancy: Is the answer actually addressing the question?
    # - Context Precision: Is the relevant chunk ranked highly?
    # - Context Recall: Did we retrieve the correct answer from the ground truth?
    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
    ]

    # 4. Run Evaluation
    print("\n🚀 Running RAGAS Evaluation... (This may take a minute)")
    try:
        results = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=gemini_judge,
            embeddings=gemini_embeddings
        )
    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        return

    # 5. Output Results
    print("\n--- 📊 Evaluation Results ---")
    print(results)

    # Save detailed results to CSV for analysis
    output_file = "ragas_results.csv"
    results_df = results.to_pandas()
    results_df.to_csv(output_file, index=False)
    print(f"\n✅ Detailed report saved to {output_file}")

if __name__ == "__main__":
    run_evaluation()
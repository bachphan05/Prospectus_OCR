# RAG System Improvements

## Problems Identified

### 1. Speed Issues (~11 minutes for 68-page document)
- **Sequential embedding batches**: 202 API calls processed one-by-one
- **Small batch size**: Only 10 chunks per embedding call
- **Excessive DB writes**: 202 separate database transactions
- **Small OCR batch size**: 15 pages per Gemini API call

### 2. Accuracy Issues
- **Limited retrieval**: Only top 15 chunks retrieved
- **Small chunk size**: 1000 chars might split important context
- **High overlap**: 500 char overlap creates redundancy

## Changes Made

### Speed Optimizations

1. **Increased Embedding Batch Size**
   - **Before**: 10 chunks per API call → 202 API calls for 2018 chunks
   - **After**: 50 chunks per API call → ~41 API calls
   - **Expected Improvement**: ~5x faster embedding (3 min → ~36 seconds)

2. **Reduced Database Writes**
   - **Before**: Write to DB after every batch (202 transactions)
   - **After**: Write every 200 chunks (~10 transactions)
   - **Expected Improvement**: 20x fewer DB operations

3. **Increased OCR Batch Size**
   - **Before**: 15 pages per Gemini call
   - **After**: 20 pages per Gemini call
   - **Expected Improvement**: ~25% faster content extraction

### Accuracy Optimizations

1. **Increased Chunk Size**
   - **Before**: 1000 chars with 500 overlap
   - **After**: 1500 chars with 300 overlap
   - **Benefit**: More context per chunk, less redundancy

2. **Retrieve More Chunks**
   - **Before**: Top 15 chunks
   - **After**: Top 25 chunks
   - **Benefit**: Better coverage of relevant information

## Expected Results

### Speed Improvements
- **Total processing time**: 11 min → **~4-5 minutes** (55% faster)
  - Content extraction: 7.5 min → ~6 min (OCR batch size increase)
  - Embedding: 3 min → ~36 sec (batch size + DB optimization)
  - Overhead: Same

### Accuracy Improvements
- **Better context**: Larger chunks preserve more semantic meaning
- **Better retrieval**: 67% more chunks retrieved (15 → 25)
- **Less redundancy**: Lower overlap reduces duplicate information

## Testing Recommendations

1. **Upload a new document** to test the new speed
2. **Ask complex questions** that require information from multiple sections
3. **Compare answers** with the old system to verify accuracy improvement

## Future Optimizations (Optional)

### For Even Better Speed:
1. **Parallel embedding calls**: Process multiple batches simultaneously
2. **Use optimized PDF for RAG**: If available, it's smaller and faster to process
3. **Cache embeddings**: Reuse embeddings if document hasn't changed

### For Even Better Accuracy:
1. **Hybrid search**: Combine keyword (BM25) + semantic search
2. **Reranking**: Use a reranker model to refine top-k results
3. **Query expansion**: Generate multiple variations of user query
4. **Metadata filtering**: Filter by page number, section headers
5. **Semantic chunking**: Use LLM to identify logical boundaries instead of fixed size

## Configuration Variables

You can tune these in `backend/api/rag_service.py`:

```python
# Embedding optimization
EMBEDDING_BATCH_SIZE = 50  # Line 153 (max: 100 for Google API)
DB_WRITE_INTERVAL = 200    # Line 155

# Chunking optimization  
CHUNK_SIZE = 1500          # Line 128
CHUNK_OVERLAP = 300        # Line 129

# Retrieval optimization
TOP_K_CHUNKS = 25          # Line 376

# Content extraction
OCR_BATCH_SIZE = 20        # Line 473
```

## Monitoring

Check logs for these improvements:
- `Embedding batch X/Y (50 chunks)` instead of `(10 chunks)`
- `Saved 200 chunks to database` instead of `Saved batch X: 10 chunks`
- Faster batch processing times
- Overall ingestion completion in 4-5 minutes instead of 11 minutes

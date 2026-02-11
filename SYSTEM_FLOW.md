# OCR System Architecture & Flow Documentation

**Last Updated:** February 9, 2026

## Table of Contents
1. [System Overview](#system-overview)
2. [Document Processing Pipeline](#document-processing-pipeline)
3. [RAG (Retrieval-Augmented Generation) Pipeline](#rag-pipeline)
4. [RAGAS Evaluation Flow](#ragas-evaluation-flow)
5. [Key Components](#key-components)
6. [Data Flow Diagrams](#data-flow-diagrams)

---

## System Overview

This is a **Vietnamese Investment Fund Prospectus OCR System** that:
- Extracts structured data from PDF documents using AI models (Gemini/Mistral)
- Enables semantic search and chat via RAG (Retrieval-Augmented Generation)
- Evaluates RAG quality using RAGAS framework

**Tech Stack:**
- **Backend:** Django 5.0 + PostgreSQL with pgvector
- **Frontend:** React + Vite
- **AI Models:** 
  - Gemini 2.0 Flash (default OCR + RAG)
  - Mistral Large / Mistral OCR (alternative)
- **Embedding:** Google Text-Embedding-004 (768 dimensions)
- **Vector Search:** pgvector with HNSW index

---

## Document Processing Pipeline

### Flow Overview
```
Upload PDF → PDF Optimization → Structured Data Extraction → Storage → (Optional) RAG Ingestion
```

### Stage 1: Document Upload
**Endpoint:** `POST /api/documents/`  
**File:** `backend/api/views.py` - `DocumentViewSet.create()`

1. User uploads PDF via frontend
2. Django saves file to `media/documents/YYYY/MM/DD/`
3. Document record created with status `'pending'`
4. Asynchronous processing triggered via background thread

### Stage 2: PDF Optimization
**Function:** `backend/api/services.py` - `create_optimized_pdf()`

**Purpose:** Filter out irrelevant pages to reduce processing time and cost

**Process:**
1. Open PDF with PyMuPDF (fitz)
2. For each page:
   - **Digital PDF:** Extract text with `page.get_text("text")`
   - **Scanned PDF:** Use RapidOCR to extract text from rendered image
3. Check for Vietnamese keywords:
   - "bản cáo bạch" (prospectus)
   - "nội dung" (contents)
   - "phí", "phí dịch vụ" (fees)
   - "quỹ", "fund"
4. Keep only pages containing ≥2 keywords
5. Create optimized PDF with filtered pages
6. Save to `media/optimized_documents/YYYY/MM/DD/`

**Fallback:** If optimization fails, use original PDF

### Stage 3: Structured Data Extraction
**Service:** `backend/api/services.py` - `DocumentProcessingService._process_document_task()`

**Models Available:**
- **Gemini 2.0 Flash** (default) - Best accuracy
- **Mistral Large** - Alternative for comparison
- **Mistral OCR + Small** - Hybrid approach

**Process:**
1. Choose PDF: optimized (preferred) or original (fallback)
2. Call AI service with detailed extraction schema
3. AI extracts 50+ fields including:
   - Basic info: fund name, code, type, license
   - Fees: management, subscription, redemption, switching
   - Governance: management company, custodian bank
   - Investment: strategy, restrictions, limits
   - Performance: portfolio, NAV history, dividends
   - Risk factors: concentration, liquidity, interest rate
4. Parse and validate JSON response
5. Store in `Document.extracted_data` (PostgreSQL JSONB)
6. Create/update `ExtractedFundData` normalized model
7. Update status to `'completed'` or `'failed'`

**Extraction Schema Location:** `_get_extraction_schema()` - returns detailed JSON schema with:
- Field types and descriptions
- Bounding box coordinates (page, bbox [ymin, xmin, ymax, xmax])
- Nested objects for complex data (fees, portfolio, etc.)

### Stage 4: Storage
**Models:** `backend/api/models.py`

1. **Document** - Main table
   - File paths (original + optimized)
   - Processing status and timestamps
   - JSON extracted data
   - Chat history
   - Edit tracking

2. **ExtractedFundData** - Normalized structured data
   - All fund fields as database columns
   - Easier querying and filtering

3. **DocumentChangeLog** - Audit trail
   - Tracks all user edits
   - Stores before/after values

---

## RAG Pipeline

### Overview
```
Extract Full Text → Clean → Chunk → Embed → Store in Vector DB → Query → Retrieve → Generate Answer
```

### Trigger Points
1. **Automatic:** After document processing completes (if enabled)
2. **Manual:** `POST /api/documents/{id}/ingest_for_rag/`
3. **Background:** Auto-triggered via threading in `DocumentViewSet.create()`

### Stage 1: Full Text Extraction for RAG
**Function:** `RAGService._extract_content_for_rag()`  
**Location:** `backend/api/services.py:2470-2618`

**Process:**
1. **File Selection:**
   ```python
   # Prefers ORIGINAL PDF (better quality)
   chosen_path = document.file.path
   # Falls back to optimized if original missing
   ```

2. **Batch Processing (20 pages per batch):**
   - For each page:
     - **Try Digital Extraction First:**
       ```python
       direct_text = page.get_text("text")  # PyMuPDF
       if len(direct_text.strip()) >= 50:
           use_directly()  # Fast path
       ```
     - **Fallback to OCR (Scanned PDFs):**
       ```python
       pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))
       image = PIL.Image.from_bytes(pix.tobytes("png"))
       send_to_gemini_ocr(image)  # Vision model
       ```

3. **Gemini OCR Prompt:**
   ```
   "You are a strict OCR engine."
   "TASK: Transcribe images to Markdown"
   "FORMAT: Start each page with === PAGE N ==="
   "RULES: 
     - No intro/summary
     - Transcribe EXACTLY word-for-word
     - Preserve tables in Markdown
     - Output Vietnamese with correct accents"
   ```

4. **Retry Logic:**
   - 3 attempts per batch with exponential backoff
   - 2-second sleep between batches (rate limit prevention)

5. **Output Format:**
   ```markdown
   === PAGE 1 ===
   [Page 1 content...]
   
   === PAGE 2 ===
   [Page 2 content...]
   ```

6. **Debug Output:**
   - Saves to `media/debug_markdown/document_{id}_extracted.md`
   - Allows inspection of pre-chunking content

### Stage 2: Text Cleaning
**Function:** `RAGService._clean_text_for_rag()`  
**Location:** `backend/api/services.py:2020-2050`

**Cleans:**
- Repetitive headers/footers
- OCR artifacts
- Formatting glitches

### Stage 3: Chunking Strategy
**Location:** `backend/api/services.py:2098-2163`

**Multi-Stage Approach:**

1. **Page Segmentation:**
   ```python
   # Split by page markers
   pages = split_on("=== PAGE N ===" or "--- PAGE N ---")
   ```

2. **Header-Based Splitting:**
   ```python
   MarkdownHeaderTextSplitter(
       headers_to_split_on=[
           ("#", "Header 1"),
           ("##", "Header 2"),
           ("###", "Header 3")
       ]
   )
   ```

3. **Recursive Text Splitting:**
   ```python
   RecursiveCharacterTextSplitter(
       chunk_size=800,           # Characters per chunk
       chunk_overlap=100,        # Overlap for context
       separators=["\n\n", "\n", ".", " ", ""]
   )
   ```

4. **Metadata Tagging:**
   ```python
   for chunk in chunks:
       chunk.metadata['page_number'] = page_num
   ```

**Output:** ~200-500 chunks per document (depends on length)

### Stage 4: Embedding Generation
**Location:** `backend/api/services.py:2163-2230`

**Configuration:**
- **Model:** `models/text-embedding-004` (Google)
- **Dimensions:** 768
- **Batch Size:** 50 chunks per API call
- **DB Write Interval:** 200 chunks per transaction

**Process:**
1. For each batch of 50 chunks:
   ```python
   embeddings = genai.embed_content(
       model="models/text-embedding-004",
       content=[chunk.page_content for chunk in batch],
       task_type="retrieval_document"  # Optimized for search
   )
   ```

2. Add header context to chunk content:
   ```python
   if 'Header 1' in metadata:
       content = f"# {metadata['Header 1']}\n{content}"
   ```

3. Create `DocumentChunk` objects:
   ```python
   DocumentChunk(
       document=document,
       content=final_content,
       page_number=page_num,
       embedding=embedding_vector  # 768-dim array
   )
   ```

4. Bulk insert every 200 chunks (performance optimization)

### Stage 5: Vector Storage
**Model:** `backend/api/models.py` - `DocumentChunk`

**Database Schema:**
```python
class DocumentChunk:
    document = ForeignKey(Document)
    content = TextField()              # Chunk text
    page_number = IntegerField()       # Source page
    embedding = VectorField(dims=768)  # pgvector
    created_at = DateTimeField()
    
    # HNSW Index for fast similarity search
    indexes = [
        HnswIndex(
            fields=['embedding'],
            m=16,                  # Max connections per layer
            ef_construction=64,    # Dynamic candidate list size
            opclasses=['vector_cosine_ops']  # Cosine similarity
        )
    ]
```

### Stage 6: Query & Retrieval
**Endpoint:** `POST /api/documents/{id}/chat/`  
**Service:** `RAGService.chat()`  
**Location:** `backend/api/services.py:2285-2470`

**Process:**

1. **Dual Retrieval Strategy:**
   ```python
   # Source 1: Structured data (priority for facts)
   structured_info = document.extracted_data
   # → Fund name, fees, dates, etc.
   
   # Source 2: Vector search (for explanations)
   query_embedding = embed(user_query)
   chunks = DocumentChunk.objects
       .annotate(distance=CosineDistance('embedding', query_embedding))
       .order_by('distance')[:25]  # Top 25 chunks
   ```

2. **Context Building:**
   ```python
   rag_context = "\n\n---\n\n".join([
       f"=== PAGE {chunk.page_number} ===\n{chunk.content}"
       for chunk in chunks
   ])
   ```

3. **Prompt Engineering:**
   ```
   "Bạn là trợ lý phân tích tài chính..."
   
   "NGUỒN 1: DỮ LIỆU CẤU TRÚC (ưu tiên cho Phí, Tên, Mã số)"
   {structured_info}
   
   "NGUỒN 2: TRÍCH ĐOẠN VĂN BẢN (cho giải thích, chiến lược)"
   {rag_context}
   
   "QUY TẮC:
   1. Kiểm tra NGUỒN 1 trước
   2. Nếu không đủ, dùng NGUỒN 2
   3. Trả lời tiếng Việt, ngắn gọn"
   ```

4. **Generation:**
   ```python
   chat = gemini_model.start_chat(history=previous_messages)
   response = chat.send_message(system_prompt + user_query)
   return response.text
   ```

5. **Response Format:**
   ```json
   {
     "answer": "Phí quản lý của quỹ là 1.2%/năm...",
     "query": "phí quản lý là bao nhiêu",
     "chunks_count": 150,
     "contexts": ["context1", "context2", ...]  // Optional
   }
   ```

---

## RAGAS Evaluation Flow

### Overview
```
Load Dataset → Generate Embeddings → Run Metrics → Save Results
```

### Script Location
`backend/api/evaluation.py`

### Dataset Format
**Input:** `backend/ragas_dataset.csv`

```csv
question,answer,contexts,ground_truth
"Tên quỹ TCSME?","Quỹ Đầu tư...","['context1', 'context2']","Tên chính thức..."
```

**Fields:**
- `question`: User query
- `answer`: RAG system's response
- `contexts`: Retrieved chunks (string-serialized list)
- `ground_truth`: Expected correct answer

### Evaluation Process

1. **Load Dataset:**
   ```python
   df = pd.read_csv('ragas_dataset.csv')
   
   # Parse string lists to actual lists
   df['contexts'] = df['contexts'].apply(ast.literal_eval)
   ```

2. **Create RAGAS Dataset:**
   ```python
   from datasets import Dataset
   eval_dataset = Dataset.from_pandas(df)
   ```

3. **Configure Models:**
   ```python
   from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
   
   # Judge LLM (evaluates quality)
   judge_llm = ChatGoogleGenerativeAI(
       model="gemini-2.0-flash-exp",
       temperature=0  # Deterministic grading
   )
   
   # Embeddings (for relevance metrics)
   embeddings = GoogleGenerativeAIEmbeddings(
       model="models/text-embedding-004"
   )
   ```

4. **Run Metrics:**
   ```python
   from ragas import evaluate
   from ragas.metrics import (
       faithfulness,        # Answer grounded in contexts?
       answer_relevancy,    # Answer relevant to question?
       context_precision,   # Relevant contexts ranked high?
       context_recall       # Ground truth in contexts?
   )
   
   result = evaluate(
       dataset=eval_dataset,
       metrics=[
           faithfulness,
           answer_relevancy,
           context_precision,
           context_recall
       ],
       llm=judge_llm,
       embeddings=embeddings
   )
   ```

5. **Save Results:**
   ```python
   result_df = result.to_pandas()
   result_df.to_csv('ragas_results.csv', index=False)
   ```

### Output Format
**File:** `backend/ragas_results.csv`

```csv
question,answer,contexts,ground_truth,faithfulness,answer_relevancy,context_precision,context_recall
"Tên quỹ?","...",["..."],"...",0.5,0.7,0.3,0.2
```

### Metric Definitions

| Metric | Range | Meaning | Good Score |
|--------|-------|---------|------------|
| **Faithfulness** | 0-1 | Answer supported by contexts | >0.7 |
| **Answer Relevancy** | 0-1 | Answer addresses question | >0.8 |
| **Context Precision** | 0-1 | Relevant chunks ranked high | >0.6 |
| **Context Recall** | 0-1 | Ground truth in contexts | >0.7 |

---

## Key Components

### Backend Services

#### 1. DocumentProcessingService
**File:** `backend/api/services.py:1644-1850`
- Manages async document processing
- Orchestrates PDF optimization → extraction
- Handles model selection (Gemini/Mistral)

#### 2. GeminiOCRService
**File:** `backend/api/services.py:~600-1200`
- Structured data extraction
- Vision API for scanned documents
- Multimodal prompting

#### 3. RAGService
**File:** `backend/api/services.py:2006-2470`
- Full text extraction for RAG
- Chunking and embedding
- Query handling and response generation

#### 4. MistralOCRService / MistralOCRSmallService
**File:** `backend/api/services.py:1200-1640`
- Alternative extraction models
- Pixtral Large for vision
- Comparison benchmarking

### Frontend Components

#### 1. Dashboard
**File:** `frontend/src/components/Dashboard.jsx`
- Document list view
- Upload interface
- Search and filtering

#### 2. ChatPanel
**File:** `frontend/src/components/ChatPanel.jsx`
- RAG chat interface
- Message history
- Markdown rendering

#### 3. FileUpload
**File:** `frontend/src/components/FileUpload.jsx`
- Drag-and-drop upload
- Model selection
- Progress tracking

### Database Models

#### Document
**Primary model storing all document data**
- File paths (original + optimized)
- Processing status
- Extracted data (JSONB)
- Chat history (JSONB)
- RAG ingestion status

#### ExtractedFundData
**Normalized fund information**
- 50+ fields as columns
- Foreign key to Document
- Optimized for queries

#### DocumentChunk
**Vector embeddings for RAG**
- Content text
- 768-dim embedding vector
- Page number metadata
- HNSW index for fast search

#### DocumentChangeLog
**Audit trail**
- User ID and timestamp
- Field-level change tracking
- Before/after values

---

## Data Flow Diagrams

### Document Upload Flow
```
┌──────────┐
│  User    │
│ Uploads  │
│   PDF    │
└────┬─────┘
     │
     v
┌────────────────┐
│  FileUpload    │
│  Component     │
└────┬───────────┘
     │ POST /api/documents/
     v
┌────────────────────┐
│  DocumentViewSet   │
│   .create()        │
└────┬───────────────┘
     │
     ├──> Save to media/documents/
     │
     ├──> Create Document record (status='pending')
     │
     └──> Start background thread
          │
          v
     ┌────────────────────────┐
     │ DocumentProcessing     │
     │ Service                │
     │ ._process_document_task│
     └────┬───────────────────┘
          │
          ├──> create_optimized_pdf()
          │    └──> RapidOCR + keyword filtering
          │
          ├──> extract_structured_data()
          │    └──> Gemini/Mistral vision API
          │
          └──> Save to Document.extracted_data
               │
               └──> Status = 'completed'
```

### RAG Query Flow
```
┌──────────┐
│  User    │
│  Query   │
└────┬─────┘
     │ "Phí quản lý?"
     v
┌────────────────┐
│  ChatPanel     │
└────┬───────────┘
     │ POST /api/documents/{id}/chat/
     v
┌────────────────────┐
│  RAGService.chat() │
└────┬───────────────┘
     │
     ├──> 1. Get structured data
     │       └──> document.extracted_data
     │
     ├──> 2. Generate query embedding
     │       └──> Google Text-Embedding-004
     │
     ├──> 3. Vector search
     │       └──> pgvector: CosineDistance
     │            └──> Top 25 chunks
     │
     ├──> 4. Build context
     │       ├──> Structured info
     │       └──> Retrieved chunks
     │
     ├──> 5. Generate prompt
     │       └──> "Nguồn 1... Nguồn 2..."
     │
     └──> 6. Call Gemini
          └──> Response → User
```

### RAG Ingestion Flow
```
┌────────────────┐
│  Trigger:      │
│  - Auto POST   │
│  - Manual API  │
└────┬───────────┘
     │
     v
┌────────────────────────┐
│  RAGService            │
│  .ingest_document()    │
└────┬───────────────────┘
     │
     ├──> 1. Extract full text
     │       ├──> Open PDF (original preferred)
     │       ├──> For each page:
     │       │    ├──> Try get_text() (digital)
     │       │    └──> Fallback: Gemini OCR (scanned)
     │       └──> Save to debug_markdown/
     │
     ├──> 2. Clean text
     │       └──> Remove artifacts
     │
     ├──> 3. Chunk
     │       ├──> Split by === PAGE N ===
     │       ├──> Markdown headers
     │       └──> Recursive (800 chars, 100 overlap)
     │
     ├──> 4. Embed (batches of 50)
     │       └──> Google Embedding API
     │
     └──> 5. Store
          └──> Bulk insert DocumentChunk
               └──> pgvector HNSW index
```

---

## Configuration Summary

### Chunking Parameters
```python
CHUNK_SIZE = 800           # Characters per chunk
CHUNK_OVERLAP = 100        # Overlap between chunks
```

### Embedding Parameters
```python
EMBEDDING_MODEL = "models/text-embedding-004"
EMBEDDING_DIMENSIONS = 768
BATCH_SIZE = 50            # Chunks per API call
DB_WRITE_INTERVAL = 200    # Chunks per DB write
```

### Retrieval Parameters
```python
TOP_K_CHUNKS = 25          # Number of chunks retrieved
SIMILARITY_METRIC = "cosine"
```

### Vector Index Parameters
```python
INDEX_TYPE = "HNSW"
M = 16                     # Max connections per layer
EF_CONSTRUCTION = 64       # Dynamic candidate list size
```

---

## Known Issues & Troubleshooting

### Low RAGAS Scores (Current Issue)
**Problem:** Scores ~0.2-0.36 across all metrics

**Root Causes:**
1. **Poor OCR quality** → Repetitive garbage text indexed
2. **Low retrieval precision** → Only 1-2 relevant chunks out of 25
3. **Lack of filtering** → Garbage chunks not filtered before indexing

**Solutions:**
- Add chunk quality validation before indexing
- Filter repetitive patterns (e.g., `unique_words/total_words < 0.3`)
- Improve OCR on source documents
- Implement semantic deduplication

### OCR Artifacts
**Symptoms:** 
- Repeated phrases like "chi phí/phí/giá dịch vụ..." × 500 times
- "Trong thời hạn 05 ngày..." repeated endlessly

**Investigation:**
```bash
# Check extracted markdown
cat backend/media/debug_markdown/document_*_extracted.md | grep -o "chi phí" | wc -l

# Check if issue is in source or chunking
python manage.py shell
>>> from api.services import RAGService
>>> rag = RAGService()
>>> text = rag._extract_content_for_rag(document)
>>> # Analyze repetition patterns
```

---

## Future Improvements

1. **Context Quality Filtering**
   - Pre-index validation
   - Semantic deduplication
   - Relevance scoring

2. **Retrieval Optimization**
   - Reduce top_k to 10-15
   - Add cross-encoder reranking
   - Implement minimum similarity threshold

3. **Chunking Strategy**
   - Increase to 1500 chars (RAG_IMPROVEMENTS.md)
   - Add semantic boundary detection
   - Preserve table integrity

4. **Monitoring**
   - Track RAG performance metrics
   - Log retrieval quality
   - Alert on OCR failures

---

## API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/documents/` | POST | Upload document |
| `/api/documents/{id}/` | GET | Get document details |
| `/api/documents/{id}/ingest_for_rag/` | POST | Trigger RAG ingestion |
| `/api/documents/{id}/rag_status/` | GET | Check RAG status |
| `/api/documents/{id}/chat/` | POST | Chat with document |
| `/api/documents/{id}/extracted-data/` | GET | Get structured data |

---

## Environment Variables

```env
# Google AI
GOOGLE_API_KEY=...

# Mistral AI (optional)
MISTRAL_API_KEY=...

# Database
DATABASE_URL=postgresql://...

# Storage
MEDIA_ROOT=backend/media/
```

---

**Document Version:** 1.0  
**System Version:** Based on codebase analysis as of Feb 9, 2026

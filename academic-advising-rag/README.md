# Academic Advising Assistant (RAG)

A retrieval-augmented generation (RAG) chatbot that answers student questions about
courses, degree requirements, faculty, and schedules. It embeds advising documents,
stores them in a FAISS vector database, retrieves the most relevant context for the
language model, and returns answers **with their source documents** for transparency.

## Tech
Python · LangChain · FAISS · HuggingFace embeddings · OpenAI / Ollama · Streamlit

## How it works
1. Loads advising documents (`.docx` / `.pdf`) from `materials/`.
2. Splits them into chunks and embeds them with sentence-transformers.
3. Stores vectors in a local FAISS index (`.faiss_index/`, built on first run).
4. On each question, retrieves the most relevant chunks and passes them to the LLM.
5. Returns the answer plus the source snippets it was drawn from.

## Structure
- `src/RAG_ChatBot.py` — core RAG pipeline (loading, chunking, embedding, retrieval, answering)
- `src/streamlitMain.py` — Streamlit UI with quick-prompt examples and source display
- `materials/` — advising documents used as the knowledge base
- `requirements.txt` — dependencies

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env        # then add your key(s)
streamlit run src/streamlitMain.py
```

Set `OPENAI_API_KEY` in `.env` to use OpenAI, or run a local model with Ollama.
The FAISS index builds automatically from `materials/` on first launch.

## Notes
Built as a graduate Business Analytics project. The knowledge base here uses public
program/course documents; no student records are included.

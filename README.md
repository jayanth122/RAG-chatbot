# RAG Chatbot 

This project is an end-to-end Retrieval-Augmented Generation (RAG) chatbot system. Users can upload documents (PDFs), and the chatbot answers questions by retrieving relevant content and generating contextual responses.

## 🧱 Architecture

- **Frontend**: React application for document upload and chat interface.
- **Proxy Server**: Flask server to act as an intermediary between frontend and ACP server.
- **Backend**: ACP Server running a RAG model that embeds documents, stores them in a vector database (e.g., FAISS), and generates answers.

Frontend (React) ⇄ Flask Proxy ⇄ ACP Server (RAG Model)

## 🚀 Features

- Upload PDF documents.
- Chatbot answers questions based on uploaded content.
- Live chat interface with optional streaming.
- Modular and scalable architecture.

## 🛠 Technologies Used
- React (Frontend)
- Flask (Proxy API)
- ACP SDK (Agent Coordination Platform)
- FAISS (Vector storage)
- SentenceTransformers or OpenAI Embeddings (for vector generation)
- LLM API (OpenRouter)

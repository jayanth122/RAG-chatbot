import os
os.environ["OTEL_SDK_DISABLED"] = "true"
import faiss
import numpy as np
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from acp_sdk.server import Server, RunYield, RunYieldResume
from acp_sdk.models import Message, MessagePart
from collections.abc import AsyncGenerator
from acp_sdk.client import Client
from dotenv import load_dotenv
from openai import OpenAI



# --- Load environment ---
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PDF_PATH = "docs/gold-hospital-and-premium-extras.pdf"
CHUNK_SIZE, OVERLAP = 1000, 200

# --- Load PDF and build FAISS index ---
print("Loading PDF and building FAISS index...")
reader = PdfReader(PDF_PATH)
text = " ".join(page.extract_text() for page in reader.pages if page.extract_text())
words = text.split()
chunks = [" ".join(words[i:i + CHUNK_SIZE]) for i in range(0, len(words), CHUNK_SIZE - OVERLAP)]

model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(chunks)
index = faiss.IndexFlatL2(len(embeddings[0]))
index.add(np.array(embeddings))


# --- OpenRouter client ---
client_llm = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# --- ACP Server ---
server = Server()

# --- Agent: PDF Processor Agent ---
@server.agent(name="pdf")
async def pdf_agent(messages: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    pdf_path = " ".join(part.content for m in messages for part in m.parts).strip()

    if not pdf_path.endswith(".pdf") or not os.path.exists(pdf_path):
        yield Message(parts=[MessagePart(content="❌ Invalid PDF path or file does not exist.")])
        return

    try:
        print(f"📄 Processing PDF: {pdf_path}")
        print("Loading PDF and building FAISS index...")
        reader = PdfReader(pdf_path)
        text = " ".join(page.extract_text() for page in reader.pages if page.extract_text())
        words = text.split()
        chunks = [" ".join(words[i:i + CHUNK_SIZE]) for i in range(0, len(words), CHUNK_SIZE - OVERLAP)]
        embeddings = model.encode(chunks)
        index = faiss.IndexFlatL2(len(embeddings[0]))
        index.add(np.array(embeddings))

    except Exception as e:
        print("❌ PDF Agent Error:", e)
        yield Message(parts=[MessagePart(content=f"❌ Failed to process PDF: {str(e)}")])



# --- Agent: Reflector Agent ---
@server.agent(name="reflector")
async def reflector_agent(messages: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    qa_input = " ".join(part.content for m in messages for part in m.parts)
    prompt = f"""
You are a reflection module that reviews answers given to users and offers a helpful analysis to improve clarity or tone.
Focus on how human-like, friendly, and helpful the message sounds. Suggest small tweaks or enhancements.

Content:
{qa_input}

Suggestions:
"""

    try:
        response = client_llm.chat.completions.create(
            model="mistralai/mistral-small-3.2-24b-instruct:free",
            messages=[{"role": "user", "content": prompt}],
            extra_headers={
                "HTTP-Referer": "https://yourdomain.com",
                "X-Title": "ReflectorAgent",
            }
        )
        feedback = response.choices[0].message.content.strip()
    except Exception as e:
        print("Reflector failed:", e)
        feedback = "No suggestions generated."

    yield Message(parts=[MessagePart(content=feedback)])

# --- Agent: RAG Agent ---
@server.agent(name="rag")
async def rag_agent(messages: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    query = " ".join(part.content for m in messages for part in m.parts).strip()

    if query.lower() in ["summary", "summarize", "overview"]:
        query = "Please provide a clear summary of the key benefits, waiting periods, and exclusions in the Gold Hospital and Premium Extras policy."

    query_vec = model.encode([query])
    _, I = index.search(np.array(query_vec), k=4)
    top_chunks = [chunks[i] for i in I[0]]

    context = "\n".join(f"- {chunk}" for chunk in top_chunks)
    prompt = f"""
You are a Senior Insurance Coverage Assistant.

Your role is to help members clearly understand their policy entitlements. You are friendly, professional, and speak in a helpful tone like you're on a customer support call.

Your job is to read the provided context from a policy document and summarize the relevant benefits, waiting periods, exclusions, and anything else important — in a **human**, **customer-friendly** way.

Avoid listing raw data or bullet points unless helpful. Speak in natural language, like you're explaining this to a member on the phone.

Keep it concise, but clear. Mention waiting periods and exclusions where appropriate. If relevant, end with advice like “If you're unsure about a specific service, it's best to give us a call.”

Here’s the document context:
---
{context}
---

And here’s the customer’s question:
"{query}"

Please provide your response below:
"""

    try:
        # Step 1: Generate initial raw response using OpenRouter
        response = client_llm.chat.completions.create(
            model="mistralai/mistral-small-3.2-24b-instruct:free",
            messages=[{"role": "user", "content": prompt}],
            extra_headers={
                "HTTP-Referer": "https://yourdomain.com",
                "X-Title": "InsuranceAgent",
            }
        )
        raw_answer = response.choices[0].message.content.strip()

        # Step 2: Call rephraser agent internally to improve the output
        async with Client(base_url="http://127.0.0.1:8000") as local_client:
            rephrased = await local_client.run_sync(
                agent="rephraser",
                input=[Message(parts=[MessagePart(content=raw_answer)])]
            )
            final_answer = rephrased.output[0].parts[0].content.strip()

    except Exception as e:
        print("❌ RAG+Rephraser error:", e)
        final_answer = "Sorry, I couldn't retrieve your answer right now."

    yield Message(parts=[MessagePart(content=final_answer)])


# --- Agent: Rephraser Agent ---
@server.agent(name="rephraser")
async def rephraser_agent(messages: list[Message]) -> AsyncGenerator[RunYield, RunYieldResume]:
    full_text = " ".join(part.content for m in messages for part in m.parts)
    prompt = f"""
You are a message enhancer. Take the input message and improve clarity, tone, and friendliness without changing the meaning. 
Remove any technical formatting like "Question:" or "Answer:" and make it a natural response from a Senior Insurance Coverage Assistant.
No feedback or suggestions at the end.
Do not mention the tone of the message in the message.
Input:
{full_text}

Improved Final Output:
"""

    try:
        response = client_llm.chat.completions.create(
            model="mistralai/mistral-small-3.2-24b-instruct:free",
            messages=[{"role": "user", "content": prompt}],
            extra_headers={
                "HTTP-Referer": "https://yourdomain.com",
                "X-Title": "RephraserAgent",
            }
        )
        improved = response.choices[0].message.content.strip()
    except Exception as e:
        print("\u274c Rephraser error:", e)
        improved = full_text

    yield Message(parts=[MessagePart(content=improved)])

# --- Start Server ---
os.environ["OTEL_SDK_DISABLED"] = "true"
print("Registered ACP Agents:", [a.name for a in server.agents])
server.run(port=8000)
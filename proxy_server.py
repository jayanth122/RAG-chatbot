# proxy_server.py

from flask import Flask, request, jsonify
import asyncio
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Constants
PDF_PATH = "docs"
ALLOWED_EXTENSIONS = {"pdf"}

# Ensure the target directory exists
os.makedirs(PDF_PATH, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Upload endpoint
@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(PDF_PATH, filename)
        file.save(filepath)

        # Fire-and-forget style PDF agent call
        try:
            asyncio.run(trigger_pdf_agent(filepath))
        except Exception as e:
            print(f"⚠️ PDF agent error: {e}")  # Don't fail upload because of it

        return jsonify({
            "message": "✅ PDF uploaded successfully.",
            "path": filepath
        }), 200

    return jsonify({"error": "Invalid file type. Only PDF allowed."}), 400


# Route to handle chat messages
@app.route("/chat", methods=["POST"])
def handle_chat():
    try:
        data = request.get_json()
        question = data.get("message")

        if not question:
            return jsonify({"error": "Missing 'message' field"}), 400

        # Call async function to talk to ACP
        response = asyncio.run(query_acp(question))
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Async function to query the PDF agent
async def trigger_pdf_agent(pdf_path: str):
    async with Client(base_url="http://127.0.0.1:8000") as client:
        await client.run_sync(
            agent="pdf",
            input=[Message(parts=[MessagePart(content=pdf_path)])]
        )


# Async function to query ACP server
async def query_acp(question: str) -> str:
    async with Client(base_url="http://127.0.0.1:8000") as client:
        run = await client.run_sync(
            agent="rag",
            input=[Message(parts=[MessagePart(content=question)])]
        )
        #print(run.output[0].parts[0].content)
        return run.output[0].parts[0].content

# Run the server
if __name__ == "__main__":
    app.run(port=3001, debug=True)

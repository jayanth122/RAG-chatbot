const BASE_URL = 'http://localhost:3001';

/**
 * Sends a chat message to the Flask proxy, which forwards it to the ACP server.
 * Returns the assistant's response as plain text.
 */
async function sendChatMessage(chatId, message) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    throw {
      status: res.status,
      data: await res.json(),
    };
  }

  const data = await res.json();
  return data.response;
}

/**
 * Creates a new chat session.
 * Returns a dummy ID for now since your backend doesn't track sessions.
 */
async function createChat() {
  return { id: 'local-chat-session' };
}

/**
 * Uploads a PDF file to the backend /upload endpoint.
 * Returns an object with a success message and file path.
 */
async function uploadPdf(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  });

  const result = await res.json();

  if (!res.ok) {
    throw {
      status: res.status,
      data: result,
    };
  }

  return result; // { message: "...", path: "docs/filename.pdf" }
}

export default {
  sendChatMessage,
  createChat,
  uploadPdf,
};

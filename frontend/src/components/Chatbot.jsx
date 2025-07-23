import { useRef, useState } from 'react';
import { useImmer } from 'use-immer';
import api from '@/api';
import ChatMessages from '@/components/ChatMessages';
import ChatInput from '@/components/ChatInput';

function Chatbot() {
  const [chatId, setChatId] = useState(null);
  const [messages, setMessages] = useImmer([]);
  const [newMessage, setNewMessage] = useState('');
  const [lastUploaded, setLastUploaded] = useState(null); // ✅ Track last uploaded file
  const fileInputRef = useRef(null);

  const isLoading = messages.length && messages[messages.length - 1].loading;

  // Submit a new chat message
  async function submitNewMessage() {
    const trimmedMessage = newMessage.trim();
    if (!trimmedMessage || isLoading) return;

    // Add user message + loading placeholder
    setMessages(draft => [
      ...draft,
      { role: 'user', content: trimmedMessage },
      { role: 'assistant', content: '', loading: true }
    ]);
    setNewMessage('');

    let chatIdOrNew = chatId;
    try {
      if (!chatId) {
        const { id } = await api.createChat();
        setChatId(id);
        chatIdOrNew = id;
      }

      const response = await api.sendChatMessage(chatIdOrNew, trimmedMessage);

      setMessages(draft => {
        draft[draft.length - 1].content = response || "No response received.";
        draft[draft.length - 1].loading = false;
      });
    } catch (err) {
      console.error(err);
      setMessages(draft => {
        draft[draft.length - 1].loading = false;
        draft[draft.length - 1].error = true;
        draft[draft.length - 1].content = "Something went wrong.";
      });
    }
  }

  // Handle PDF upload
  async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file || file.type !== "application/pdf") {
      alert("Please select a valid PDF file.");
      return;
    }

    try {
      const result = await api.uploadPdf(file);
      setLastUploaded(file.name); // ✅ Save uploaded file name
      alert("✅ PDF uploaded successfully!");
      console.log("Uploaded to:", result.path);
    } catch (err) {
      console.error(err);
      const errorMsg = err?.data?.error || "Upload failed.";
      alert(`❌ ${errorMsg}`);
    }
  }

  return (
    <div className="relative grow flex flex-col gap-6 pt-6">
      {/* Upload PDF section */}
      <div className="px-4">
        <button
          className="text-sm px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          onClick={() => fileInputRef.current.click()}
        >
          📄 Upload PDF
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          style={{ display: "none" }}
          onChange={handleFileUpload}
        />

        {/* ✅ Show uploaded filename */}
        {lastUploaded && (
          <p className="mt-2 text-sm text-gray-600">
            Last uploaded: <strong>{lastUploaded}</strong>
          </p>
        )}
      </div>

      {/* Welcome message */}
      {messages.length === 0 && (
        <div className="mt-3 font-urbanist text-primary-blue text-xl font-light space-y-2 px-4">
          <p>👋 Welcome!</p>
          <p>You can ask about your policy or upload a PDF for custom Q&A.</p>
        </div>
      )}

      {/* Chat messages */}
      <ChatMessages messages={messages} isLoading={isLoading} />

      {/* Chat input */}
      <ChatInput
        newMessage={newMessage}
        isLoading={isLoading}
        setNewMessage={setNewMessage}
        submitNewMessage={submitNewMessage}
      />
    </div>
  );
}

export default Chatbot;

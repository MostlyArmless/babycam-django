import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface Message {
  user: string;
  text: string;
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>("");

  const handleSend = () => {
    if (input.trim()) {
      setMessages([...messages, { user: "Me", text: input }]);
      setInput("");
    }
  };

  useEffect(() => {
    // Simulate receiving messages from other users
    const interval = setInterval(() => {
      setMessages((prevMessages) => [
        ...prevMessages,
        { user: "Other", text: "Hello from the other side!" },
      ]);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <div
        className="chat-container"
        style={{
          height: "400px",
          width: "300px",
          overflowY: "auto",
          border: "2px solid #ccc",
          borderRadius: "8px",
          padding: "10px",
          marginBottom: "10px",
        }}
        ref={(el) => {
          if (el) {
            el.scrollTop = el.scrollHeight;
          }
        }}
      >
        <div className="messages"></div>
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message ${message.user === "Me" ? "me" : "other"}`}
          >
            <strong>{message.user}:</strong> {message.text}
          </div>
        ))}
      </div>
      <div className="input-container" style={{ display: "flex", gap: "10px" }}>
        <Input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSend()}
        />
        <Button onClick={handleSend}>Send</Button>
      </div>
    </>
  );
};

export default Chat;

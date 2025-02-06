import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { WebsocketConnectionStatusBadge } from "./WebsocketConnectionStatusBadge";
import { ReadyState } from "react-use-websocket";

interface Message {
  user: string;
  text: string;
  timestamp: string;
}

interface ChatProps {
  username: string;
}

const formatTimestamp = (date: Date): string => {
  return date
    .toLocaleString("en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    })
    .replace(/(\d+)\/(\d+)\/(\d+)/, "$3-$1-$2");
};

const Chat: React.FC<ChatProps> = ({ username }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>("");
  const [readyState, setReadyState] = useState<ReadyState>(
    WebSocket.CONNECTING
  );
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Establish the WebSocket connection
    wsRef.current = new WebSocket(`ws://localhost:8000/ws/chat/main/`); // For now there's only a single chat room, app-wide
    wsRef.current.onopen = (event: Event) => {
      console.log("Chat ws connected", event);
      setReadyState(WebSocket.OPEN);
    };
    wsRef.current.onmessage = (evt) => {
      // When we first connect to the server, we receive all the messages
      // that were sent before we connected.
      // Subsequently, we only receive messages that were sent after we connected.
      console.log("Chat ws message received", evt.data);
      const data = JSON.parse(evt.data);
      if (data.type === "chat_message") {
        const msg: Message = data.message;
        setMessages((prev) => [...prev, msg]);
      } else if (data.type === "chat_history") {
        const msgs: Message[] = data.messages;
        setMessages(msgs);
      }
    };

    wsRef.current.onclose = () => {
      console.log("Chat ws closed");
      setReadyState(WebSocket.CLOSED);
    };

    return () => {
      wsRef.current?.close();
    };
  }, []);

  const handleSend = () => {
    if (!input.trim() || wsRef.current?.readyState !== WebSocket.OPEN) {
      return;
    }

    const now = new Date();
    const newMessage: Message = {
      user: username,
      text: input,
      timestamp: now.toISOString(),
    };

    const messageString = JSON.stringify(newMessage);
    console.log(`Sending message: ${messageString}`);
    wsRef.current.send(messageString);
    setInput("");
  };

  return (
    <>
      <WebsocketConnectionStatusBadge readyState={readyState} />
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
            <div>
              <strong>{message.user}:</strong> {message.text}
            </div>
            <small className="text-gray-500">
              {formatTimestamp(new Date(message.timestamp))}
            </small>
          </div>
        ))}
      </div>
      <div className="input-container" style={{ display: "flex", gap: "10px" }}>
        <Input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleSend();
            }
          }}
        />
        <Button onClick={handleSend}>Send</Button>
      </div>
    </>
  );
};

export default Chat;

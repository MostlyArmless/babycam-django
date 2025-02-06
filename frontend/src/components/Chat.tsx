import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { WebsocketConnectionStatusBadge } from "./WebsocketConnectionStatusBadge";
import { ReadyState } from "react-use-websocket";
import { useUser } from "@/contexts/UserContext";

interface Message {
  user: string;
  text: string;
  timestamp: string;
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

const getRelativeTimeString = (timestamp: string): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) {
    return `${diffDays}d ago`;
  }
  if (diffHours > 0) {
    const remainingMins = diffMins % 60;
    return `${diffHours}h${remainingMins}m ago`;
  }
  if (diffMins > 0) {
    return `${diffMins}m ago`;
  }
  return `${diffSecs}s ago`;
};

const hasRecentMessage = (messages: Message[]): boolean => {
  const now = new Date();
  return messages.some((msg) => {
    const msgDate = new Date(msg.timestamp);
    return now.getTime() - msgDate.getTime() < 60000; // 60 seconds
  });
};

const Chat = () => {
  const { username } = useUser();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>("");
  const [readyState, setReadyState] = useState<ReadyState>(
    WebSocket.CONNECTING
  );
  const [updateKey, setUpdateKey] = useState(0); // Force re-render of relative times
  const wsRef = useRef<WebSocket | null>(null);
  const updateIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const setupUpdateInterval = (msgs: Message[]) => {
    // Clear existing interval if any
    if (updateIntervalRef.current) {
      clearInterval(updateIntervalRef.current);
    }

    // Set new interval based on message ages
    const interval = hasRecentMessage(msgs) ? 1000 : 30000; // 1s or 30s
    updateIntervalRef.current = setInterval(() => {
      setUpdateKey((prev) => prev + 1);

      // Dynamically adjust interval if needed
      if (interval === 1000 && !hasRecentMessage(msgs)) {
        setupUpdateInterval(msgs);
      }
    }, interval);
  };

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
        setMessages((prev) => {
          const newMessages = [...prev, msg];
          setupUpdateInterval(newMessages);
          return newMessages;
        });
      } else if (data.type === "chat_history") {
        const msgs: Message[] = data.messages;
        setMessages(msgs);
        setupUpdateInterval(msgs);
      }
    };

    wsRef.current.onclose = () => {
      console.log("Chat ws closed");
      setReadyState(WebSocket.CLOSED);
    };

    return () => {
      if (updateIntervalRef.current) {
        clearInterval(updateIntervalRef.current);
      }
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

  const handleDeleteHistory = async () => {
    if (
      !confirm(
        "Are you sure you want to delete all chat history? This cannot be undone."
      )
    ) {
      return;
    }

    setIsDeleting(true);
    try {
      const response = await fetch(`/api/chat/main/history`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Failed to delete chat history");
      }

      setMessages([]);
    } catch (error) {
      console.error("Error deleting chat history:", error);
      alert("Failed to delete chat history. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <div className="flex justify-between items-center mb-2">
      <WebsocketConnectionStatusBadge readyState={readyState} />
        <Button
          variant="destructive"
          onClick={handleDeleteHistory}
          disabled={isDeleting}
        >
          {isDeleting ? "Deleting..." : "Delete History"}
        </Button>
      </div>
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
            style={{
              backgroundColor: "#f3f4f6",
              borderRadius: "12px",
              padding: "10px",
              marginBottom: "12px",
              maxWidth: "85%",
              boxShadow: "0 1px 2px rgba(0, 0, 0, 0.1)",
              border: "1px solid #e5e7eb",
            }}
          >
            <div style={{ marginBottom: "4px" }}>
              <strong>{message.user}:</strong> {message.text}
            </div>
            <small
              className="text-gray-500"
              style={{
                display: "block",
                fontSize: "0.75rem",
              }}
            >
              {formatTimestamp(new Date(message.timestamp))} (
              {getRelativeTimeString(message.timestamp)})
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

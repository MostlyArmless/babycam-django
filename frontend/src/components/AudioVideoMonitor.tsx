import { useState, useEffect } from "react";
import useWebSocket from "react-use-websocket";
import WebcamVideoStream from "./WebcamVideoStream";
import { WebsocketConnectionStatusBadge } from "./WebsocketConnectionStatusBadge";

interface AudioMessage {
  type: "audio_level";
  device_id: number;
  peak: number;
  alert_level: "NONE" | "YELLOW" | "RED";
  timestamp: string;
}

interface WebSocketMessage {
  message: AudioMessage;
}

const AudioVideoMonitor = () => {
  const { lastMessage, readyState } = useWebSocket(
    "ws://localhost:8000/ws/monitor/1/",
    {
      onMessage: (event) => {
        console.log("Raw WebSocket message received:", event.data);
        try {
          const parsed = JSON.parse(event.data);
          // TODO
          console.log("Parsed message:", parsed);
        } catch (e) {
          console.error("Error parsing message:", e);
        }
      },
      onOpen: () => console.log("ws a/v monitor connection established"),
      onClose: () => console.log("ws a/v monitor connection closed"),
      onError: (event) => console.error("ws a/v monitor error:", event),
    }
  );

  // Parse the lastMessage into our expected format
  const audioData = lastMessage
    ? (JSON.parse(lastMessage.data) as WebSocketMessage)
    : null;

  let audioDataView = audioData && (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span>Audio Level:</span>
        <span className="font-mono">{audioData.message.peak}</span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className={`h-full rounded-full transition-all duration-300 ${
            audioData.message.alert_level === "RED"
              ? "bg-red-500"
              : audioData.message.alert_level === "YELLOW"
              ? "bg-yellow-500"
              : "bg-green-500"
          }`}
          style={{
            width: `${Math.min((audioData.message.peak / 3000) * 100, 100)}%`,
          }}
        />
      </div>

      <div className="flex justify-between items-center text-sm text-gray-500">
        <span>Status:</span>
        <span
          className={`font-medium ${
            audioData.message.alert_level === "RED"
              ? "text-red-500"
              : audioData.message.alert_level === "YELLOW"
              ? "text-yellow-500"
              : "text-green-500"
          }`}
        >
          {audioData.message.alert_level}
        </span>
      </div>
    </div>
  );
  const [currentTime, setCurrentTime] = useState(new Date());

  // tick the clock every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer); // Cleanup on unmount
  }, []);

  return (
    <>
      <WebcamVideoStream
        // TODO get the IP from the server which in turn should get it from the .env file
        streamUrl={"http://192.168.0.222:8080/video/live.m3u8"}
      />

      <div className="p-4">
        <WebsocketConnectionStatusBadge readyState={readyState} />

        {audioData ? audioDataView : "No audio data yet"}
        <div className="text-xs text-gray-400 text-right">
          Current time:{" "}
          {currentTime.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
            hour12: true,
          })}
        </div>
        <div className="text-xs text-gray-400 text-right">
          Last event at:{" "}
          {audioData
            ? new Date(audioData.message.timestamp + "Z").toLocaleTimeString(
                "en-US",
                {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                  hour12: true,
                }
              )
            : "N/A"}
        </div>
      </div>
    </>
  );
};

export default AudioVideoMonitor;

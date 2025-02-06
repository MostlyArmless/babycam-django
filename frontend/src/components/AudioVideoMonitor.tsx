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

interface MonitorDevice {
  id: number;
  name: string;
  stream_url: string;
  is_active: boolean;
}

const AudioVideoMonitor = () => {
  const [device, setDevice] = useState<MonitorDevice | null>(null);
  const [audioData, setAudioData] = useState<AudioMessage | null>(null);
  const deviceId = 1; // We'll use device ID 1 for now

  useEffect(() => {
    const fetchDevice = async () => {
      try {
        const response = await fetch(`/api/device/${deviceId}`);
        if (!response.ok) {
          throw new Error("Failed to fetch device data");
        }
        const data = await response.json();
        setDevice(data);
      } catch (error) {
        console.error("Error fetching device data:", error);
      }
    };

    fetchDevice();
  }, [deviceId]);

  const { readyState } = useWebSocket(
    `ws://localhost:8000/ws/monitor/${deviceId}/`,
    {
      onMessage: (event) => {
        console.log("Raw WebSocket message received:", event.data);
        try {
          const parsed = JSON.parse(event.data) as WebSocketMessage;
          console.log("Parsed message:", parsed);
          if (parsed.message.type === "audio_level") {
            setAudioData(parsed.message);
          }
        } catch (e) {
          console.error("Error parsing message:", e);
        }
      },
      onOpen: () => console.log("ws a/v monitor connection established"),
      onClose: () => console.log("ws a/v monitor connection closed"),
      onError: (event) => console.error("ws a/v monitor error:", event),
    }
  );

  let audioDataView = audioData && (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span>Audio Level:</span>
        <span className="font-mono">{audioData.peak}</span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className={`h-full rounded-full transition-all duration-300 ${
            audioData.alert_level === "RED"
              ? "bg-red-500"
              : audioData.alert_level === "YELLOW"
              ? "bg-yellow-500"
              : "bg-green-500"
          }`}
          style={{
            width: `${Math.min((audioData.peak / 3000) * 100, 100)}%`,
          }}
        />
      </div>

      <div className="flex justify-between items-center text-sm text-gray-500">
        <span>Status:</span>
        <span
          className={`font-medium ${
            audioData.alert_level === "RED"
              ? "text-red-500"
              : audioData.alert_level === "YELLOW"
              ? "text-yellow-500"
              : "text-green-500"
          }`}
        >
          {audioData.alert_level}
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

  if (!device) {
    return <div>Loading device data...</div>;
  }

  return (
    <>
      <WebcamVideoStream streamUrl={device.stream_url} />

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
            ? new Date(audioData.timestamp + "Z").toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: true,
              })
            : "N/A"}
        </div>
      </div>
    </>
  );
};

export default AudioVideoMonitor;

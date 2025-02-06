import { ReadyState } from "react-use-websocket";

interface WsConnectionProps {
  readyState: ReadyState;
}

export const WebsocketConnectionStatusBadge: React.FC<WsConnectionProps> = ({
  readyState,
}) => {
  return (
    <div className="mb-4">
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium
    ${
      readyState === WebSocket.OPEN
        ? "bg-green-100 text-green-800"
        : "bg-red-100 text-red-800"
    }`}
      >
        {getWebsocketStatusString(readyState)}
      </span>
    </div>
  );
};

function getWebsocketStatusString(readyState: ReadyState) {
  if (!readyState && readyState !== 0) {
    return "Unknown";
  }

  switch (readyState) {
    case WebSocket.CONNECTING:
      return "Connecting";
    case WebSocket.OPEN:
      return "Connected";
    case WebSocket.CLOSING:
      return "Closing";
    case WebSocket.CLOSED:
      return "Disconnected";
    default:
      return "Unknown";
  }
}

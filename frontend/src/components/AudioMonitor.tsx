import useWebSocket from 'react-use-websocket';

interface AudioMessage {
  type: 'audio_level';
  device_id: number;
  peak: number;
  alert_level: 'NONE' | 'YELLOW' | 'RED';
  timestamp: string;
}

interface WebSocketMessage {
  message: AudioMessage;
}

const AudioMonitor = () => {
  const { lastMessage, readyState } = useWebSocket('ws://localhost:8000/ws/monitor/1/', {
    onMessage: (event) => {
      console.log('Raw WebSocket message received:', event.data);
      try {
        const parsed = JSON.parse(event.data);
        console.log('Parsed message:', parsed);
      } catch (e) {
        console.error('Error parsing message:', e);
      }
    },
    onOpen: () => console.log('WebSocket connection established'),
    onClose: () => console.log('WebSocket connection closed'),
    onError: (event) => console.error('WebSocket error:', event),
  });

  // Parse the lastMessage into our expected format
  const audioData = lastMessage ? JSON.parse(lastMessage.data) as WebSocketMessage : null;
  
  // Get connection status text
  const connectionStatus = {
    [WebSocket.CONNECTING]: 'Connecting',
    [WebSocket.OPEN]: 'Connected',
    [WebSocket.CLOSING]: 'Closing',
    [WebSocket.CLOSED]: 'Disconnected',
  }[readyState];

  let audioDataView = audioData && (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span>Audio Level:</span>
        <span className="font-mono">{audioData.message.peak}</span>
      </div>
      
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className={`h-full rounded-full transition-all duration-300 ${
            audioData.message.alert_level === 'RED' ? 'bg-red-500' :
            audioData.message.alert_level === 'YELLOW' ? 'bg-yellow-500' :
            'bg-green-500'
          }`}
          style={{
            width: `${Math.min((audioData.message.peak / 3000) * 100, 100)}%`
          }}
        />
      </div>

      <div className="flex justify-between items-center text-sm text-gray-500">
        <span>Status:</span>
        <span className={`font-medium ${
          audioData.message.alert_level === 'RED' ? 'text-red-500' :
          audioData.message.alert_level === 'YELLOW' ? 'text-yellow-500' :
          'text-green-500'
        }`}>
          {audioData.message.alert_level}
        </span>
      </div>

      <div className="text-xs text-gray-400">
        Last update: {new Date(audioData.message.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );

  return (
    <div className="p-4">
      <div className="mb-4">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium
          ${readyState === WebSocket.OPEN ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
          {connectionStatus}
        </span>
      </div>

      {audioData ? audioDataView : "No audio data yet"}
    </div>
  );
};

export default AudioMonitor;
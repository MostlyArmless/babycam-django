import ReactHlsPlayer from "@gumlet/react-hls-player";
import { useEffect, useRef, useState } from "react";
import { Switch } from "@/components/ui/switch";

interface WebcamVideoStreamProps {
  streamUrl: string;
}

const WebcamVideoStream = ({ streamUrl }: WebcamVideoStreamProps) => {
  const playerRef = useRef<HTMLVideoElement>(null);
  const [isMuted, setIsMuted] = useState(true); // Start muted

  // Sync player mute state with React state
  useEffect(() => {
    if (playerRef.current) {
      playerRef.current.muted = isMuted;
    }
  }, [isMuted]);

  // Auto-mute on initial play
  useEffect(() => {
    const player = playerRef.current;
    function handlePlay() {
      setIsMuted(true);
    }

    player?.addEventListener("play", handlePlay);
    return () => player?.removeEventListener("play", handlePlay);
  }, []);

  useEffect(() => {
    function fireOnVideoEnd() {
      console.log("video ended");
      console.log(playerRef);
    }

    playerRef.current?.addEventListener("ended", fireOnVideoEnd);

    return playerRef.current?.removeEventListener("ended", fireOnVideoEnd);
  }, []);

  const toggleMute = () => setIsMuted(!isMuted);

  return (
    <>
      <p>Live video feed:</p>
      <ReactHlsPlayer
        playerRef={playerRef}
        src={streamUrl}
        autoPlay={true}
        controls={true}
      />
      <div>
        <div className="flex items-center gap-2">
          <div className="text-gray-600 text-lg">🔇</div>
          <Switch checked={!isMuted} onCheckedChange={toggleMute} />
          <div className="text-gray-600 text-lg">🔊</div>
        </div>
      </div>
    </>
  );
};

export default WebcamVideoStream;

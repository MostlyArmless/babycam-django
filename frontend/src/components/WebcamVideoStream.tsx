import ReactHlsPlayer from "@gumlet/react-hls-player";
import { useEffect, useRef, useState } from "react";
import { Switch } from "@/components/ui/switch";
import Hls from "hls.js";

interface WebcamVideoStreamProps {
  streamUrl: string;
  username?: string;
  password?: string;
}

const WebcamVideoStream = ({
  streamUrl,
  username,
  password,
}: WebcamVideoStreamProps) => {
  const playerRef = useRef<HTMLVideoElement>(null);
  const [isMuted, setIsMuted] = useState(true); // Start muted
  const hlsRef = useRef<Hls | null>(null);

  useEffect(() => {
    if (!playerRef.current) return;

    // Clean up existing HLS instance
    if (hlsRef.current) {
      hlsRef.current.destroy();
    }

    // Create new HLS instance
    if (Hls.isSupported()) {
      const hls = new Hls({
        xhrSetup: (xhr) => {
          if (username && password) {
            const authHeader = "Basic " + btoa(`${username}:${password}`);
            xhr.setRequestHeader("Authorization", authHeader);
          }
        },
        // Add retry delays for better reliability
        manifestLoadingRetryDelay: 1000,
        levelLoadingRetryDelay: 1000,
        fragLoadingRetryDelay: 1000,
      });

      hls.attachMedia(playerRef.current);
      hls.on(Hls.Events.MEDIA_ATTACHED, () => {
        hls.loadSource(streamUrl);
      });

      hls.on(Hls.Events.ERROR, (event, data) => {
        console.error("HLS error:", data);
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              console.log("Network error, trying to recover...");
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              console.log("Media error, trying to recover...");
              hls.recoverMediaError();
              break;
            default:
              console.error("Fatal error, destroying HLS instance");
              hls.destroy();
              break;
          }
        }
      });

      hlsRef.current = hls;
    } else if (playerRef.current.canPlayType("application/vnd.apple.mpegurl")) {
      // For Safari - it has built-in HLS support
      playerRef.current.src = streamUrl;
    }

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
      }
    };
  }, [streamUrl, username, password]);

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
      <video
        ref={playerRef}
        autoPlay
        controls
        style={{ width: "100%", maxWidth: "100%" }}
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

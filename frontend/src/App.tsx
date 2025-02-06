import AudioVideoMonitor from "./components/AudioVideoMonitor";
import Chat from "./components/Chat";
import { useState } from "react";
import UsernameInput from "./components/UsernameInput";

function App() {
  const [username, setUsername] = useState("Guest");

  return (
    <>
      <div className="min-h-screen bg-gray-100 py-6 flex flex-col justify-center">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Baby Monitor</h1>
            <UsernameInput onUsernameChange={setUsername} />
          </div>
          <div className="flex">
            <div className="flex-1">
              <AudioVideoMonitor />
            </div>
            <div className="w-1/3 ml-4">
              <Chat username={username} />
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default App;

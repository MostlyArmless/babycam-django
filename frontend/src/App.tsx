import AudioVideoMonitor from "./components/AudioVideoMonitor";
import Chat from "./components/Chat";
import UserInfoInput from "./components/UserInfoInput";
import { UserProvider } from "@/contexts/UserContext";

function App() {
  return (
    <UserProvider>
      <div className="min-h-screen bg-gray-100 py-6 flex flex-col justify-center">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Baby Monitor</h1>
            <UserInfoInput />
          </div>
          <div className="flex">
            <div className="flex-1">
              <AudioVideoMonitor />
            </div>
            <div className="w-1/3 ml-4">
              <Chat />
            </div>
          </div>
        </div>
      </div>
    </UserProvider>
  );
}

export default App;

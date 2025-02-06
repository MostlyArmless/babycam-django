import { Input } from "@/components/ui/input";
import { useUser } from "@/contexts/UserContext";

const UserInfoInput = () => {
  const { username, setUsername, userColor, setUserColor } = useUser();

  return (
    <div className="mt-4 flex justify-center items-center gap-2">
      <span className="text-gray-600">Your name:</span>
      <Input
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        className="max-w-[200px]"
        placeholder="Enter your name"
      />
      <span className="text-gray-600">Your color:</span>
      <Input
        type="color"
        value={userColor}
        onChange={(e) => setUserColor(e.target.value)}
      />
    </div>
  );
};

export default UserInfoInput;

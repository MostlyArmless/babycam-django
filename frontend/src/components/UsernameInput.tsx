import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";

interface UsernameInputProps {
  onUsernameChange: (username: string) => void;
}

const UsernameInput: React.FC<UsernameInputProps> = ({ onUsernameChange }) => {
  const [username, setUsername] = useState(() => {
    // Try to get username from localStorage, default to "Guest" if not found
    return localStorage.getItem("username") || "Guest";
  });

  // Save username to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem("username", username);
    onUsernameChange(username);
  }, [username, onUsernameChange]);

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
    </div>
  );
};

export default UsernameInput;

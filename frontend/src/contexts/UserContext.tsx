import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";

interface UserContextType {
  username: string;
  setUsername: (username: string) => void;
  userColor: string;
  setUserColor: (color: string) => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState(() => {
    return localStorage.getItem("username") || "Guest";
  });

  const [userColor, setUserColor] = useState(() => {
    return localStorage.getItem("userColor") || "#000000";
  });

  useEffect(() => {
    localStorage.setItem("username", username);
  }, [username]);

  useEffect(() => {
    localStorage.setItem("userColor", userColor);
  }, [userColor]);

  return (
    <UserContext.Provider
      value={{ username, setUsername, userColor, setUserColor }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return context;
}

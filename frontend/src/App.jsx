// src/App.jsx
import { useState } from "react";
import AuthPage from "./pages/AuthPage";
import GamePage from "./pages/GamePage"; // your existing page with Godot iframe etc.

function App() {
  const [authenticated, setAuthenticated] = useState(
    !!localStorage.getItem("accessToken")
  );

  const handleAuthenticated = () => {
    setAuthenticated(true);
  };

  if (!authenticated) {
    return <AuthPage onAuthenticated={handleAuthenticated} />;
  }

  return <GamePage />;
}

export default App;

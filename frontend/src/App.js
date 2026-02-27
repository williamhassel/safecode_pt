import logo from './logo.svg';
import './App.css';

import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import GamePage from "./pages/GamePage";
import AdminPage from "./pages/AdminPage";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/game" element={<GamePage />} />
        <Route path="/admin-review" element={<AdminPage />} />
      </Routes>
    </Router>
  );
}
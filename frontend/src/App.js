import logo from './logo.svg';
import './App.css';

import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import GamePage from "./GamePage";

export default function App() {
  return (
    <Router>
      <nav>
        <Link to="/">Home</Link> | <Link to="/game">Play Game</Link>
      </nav>
      <Routes>
        <Route path="/game" element={<GamePage />} />
      </Routes>
    </Router>
  );
}
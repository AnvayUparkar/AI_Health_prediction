import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import FloatingNavbar from './components/FloatingNavbar';
import Footer from './components/Footer';
import Home from './pages/Home';
import About from './pages/About';
import WhatWeDo from './pages/WhatWeDo';
import LungCancer from './pages/LungCancer';
import Diabetes from './pages/Diabetes';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-health-bg font-inter flex flex-col">
        <FloatingNavbar />
        <main className="flex-grow">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/about" element={<About />} />
            <Route path="/what-we-do" element={<WhatWeDo />} />
            <Route path="/lung-cancer" element={<LungCancer />} />
            <Route path="/diabetes" element={<Diabetes />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </Router>
  );
}

export default App;
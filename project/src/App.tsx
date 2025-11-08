import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import FloatingNavbar from './components/FloatingNavbar';
import Home from './pages/Home';
import LungCancer from './pages/LungCancer';
import Diabetes from './pages/Diabetes';
import About from './pages/About';
import WhatWeDo from './pages/WhatWeDo';
import BookAppointment from './pages/BookAppointment';
import Predictions from './pages/Predictions';
import DietPlanner from './pages/DietPlanner';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
        <FloatingNavbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/lung-cancer" element={<LungCancer />} />
          <Route path="/diabetes" element={<Diabetes />} />
          <Route path="/about" element={<About />} />
          <Route path="/what-we-do" element={<WhatWeDo />} />
          <Route path="/book-appointment" element={<BookAppointment />} />
          <Route path="/predictions" element={<Predictions />} />
          <Route path="/diet-planner" element={<DietPlanner />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
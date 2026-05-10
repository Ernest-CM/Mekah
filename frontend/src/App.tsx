import { NavLink, Route, Routes } from 'react-router-dom';
import DemoTask from './pages/DemoTask';
import ReviewerDashboard from './pages/ReviewerDashboard';
import MetricsDashboard from './pages/MetricsDashboard';

export default function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Mekah - Adaptive Web Interface</h1>
        <nav>
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
            Demo task
          </NavLink>
          <NavLink to="/reviewer" className={({ isActive }) => (isActive ? 'active' : '')}>
            HITL reviewer
          </NavLink>
          <NavLink to="/metrics" className={({ isActive }) => (isActive ? 'active' : '')}>
            Metrics
          </NavLink>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<DemoTask />} />
          <Route path="/reviewer" element={<ReviewerDashboard />} />
          <Route path="/metrics" element={<MetricsDashboard />} />
        </Routes>
      </main>
    </div>
  );
}

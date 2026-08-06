import { Outlet, NavLink } from 'react-router-dom';
import { Home, Upload, Activity, Settings, Brain } from 'lucide-react';

export default function Layout() {
  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <Brain color="#2563EB" size={28} />
          <span>Resume AI</span>
        </div>
        
        <nav className="nav-links">
          <NavLink to="/" className={({isActive}) => isActive ? "nav-link active" : "nav-link"} end>
            <Home size={20} /> Dashboard
          </NavLink>
          <NavLink to="/upload" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
            <Upload size={20} /> Data Upload
          </NavLink>
          <NavLink to="/analyze" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
            <Activity size={20} /> Analysis
          </NavLink>
          <NavLink to="/settings" className={({isActive}) => isActive ? "nav-link active" : "nav-link"}>
            <Settings size={20} /> Settings
          </NavLink>
        </nav>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

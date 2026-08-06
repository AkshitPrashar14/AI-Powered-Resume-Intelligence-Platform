import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Analyze from './pages/Analyze';
import Settings from './pages/Settings';

import { useEffect } from 'react';

function App() {
  useEffect(() => {
    const font = localStorage.getItem('font') || "'Inter', sans-serif";
    document.documentElement.style.setProperty('--font-family', font);
  }, []);

  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="upload" element={<Upload />} />
        <Route path="analyze" element={<Analyze />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}

export default App;

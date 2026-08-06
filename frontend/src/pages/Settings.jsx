import { useState, useEffect } from 'react';
import { Moon, Sun } from 'lucide-react';

export default function Settings() {
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light');
  const [font, setFont] = useState(localStorage.getItem('font') || "'Inter', sans-serif");

  useEffect(() => {
    document.documentElement.style.setProperty('--font-family', font);
    localStorage.setItem('font', font);
  }, [font]);

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  return (
    <div>
      <div style={{ marginBottom: '2.5rem' }}>
        <h1>Settings</h1>
        <p>Manage your application preferences.</p>
      </div>
      
      <div className="card" style={{ maxWidth: '600px' }}>
        <h3>Appearance</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Customize how the platform looks on your device.</p>
        
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {theme === 'dark' ? <Moon color="var(--color-accent)" size={24} /> : <Sun color="var(--color-accent)" size={24} />}
            <div>
              <h4 style={{ margin: 0 }}>Theme</h4>
              <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Toggle between Light and Dark mode</p>
            </div>
          </div>
          
          <button 
            className="btn btn-primary"
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
          >
            Switch to {theme === 'light' ? 'Dark' : 'Light'} Mode
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', marginTop: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ fontSize: '24px' }}>Aa</div>
            <div>
              <h4 style={{ margin: 0 }}>Font Style</h4>
              <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Choose your preferred typography</p>
            </div>
          </div>
          
          <select 
            className="input" 
            style={{ width: '200px' }}
            value={font}
            onChange={(e) => setFont(e.target.value)}
          >
            <option value="'Inter', sans-serif">Inter (Modern)</option>
            <option value="'Roboto', sans-serif">Roboto (Clean)</option>
            <option value="'Playfair Display', serif">Playfair Display (Elegant)</option>
            <option value="'Fira Code', monospace">Fira Code (Developer)</option>
            <option value="'Comic Sans MS', 'Comic Sans', cursive">Comic Sans (Fun)</option>
          </select>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { FileText, Activity, Target, Zap } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function Dashboard() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const { data } = await api.get('/history');
        setHistory(data || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  const latestScore = history.length > 0 ? history[0].ats_score : 0;
  const latestMatch = history.length > 0 ? history[0].similarity_score : 0;

  // Mock data for the chart based on history
  const chartData = history.slice(0, 10).reverse().map((h, i) => ({
    name: `Analysis ${i+1}`,
    score: h.ats_score,
    match: h.similarity_score
  }));

  if (loading) return <div style={{ padding: '2rem' }}>Loading...</div>;

  return (
    <div>
      <div style={{ 
        marginBottom: '2.5rem', 
        padding: '2rem', 
        background: 'linear-gradient(135deg, rgba(37,99,235,0.1) 0%, rgba(16,185,129,0.1) 100%)',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border-color)'
      }}>
        <h1 style={{ marginBottom: '1rem', color: 'var(--text-primary)' }}>Welcome to AI Resume Intelligence</h1>
        <p style={{ fontSize: '1.1rem', color: 'var(--text-secondary)', maxWidth: '800px', lineHeight: '1.6' }}>
          We use <strong>Google Gemini</strong> and <strong>FAISS Vector Search</strong> to analyze your resume against real job descriptions. 
          Upload your resume to get instant ATS scoring, discover critical skill gaps, and receive AI-driven bullet point improvements to land your dream job!
        </p>
      </div>

      <div className="grid-4 mb-8">
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: 'var(--text-secondary)' }}>Total Analyses</h3>
            <Activity color="#2563EB" />
          </div>
          <h2 style={{ fontSize: '2.5rem', margin: 0 }}>{history.length}</h2>
        </div>
        
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: 'var(--text-secondary)' }}>Latest ATS</h3>
            <Target color="#10B981" />
          </div>
          <h2 style={{ fontSize: '2.5rem', margin: 0, color: latestScore > 75 ? '#10B981' : '#F59E0B' }}>
            {latestScore ? `${latestScore.toFixed(0)}/100` : '-'}
          </h2>
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: 'var(--text-secondary)' }}>Latest Match</h3>
            <Zap color="#F59E0B" />
          </div>
          <h2 style={{ fontSize: '2.5rem', margin: 0, color: latestMatch > 75 ? '#10B981' : '#F59E0B' }}>
            {latestMatch ? `${latestMatch.toFixed(0)}%` : '-'}
          </h2>
        </div>
        
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: 'var(--text-secondary)' }}>Quick Actions</h3>
            <FileText color="#6B7280" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <button className="btn btn-primary" style={{ width: '100%' }} onClick={() => navigate('/upload')}>
              Tailored Analysis
            </button>
            <button className="btn" style={{ width: '100%', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }} onClick={() => navigate('/upload', { state: { skipJd: true } })}>
              General Analysis (No JD)
            </button>
          </div>
        </div>
      </div>

      {history.length > 0 && (
        <div className="card">
          <h3>Performance Trend (Live Data)</h3>
          <p style={{ color: 'var(--text-muted)' }}>
            <strong>100% Real Data:</strong> This chart plots the actual ATS and Semantic Match scores from the last {Math.min(history.length, 10)} real analyses performed on this platform.
          </p>
          <div style={{ height: '300px', marginTop: '2rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} domain={[0, 100]} />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                />
                <Line type="monotone" dataKey="score" name="ATS Score" stroke="#2563EB" strokeWidth={3} dot={{r: 4}} activeDot={{r: 6}} />
                <Line type="monotone" dataKey="match" name="Match %" stroke="#10B981" strokeWidth={3} dot={{r: 4}} activeDot={{r: 6}} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

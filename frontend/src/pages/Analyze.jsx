import { useState } from 'react';
import api from '../api';
import { Activity, Target, Zap, ChevronDown, ChevronUp } from 'lucide-react';

export default function Analyze() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  
  const resumeId = localStorage.getItem('current_resume_id');
  const jdText = localStorage.getItem('current_jd_text');

  const runAnalysis = async () => {
    if (!resumeId || !jdText) {
      setError('Please upload a resume and JD first in the Data Upload page.');
      return;
    }
    
    setLoading(true);
    setError('');
    try {
      const { data } = await api.post('/analyze', {
        resume_id: resumeId,
        job_description: jdText
      });
      setResult(data);
    } catch (err) {
      let errorMessage = err.message;
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMessage = err.response.data.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join(', ');
        } else {
          errorMessage = err.response.data.detail;
        }
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (!result && !loading) {
    return (
      <div className="card text-center" style={{ padding: '5rem 2rem' }}>
        <Activity size={48} color="#2563EB" style={{ marginBottom: '1rem' }} />
        <h2>Ready for Analysis</h2>
        <p className="mb-4">We have your Resume and Job Description. Click below to run the AI engine.</p>
        <button className="btn btn-primary" onClick={runAnalysis}>
          Run Full AI Analysis
        </button>
        {error && <p className="text-danger mt-4">{error}</p>}
      </div>
    );
  }

  if (loading) {
    return (
      <div className="card text-center" style={{ padding: '5rem 2rem' }}>
        <h2>Analyzing...</h2>
        <p>Our AI is reading your resume and comparing it against the job description.</p>
        <p>This usually takes 30-60 seconds.</p>
      </div>
    );
  }

  const ats = result.ats_score || {};
  const match = result.match_result || {};

  return (
    <div>
      <div style={{ marginBottom: '2.5rem' }}>
        <h1>Analysis Results</h1>
        <p>Here is how your resume stacks up.</p>
      </div>

      <div className="grid-2 mb-4">
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Target color="#2563EB" />
            <h3 style={{ margin: 0 }}>ATS Score</h3>
          </div>
          <h2 style={{ fontSize: '3rem', color: ats.total_score >= 75 ? '#10B981' : '#F59E0B' }}>
            {ats.total_score?.toFixed(0)}<span style={{ fontSize: '1.5rem', color: 'var(--text-muted)' }}>/100</span>
          </h2>
          <div style={{ marginTop: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
              <span>Keywords ({ats.keyword_score}/25)</span>
            </div>
            <div style={{ width: '100%', height: '8px', background: '#F3F4F6', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: `${(ats.keyword_score/25)*100}%`, height: '100%', background: '#2563EB' }} />
            </div>
          </div>
        </div>
        
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <Zap color="#F59E0B" />
            <h3 style={{ margin: 0 }}>Semantic Match</h3>
          </div>
          <h2 style={{ fontSize: '3rem', color: match.similarity_percentage >= 75 ? '#10B981' : '#F59E0B' }}>
            {match.similarity_percentage?.toFixed(0)}<span style={{ fontSize: '1.5rem', color: 'var(--text-muted)' }}>%</span>
          </h2>
          <p style={{ marginTop: '1rem' }}>{match.match_verdict}</p>
        </div>
      </div>

      <div className="card mb-4">
        <h3>AI Insights</h3>
        {(!result.strengths?.length && !result.weaknesses?.length) ? (
          <p className="text-muted">AI insights are currently unavailable. This is usually caused by the Gemini API rate limit being exceeded (15 requests/minute). Please try again in a minute.</p>
        ) : (
          <div className="grid-2">
            <div>
              <h4 style={{ color: '#10B981' }}>Strengths</h4>
              <ul style={{ paddingLeft: '1.5rem' }}>
                {result.strengths?.map((s, i) => <li key={i} className="mb-1">{s}</li>)}
              </ul>
            </div>
            <div>
              <h4 style={{ color: '#F59E0B' }}>Weaknesses</h4>
              <ul style={{ paddingLeft: '1.5rem' }}>
                {result.weaknesses?.map((w, i) => <li key={i} className="mb-1">{w}</li>)}
              </ul>
            </div>
          </div>
        )}
      </div>
      
      <div className="card">
        <h3>Missing Skills (High Priority)</h3>
        <div>
          {(!result.skill_gap?.job_skills?.length) ? (
            <p className="text-muted">Skill gap analysis is currently unavailable (Rate limit exceeded).</p>
          ) : result.skill_gap?.high_priority_missing?.length > 0 ? (
            result.skill_gap.high_priority_missing.map((s, i) => (
              <span key={i} className="tag tag-missing">{s}</span>
            ))
          ) : (
            <p>None! Great job.</p>
          )}
        </div>
      </div>
    </div>
  );
}

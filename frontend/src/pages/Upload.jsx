import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api from '../api';
import { UploadCloud, FileText, CheckCircle, Target } from 'lucide-react';

export default function Upload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [resumeId, setResumeId] = useState(localStorage.getItem('current_resume_id') || '');
  
  const [jdTitle, setJdTitle] = useState('');
  const [jdText, setJdText] = useState(localStorage.getItem('current_jd_text') || '');
  const [jdUploading, setJdUploading] = useState(false);
  const [jdId, setJdId] = useState(localStorage.getItem('current_jd_id') || '');
  const [pastResumes, setPastResumes] = useState([]);

  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const fetchResumes = async () => {
      try {
        const { data } = await api.get('/upload/resumes');
        setPastResumes(data || []);
      } catch (err) {
        console.error("Failed to fetch past resumes", err);
      }
    };
    fetchResumes();
  }, []);

  const clearResume = () => {
    setResumeId('');
    setFile(null);
    localStorage.removeItem('current_resume_id');
  };

  const clearJD = () => {
    setJdId('');
    setJdTitle('');
    setJdText('');
    localStorage.removeItem('current_jd_id');
    localStorage.removeItem('current_jd_text');
  };

  const handleSkipJD = async () => {
    setJdUploading(true);
    const genericTitle = "General Professional Role";
    const genericText = "Seeking a capable professional with strong industry skills, good communication, problem-solving abilities, and a solid track record of performance in relevant roles.";
    try {
      const { data } = await api.post('/upload/job-description', {
        title: genericTitle,
        description: genericText
      });
      setJdId(data.id);
      localStorage.setItem('current_jd_text', genericText);
      localStorage.setItem('current_jd_id', data.id);
      setJdTitle(genericTitle);
      setJdText(genericText);
      
      // If we got here via Dashboard Quick Action, we can automatically go to analyze if resume is also ready.
      if (location.state?.skipJd && resumeId) {
        navigate('/analyze');
      }
    } catch (err) {
      alert('Skip JD failed: ' + err.message);
    } finally {
      setJdUploading(false);
    }
  };

  useEffect(() => {
    // Automatically trigger Skip JD if navigated from 'General Analysis'
    if (location.state?.skipJd && !jdId && !jdUploading) {
      handleSkipJD();
    }
  }, [location.state]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUploadResume = async () => {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const { data } = await api.post('/upload', formData);
      setResumeId(data.resume_id);
      localStorage.setItem('current_resume_id', data.resume_id);
    } catch (err) {
      alert('Upload failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  const handleUploadJD = async () => {
    if (!jdTitle || !jdText) return;
    setJdUploading(true);
    
    try {
      const { data } = await api.post('/upload/job-description', {
        title: jdTitle,
        description: jdText
      });
      setJdId(data.id);
      localStorage.setItem('current_jd_text', jdText);
      localStorage.setItem('current_jd_id', data.id);
    } catch (err) {
      let errorMessage = err.message;
      if (err.response?.data?.detail) {
        if (Array.isArray(err.response.data.detail)) {
          errorMessage = err.response.data.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join(', ');
        } else {
          errorMessage = err.response.data.detail;
        }
      }
      alert('JD Upload failed: ' + errorMessage);
    } finally {
      setJdUploading(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: '2.5rem' }}>
        <h1>Data Upload</h1>
        <p>Upload your resume and the target job description to begin analysis.</p>
      </div>

      <div className="grid-2">
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
            <FileText color="#2563EB" />
            <h2 style={{ margin: 0, fontSize: '1.25rem' }}>1. Upload Resume</h2>
          </div>
          
          {!resumeId ? (
            <div 
              style={{ 
                border: '2px dashed var(--border-color)', 
                borderRadius: 'var(--radius-md)', 
                padding: '3rem 2rem', 
                textAlign: 'center',
                backgroundColor: 'var(--bg-primary)'
              }}
            >
              <UploadCloud size={48} color="var(--text-muted)" style={{ marginBottom: '1rem' }} />
              <div className="input-group">
                <input type="file" accept=".pdf,.docx,.txt" onChange={handleFileChange} />
              </div>
              <p style={{ fontSize: '0.875rem' }}>Supported formats: PDF, DOCX, TXT</p>
              
              <button 
                className="btn btn-primary" 
                onClick={handleUploadResume} 
                disabled={!file || uploading}
                style={{ marginTop: '1rem' }}
              >
                {uploading ? 'Uploading...' : 'Upload Resume'}
              </button>
              
              {pastResumes.length > 0 && (
                <div className="input-group text-left" style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-color)', textAlign: 'left' }}>
                  <label>Or select a previously uploaded resume:</label>
                  <select 
                    className="input"
                    onChange={(e) => {
                      if (e.target.value) {
                        setResumeId(e.target.value);
                        localStorage.setItem('current_resume_id', e.target.value);
                      }
                    }}
                  >
                    <option value="">-- Select a Resume --</option>
                    {pastResumes.map(r => (
                      <option key={r.id} value={r.id}>{r.original_filename}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem 0' }}>
              <CheckCircle size={48} color="#10B981" style={{ marginBottom: '1rem' }} />
              <h3>Resume Uploaded!</h3>
              <p>ID: {resumeId.slice(0,8)}...</p>
              <button className="btn btn-outline" style={{ marginTop: '1rem' }} onClick={clearResume}>
                Upload a Different Resume
              </button>
            </div>
          )}
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
            <Target color="#2563EB" />
            <h2 style={{ margin: 0, fontSize: '1.25rem' }}>2. Job Description</h2>
          </div>
          
          {!jdId ? (
            <div>
              <div className="input-group">
                <label>Job Title</label>
                <input className="input" value={jdTitle} onChange={e => setJdTitle(e.target.value)} placeholder="e.g. Senior Software Engineer (Optional)" />
              </div>
              <div className="input-group">
                <label>Job Description</label>
                <textarea 
                  className="input" 
                  rows="6" 
                  value={jdText} 
                  onChange={e => setJdText(e.target.value)} 
                  placeholder="For a tailored experience, paste the job description here. If you just want a general resume review, click 'Skip JD'."
                  style={{ resize: 'vertical' }}
                />
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button 
                  className="btn btn-primary" 
                  onClick={handleUploadJD} 
                  disabled={!jdTitle || !jdText || jdUploading}
                >
                  {jdUploading ? 'Saving...' : 'Save Job Description'}
                </button>
                <button 
                  className="btn" 
                  style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}
                  onClick={handleSkipJD} 
                  disabled={jdUploading}
                >
                  Skip JD & Proceed
                </button>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem 0' }}>
              <CheckCircle size={48} color="#10B981" style={{ marginBottom: '1rem' }} />
              <h3>Job Description Saved!</h3>
              <button className="btn btn-outline" style={{ marginTop: '1rem' }} onClick={clearJD}>
                Clear and Enter New JD
              </button>
            </div>
          )}
        </div>
      </div>
      
      {resumeId && jdId && (
        <div className="text-center mt-4">
          <button className="btn btn-primary" style={{ padding: '1rem 3rem', fontSize: '1.1rem' }} onClick={() => navigate('/analyze')}>
            Proceed to Analysis
          </button>
        </div>
      )}
    </div>
  );
}



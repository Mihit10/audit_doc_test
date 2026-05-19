import React, { useState } from 'react';
import { PhotoArrayInput } from './components/PhotoArrayInput';
import { submitPhotoAudit } from './services/api';

function App() {
  const [photoEvidence, setPhotoEvidence] = useState<any[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setResult(null);
    try {
      const response = await submitPhotoAudit(photoEvidence);
      setResult(response);
    } catch (err: any) {
      setResult({ success: false, message: err.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '24px', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ color: 'var(--text-h)', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
        Isolated Photo Evidence Test
      </h1>
      
      <div style={{ marginTop: '24px', marginBottom: '32px' }}>
        <p style={{ color: 'var(--text)', marginBottom: '16px' }}>
          Add your photo observations below. Click Submit to generate the DOCX without LLM or DB.
        </p>
        
        <PhotoArrayInput value={photoEvidence} onChange={setPhotoEvidence} />
      </div>

      <div style={{ padding: '24px', background: 'var(--code-bg)', borderRadius: '8px', border: '1px solid var(--border)' }}>
        <button
          onClick={handleSubmit}
          disabled={isSubmitting || photoEvidence.length === 0}
          style={{
            background: isSubmitting ? 'var(--border)' : 'var(--accent)',
            color: 'white',
            padding: '12px 24px',
            border: 'none',
            borderRadius: '6px',
            fontSize: '1rem',
            cursor: isSubmitting ? 'not-allowed' : 'pointer',
            fontWeight: '600'
          }}
        >
          {isSubmitting ? 'Generating Report...' : 'Submit to Backend'}
        </button>

        {result && (
          <div style={{ marginTop: '24px', padding: '16px', borderRadius: '6px', background: result.success ? 'var(--accent-bg)' : 'rgba(255, 0, 0, 0.1)', border: `1px solid ${result.success ? 'var(--accent-border)' : 'rgba(255, 0, 0, 0.3)'}` }}>
            <h4 style={{ margin: '0 0 8px 0', color: result.success ? 'var(--text-h)' : '#ff4444' }}>
              {result.success ? 'Success!' : 'Error'}
            </h4>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: 'var(--text)' }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

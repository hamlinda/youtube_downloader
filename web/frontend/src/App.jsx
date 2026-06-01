import React, { useState, useEffect, useRef } from 'react';
import { Download, CheckCircle2, AlertCircle } from 'lucide-react';
import './index.css';

function App() {
  const [url, setUrl] = useState('');
  const [browser, setBrowser] = useState('None');
  const [audioOnly, setAudioOnly] = useState(false);
  const [summarize, setSummarize] = useState(false);
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [ollamaModel, setOllamaModel] = useState('llama3:8b');
  const [summary, setSummary] = useState('');
  const [transcript, setTranscript] = useState('');
  
  const [isDownloading, setIsDownloading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState({ text: 'Ready', type: 'normal' });
  const [logs, setLogs] = useState([]);
  
  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  const browsers = ["None", "chrome", "firefox", "edge", "opera", "safari", "vivaldi", "brave"];

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const startDownload = () => {
    if (!url.trim()) {
      setStatus({ text: 'Error: Please enter a YouTube URL.', type: 'error' });
      return;
    }

    setIsDownloading(true);
    setProgress(0);
    setLogs([]);
    setSummary('');
    setTranscript('');
    setStatus({ text: 'Connecting to server...', type: 'normal' });

    // Connect to WebSocket
    // Use window.location.hostname to connect back to the same server if running in Docker/prod
    // For dev, assuming FastAPI is running on port 8000 on localhost
    const wsUrl = `ws://${window.location.hostname || 'localhost'}:8000/ws/download`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ 
        url, 
        browser, 
        audio_only: audioOnly,
        summarize,
        ollama_url: ollamaUrl,
        ollama_model: ollamaModel
      }));
      setStatus({ text: 'Starting download...', type: 'white' });
      setLogs(prev => [...prev, { text: `Starting download for: ${url}`, isError: false }]);
      if (browser !== 'None') {
        setLogs(prev => [...prev, { text: `Using ${browser} cookies for authentication.`, isError: false }]);
      }
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'progress') {
        setProgress(data.percent);
        setStatus({ text: `Downloading: ${data.percent.toFixed(1)}% at ${data.speed} ETA: ${data.eta}`, type: 'white' });
      } else if (data.type === 'log') {
        setLogs(prev => [...prev, { text: data.message, isError: false }]);
      } else if (data.type === 'success') {
        setProgress(100);
        setStatus({ text: 'Download Finished!', type: 'success' });
        setIsDownloading(false);
        if (data.summary) {
          setSummary(data.summary);
        }
        if (data.transcript) {
          setTranscript(data.transcript);
        }
        ws.close();
      } else if (data.type === 'error') {
        setStatus({ text: 'Error occurred', type: 'error' });
        setLogs(prev => [...prev, { text: data.message, isError: true }]);
        setIsDownloading(false);
        ws.close();
      }
    };

    ws.onclose = () => {
      if (isDownloading) {
        setStatus({ text: 'Connection to server lost.', type: 'error' });
        setIsDownloading(false);
      }
    };
    
    ws.onerror = () => {
        setStatus({ text: 'WebSocket connection failed. Make sure backend is running.', type: 'error' });
        setIsDownloading(false);
    };
  };

  return (
    <div className="app-container">
      <h1>YouTube Video Downloader</h1>

      <div className="input-group">
        <label>YouTube URL:</label>
        <input 
          type="text" 
          placeholder="https://www.youtube.com/watch?v=..." 
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={isDownloading}
        />
      </div>

      <div className="input-group">
        <label>Authentication (Browser Cookies):</label>
        <select value={browser} onChange={(e) => setBrowser(e.target.value)} disabled={isDownloading}>
          {browsers.map(b => <option key={b} value={b}>{b}</option>)}
        </select>
      </div>

      <div className="options-row">
        <label className="checkbox-group">
          <input 
            type="checkbox" 
            checked={audioOnly} 
            onChange={(e) => setAudioOnly(e.target.checked)} 
            disabled={isDownloading}
          />
          <span>Audio Only (MP3)</span>
        </label>

        <label className="checkbox-group">
          <input 
            type="checkbox" 
            checked={summarize} 
            onChange={(e) => setSummarize(e.target.checked)} 
            disabled={isDownloading}
          />
          <span>Summarize Video (via AI)</span>
        </label>
      </div>

      {summarize && (
        <details className="settings-details">
          <summary>AI Summary Settings</summary>
          <div className="settings-content">
            <div className="input-group">
              <label>Ollama URL:</label>
              <input 
                type="text" 
                value={ollamaUrl} 
                onChange={(e) => setOllamaUrl(e.target.value)} 
                disabled={isDownloading}
              />
            </div>
            <div className="input-group">
              <label>Ollama Model:</label>
              <input 
                type="text" 
                value={ollamaModel} 
                onChange={(e) => setOllamaModel(e.target.value)} 
                disabled={isDownloading}
              />
            </div>
          </div>
        </details>
      )}

      <button className="download-btn" onClick={startDownload} disabled={isDownloading}>
        {isDownloading ? 'Downloading...' : <><Download size={18}/> Download Video</>}
      </button>

      <div className="progress-container">
        <div className="progress-bar-bg">
          <div className="progress-bar-fill" style={{ width: `${progress}%` }}></div>
        </div>
        <div className={`status-text ${status.type}`}>
          {status.type === 'success' && <CheckCircle2 size={14} style={{display:'inline', verticalAlign:'middle', marginRight:'4px'}}/>}
          {status.type === 'error' && <AlertCircle size={14} style={{display:'inline', verticalAlign:'middle', marginRight:'4px'}}/>}
          {status.text}
        </div>
      </div>

      <div className="log-box">
        {logs.map((log, i) => (
          <p key={i} className={`log-line ${log.isError ? 'error' : ''}`}>{log.text}</p>
        ))}
        <div ref={logsEndRef} />
      </div>

      {summary && (
        <div className="result-container">
          <h2>AI Summary</h2>
          <div className="summary-text">{summary}</div>
        </div>
      )}

      {transcript && (
        <div className="result-container">
          <h2>Transcript</h2>
          <pre className="transcript-text">{transcript}</pre>
        </div>
      )}
    </div>
  );
}

export default App;

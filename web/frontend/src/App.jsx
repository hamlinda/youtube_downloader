import React, { useState, useEffect, useRef } from 'react';
import { Download, CheckCircle2, AlertCircle } from 'lucide-react';
import './index.css';

function App() {
  const [url, setUrl] = useState('');
  const [browser, setBrowser] = useState('None');
  const [audioOnly, setAudioOnly] = useState(false);
  const [summarize, setSummarize] = useState(false);
  const [ollamaUrl, setOllamaUrl] = useState(() => {
    const host = window.location.hostname || 'localhost';
    return `http://${host}:11434`;
  });
  const [ollamaModel, setOllamaModel] = useState('llama3:8b');
  const [summary, setSummary] = useState('');
  const [transcript, setTranscript] = useState('');
  
  const [isDownloading, setIsDownloading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState({ text: 'Ready', type: 'normal' });
  const [logs, setLogs] = useState([]);
  const [downloadedFiles, setDownloadedFiles] = useState({
    video: null,
    audio: null,
    transcript: null,
    summary: null
  });

  // Upload and Library states
  const [activeTab, setActiveTab] = useState('download'); // 'download' or 'upload'
  const [uploadFile, setUploadFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [showLibrary, setShowLibrary] = useState(false);
  const [savedVideos, setSavedVideos] = useState([]);
  const [previewVideo, setPreviewVideo] = useState(null);
  
  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  const browsers = ["None", "chrome", "firefox", "edge", "opera", "safari", "vivaldi", "brave"];

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const fetchSavedVideos = async () => {
    try {
      const response = await fetch('/api/videos');
      if (response.ok) {
        const data = await response.json();
        setSavedVideos(data);
      }
    } catch (err) {
      console.error("Failed to fetch saved videos", err);
    }
  };

  useEffect(() => {
    if (showLibrary) {
      fetchSavedVideos();
      const timer = setInterval(fetchSavedVideos, 10000); // refresh every 10s
      return () => clearInterval(timer);
    }
  }, [showLibrary]);

  const handleDeleteVideo = async (filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) return;
    try {
      const response = await fetch(`/api/videos/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        if (previewVideo === filename) {
          setPreviewVideo(null);
        }
        fetchSavedVideos();
      }
    } catch (err) {
      console.error("Failed to delete video", err);
    }
  };

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
    setDownloadedFiles({ video: null, audio: null, transcript: null, summary: null });
    setStatus({ text: 'Connecting to server...', type: 'normal' });

    const isDev = import.meta.env.DEV;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname || 'localhost';
    const port = isDev ? '8000' : window.location.port;
    const base = window.location.pathname.replace(/\/?[^\/]*$/, '');
    const wsUrl = `${protocol}//${host}${port ? `:${port}` : ''}${base}/ws/download`;
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
        setDownloadedFiles({
          video: data.video_file || null,
          audio: data.audio_file || null,
          transcript: data.transcript_file || null,
          summary: data.summary_file || null
        });
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

  const startUpload = () => {
    if (!uploadFile) {
      setStatus({ text: 'Error: Please select a video file to upload.', type: 'error' });
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setLogs([]);
    setSummary('');
    setTranscript('');
    setDownloadedFiles({ video: null, audio: null, transcript: null, summary: null });
    setStatus({ text: 'Uploading file...', type: 'normal' });
    setLogs(prev => [...prev, { text: `Uploading file: ${uploadFile.name} (${(uploadFile.size / (1024 * 1024)).toFixed(2)} MB)...`, isError: false }]);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload');

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percentComplete = (event.loaded / event.total) * 100;
        setUploadProgress(percentComplete);
        setStatus({ text: `Uploading: ${percentComplete.toFixed(1)}%`, type: 'white' });
      }
    };

    xhr.onload = () => {
      if (xhr.status === 200) {
        const response = JSON.parse(xhr.responseText);
        setLogs(prev => [...prev, { text: `Upload complete! Starting transcription...`, isError: false }]);
        setIsUploading(false);
        startTranscription(response.filename);
      } else {
        setIsUploading(false);
        setStatus({ text: 'Upload failed.', type: 'error' });
        setLogs(prev => [...prev, { text: `Upload failed with status: ${xhr.status}`, isError: true }]);
      }
    };

    xhr.onerror = () => {
      setIsUploading(false);
      setStatus({ text: 'Upload failed due to network error.', type: 'error' });
      setLogs(prev => [...prev, { text: `Upload network error.`, isError: true }]);
    };

    const formData = new FormData();
    formData.append('file', uploadFile);
    xhr.send(formData);
  };

  const startTranscription = (filename) => {
    setIsTranscribing(true);
    setStatus({ text: 'Starting transcription...', type: 'normal' });

    const isDev = import.meta.env.DEV;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname || 'localhost';
    const port = isDev ? '8000' : window.location.port;
    const base = window.location.pathname.replace(/\/?[^\/]*$/, '');
    const wsUrl = `${protocol}//${host}${port ? `:${port}` : ''}${base}/ws/transcribe`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ 
        filename, 
        summarize,
        ollama_url: ollamaUrl,
        ollama_model: ollamaModel
      }));
      setLogs(prev => [...prev, { text: `Transcription connection established.`, isError: false }]);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'log') {
        setLogs(prev => [...prev, { text: data.message, isError: false }]);
      } else if (data.type === 'success') {
        setStatus({ text: 'Transcription Finished!', type: 'success' });
        setIsTranscribing(false);
        setDownloadedFiles({
          video: filename,
          audio: null,
          transcript: data.transcript_file || null,
          summary: data.summary_file || null
        });
        if (data.summary) {
          setSummary(data.summary);
        }
        if (data.transcript) {
          setTranscript(data.transcript);
        }
        ws.close();
      } else if (data.type === 'error') {
        setStatus({ text: 'Error occurred during transcription', type: 'error' });
        setLogs(prev => [...prev, { text: data.message, isError: true }]);
        setIsTranscribing(false);
        ws.close();
      }
    };

    ws.onclose = () => {
      if (isTranscribing) {
        setStatus({ text: 'Transcription connection lost.', type: 'error' });
        setIsTranscribing(false);
      }
    };
    
    ws.onerror = () => {
        setStatus({ text: 'WebSocket connection failed.', type: 'error' });
        setIsTranscribing(false);
    };
  };

  const displayProgress = activeTab === 'download' 
    ? progress 
    : (isUploading ? uploadProgress : (isTranscribing ? 100 : 0));

  const isWorking = isDownloading || isUploading || isTranscribing;

  return (
    <div className="app-container">
      <div className="app-header">
        <h1>YouTube Media Hub</h1>
        <button className="library-btn" onClick={() => setShowLibrary(true)}>
          📁 Saved Library
        </button>
      </div>

      <div className="tab-bar">
        <button 
          className={`tab-btn ${activeTab === 'download' ? 'active' : ''}`}
          onClick={() => setActiveTab('download')}
          disabled={isWorking}
        >
          Download from URL
        </button>
        <button 
          className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
          disabled={isWorking}
        >
          Upload Local Video
        </button>
      </div>

      {activeTab === 'download' ? (
        <>
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
        </>
      ) : (
        <div className="upload-section">
          <label>Upload Video File:</label>
          <div 
            className="upload-dropzone"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                setUploadFile(e.dataTransfer.files[0]);
              }
            }}
          >
            <input 
              type="file" 
              id="file-upload" 
              accept="video/*" 
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setUploadFile(e.target.files[0]);
                }
              }}
              style={{ display: 'none' }}
              disabled={isUploading || isTranscribing}
            />
            <label htmlFor="file-upload" className="dropzone-label">
              <div className="upload-icon">⬆️</div>
              {uploadFile ? (
                <div className="selected-file-info">
                  <span className="file-name">{uploadFile.name}</span>
                  <span className="file-size">({(uploadFile.size / (1024 * 1024)).toFixed(2)} MB)</span>
                </div>
              ) : (
                <span>Drag & drop video here, or click to browse</span>
              )}
            </label>
          </div>
        </div>
      )}

      <div className="options-row">
        {activeTab === 'download' && (
          <label className="checkbox-group">
            <input 
              type="checkbox" 
              checked={audioOnly} 
              onChange={(e) => setAudioOnly(e.target.checked)} 
              disabled={isDownloading}
            />
            <span>Audio Only (MP3)</span>
          </label>
        )}

        <label className="checkbox-group">
          <input 
            type="checkbox" 
            checked={summarize} 
            onChange={(e) => setSummarize(e.target.checked)} 
            disabled={isWorking}
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
                disabled={isWorking}
              />
            </div>
            <div className="input-group">
              <label>Ollama Model:</label>
              <input 
                type="text" 
                value={ollamaModel} 
                onChange={(e) => setOllamaModel(e.target.value)} 
                disabled={isWorking}
              />
            </div>
          </div>
        </details>
      )}

      {activeTab === 'download' ? (
        <button className="download-btn" onClick={startDownload} disabled={isDownloading}>
          {isDownloading ? 'Downloading...' : <><Download size={18}/> Download Video</>}
        </button>
      ) : (
        <button 
          className="download-btn upload-btn-color" 
          onClick={startUpload} 
          disabled={isUploading || isTranscribing || !uploadFile}
        >
          {isUploading ? 'Uploading...' : isTranscribing ? 'Transcribing...' : 'Upload & Transcribe'}
        </button>
      )}

      <div className="progress-container">
        <div className="progress-bar-bg">
          <div 
            className={`progress-bar-fill ${activeTab === 'upload' && isTranscribing ? 'shimmering' : ''}`} 
            style={{ width: `${displayProgress}%` }}
          ></div>
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

      {(downloadedFiles.video || downloadedFiles.audio || downloadedFiles.transcript || downloadedFiles.summary) && (
        <div className="result-container">
          <h2>Download Collateral</h2>
          <div className="download-buttons-group">
            {downloadedFiles.video && (
              <a 
                href={`/downloads/${encodeURIComponent(downloadedFiles.video)}`} 
                download={downloadedFiles.video}
                className="collateral-btn video-btn"
              >
                Download Video (MP4)
              </a>
            )}
            {downloadedFiles.audio && (
              <a 
                href={`/downloads/${encodeURIComponent(downloadedFiles.audio)}`} 
                download={downloadedFiles.audio}
                className="collateral-btn audio-btn"
              >
                Download Audio (MP3)
              </a>
            )}
            {downloadedFiles.transcript && (
              <a 
                href={`/downloads/${encodeURIComponent(downloadedFiles.transcript)}`} 
                download={downloadedFiles.transcript}
                className="collateral-btn text-btn"
              >
                Download Transcript (TXT)
              </a>
            )}
            {downloadedFiles.summary && (
              <a 
                href={`/downloads/${encodeURIComponent(downloadedFiles.summary)}`} 
                download={downloadedFiles.summary}
                className="collateral-btn text-btn"
              >
                Download Summary (TXT)
              </a>
            )}
          </div>
        </div>
      )}

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

      {showLibrary && (
        <div className="modal-overlay" onClick={() => { setShowLibrary(false); setPreviewVideo(null); }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📁 Saved Library</h2>
              <button className="close-modal-btn" onClick={() => { setShowLibrary(false); setPreviewVideo(null); }}>
                ✕
              </button>
            </div>
            
            <p className="library-note">
              ⚠️ MP4 files are automatically deleted 24 hours after download/upload.
            </p>

            <div className="library-list">
              {savedVideos.length === 0 ? (
                <div className="empty-library">No saved videos found.</div>
              ) : (
                savedVideos.map((video) => {
                  const hoursLeft = Math.floor(video.expires_in / 3600);
                  const minsLeft = Math.floor((video.expires_in % 3600) / 60);
                  const isExpiringSoon = hoursLeft < 2;
                  
                  return (
                    <div key={video.filename} className="library-item">
                      <div className="library-item-main">
                        <div className="library-item-info">
                          <span className="library-item-title" title={video.filename}>
                            {video.filename}
                          </span>
                          <div className="library-item-meta">
                            <span className="meta-size">
                              {(video.size / (1024 * 1024)).toFixed(2)} MB
                            </span>
                            <span className={`meta-expires ${isExpiringSoon ? 'expiring-soon' : ''}`}>
                              ⏰ Expires in {hoursLeft}h {minsLeft}m
                            </span>
                          </div>
                        </div>
                        
                        <div className="library-item-actions">
                          <button 
                            className={`lib-action-btn play-btn ${previewVideo === video.filename ? 'active' : ''}`}
                            onClick={() => setPreviewVideo(previewVideo === video.filename ? null : video.filename)}
                          >
                            {previewVideo === video.filename ? '⏸️ Stop' : '▶️ Play'}
                          </button>
                          <button 
                            className="lib-action-btn delete-btn-lib" 
                            onClick={() => handleDeleteVideo(video.filename)}
                          >
                            🗑️ Delete
                          </button>
                        </div>
                      </div>

                      {previewVideo === video.filename && (
                        <div className="library-video-preview">
                          <video 
                            controls 
                            autoPlay 
                            src={`/downloads/${encodeURIComponent(video.filename)}`}
                            className="preview-video-element"
                          />
                        </div>
                      )}

                      <div className="library-collateral-links">
                        <a 
                          href={`/downloads/${encodeURIComponent(video.filename)}`} 
                          download={video.filename}
                          className="lib-link video"
                        >
                          Video (MP4)
                        </a>
                        {video.has_transcript ? (
                          <a 
                            href={`/downloads/${encodeURIComponent(video.filename.replace(/\.mp4$/, '_transcript.txt'))}`} 
                            download={video.filename.replace(/\.mp4$/, '_transcript.txt')}
                            className="lib-link doc"
                          >
                            Transcript (TXT)
                          </a>
                        ) : (
                          <span className="lib-link-disabled">No Transcript</span>
                        )}
                        {video.has_summary ? (
                          <a 
                            href={`/downloads/${encodeURIComponent(video.filename.replace(/\.mp4$/, '_summary.txt'))}`} 
                            download={video.filename.replace(/\.mp4$/, '_summary.txt')}
                            className="lib-link doc"
                          >
                            Summary (TXT)
                          </a>
                        ) : (
                          <span className="lib-link-disabled">No Summary</span>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

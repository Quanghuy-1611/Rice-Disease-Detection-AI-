import React, { useState, useRef } from 'react';
import axios from 'axios';
import { DISEASES } from './DiseaseLibrary';
import './Home.css';

const UploadIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="drop-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
  </svg>
);

const ScanIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);

const DISEASE_NAMES = {
  "bacterial_leaf_blight": "Cháy lá vi khuẩn",
  "bacterial_leaf_streak": "Sọc lá vi khuẩn",
  "bacterial_panicle_blight": "Cháy gié vi khuẩn",
  "blast": "Bệnh Đạo ôn",
  "brown_spot": "Bệnh Đốm nâu",
  "dead_heart": "Bệnh đục thân (Dead Heart)",
  "downy_mildew": "Bệnh Sương mai",
  "hispa": "Bọ gai (Hispa)",
  "normal": "Cây lúa khỏe mạnh 🌿",
  "tungro": "Bệnh Tungro (Vàng lụi)",
  "leaf_smut": "Bệnh Than Đen (Leaf Smut)",
  "weeds": "Cỏ dại 🌿",
  "golden_apple_snail": "Ốc bươu vàng 🐌",
  "stem_borer": "Sâu đục thân 🐛",
  "leaf_roller": "Sâu cuốn lá nhỏ 🐛",
  "brown_planthopper": "Rầy nâu 🪲",
  "whitebacked_planthopper": "Rầy phấn trắng 🪲",
  "southern_black_streaked_dwarf": "Bệnh Lùn sọc đen 📉",
  "sheath_blight": "Bệnh Khô vằn 🍂"
};

function Home() {
  const [selectedImage, setSelectedImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [severity, setSeverity] = useState('low');
  
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file && file.type.startsWith('image/')) {
      processFile(file);
    }
  };

  const processFile = (file) => {
    setSelectedImage(file);
    if (file) {
      setPreviewUrl(URL.createObjectURL(file));
    } else {
      setPreviewUrl(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
    setResult(null);
    setError(null);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      processFile(file);
    }
  };

  const analyzeImage = async () => {
    if (!selectedImage) return;
    setIsAnalyzing(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', selectedImage);
    formData.append('severity', severity);
    
    const token = localStorage.getItem('token');
    
    try {
      const response = await axios.post('/api/predict', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });
      setResult(response.data);
    } catch (err) {
      if (err.response && err.response.status === 401) {
        setError('Vui lòng Đăng nhập để sử dụng chức năng phân tích.');
      } else {
        setError(err.response?.data?.detail || 'Lỗi khi kết nối đến server.');
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Tìm chi tiết bệnh từ Thư viện
  const diseaseInfo = result && result.prediction !== 'normal' 
    ? DISEASES.find(d => d.id === result.prediction) 
    : null;

  return (
    <div className="home-container">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <h1>Bảo Vệ Mùa Màng Cùng <span className="highlight">RiceAI</span></h1>
          <p>Tải ảnh chụp lá lúa lên để AI chẩn đoán bệnh tức thì. Khoanh vùng chính xác, độ tin cậy cao, giải pháp tức thời.</p>
          <div className="hero-features">
            <span>⚡ Tốc độ &lt; 1s</span>
            <span>🎯 Chính xác 95%</span>
            <span>🤖 Trợ lý AI 24/7</span>
          </div>
        </div>
      </section>

      <div className="glass-panel main-panel">
        {!previewUrl ? (
          <>
            <div className="upload-section">
              <div 
                className={`drop-zone ${isDragging ? 'active' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current.click()}
              >
                <UploadIcon />
                <div className="upload-text">Nhấp để chọn ảnh hoặc kéo thả vào đây</div>
                <div className="upload-hint">Định dạng hỗ trợ: JPG, PNG, WEBP</div>
                <input type="file" ref={fileInputRef} onChange={handleFileSelect} accept="image/*" style={{ display: 'none' }} />
              </div>
            </div>

          </>
        ) : (
          <div className="preview-section">
            <div className="image-preview-wrapper" style={{ position: 'relative', display: 'inline-block' }}>
              <img src={previewUrl} alt="Preview" className="image-preview" />
              {/* Heatmap Overlay (Grad-CAM) */}
              {result && result.heatmap_url && (
                <div 
                  className="heatmap-overlay"
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    pointerEvents: 'none',
                    animation: 'fadeIn 1s ease-in-out'
                  }}
                >
                  <img src={result.heatmap_url} alt="Heatmap" style={{width: '100%', height: '100%', objectFit: 'contain', opacity: 0.85}} />
                  <span style={{
                    position: 'absolute',
                    top: '10px',
                    left: '10px',
                    backgroundColor: '#ef4444',
                    color: '#fff',
                    padding: '4px 10px',
                    fontSize: '14px',
                    fontWeight: 'bold',
                    borderRadius: '4px',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                  }}>
                    {DISEASE_NAMES[result.prediction] || result.prediction}
                  </span>
                </div>
              )}
            </div>
            
            {!result && !error && (
              <div className="analyze-actions-container">
                <div className="severity-selector" style={{margin: '20px 0', textAlign: 'left', padding: '15px', background: 'var(--bg-card)', borderRadius: '8px', border: '1px solid var(--border-color)'}}>
                  <label style={{display: 'block', fontWeight: 'bold', marginBottom: '10px', color: 'var(--text-main)'}}>Mức độ lây lan / Mật độ dịch hại (Ước lượng):</label>
                  <div style={{display: 'flex', gap: '15px', color: 'var(--text-muted)'}}>
                    <label style={{display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer'}}>
                      <input type="radio" name="severity" value="low" checked={severity === 'low'} onChange={(e) => setSeverity(e.target.value)} /> Ít / Thấp
                    </label>
                    <label style={{display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer'}}>
                      <input type="radio" name="severity" value="medium" checked={severity === 'medium'} onChange={(e) => setSeverity(e.target.value)} /> Trung bình
                    </label>
                    <label style={{display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer'}}>
                      <input type="radio" name="severity" value="high" checked={severity === 'high'} onChange={(e) => setSeverity(e.target.value)} /> Cao / Nghiêm trọng
                    </label>
                  </div>
                </div>

                <div className="analyze-actions">
                  <button className="btn-secondary" onClick={() => processFile(null)} disabled={isAnalyzing}>
                    Chọn ảnh khác
                  </button>
                  <button className="btn-primary" onClick={analyzeImage} disabled={isAnalyzing}>
                    {isAnalyzing ? <><div className="loader"></div> Đang phân tích...</> : <><ScanIcon /> Phân tích ngay</>}
                  </button>
                </div>
              </div>
            )}

            {error && (
              <div style={{color: '#ef4444', marginTop: '10px', textAlign: 'center'}}>
                ⚠️ {error} <br/>
                <button className="btn-secondary" onClick={() => processFile(null)} style={{marginTop: '16px'}}>Quay lại</button>
              </div>
            )}

            {result && (
              <div className="detailed-result-card">
                <div className="result-header">
                  <h3>Phiếu Chẩn Đoán</h3>
                  <div className={`result-disease ${result.prediction === 'normal' ? 'healthy' : ''}`}>
                    {DISEASE_NAMES[result.prediction] || result.prediction}
                  </div>
                </div>
                
                <div className="confidence-container">
                  <div className="confidence-text">Độ tin cậy của AI: {(result.confidence * 100).toFixed(1)}%</div>
                  <div className="confidence-bar">
                    <div className="confidence-fill" style={{ width: `${(result.confidence * 100)}%` }}></div>
                  </div>
                </div>

                {result.ipm_advice ? (
                  <div className="disease-widgets">
                    <div className="widget severity-widget" style={{ gridColumn: '1 / -1', background: result.ipm_advice.threshold_reached ? '#fef2f2' : '#f0fdf4' }}>
                      <span className="widget-icon">{result.ipm_advice.threshold_reached ? '⚠️' : '✅'}</span>
                      <div className="widget-content">
                        <strong style={{color: result.ipm_advice.threshold_reached ? '#b91c1c' : '#15803d'}}>Tư vấn chuẩn IPHM:</strong>
                        <p style={{marginTop: '5px', color: '#334155'}}>{result.ipm_advice.recommendation}</p>
                      </div>
                    </div>
                    
                    {result.ipm_advice.organic_methods && result.ipm_advice.organic_methods.length > 0 && (
                      <div className="widget action-widget" style={{ gridColumn: '1 / -1', borderLeft: '4px solid #22c55e' }}>
                        <span className="widget-icon">🌱</span>
                        <div className="widget-content">
                          <strong>Biện pháp Sinh học / Hữu cơ / Canh tác:</strong>
                          <ul style={{ margin: '5px 0 0 0', paddingLeft: '20px', color: '#334155', fontSize: '0.9rem', lineHeight: '1.5' }}>
                            {result.ipm_advice.organic_methods.map((t, idx) => (
                              <li key={idx}>{t}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}

                    {result.ipm_advice.chemical_methods && result.ipm_advice.chemical_methods.length > 0 && (
                      <div className="widget action-widget" style={{ gridColumn: '1 / -1', borderLeft: '4px solid #ef4444' }}>
                        <span className="widget-icon">🧪</span>
                        <div className="widget-content">
                          <strong>Biện pháp Hóa học (Sử dụng đúng Ngưỡng):</strong>
                          <ul style={{ margin: '5px 0 0 0', paddingLeft: '20px', color: '#334155', fontSize: '0.9rem', lineHeight: '1.5' }}>
                            {result.ipm_advice.chemical_methods.map((t, idx) => (
                              <li key={idx}>{t}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  diseaseInfo && (
                    <div className="disease-widgets">
                      <div className="widget severity-widget">
                        <span className="widget-icon">🚨</span>
                        <div className="widget-content">
                          <strong>Mức độ:</strong>
                          <span className={`badge ${diseaseInfo.severity}`}>
                            {diseaseInfo.severity === 'high' ? 'Nghiêm trọng' : diseaseInfo.severity === 'medium' ? 'Trung bình' : 'Thấp'}
                          </span>
                        </div>
                      </div>
                      
                      <div className="widget action-widget" style={{ gridColumn: '1 / -1' }}>
                        <span className="widget-icon">💡</span>
                        <div className="widget-content">
                          <strong>Lời khuyên điều trị:</strong>
                          <ul style={{ margin: '5px 0 0 0', paddingLeft: '20px', color: '#334155', fontSize: '0.9rem', lineHeight: '1.5' }}>
                            {diseaseInfo.treatment.map((t, idx) => (
                              <li key={idx}>{t}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )
                )}

                <div className="result-actions">
                  <button className="btn-secondary" onClick={() => processFile(null)}>
                    Phân tích ảnh mới
                  </button>
                  {diseaseInfo && (
                    <button className="btn-chat-ai" onClick={() => {
                      // Kích hoạt Chatbot bằng Event (hoặc quản lý state global)
                      window.dispatchEvent(new CustomEvent('open-chat', { 
                        detail: `Tôi vừa quét ra ${diseaseInfo.name}. Hãy lập cho tôi phác đồ điều trị chi tiết nhất.` 
                      }));
                    }}>
                      💬 Hỏi AI Chi Tiết
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Home;

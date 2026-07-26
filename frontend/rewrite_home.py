import os

content = """import React, { useState, useRef } from 'react';
import axios from 'axios';
import { DISEASES } from './DiseaseLibrary';

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
  "leaf_smut": "Bệnh Than Đen (Leaf Smut)"
};

function Home() {
  const [selectedImage, setSelectedImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  
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

            <div className="how-it-works">
              <h3>Cách hoạt động</h3>
              <div className="steps-container">
                <div className="step">
                  <div className="step-number">1</div>
                  <h4>Chụp Ảnh</h4>
                  <p>Chụp rõ nét phần lá lúa có dấu hiệu bị bệnh</p>
                </div>
                <div className="step">
                  <div className="step-number">2</div>
                  <h4>Tải Lên</h4>
                  <p>Đưa ảnh vào hệ thống RiceAI</p>
                </div>
                <div className="step">
                  <div className="step-number">3</div>
                  <h4>Nhận Kết Quả</h4>
                  <p>AI khoanh vùng và đưa ra phác đồ điều trị</p>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="preview-section">
            <div className="image-preview-wrapper" style={{ position: 'relative', display: 'inline-block' }}>
              <img src={previewUrl} alt="Preview" className="image-preview" />
              {/* Bounding Box Overlay */}
              {result && result.bbox && (
                <div 
                  className="bounding-box"
                  style={{
                    position: 'absolute',
                    left: `${result.bbox.x * 100}%`,
                    top: `${result.bbox.y * 100}%`,
                    width: `${result.bbox.w * 100}%`,
                    height: `${result.bbox.h * 100}%`,
                    border: '3px solid #ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    boxShadow: '0 0 10px rgba(239, 68, 68, 0.5)',
                    borderRadius: '4px',
                    pointerEvents: 'none',
                    animation: 'pulse 2s infinite'
                  }}
                >
                  <span style={{
                    position: 'absolute',
                    top: '-25px',
                    left: '-3px',
                    backgroundColor: '#ef4444',
                    color: '#fff',
                    padding: '2px 8px',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    borderRadius: '4px 4px 4px 0',
                    whiteSpace: 'nowrap'
                  }}>
                    {DISEASE_NAMES[result.prediction]}
                  </span>
                </div>
              )}
            </div>
            
            {!result && !error && (
              <div className="analyze-actions">
                <button className="btn-secondary" onClick={() => processFile(null)} disabled={isAnalyzing}>
                  Chọn ảnh khác
                </button>
                <button className="btn-primary" onClick={analyzeImage} disabled={isAnalyzing}>
                  {isAnalyzing ? <><div className="loader"></div> Đang phân tích...</> : <><ScanIcon /> Phân tích ngay</>}
                </button>
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

                {diseaseInfo && (
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
                    
                    <div className="widget action-widget">
                      <span className="widget-icon">💊</span>
                      <div className="widget-content">
                        <strong>Xử lý nhanh:</strong>
                        <p>{diseaseInfo.treatment[0]}</p>
                      </div>
                    </div>
                  </div>
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
"""

with open(r"D:\Phát hiện bệnh cây lúa\frontend\src\pages\Home.jsx", "w", encoding="utf-8") as f:
    f.write(content)

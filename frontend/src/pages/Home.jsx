import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { DISEASES } from '../data/diseases';
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
  const [plan, setPlan] = useState(null);
  
  const fileInputRef = useRef(null);
  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;
    axios.get('/api/plans/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(({ data }) => setPlan(data)).catch(() => {});
  }, []);

  const isSupportedImage = (file) => {
    if (!file) return false;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setError('Chọn ảnh JPG, PNG hoặc WEBP.');
      return false;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('Ảnh vượt quá giới hạn 10 MB.');
      return false;
    }
    return true;
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (isSupportedImage(file)) {
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
    if (isSupportedImage(file)) {
      processFile(file);
    }
  };

  const analyzeImage = async () => {
    if (!selectedImage) return;
    const token = localStorage.getItem('token');
    if (!token) {
      setError('Vui lòng đăng nhập bằng email đã xác minh để phân tích ảnh.');
      return;
    }
    setIsAnalyzing(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', selectedImage);
    formData.append('severity', severity);
    
    try {
      const response = await axios.post('/api/predict', formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'X-RiceAI-Client': 'web',
          'X-RiceAI-Version': 'web',
        }
      });
      setResult(response.data);
      if (response.data.plan) setPlan(response.data.plan);
    } catch (err) {
      if (err.response && [401, 403].includes(err.response.status)) {
        setError('Phiên đăng nhập đã hết hạn hoặc không có quyền. Vui lòng đăng nhập lại.');
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
      <section className="hero-section">
        <div className="hero-content">
          <span className="hero-eyebrow">RICEAI BASIC · CHẨN ĐOÁN TỪ ẢNH</span>
          <h1>Hiểu rõ cây lúa.<br /><span>Chăm đúng lúc.</span></h1>
          <p>Chọn một ảnh cây lúa để xem kết quả nhận diện, vùng ảnh mô hình chú ý và gợi ý xử lý trong cùng một nơi.</p>
          <div className="hero-features">
            <span><b>01</b> Tải ảnh</span>
            <span><b>02</b> Nhận diện</span>
            <span><b>03</b> Xem gợi ý</span>
          </div>
        </div>
        <div className="hero-visual" aria-hidden="true"><div className="hero-orbit"><img src="/riceai-logo.png" alt="" /></div></div>
      </section>

      <div className="glass-panel main-panel">
        <div className="panel-heading"><div><span className="section-kicker">BƯỚC ĐẦU TIÊN</span><h2>Phân tích ảnh cây lúa</h2><p>Ảnh rõ nét, đủ sáng sẽ giúp mô hình đọc được đặc điểm tốt hơn.</p></div><span className="panel-format">JPG · PNG · WEBP</span></div>
        {plan && <p className="basic-plan-status" role="status">{plan.unlimited ? 'Tài khoản nhân viên · không giới hạn lượt' : `${plan.plan === 'plus' ? 'Plus' : 'Basic'} · Còn ${plan.remaining} / ${plan.limits[plan.plan]} lượt trong tháng ${plan.period}`}{!plan.unlimited && plan.remaining === 0 && <> · <Link to="/plans">Xem gói sử dụng</Link></>}</p>}
        {!previewUrl ? (
          <>
            <div className="upload-section">
              <div 
                className={`drop-zone ${isDragging ? 'active' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); fileInputRef.current?.click(); } }}
                role="button"
                tabIndex={0}
                aria-label="Chọn ảnh JPG, PNG hoặc WEBP để phân tích"
              >
                <UploadIcon />
                <div className="upload-copy"><div className="upload-text">Kéo ảnh vào đây hoặc nhấp để chọn</div><div className="upload-hint">Tối đa 10 MB · Chụp gần lá, thân hoặc bông lúa cần kiểm tra</div></div>
                <input type="file" ref={fileInputRef} onChange={handleFileSelect} accept="image/jpeg,image/png,image/webp" style={{ display: 'none' }} />
              </div>
              {error && <div className="auth-error" role="alert" style={{ marginTop: '12px' }}>{error}</div>}
            </div>

          </>
        ) : (
          <div className="preview-section">
            <div className="image-preview-wrapper">
              <img src={previewUrl} alt="Ảnh cây lúa đã chọn" className="image-preview" />
              {/* Heatmap Overlay (Grad-CAM) */}
              {result && result.heatmap_url && (
                <div className="heatmap-overlay">
                  <img src={result.heatmap_url} alt="Heatmap" style={{width: '100%', height: '100%', objectFit: 'contain', opacity: 0.85}} />
                  <span className="heatmap-label">
                    {DISEASE_NAMES[result.prediction] || result.prediction}
                  </span>
                </div>
              )}
            </div>
            
            {!result && !error && (
              <div className="analyze-actions-container">
                <div className="severity-selector">
                  <p>Mức độ bạn tự quan sát trên ruộng <small>(dùng để gợi ý xử lý)</small></p>
                  <div className="severity-options">
                    <label>
                      <input type="radio" name="severity" value="low" checked={severity === 'low'} onChange={(e) => setSeverity(e.target.value)} /> Ít / Thấp
                    </label>
                    <label>
                      <input type="radio" name="severity" value="medium" checked={severity === 'medium'} onChange={(e) => setSeverity(e.target.value)} /> Trung bình
                    </label>
                    <label>
                      <input type="radio" name="severity" value="high" checked={severity === 'high'} onChange={(e) => setSeverity(e.target.value)} /> Cao / Nghiêm trọng
                    </label>
                  </div>
                </div>

                <div className="analyze-actions">
                  <button className="btn-secondary" onClick={() => processFile(null)} disabled={isAnalyzing}>
                    Chọn ảnh khác
                  </button>
                  <button className="btn-primary" onClick={analyzeImage} disabled={isAnalyzing || (!plan?.unlimited && plan?.remaining === 0)}>
                    {isAnalyzing ? <><div className="loader"></div> Đang phân tích...</> : <><ScanIcon /> Phân tích ngay</>}
                  </button>
                </div>
              </div>
            )}

            {error && (
                <div className="analysis-error" role="alert">
                {error}<br/>
                <button className="btn-secondary" onClick={() => processFile(null)}>Chọn ảnh khác</button>
              </div>
            )}

            {result && (
              <div className="detailed-result-card">
                <div className="result-header">
                  <h3>Kết quả chẩn đoán</h3>
                  <div className={`result-disease ${result.prediction === 'normal' ? 'healthy' : ''}`}>
                    {result.uncertain ? 'Chưa xác định' : DISEASE_NAMES[result.prediction] || result.prediction}
                  </div>
                </div>

                
                <div className="confidence-container">
                  <div className="confidence-text">Mức tự tin của mô hình: {(result.confidence * 100).toFixed(1)}%</div>
                  <div className="confidence-bar">
                    <div className="confidence-fill" style={{ width: `${(result.confidence * 100)}%` }}></div>
                  </div>
                </div>
                {result.uncertain && <div className="analysis-error" role="status">{result.message}</div>}
                {result.scope_warning && <p className="result-scope-warning">{result.scope_warning}</p>}

                {result.ipm_advice ? (
                  <div className="disease-widgets">
                    <div className="widget severity-widget" style={{ gridColumn: '1 / -1', background: result.ipm_advice.threshold_reached ? '#fef2f2' : '#f0fdf4' }}>
                      <span className="widget-icon">{result.ipm_advice.threshold_reached ? '⚠️' : '✅'}</span>
                      <div className="widget-content">
                          <strong style={{color: result.ipm_advice.threshold_reached ? '#b91c1c' : '#15803d'}}>Khuyến nghị IPM:</strong>
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
      <div className="home-footnote"><span className="footnote-mark">i</span><p>RiceAI đưa ra gợi ý tham khảo từ ảnh. Hãy kiểm tra thực tế trên ruộng trước khi quyết định biện pháp xử lý.</p></div>
    </div>
  );
}

export default Home;

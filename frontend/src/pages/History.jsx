import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { DISEASES } from '../data/diseases';
import { clearSession } from '../auth/session';
import './History.css';

const DISEASE_NAMES = {
  "bacterial_leaf_blight": "Cháy lá vi khuẩn",
  "bacterial_leaf_streak": "Sọc lá vi khuẩn",
  "bacterial_panicle_blight": "Cháy gié vi khuẩn",
  "blast": "Bệnh Đạo ôn",
  "brown_spot": "Bệnh Đốm nâu",
  "dead_heart": "Bệnh đục thân",
  "downy_mildew": "Bệnh Sương mai",
  "hispa": "Bọ gai (Hispa)",
  "normal": "Cây khỏe mạnh",
  "tungro": "Bệnh Tungro",
  "leaf_smut": "Bệnh Than Đen",
  "weeds": "Cỏ dại",
  "golden_apple_snail": "Ốc bươu vàng",
  "stem_borer": "Sâu đục thân",
  "leaf_roller": "Sâu cuốn lá nhỏ",
  "brown_planthopper": "Rầy nâu",
  "whitebacked_planthopper": "Rầy phấn trắng",
  "southern_black_streaked_dwarf": "Bệnh Lùn sọc đen"
};

function History() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [exportError, setExportError] = useState('');
  const navigate = useNavigate();
  
  // Hidden container reference for PDF generation
  const printRef = useRef();
  const [printData, setPrintData] = useState(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    const fetchHistory = async () => {
      const token = localStorage.getItem('token');
      if (!token) { navigate('/login'); return; }
      try {
        const res = await axios.get('/api/history', {
          headers: { Authorization: `Bearer ${token}` }
        });
        setHistory(res.data);
      } catch (err) {
        if (err.response?.status === 401) {
          clearSession();
          navigate('/login');
        } else {
          setError('Không tải được lịch sử. Kiểm tra kết nối máy chủ rồi thử lại.');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [navigate]);

  const handleExportPDF = (item) => {
    if (exporting) return;
    setExportError('');
    const diseaseInfo = DISEASES.find(d => d.id === item.prediction);
    setExporting(true);
    setPrintData({ item, diseaseInfo });
  };

  useEffect(() => {
    if (!printData || !printRef.current) return;
    let cancelled = false;
    const element = printRef.current;
    const exportPDF = async () => {
      try {
        await Promise.all(Array.from(element.querySelectorAll('img')).map((img) => {
          if (img.complete) return Promise.resolve();
          return new Promise((resolve) => {
            img.addEventListener('load', resolve, { once: true });
            img.addEventListener('error', resolve, { once: true });
            setTimeout(resolve, 10000);
          });
        }));
        await document.fonts.ready;
        if (cancelled) return;
        const { default: html2pdf } = await import('html2pdf.js');
        if (cancelled) return;
        await html2pdf().set({
          margin: [10, 10, 10, 10],
          filename: `Phieu_Chan_Doan_${printData.item.id}.pdf`,
          image: { type: 'jpeg', quality: 1.0 },
          html2canvas: { scale: 2, useCORS: true },
          jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        }).from(element).save();
      } catch {
        if (!cancelled) setExportError('Không xuất được PDF. Vui lòng thử lại.');
      } finally {
        if (!cancelled) {
          setPrintData(null);
          setExporting(false);
        }
      }
    };
    exportPDF();
    return () => { cancelled = true; };
  }, [printData]);

  return (
    <div className="history-page glass-panel">
      <h2>Lịch Sử Chẩn Đoán</h2>
      <p className="history-subtitle">Các lần phân tích ảnh lá lúa trước đó của bạn</p>
      {exportError && <div className="auth-error" role="alert">{exportError}</div>}
      
      {/* Thống kê nhanh */}
      {!loading && history.length > 0 && (
        <div className="history-stats">
          <div className="stat-card">
            <h4>Tổng số lần quét</h4>
            <div className="stat-value">{history.length}</div>
          </div>
          <div className="stat-card">
            <h4>Phát hiện bệnh</h4>
            <div className="stat-value disease-val">
              {history.filter(h => h.prediction !== 'normal' && h.prediction !== 'uncertain').length}
            </div>
          </div>
          <div className="stat-card">
            <h4>Khỏe mạnh</h4>
            <div className="stat-value healthy-val">
              {history.filter(h => h.prediction === 'normal').length}
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px' }}><div className="loader" style={{ display: 'inline-block' }}></div></div>
      ) : error ? (
        <div className="auth-error" role="alert">{error}</div>
      ) : history.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <p>Bạn chưa thực hiện phân tích nào.</p>
          <p style={{ marginTop: '8px', fontSize: '0.85rem' }}>Hãy tải ảnh lá lúa lên trang Chẩn đoán để bắt đầu!</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="history-table">
            <thead>
              <tr>
                <th>Thời gian</th>
                <th>Tên ảnh</th>
                <th>Kết quả</th>
                <th>Độ tin cậy</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr key={item.id}>
                  <td style={{ color: 'var(--text-dim)' }}>
                    {new Date(item.created_at).toLocaleString('vi-VN')}
                  </td>
                  <td>{item.image_filename}</td>
                  <td>
                    <span className={`badge ${item.prediction === 'normal' ? 'badge-healthy' : 'badge-disease'}`}>
                      {item.prediction === 'uncertain' ? 'Chưa xác định' : (DISEASE_NAMES[item.prediction] || item.prediction)}
                    </span>
                  </td>
                  <td>{(item.confidence * 100).toFixed(1)}%</td>
                  <td>
                    <button 
                      className="btn-export" 
                      onClick={() => handleExportPDF(item)}
                      title="Xuất báo cáo PDF"
                      disabled={exporting}
                    >
                      {exporting ? 'Đang xuất...' : '📄 Xuất PDF'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Giao diện ẩn (chỉ dùng để in PDF) */}
      {printData && (
        <div style={{ position: 'absolute', left: '-10000px', top: 0, width: '800px' }}>
          <div ref={printRef} className="pdf-print-container" style={{ padding: '30px', color: '#000', background: '#fff', fontFamily: 'Arial, sans-serif' }}>
            {/* Header chuyên nghiệp */}
            <div style={{ borderBottom: '3px solid #245a3d', paddingBottom: '15px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <img src="/riceai-logo.png" alt="RiceAI" style={{ width: '60px', height: '60px', objectFit: 'contain' }} />
                <div>
                  <h1 style={{ color: '#183d2b', margin: '0 0 5px 0', fontSize: '28px' }}>RICEAI BASIC</h1>
                  <h3 style={{ margin: 0, color: '#475569', fontSize: '16px', fontWeight: 'normal' }}>Báo cáo kết quả AI tham khảo</h3>
                </div>
              </div>
              <div style={{ textAlign: 'right', fontSize: '13px', color: '#64748b' }}>
                <p style={{ margin: '0 0 5px 0' }}><strong>Mã phiếu:</strong> #{printData.item.id.toString().padStart(6, '0')}</p>
                <p style={{ margin: '0 0 5px 0' }}><strong>Ngày tạo:</strong> {new Date(printData.item.created_at).toLocaleString('vi-VN')}</p>
                <p style={{ margin: 0 }}><strong>Nguồn:</strong> Lịch sử tài khoản RiceAI</p>
              </div>
            </div>

            <h2 style={{ textAlign: 'center', color: '#1e293b', marginBottom: '25px', fontSize: '24px', textTransform: 'uppercase', letterSpacing: '1px' }}>
              Phiếu Kết Quả Phân Tích Bằng AI
            </h2>

            {/* Phần thông tin chẩn đoán */}
            <div style={{ display: 'flex', gap: '20px', marginBottom: '25px' }}>
              {/* Ảnh gốc của lần phân tích */}
              <div style={{ flex: '0 0 40%', position: 'relative' }}>
                <h4 style={{ margin: '0 0 10px 0', color: '#334155', borderBottom: '1px solid #e2e8f0', paddingBottom: '5px' }}>Ảnh Mẫu Vật</h4>
                <div style={{ border: '1px solid #cbd5e1', borderRadius: '8px', padding: '5px', backgroundColor: '#f8fafc' }}>
                  <img 
                    src={`/uploads/${printData.item.image_filename}`} 
                    alt="Rice Leaf" 
                    style={{ width: '100%', height: '200px', objectFit: 'contain', borderRadius: '4px' }}
                    crossOrigin="anonymous"
                  />
                </div>
                <p style={{ fontSize: '11px', color: '#64748b', textAlign: 'center', marginTop: '5px' }}>Ảnh đã gửi để mô hình phân loại. PDF này không thể hiện vị trí tổn thương.</p>
              </div>

              {/* Chi tiết kết quả */}
              <div style={{ flex: '1', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                <div style={{ padding: '15px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#334155' }}>KẾT QUẢ AI PHÂN TÍCH</h4>
                  <p style={{ fontSize: '18px', margin: '0 0 10px 0' }}>
                    Tên bệnh: <strong style={{ color: printData.item.prediction === 'normal' ? '#10b981' : '#ef4444', fontSize: '20px' }}>
                      {printData.item.prediction === 'uncertain' ? 'Chưa xác định' : DISEASE_NAMES[printData.item.prediction]}
                    </strong>
                  </p>
                  <p style={{ fontSize: '15px', margin: '0 0 10px 0' }}>
                    Độ tin cậy: <strong>{(printData.item.confidence * 100).toFixed(1)}%</strong>
                  </p>
                  {/* Biểu đồ thanh ngang */}
                  <div style={{ width: '100%', height: '8px', backgroundColor: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ 
                      width: `${printData.item.confidence * 100}%`, 
                      height: '100%', 
                      backgroundColor: printData.item.prediction === 'normal' ? '#10b981' : '#ef4444' 
                    }}></div>
                  </div>
                </div>
                
                {printData.diseaseInfo && printData.item.prediction !== 'normal' && (
                  <div style={{ padding: '15px', background: '#fff1f2', borderRadius: '8px', border: '1px solid #ffe4e6', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{ fontSize: '24px' }}>🚨</div>
                    <div>
                      <h4 style={{ margin: '0 0 5px 0', color: '#be123c' }}>LƯU Ý</h4>
                      <p style={{ margin: 0, color: '#9f1239', fontSize: '15px' }}>Mức độ bệnh thực tế cần được kiểm tra tại ruộng; mô hình chỉ phân loại nhóm ảnh.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Phác đồ chi tiết */}
            {printData.diseaseInfo && printData.item.prediction !== 'normal' && (
              <>
                <div style={{ marginBottom: '20px' }}>
                  <h3 style={{ color: '#0f172a', borderBottom: '2px solid #e2e8f0', paddingBottom: '8px', margin: '0 0 10px 0', fontSize: '18px' }}>
                    1. Tác nhân & Triệu chứng
                  </h3>
                  <div style={{ background: '#f1f5f9', padding: '12px', borderRadius: '6px' }}>
                    <p style={{ margin: '0 0 8px 0', color: '#334155', lineHeight: '1.5' }}><strong>Nguyên nhân:</strong> {printData.diseaseInfo.cause}</p>
                    <p style={{ margin: 0, color: '#334155', lineHeight: '1.5' }}><strong>Triệu chứng:</strong> {printData.diseaseInfo.symptoms}</p>
                  </div>
                </div>

                <div style={{ marginBottom: '20px' }}>
                  <h3 style={{ color: '#0f172a', borderBottom: '2px solid #e2e8f0', paddingBottom: '8px', margin: '0 0 10px 0', fontSize: '18px' }}>
                    2. Thông tin xử lý tham khảo
                  </h3>
                  <div style={{ padding: '0 12px' }}>
                    <ul style={{ paddingLeft: '20px', color: '#334155', lineHeight: '1.6', margin: 0 }}>
                      {printData.diseaseInfo.treatment.map((t, idx) => (
                        <li key={idx} style={{ marginBottom: '6px' }}>{t}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </>
            )}

            <div style={{ marginTop: '32px', borderTop: '2px solid #e2e8f0', paddingTop: '14px', color: '#64748b', fontSize: '12px' }}>
              Phiếu tham khảo được xuất từ lịch sử RiceAI. Kết quả AI cần đối chiếu với quan sát thực tế trước khi áp dụng biện pháp xử lý.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default History;

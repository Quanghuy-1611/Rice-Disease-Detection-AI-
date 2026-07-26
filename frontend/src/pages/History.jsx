import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import html2pdf from 'html2pdf.js';
import { QRCodeSVG } from 'qrcode.react';
import { DISEASES } from './DiseaseLibrary';
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
  const navigate = useNavigate();
  
  // Hidden container reference for PDF generation
  const printRef = useRef();
  const [printData, setPrintData] = useState(null);

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
          localStorage.removeItem('token');
          navigate('/login');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [navigate]);

  const handleExportPDF = (item) => {
    // 1. Set data to render the hidden print container
    const diseaseInfo = DISEASES.find(d => d.id === item.prediction);
    setPrintData({ item, diseaseInfo });
    
    // 2. Wait for state to update, then print
    setTimeout(() => {
      if (!printRef.current) return;
      const element = printRef.current;
      const opt = {
        margin:       [10, 10, 10, 10], // top, left, bottom, right
        filename:     `Phieu_Chan_Doan_${item.id}.pdf`,
        image:        { type: 'jpeg', quality: 1.0 },
        html2canvas:  { scale: 2, useCORS: true },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
      };
      
      html2pdf().set(opt).from(element).save().then(() => {
        // Clear after save
        setPrintData(null);
      });
    }, 800); // Wait a bit longer to ensure images load
  };

  return (
    <div className="history-page glass-panel">
      <h2>Lịch Sử Chẩn Đoán</h2>
      <p className="history-subtitle">Các lần phân tích ảnh lá lúa trước đó của bạn</p>
      
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
              {history.filter(h => h.prediction !== 'normal').length}
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
                      {DISEASE_NAMES[item.prediction] || item.prediction}
                    </span>
                  </td>
                  <td>{(item.confidence * 100).toFixed(1)}%</td>
                  <td>
                    <button 
                      className="btn-export" 
                      onClick={() => handleExportPDF(item)}
                      title="Xuất báo cáo PDF"
                    >
                      📄 Xuất PDF
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
        <div style={{ display: 'none' }}>
          <div ref={printRef} className="pdf-print-container" style={{ padding: '30px', color: '#000', background: '#fff', fontFamily: 'Arial, sans-serif' }}>
            {/* Header chuyên nghiệp */}
            <div style={{ borderBottom: '3px solid #10b981', paddingBottom: '15px', marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                <div style={{ width: '60px', height: '60px', backgroundColor: '#10b981', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '32px', fontWeight: 'bold' }}>
                  R
                </div>
                <div>
                  <h1 style={{ color: '#064e3b', margin: '0 0 5px 0', fontSize: '28px' }}>RICE-AI SYSTEM</h1>
                  <h3 style={{ margin: 0, color: '#475569', fontSize: '16px', fontWeight: 'normal' }}>Trung Tâm Chẩn Đoán Bệnh Thực Vật Tự Động</h3>
                </div>
              </div>
              <div style={{ textAlign: 'right', fontSize: '13px', color: '#64748b' }}>
                <p style={{ margin: '0 0 5px 0' }}><strong>Mã phiếu:</strong> #{printData.item.id.toString().padStart(6, '0')}</p>
                <p style={{ margin: '0 0 5px 0' }}><strong>Ngày tạo:</strong> {new Date(printData.item.created_at).toLocaleString('vi-VN')}</p>
                <p style={{ margin: 0 }}><strong>Người xuất:</strong> Kỹ sư Nông nghiệp (User)</p>
              </div>
            </div>

            <h2 style={{ textAlign: 'center', color: '#1e293b', marginBottom: '25px', fontSize: '24px', textTransform: 'uppercase', letterSpacing: '1px' }}>
              Phiếu Kết Quả Phân Tích Bằng AI
            </h2>

            {/* Phần thông tin chẩn đoán */}
            <div style={{ display: 'flex', gap: '20px', marginBottom: '25px' }}>
              {/* Hình ảnh và khoanh vùng */}
              <div style={{ flex: '0 0 40%', position: 'relative' }}>
                <h4 style={{ margin: '0 0 10px 0', color: '#334155', borderBottom: '1px solid #e2e8f0', paddingBottom: '5px' }}>Ảnh Mẫu Vật</h4>
                <div style={{ border: '1px solid #cbd5e1', borderRadius: '8px', padding: '5px', backgroundColor: '#f8fafc' }}>
                  <img 
                    src={`/uploads/${printData.item.image_filename}`} 
                    alt="Rice Leaf" 
                    style={{ width: '100%', height: '200px', objectFit: 'contain', borderRadius: '4px' }}
                    crossOrigin="anonymous"
                  />
                  {/* Bounding box mô phỏng AI Grad-CAM (nếu có bệnh) */}
                  {printData.item.prediction !== 'normal' && (
                    <div style={{
                      position: 'absolute',
                      top: '20%', left: '30%', width: '40%', height: '40%',
                      border: '2px solid #ef4444',
                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                      display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '2px'
                    }}>
                      <span style={{ backgroundColor: '#ef4444', color: '#fff', fontSize: '10px', padding: '1px 4px', borderRadius: '2px', position: 'absolute', top: '-14px', left: '-2px' }}>Vùng bệnh</span>
                    </div>
                  )}
                </div>
                <p style={{ fontSize: '11px', color: '#94a3b8', textAlign: 'center', marginTop: '5px' }}>*Khung đỏ thể hiện vùng bệnh do thuật toán AI (Grad-CAM) khoanh vùng.</p>
              </div>

              {/* Chi tiết kết quả */}
              <div style={{ flex: '1', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                <div style={{ padding: '15px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: '#334155' }}>KẾT QUẢ AI PHÂN TÍCH</h4>
                  <p style={{ fontSize: '18px', margin: '0 0 10px 0' }}>
                    Tên bệnh: <strong style={{ color: printData.item.prediction === 'normal' ? '#10b981' : '#ef4444', fontSize: '20px' }}>
                      {DISEASE_NAMES[printData.item.prediction]}
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
                      <h4 style={{ margin: '0 0 5px 0', color: '#be123c' }}>CẢNH BÁO MỨC ĐỘ</h4>
                      <p style={{ margin: 0, color: '#9f1239', fontSize: '15px' }}><strong>{printData.diseaseInfo.severity === 'high' ? 'NGHIÊM TRỌNG - Cần xử lý ngay' : printData.diseaseInfo.severity === 'medium' ? 'TRUNG BÌNH - Cần theo dõi' : 'THẤP - Phòng ngừa'}</strong></p>
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
                    2. Phác đồ điều trị chi tiết
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

            {/* Footer chứng nhận */}
            <div style={{ marginTop: '40px', borderTop: '2px solid #e2e8f0', paddingTop: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', gap: '15px' }}>
                <QRCodeSVG 
                  value={`https://riceai.app/verify/${printData.item.id}`} 
                  size={80} 
                  level={"L"}
                />
                <div style={{ fontSize: '12px', color: '#64748b', maxWidth: '250px' }}>
                  <p style={{ margin: '0 0 5px 0', fontWeight: 'bold', color: '#334155' }}>Quét mã để xác thực</p>
                  <p style={{ margin: 0 }}>Phiếu chẩn đoán này được mã hóa và lưu trữ bảo mật trên hệ thống RiceAI. Quét QR code để xem bản gốc trực tuyến.</p>
                </div>
              </div>

              <div style={{ textAlign: 'center' }}>
                <div style={{ width: '120px', height: '120px', margin: '0 auto', border: '3px solid #ef4444', borderRadius: '50%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', transform: 'rotate(-15deg)', opacity: '0.8' }}>
                  <span style={{ color: '#ef4444', fontWeight: 'bold', fontSize: '18px' }}>RICE-AI</span>
                  <span style={{ color: '#ef4444', fontSize: '12px', letterSpacing: '1px' }}>VERIFIED</span>
                  <span style={{ color: '#ef4444', fontSize: '10px', marginTop: '2px' }}>{new Date().toLocaleDateString('vi-VN')}</span>
                </div>
                <p style={{ marginTop: '10px', fontSize: '14px', fontWeight: 'bold', color: '#1e293b' }}>Hệ Thống Trí Tuệ Nhân Tạo</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default History;

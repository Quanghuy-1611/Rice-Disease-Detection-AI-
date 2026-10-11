import { useEffect, useState } from 'react';
import axios from 'axios';

function DiseaseLibrary() {
  const [diseases, setDiseases] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    axios.get('/api/disease-library')
      .then(({ data }) => setDiseases(data.data || []))
      .catch(() => setError('Không tải được cẩm nang. Hãy kiểm tra kết nối máy chủ.'));
  }, []);
  return (
    <div className="library-page">
      <header className="library-heading"><div><span className="section-kicker">Thư viện bệnh</span><h1>Cẩm nang cây lúa</h1><p>Chọn một mục để xem dấu hiệu, điều kiện phát sinh và cách phòng ngừa.</p></div></header>
      {error && <div className="auth-error" role="alert">{error}</div>}
      {!error && !diseases.length && <p style={{ textAlign: 'center' }}>Đang tải cẩm nang...</p>}
      <div className="disease-grid">
        {diseases.map((item, index) => <button type="button" key={item.slug} className="disease-card" onClick={() => setSelected(item)}>
          <div className="disease-card-header"><div className="disease-emoji" aria-hidden="true">{String(index + 1).padStart(2, '0')}</div><div>
            <div className="disease-card-title">{item.display_name_vi}</div>
            <div className="disease-card-subtitle">{item.display_name_en}</div>
          </div></div>
          <div className="disease-card-body"><p style={{ color: 'var(--text-main)' }}>{item.overview}</p></div>
        </button>)}
      </div>
      {selected && <div className="modal-overlay" onClick={() => setSelected(null)}>
        <div className="modal-content" onClick={(event) => event.stopPropagation()}>
          <button type="button" className="modal-close" onClick={() => setSelected(null)} aria-label="Đóng">×</button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
            <div className="disease-emoji" aria-hidden="true">{String(diseases.findIndex((item) => item.slug === selected.slug) + 1).padStart(2, '0')}</div>
            <div><h3 style={{ color: 'var(--primary-dark)', margin: 0 }}>{selected.display_name_vi}</h3><span>{selected.display_name_en}</span></div>
          </div>
          {[['Tổng quan', selected.overview], ['Dấu hiệu nhận biết', selected.symptoms],
            ['Điều kiện phát sinh', selected.favorable_conditions], ['Phòng ngừa', selected.prevention],
            ['Khuyến nghị IPM', selected.ipm_advice]].map(([title, body]) => <div className="modal-section" key={title}>
              <h4>{title}</h4><p style={{ color: 'var(--text-main)' }}>{body}</p>
            </div>)}
        </div>
      </div>}
    </div>
  );
}

export default DiseaseLibrary;

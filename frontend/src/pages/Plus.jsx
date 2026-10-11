import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './Plus.css';

const names = { bacterial_leaf_blight: 'Bạc lá vi khuẩn', brown_spot: 'Đốm nâu',
  golden_apple_snail: 'Ốc bươu vàng', leaf_roller: 'Sâu cuốn lá', normal: 'Lúa khỏe',
  tungro: 'Tungro', weeds: 'Cỏ dại' };

export default function Plus() {
  const [ready, setReady] = useState(null);
  const [plan, setPlan] = useState(null);
  const [planLoaded, setPlanLoaded] = useState(false);
  const [files, setFiles] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const token = localStorage.getItem('token');
  useEffect(() => {
    axios.get('/api/plans/catalog').then(({ data }) => setReady(data.plus_ready)).catch(() => setReady(false));
    if (token) axios.get('/api/plans/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(({ data }) => setPlan(data)).catch(() => setPlan(null)).finally(() => setPlanLoaded(true));
    else setPlanLoaded(true);
  }, [token]);

  const chooseFiles = (chosen) => {
    const picked = Array.from(chosen);
    if (!picked.length || picked.length > 5) { setError('Chọn từ 1 đến 5 ảnh.'); return; }
    if (picked.some((file) => !['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 10 * 1024 * 1024)) {
      setError('Mỗi ảnh phải là JPG, PNG hoặc WEBP và không quá 10 MB.'); return;
    }
    setError(''); setResult(null); setFiles(picked);
  };

  const analyze = async () => {
    const form = new FormData();
    files.forEach((file) => form.append('files', file));
    setBusy(true); setError('');
    try {
      const { data } = await axios.post('/api/predict/plus', form, { headers: {
        Authorization: `Bearer ${token}`, 'X-RiceAI-Client': 'web', 'X-RiceAI-Version': 'web',
      } });
      setResult(data); setPlan(data.plan);
    } catch (err) { setError(err.response?.data?.detail || 'Chưa phân tích được bộ ảnh.'); }
    finally { setBusy(false); }
  };

  if (ready === null || !planLoaded) return <main className="plus-page"><p>Đang tải RiceAI Plus...</p></main>;

  if (!ready) return <main className="plus-page"><span className="section-kicker">RICEAI PLUS</span>
    <h1>Plus đang được kiểm định</h1><p>Mô hình phân loại thứ hai và phần khoanh vùng tổn thương chưa đạt đủ điều kiện phát hành. RiceAI chưa mở đăng ký hoặc thanh toán Plus.</p>
    <Link to="/" className="plus-back">Tiếp tục với Basic</Link></main>;

  if (!token || plan?.plan !== 'plus') return <main className="plus-page"><h1>RiceAI Plus</h1>
    <p>Bạn cần tài khoản Plus để phân tích nhiều ảnh.</p><Link to="/plans" className="plus-back">Xem gói sử dụng</Link></main>;

  return <main className="plus-page"><span className="section-kicker">RICEAI PLUS</span>
    <h1>Phân tích nhiều ảnh cùng lúc</h1><p>Chọn tối đa 5 ảnh của cùng một vấn đề. Nếu ảnh khác bệnh hoặc mô hình không thống nhất, RiceAI sẽ không kết luận chung.</p>
    <div className="plus-quota" role="status">{plan.unlimited ? 'Nhân viên · không giới hạn lượt' : `Còn ${plan.remaining}/80 lượt tháng ${plan.period}`}
      {plan.halfway_notice && <strong> Đã dùng hơn nửa số lượt Plus.</strong>}</div>
    <section className="plus-upload"><label htmlFor="plus-images">Chọn ảnh cây lúa</label><input id="plus-images" type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(event) => chooseFiles(event.target.files)} />
      <span>{files.length ? `${files.length} ảnh đã chọn` : 'Từ 1 đến 5 ảnh · mỗi ảnh tối đa 10 MB'}</span>
      {!!files.length && <div className="plus-previews">{files.map((file, i) => <div key={`${file.name}-${i}`}><strong>Ảnh {i + 1}</strong><span>{file.name}</span></div>)}</div>}
      <button type="button" disabled={busy || !files.length || (!plan.unlimited && plan.remaining === 0)} onClick={analyze}>{busy ? 'Đang phân tích...' : 'Phân tích bộ ảnh'}</button>
      {error && <p className="analysis-error" role="alert">{error}</p>}
    </section>
    {result && <section className="plus-results"><h2>{result.prediction ? names[result.prediction] : 'Chưa thể kết luận chung'}</h2>
      {result.message && <p>{result.message}</p>}
      <div className="plus-result-grid">{result.images.map((item, i) => <article key={item.filename}>
        <img src={item.heatmap_url || `/uploads/${item.filename}`} alt={`Ảnh phân tích ${i + 1}`} />
        <strong>Ảnh {i + 1}: {item.prediction ? names[item.prediction] : 'Chưa xác định'}</strong>
        <span>{item.disagreement ? 'Hai mô hình không thống nhất.' : item.prediction
          ? `Mức tự tin: ${(item.confidence * 100).toFixed(1)}%`
          : 'Chưa đủ chắc chắn để kết luận ảnh này.'}</span>
      </article>)}</div>
      {result.ipm_advice && <div className="plus-advice"><strong>Gợi ý xử lý</strong><p>{result.ipm_advice.recommendation}</p></div>}
    </section>}
  </main>;
}

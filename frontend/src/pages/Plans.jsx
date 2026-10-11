import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './Plans.css';

export default function Plans() {
  const [catalog, setCatalog] = useState(null);
  const [status, setStatus] = useState(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const token = localStorage.getItem('token');

  const refresh = async () => {
    const response = await axios.get('/api/plans/catalog');
    setCatalog(response.data);
    if (token) {
      const account = await axios.get('/api/plans/me', { headers: { Authorization: `Bearer ${token}` } });
      setStatus(account.data);
    }
  };

  useEffect(() => { refresh().catch(() => setMessage('Chưa tải được thông tin gói.')); }, [token]);

  const requestPlus = async () => {
    setBusy(true);
    setMessage('');
    try {
      await axios.post('/api/plans/request-plus', {}, { headers: { Authorization: `Bearer ${token}` } });
      await refresh();
      setMessage('Yêu cầu đã được ghi nhận. Plus chỉ được kích hoạt sau khi Admin xác nhận thanh toán.');
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Chưa gửi được yêu cầu. Vui lòng thử lại.');
    } finally {
      setBusy(false);
    }
  };

  return <main className="plans-page">
    <header className="plans-header"><span className="section-kicker">RICEAI · GÓI SỬ DỤNG</span>
      <h1>Chọn cách chăm lúa phù hợp</h1>
      <p>Mỗi lượt chẩn đoán được tính khi ảnh được phân tích thành công. Lượt được làm mới đầu mỗi tháng.</p>
    </header>
    {status && <div className="plans-current" role="status">
      <div><strong>Gói đang dùng: {status.plan === 'plus' ? 'Plus' : 'Basic'}</strong>
        <span>{status.unlimited ? 'Admin và Employee dùng không giới hạn.' : `Tháng ${status.period}: còn ${status.remaining} lượt.`}</span></div>
      {status.halfway_notice && <span className="plans-warning">Bạn đã dùng hơn một nửa lượt Plus trong tháng.</span>}
    </div>}
    <div className="plans-grid">
      <article className="plan-card"><span className="plan-label">BASIC</span><h2>Dùng hằng ngày</h2>
        <p className="plan-price">Miễn phí</p>
        <ul><li>15 lượt chẩn đoán mỗi tháng</li><li>1 ảnh mỗi lượt</li><li>Nhận diện 7 nhóm hiện có</li><li>Vùng ảnh mô hình chú ý bằng Grad-CAM</li><li>Lưu lịch sử và gợi ý IPM</li></ul>
        <Link to="/" className="plan-action">Chẩn đoán với Basic</Link>
      </article>
      <article className="plan-card plan-card-plus"><span className="plan-label">PLUS</span><h2>Phân tích nhiều ảnh</h2>
        <p className="plan-price">29.000đ <small>/ tháng đầu</small></p><p className="plan-renewal">Sau đó 49.000đ/tháng · mức giá dự kiến</p>
        <ul><li>80 lượt chẩn đoán mỗi tháng</li><li>Tối đa 5 ảnh mỗi lượt</li><li>Kết hợp MobileNetV3 Large và Swin Tiny</li><li>Đối chiếu vùng tổn thương bằng DeepLabV3+</li><li>Cảnh báo khi ảnh chưa đủ rõ hoặc các ảnh không thống nhất</li></ul>
        {!token ? <Link to="/login" className="plan-action">Đăng nhập để xem gói</Link>
          : !catalog?.plus_ready ? <div className="plan-unavailable">Đang kiểm định mô hình Plus. Chưa mở đăng ký hoặc thanh toán.</div>
          : status?.plan === 'plus' ? <Link to="/plus" className="plan-action">Mở giao diện Plus</Link>
          : status?.pending_request ? <div className="plan-unavailable">Yêu cầu Plus đang chờ Admin xác nhận.</div>
          : <button className="plan-action" disabled={busy} onClick={requestPlus}>{busy ? 'Đang gửi...' : 'Gửi yêu cầu nâng cấp'}</button>}
      </article>
    </div>
    {message && <p className="plans-message" role="status">{message}</p>}
    <p className="plans-note">RiceAI chưa tích hợp cổng thanh toán trực tuyến. Việc gửi yêu cầu không trừ tiền hoặc tự kích hoạt Plus.</p>
  </main>;
}

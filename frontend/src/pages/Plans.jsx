import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import './Plans.css';

const money = (value) => `${Number(value || 0).toLocaleString('vi-VN')}đ`;
const date = (value) => value ? new Date(value).toLocaleDateString('vi-VN') : '';

export default function Plans() {
  const [catalog, setCatalog] = useState(null);
  const [status, setStatus] = useState(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const token = localStorage.getItem('token');

  const refresh = useCallback(async () => {
    const response = await axios.get('/api/plans/catalog');
    setCatalog(response.data);
    if (token) {
      const account = await axios.get('/api/plans/me', { headers: { Authorization: `Bearer ${token}` } });
      setStatus(account.data);
    }
  }, [token]);

  useEffect(() => { refresh().catch(() => setMessage('Chưa tải được thông tin gói.')); }, [refresh]);

  const submit = async (path, success) => {
    setBusy(true);
    setMessage('');
    try {
      await axios.post(path, {}, { headers: { Authorization: `Bearer ${token}` } });
      await refresh();
      setMessage(success);
    } catch (error) {
      setMessage(error.response?.data?.detail || 'Chưa thực hiện được. Vui lòng thử lại.');
    } finally {
      setBusy(false);
    }
  };

  const pending = status?.pending_request;
  const bank = catalog?.payment_bank;

  return <main className="plans-page">
    <header className="plans-header"><span className="section-kicker">RICEAI · GÓI SỬ DỤNG</span>
      <h1>Chọn gói RiceAI</h1>
      <p>Một tài khoản dùng cùng một gói trên web và iPhone. Lượt chẩn đoán được làm mới đầu mỗi tháng.</p>
    </header>
    {status && <div className="plans-current" role="status">
      <div><strong>Gói hiện tại: {status.plan === 'plus' ? 'Plus' : 'Basic'}{status.trial_active ? ' · dùng thử' : ''}</strong>
        <span>{status.unlimited ? 'Admin và Employee dùng không giới hạn.' : `Tháng ${status.period}: còn ${status.remaining} lượt.`}</span>
        {status.valid_until && <span>Có hiệu lực đến {date(status.valid_until)}.</span>}</div>
      {status.halfway_notice && <span className="plans-warning">Bạn đã dùng hơn một nửa lượt Plus trong tháng.</span>}
    </div>}
    <div className="plans-grid">
      <article className="plan-card"><span className="plan-label">BASIC</span><h2>Dùng hằng ngày</h2>
        <p className="plan-price">Miễn phí</p>
        <ul><li>15 lượt chẩn đoán mỗi tháng</li><li>1 ảnh mỗi lượt</li><li>Nhận diện 7 nhóm hiện có</li><li>Vùng ảnh mô hình chú ý bằng Grad-CAM</li><li>Lưu lịch sử và gợi ý IPM</li></ul>
        <Link to="/" className="plan-action">Tiếp tục chẩn đoán</Link>
      </article>
      <article className="plan-card plan-card-plus"><span className="plan-label">PLUS</span><h2>Phân tích nhiều ảnh</h2>
        <p className="plan-price">Dùng thử 1 tháng</p><p className="plan-renewal">Sau đó {money(catalog?.plus?.intro_price_vnd || 29000)} cho tháng trả phí đầu tiên; các tháng tiếp theo {money(catalog?.plus?.monthly_price_vnd || 49000)}.</p>
        <ul><li>80 lượt chẩn đoán mỗi tháng</li><li>Tối đa 5 ảnh mỗi lượt</li><li>Kết hợp MobileNetV3 Large và Swin Tiny</li><li>Đối chiếu vùng tổn thương bằng DeepLabV3+</li><li>Cảnh báo khi ảnh chưa đủ rõ hoặc các ảnh không thống nhất</li></ul>
        {!token ? <Link to="/login" className="plan-action">Đăng nhập để nâng cấp</Link>
          : !catalog?.plus_ready ? <div className="plan-unavailable">Plus đang được kiểm định. Chưa mở dùng thử hoặc thanh toán.</div>
          : status?.unlimited ? <Link to="/plus" className="plan-action">Sử dụng Plus</Link>
          : status?.trial_available ? <button type="button" className="plan-action" disabled={busy} onClick={() => submit('/api/plans/start-trial', 'Đã bật Plus dùng thử 1 tháng. Trên iPhone, hãy đóng và mở lại RiceAI để chuyển gói.')}>{busy ? 'Đang bật...' : 'Dùng thử Plus miễn phí 1 tháng'}</button>
          : status?.plan === 'plus' && !status?.trial_active ? <Link to="/plus" className="plan-action">Sử dụng Plus</Link>
          : pending ? <div className="plan-unavailable">Yêu cầu thanh toán đang chờ đối chiếu giao dịch.</div>
          : <button type="button" className="plan-action" disabled={busy} onClick={() => submit('/api/plans/request-plus', 'Đã tạo yêu cầu. Chuyển khoản đúng số tiền và nội dung hiển thị bên dưới.')}>{busy ? 'Đang tạo...' : status?.trial_active ? 'Gia hạn Plus sau dùng thử' : 'Nâng cấp Plus bằng chuyển khoản'}</button>}
      </article>
    </div>
    {pending && bank && <section className="plans-payment" aria-label="Hướng dẫn chuyển khoản Plus">
      <div><span className="section-kicker">THANH TOÁN PLUS</span><h2>Chuyển khoản theo mã yêu cầu #{pending.id}</h2>
        <p>Quét QR ngân hàng bạn đã cung cấp hoặc nhập thông tin bên dưới. QR này chưa điền sẵn số tiền và nội dung; hãy nhập đúng cả hai trong ứng dụng ngân hàng. Chỉ chuyển khoản khi tên người nhận khớp.</p>
        <dl><div><dt>Ngân hàng</dt><dd>Techcombank</dd></div><div><dt>Người nhận</dt><dd>{bank.account_name}</dd></div><div><dt>Số tài khoản</dt><dd>{bank.account_number}</dd></div><div><dt>Số tiền</dt><dd>{money(pending.price_vnd)}</dd></div><div><dt>Nội dung chuyển khoản</dt><dd><strong>{pending.payment_code}</strong></dd></div></dl>
        <p className="plans-payment-note">RiceAI không tự trừ tiền. Sau khi chuyển khoản, Admin đối chiếu số tiền, nội dung và mã giao dịch ngân hàng rồi mới kích hoạt Plus. Tài khoản dùng thử vẫn hoạt động đến hết hạn.</p>
      </div>
      <svg className="plans-payment-qr" viewBox="270 680 530 540" role="img" aria-label={`Mã VietQR tài khoản ${bank.account_number} của ${bank.account_name}`}>
        <image href="/riceai-payment-qr.png" width="1125" height="2172" />
      </svg>
    </section>}
    {message && <p className="plans-message" role="status">{message}</p>}
    <p className="plans-note">Chuyển khoản hiện được xác nhận thủ công; RiceAI chưa kết nối dữ liệu giao dịch ngân hàng để tự kích hoạt Plus.</p>
  </main>;
}

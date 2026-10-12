import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { sendPasswordResetEmail } from 'firebase/auth';
import { auth } from '../auth/firebase';
import './AdminDashboard.css';

const FIELDS = [
  ['overview', 'Tổng quan'],
  ['symptoms', 'Dấu hiệu nhận biết'],
  ['favorable_conditions', 'Điều kiện phát sinh'],
  ['prevention', 'Phòng ngừa'],
  ['ipm_advice', 'Khuyến nghị IPM'],
];
const LABELS = {
  bacterial_leaf_blight: 'Bạc lá vi khuẩn', brown_spot: 'Đốm nâu',
  golden_apple_snail: 'Ốc bươu vàng', leaf_roller: 'Sâu cuốn lá',
  normal: 'Lúa khỏe', tungro: 'Tungro', weeds: 'Cỏ dại',
  uncertain: 'Chưa xác định',
  blast: 'Đạo ôn (dữ liệu cũ)', sheath_blight: 'Khô vằn (dữ liệu cũ)',
};
const dateText = (value) => value ? new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`).toLocaleString('vi-VN') : '—';
const api = (path, options = {}) => axios({
  url: `/api/admin${path}`,
  headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
  ...options,
}).then((response) => response.data);

function AdminDashboard() {
  const navigate = useNavigate();
  const [role, setRole] = useState('');
  const [tab, setTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [live, setLive] = useState(null);
  const [content, setContent] = useState([]);
  const [selected, setSelected] = useState('');
  const [draft, setDraft] = useState({});
  const [mobile, setMobile] = useState(null);
  const [users, setUsers] = useState([]);
  const [plusRequests, setPlusRequests] = useState([]);
  const [paymentChecked, setPaymentChecked] = useState({});
  const [audits, setAudits] = useState([]);
  const [invite, setInvite] = useState({ email: '', full_name: '', role: 'employee' });
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  const refresh = useCallback(async (currentRole) => {
    const [statsData, contentData, mobileData, liveData] = await Promise.all([
      api('/stats'), api('/content'), api('/mobile'), api('/live'),
    ]);
    setStats(statsData);
    setContent(contentData);
    setMobile(mobileData);
    setLive(liveData);
    if (currentRole === 'admin') {
      const [userData, auditData, requestData] = await Promise.all([
        api('/users'), api('/audit'), axios.get('/api/plans/requests', {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        }).then((response) => response.data),
      ]);
      setUsers(userData);
      setAudits(auditData);
      setPlusRequests(requestData);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const load = async () => {
      if (!localStorage.getItem('token')) {
        navigate('/login', { state: { from: '/admin' } });
        return;
      }
      try {
        const profile = await axios.get('/api/auth/me', {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        });
        if (!['admin', 'employee'].includes(profile.data.role)) {
          throw new Error('Tài khoản này không có quyền vào khu vực quản trị.');
        }
        if (!active) return;
        setRole(profile.data.role);
        localStorage.setItem('user_role', profile.data.role);
        window.dispatchEvent(new Event('riceai-auth-changed'));
        await refresh(profile.data.role);
      } catch (err) {
        if (active) setError(err.response?.data?.detail || err.message || 'Không thể tải dữ liệu quản trị.');
      }
    };
    load();
    return () => { active = false; };
  }, [navigate, refresh]);

  useEffect(() => {
    if (!role) return undefined;
    let active = true;
    const update = () => {
      if (document.hidden) return;
      api('/live').then((data) => { if (active) setLive(data); }).catch(() => { if (active) setLive(null); });
    };
    const timer = window.setInterval(update, 15000);
    document.addEventListener('visibilitychange', update);
    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', update);
    };
  }, [role]);

  useEffect(() => {
    if (!content.length) return;
    const row = content.find((item) => item.slug === selected) || content[0];
    if (!selected) setSelected(row.slug);
    setDraft(row.draft);
  }, [content, selected]);

  const run = async (work, success) => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await work();
      await refresh(role);
      setNotice(success);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Thao tác chưa hoàn tất.');
    } finally {
      setBusy(false);
    }
  };

  const saveDraft = () => run(
    () => api(`/content/${selected}`, { method: 'put', data: draft }),
    'Đã lưu bản nháp. Nội dung công khai chưa thay đổi.',
  );
  const publish = () => run(
    async () => {
      await api(`/content/${selected}`, { method: 'put', data: draft });
      await api(`/content/${selected}/publish`, { method: 'post' });
    },
    'Đã xuất bản. Web và mobile sẽ thấy nội dung mới khi tải lại cẩm nang.',
  );
  const createStaff = (event) => {
    event.preventDefault();
    run(async () => {
      const result = await api('/staff', { method: 'post', data: invite });
      if (result.created_firebase) {
        try {
          await sendPasswordResetEmail(auth, result.email);
        } catch {
          throw new Error('Tài khoản đã tạo nhưng thư đặt mật khẩu chưa gửi được. Hãy dùng “Quên mật khẩu?” trên trang đăng nhập với email này.');
        }
      }
      setInvite({ email: '', full_name: '', role: 'employee' });
    }, 'Đã tạo hoặc cập nhật nhân viên. Nếu là tài khoản mới, Firebase đã gửi thư đặt mật khẩu.');
  };
  const changeRole = (user, nextRole) => run(
    () => api(`/users/${user.id}/role`, { method: 'put', data: { role: nextRole } }),
    `Đã cập nhật quyền của ${user.email}.`,
  );
  const activatePlus = (item) => run(
    () => axios.post(`/api/plans/requests/${item.id}/activate`, { payment_verified: true },
      { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }),
    `Đã kích hoạt Plus 30 ngày cho ${item.email}.`,
  );
  const grantDemo = (user) => run(
    () => axios.post('/api/plans/admin/grant', { user_id: user.id, days: 30, reason: 'Trải nghiệm thử nghiệm' },
      { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }),
    `Đã cấp Plus thử nghiệm 30 ngày cho ${user.email}.`,
  );

  const row = content.find((item) => item.slug === selected);
  const tabs = [
    ['overview', 'Tổng quan'], ['content', 'Nội dung cẩm nang'],
    ['mobile', 'Ứng dụng mobile'],
    ...(role === 'admin' ? [['users', 'Tài khoản'], ['plus', 'Yêu cầu Plus'], ['audit', 'Nhật ký']] : []),
  ];

  return (
    <main className="admin-shell">
      <header className="admin-hero">
        <div>
          <span className="admin-eyebrow">RICEAI · WORKSPACE</span>
          <h1>Trung tâm quản trị</h1>
          <p>Dữ liệu chẩn đoán, nội dung cẩm nang và phiên bản ứng dụng trong một nơi.</p>
        </div>
        <span className="admin-role">{role === 'admin' ? 'Quản trị viên' : role === 'employee' ? 'Nhân viên' : 'Đang kiểm tra quyền'}</span>
      </header>
      {error && <div className="admin-alert error" role="alert">{error}</div>}
      {notice && <div className="admin-alert success" role="status">{notice}</div>}
      {!role ? <div className="admin-panel">Đang tải khu vực quản trị...</div> : <>
        <nav className="admin-tabs" aria-label="Các mục quản trị">
          {tabs.map(([key, label]) => <button key={key} type="button" className={tab === key ? 'active' : ''} onClick={() => { setTab(key); setError(''); setNotice(''); }}>{label}</button>)}
        </nav>

        {tab === 'overview' && stats && <section>
          <div className="admin-metrics">
            <div className="admin-metric"><span>Người dùng</span><strong>{stats.total_users}</strong><small>Tài khoản hệ thống</small></div>
            <div className="admin-metric"><span>Lượt chẩn đoán</span><strong>{stats.total_scans}</strong><small>Tất cả nền tảng</small></div>
            <div className="admin-metric"><span>Nhân sự</span><strong>{stats.total_staff}</strong><small>Admin và Employee</small></div>
            <div className="admin-metric"><span>Hoạt động iOS</span><strong>{stats.client_activity.find((item) => item.platform === 'ios')?.events || 0}</strong><small>Từ khi bật theo dõi</small></div>
            <div className="admin-metric"><span>Người đang sử dụng</span><strong>{live?.active_users ?? '—'}</strong><small>Tài khoản có hoạt động trong 2 phút gần nhất</small></div>
            <div className="admin-metric"><span>Thiết bị đang hoạt động</span><strong>{live?.active_devices ?? '—'}</strong><small>Có báo trạng thái trong 2 phút gần nhất</small></div>
            <div className="admin-metric"><span>Đang phân tích ảnh</span><strong>{live?.diagnoses.processing ?? '—'}</strong><small>Yêu cầu đang chạy trên laptop</small></div>
            <div className="admin-metric"><span>Đang chờ phân tích</span><strong>{live?.diagnoses.waiting ?? '—'}</strong><small>{live ? `Giới hạn ${live.diagnosis_queue_limit} yêu cầu cùng lúc` : 'Yêu cầu chẩn đoán trong hàng đợi'}</small></div>
          </div>
          <div className="admin-columns">
            <div className="admin-panel"><h2>Phân bố chẩn đoán</h2>
              {stats.disease_distribution.length ? stats.disease_distribution.map((item) => <div className="admin-bar-row" key={item.name}>
                <span>{LABELS[item.name] || item.name}</span>
                <div><i style={{ width: `${Math.max(5, item.value / Math.max(...stats.disease_distribution.map((x) => x.value)) * 100)}%` }} /></div>
                <strong>{item.value}</strong>
              </div>) : <p className="admin-muted">Chưa có lượt chẩn đoán.</p>}
            </div>
            <div className="admin-panel"><h2>Chẩn đoán gần đây</h2>
              <div className="admin-table-wrap"><table><thead><tr><th>Thời gian</th><th>Người dùng</th><th>Kết quả</th><th>Độ tin cậy</th></tr></thead>
                <tbody>{stats.recent_scans.map((item) => <tr key={item.id}><td>{dateText(item.created_at)}</td><td>{item.user}</td><td>{LABELS[item.prediction] || item.prediction}</td><td>{item.prediction === 'uncertain' ? '—' : `${Math.round(item.confidence * 100)}%`}</td></tr>)}</tbody></table></div>
              {!stats.recent_scans.length && <p className="admin-muted">Chưa có dữ liệu.</p>}
            </div>
          </div>
        </section>}

        {tab === 'content' && <section className="admin-columns content-layout">
          <div className="admin-panel"><h2>Nội dung cẩm nang</h2><p className="admin-muted">Employee lưu nháp; Admin xuất bản.</p>
            <div className="admin-content-list">{content.map((item) => <button key={item.slug} type="button" className={selected === item.slug ? 'selected' : ''} onClick={() => setSelected(item.slug)}>
              <span>{item.display_name_vi}</span>{item.has_unpublished_changes && <small>Chờ duyệt</small>}
            </button>)}</div>
          </div>
          <div className="admin-panel"><div className="admin-panel-head"><div><h2>{row?.display_name_vi || 'Chọn nhóm bệnh'}</h2><p className="admin-muted">Bản nháp chỉ công khai sau khi Admin xuất bản.</p></div>{row?.published_at && <small>Xuất bản {dateText(row.published_at)}</small>}</div>
            {row && <form onSubmit={(event) => { event.preventDefault(); saveDraft(); }} className="admin-editor">
              {FIELDS.map(([field, label]) => <label key={field}>{label}<textarea rows={field === 'ipm_advice' ? 4 : 3} minLength={10} maxLength={2000} required value={draft[field] || ''} onChange={(event) => setDraft({ ...draft, [field]: event.target.value })} /></label>)}
              <div className="admin-actions"><button type="submit" disabled={busy}>Lưu bản nháp</button>{role === 'admin' && <button type="button" className="primary" disabled={busy} onClick={publish}>Xuất bản lên web và mobile</button>}</div>
            </form>}
          </div>
        </section>}

        {tab === 'mobile' && <section className="admin-columns">
          <div className="admin-panel"><h2>Người dùng và thiết bị đang hoạt động</h2><p className="admin-muted">{live ? `${live.active_users} người dùng trên ${live.active_devices} thiết bị · ghi nhận trong 2 phút gần nhất · cập nhật ${dateText(live.sampled_at)}` : 'Chưa lấy được trạng thái hiện tại.'}</p>
            <div className="admin-live-grid"><div><strong>{live?.by_platform?.web ?? '—'}</strong><span>Web</span></div><div><strong>{live?.by_platform?.ios ?? '—'}</strong><span>iPhone</span></div><div><strong>{live?.by_platform?.android ?? '—'}</strong><span>Android</span></div></div>
            <p className="admin-muted">Chỉ tính thiết bị đang mở ứng dụng và kết nối được máy chủ.</p>
          </div>
          <div className="admin-panel"><h2>Phiên bản đã ghi nhận</h2><p className="admin-muted">Tổng hợp 500 sự kiện gần nhất khi app mở phiên đăng nhập, đổi phiên bản hoặc gửi chẩn đoán. Mã thiết bị ngẫu nhiên chỉ được lưu dưới dạng băm.</p>
            <div className="admin-table-wrap"><table><thead><tr><th>Nền tảng</th><th>Phiên bản</th><th>Sự kiện</th></tr></thead><tbody>
              {mobile?.versions.map((item) => <tr key={`${item.platform}-${item.version}`}><td>{item.platform.toUpperCase()}</td><td>{item.version}</td><td>{item.events}</td></tr>)}
            </tbody></table></div>{!mobile?.versions.length && <p className="admin-muted">Chưa có app nào báo phiên bản. Bản iPhone cũ cần được cài bản cập nhật có tính năng báo phiên bản một lần.</p>}
          </div>
          <div className="admin-panel"><h2>Hoạt động gần đây</h2><div className="admin-table-wrap"><table><thead><tr><th>Thời gian</th><th>Nền tảng</th><th>Phiên bản</th><th>Hoạt động</th></tr></thead><tbody>
            {mobile?.recent.map((item, index) => <tr key={index}><td>{dateText(item.at)}</td><td>{item.platform}</td><td>{item.version}</td><td>{item.event === 'diagnosis' ? 'Chẩn đoán' : 'Mở phiên'}</td></tr>)}
          </tbody></table></div></div>
        </section>}

        {tab === 'users' && role === 'admin' && <section className="admin-columns">
          <div className="admin-panel"><h2>Tạo nhân viên</h2><p className="admin-muted">Nếu email chưa có trên Firebase, người nhận sẽ được gửi thư tự đặt mật khẩu.</p>
            <form className="admin-editor" onSubmit={createStaff}>
              <label>Email<input type="email" required value={invite.email} onChange={(event) => setInvite({ ...invite, email: event.target.value })} /></label>
              <label>Họ tên<input required minLength={2} value={invite.full_name} onChange={(event) => setInvite({ ...invite, full_name: event.target.value })} /></label>
              <label>Vai trò<select value={invite.role} onChange={(event) => setInvite({ ...invite, role: event.target.value })}><option value="employee">Employee</option><option value="admin">Admin</option></select></label>
              <div className="admin-actions"><button type="submit" className="primary" disabled={busy}>Tạo tài khoản</button></div>
            </form>
          </div>
          <div className="admin-panel"><h2>Tài khoản hệ thống</h2><div className="admin-table-wrap"><table><thead><tr><th>Người dùng</th><th>Email</th><th>Vai trò</th><th>Plus thử nghiệm</th></tr></thead><tbody>
            {users.map((user) => <tr key={user.id}><td>{user.full_name}</td><td>{user.email}</td><td><select aria-label={`Vai trò của ${user.email}`} value={user.role} disabled={busy || user.email === localStorage.getItem('user_email')} onChange={(event) => changeRole(user, event.target.value)}><option value="farmer">Người dùng</option><option value="employee">Employee</option><option value="admin">Admin</option></select></td><td>{user.role === 'farmer' && <button type="button" disabled={busy} onClick={() => grantDemo(user)}>Cấp 30 ngày</button>}</td></tr>)}
          </tbody></table></div></div>
        </section>}

        {tab === 'plus' && role === 'admin' && <section className="admin-panel"><h2>Yêu cầu nâng cấp Plus</h2>
          <p className="admin-muted">RiceAI không thu tiền trực tuyến. Chỉ xác nhận sau khi bạn tự đối chiếu khoản thanh toán bên ngoài.</p>
          <div className="admin-table-wrap"><table><thead><tr><th>Ngày gửi</th><th>Email</th><th>Số tiền dự kiến</th><th>Trạng thái</th><th>Xác nhận</th></tr></thead><tbody>
            {plusRequests.map((item) => <tr key={item.id}><td>{dateText(item.created_at)}</td><td>{item.email}</td><td>{item.price_vnd.toLocaleString('vi-VN')}đ</td><td>{item.status}</td><td>{item.status === 'pending' && <><label><input type="checkbox" checked={!!paymentChecked[item.id]} onChange={(event) => setPaymentChecked({ ...paymentChecked, [item.id]: event.target.checked })} /> Đã kiểm tra thanh toán</label><button type="button" disabled={busy || !paymentChecked[item.id]} onClick={() => activatePlus(item)}>Kích hoạt</button></>}</td></tr>)}
          </tbody></table></div>{!plusRequests.length && <p className="admin-muted">Chưa có yêu cầu nâng cấp.</p>}
        </section>}

        {tab === 'audit' && role === 'admin' && <section className="admin-panel"><h2>Nhật ký quản trị</h2><div className="admin-table-wrap"><table><thead><tr><th>Thời gian</th><th>Thao tác</th><th>Đối tượng</th><th>ID nhân viên</th></tr></thead><tbody>
          {audits.map((item, index) => <tr key={index}><td>{dateText(item.at)}</td><td>{item.action}</td><td>{item.target}</td><td>{item.actor}</td></tr>)}
        </tbody></table></div>{!audits.length && <p className="admin-muted">Chưa có thay đổi nào.</p>}</section>}
      </>}
    </main>
  );
}

export default AdminDashboard;

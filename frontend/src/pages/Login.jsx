import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await axios.post('/api/login', { email, password });
      localStorage.setItem('token', res.data.access_token);
      localStorage.setItem('user_name', res.data.full_name);
      localStorage.setItem('user_role', res.data.role); // Lưu quyền hạn
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Sai email hoặc mật khẩu');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page glass-panel">
      <h2>Đăng Nhập</h2>
      <p className="auth-subtitle">Chào mừng trở lại! Đăng nhập để tiếp tục.</p>
      <form onSubmit={handleLogin} className="auth-form">
        <div>
          <label className="form-label">Email</label>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="form-input" placeholder="you@example.com" />
        </div>
        <div>
          <label className="form-label">Mật khẩu</label>
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="form-input" placeholder="••••••••" />
        </div>
        {error && <div className="auth-error">⚠ {error}</div>}
        <button type="submit" className="btn-primary" style={{ justifyContent: 'center', width: '100%', marginTop: '4px' }} disabled={loading}>
          {loading ? <><div className="loader"></div> Đang xử lý...</> : 'Đăng nhập'}
        </button>
      </form>
      <div className="auth-footer">
        Chưa có tài khoản? <Link to="/register">Đăng ký ngay</Link>
      </div>
    </div>
  );
}

export default Login;

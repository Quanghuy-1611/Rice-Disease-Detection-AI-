import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';

function Register() {
  const [formData, setFormData] = useState({ full_name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await axios.post('/api/register', formData);
      alert("Đăng ký thành công! Vui lòng đăng nhập.");
      navigate('/login');
    } catch (err) {
      setError(err.response?.data?.detail || 'Có lỗi xảy ra, vui lòng thử lại.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page glass-panel">
      <h2>Tạo Tài Khoản</h2>
      <p className="auth-subtitle">Đăng ký miễn phí để sử dụng hệ thống AI.</p>
      <form onSubmit={handleRegister} className="auth-form">
        <div>
          <label className="form-label">Họ và tên</label>
          <input type="text" required value={formData.full_name} onChange={(e) => setFormData({...formData, full_name: e.target.value})} className="form-input" placeholder="Nguyễn Văn A" />
        </div>
        <div>
          <label className="form-label">Email</label>
          <input type="email" required value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} className="form-input" placeholder="you@example.com" />
        </div>
        <div>
          <label className="form-label">Mật khẩu</label>
          <input type="password" required value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} className="form-input" placeholder="Tối thiểu 6 ký tự" />
        </div>
        {error && <div className="auth-error">⚠ {error}</div>}
        <button type="submit" className="btn-primary" style={{ justifyContent: 'center', width: '100%', marginTop: '4px' }} disabled={loading}>
          {loading ? <><div className="loader"></div> Đang xử lý...</> : 'Đăng ký'}
        </button>
      </form>
      <div className="auth-footer">
        Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
      </div>
    </div>
  );
}

export default Register;

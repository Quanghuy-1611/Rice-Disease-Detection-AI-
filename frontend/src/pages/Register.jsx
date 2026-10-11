import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  createUserWithEmailAndPassword,
  sendEmailVerification,
  signOut,
  updateProfile,
} from 'firebase/auth';

import { auth, authErrorMessage } from '../auth/firebase';

function Register() {
  const [formData, setFormData] = useState({ full_name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleRegister = async (event) => {
    event.preventDefault();
    setError('');
    if (formData.full_name.trim().length < 2) {
      setError('Vui lòng nhập họ tên đầy đủ.');
      return;
    }
    if (formData.password.length < 6) {
      setError('Mật khẩu cần có ít nhất 6 ký tự.');
      return;
    }
    setLoading(true);
    try {
      const { user } = await createUserWithEmailAndPassword(auth, formData.email.trim(), formData.password);
      await updateProfile(user, { displayName: formData.full_name.trim() });
      await sendEmailVerification(user);
      await signOut(auth);
      navigate('/login', {
        replace: true,
        state: { notice: 'Đã gửi thư xác minh đến email của bạn. Hãy mở thư và xác minh trước khi đăng nhập.' },
      });
    } catch (err) {
      await signOut(auth).catch(() => {});
      setError(authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const setField = (field, value) => setFormData((current) => ({ ...current, [field]: value }));

  return (
    <div className="auth-page glass-panel">
      <div className="auth-mark"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/></svg></div>
      <div className="auth-eyebrow">Tài khoản RiceAI Basic</div>
      <h2>Tạo tài khoản</h2>
      <p className="auth-subtitle">Đăng ký bằng email bạn dùng được. RiceAI sẽ gửi một thư xác minh.</p>
      <form onSubmit={handleRegister} className="auth-form">
        <div>
          <label className="form-label" htmlFor="register-name">Họ và tên</label>
          <input id="register-name" type="text" autoComplete="name" required minLength={2} value={formData.full_name} onChange={(event) => setField('full_name', event.target.value)} className="form-input" placeholder="Nguyễn Văn A" />
        </div>
        <div>
          <label className="form-label" htmlFor="register-email">Email</label>
          <div className="input-with-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/></svg><input id="register-email" type="email" autoComplete="email" required value={formData.email} onChange={(event) => setField('email', event.target.value)} className="form-input" placeholder="ban@example.com" /></div>
        </div>
        <div>
          <label className="form-label" htmlFor="register-password">Mật khẩu</label>
          <input id="register-password" type="password" autoComplete="new-password" required minLength={6} value={formData.password} onChange={(event) => setField('password', event.target.value)} className="form-input" placeholder="Tối thiểu 6 ký tự" />
        </div>
        {error && <div className="auth-error" role="alert">{error}</div>}
        <button type="submit" className="btn-primary auth-submit" disabled={loading}>
          {loading ? 'Đang gửi thư xác minh...' : 'Đăng ký bằng email'}
        </button>
      </form>
      <div className="auth-footer">Đã có tài khoản? <Link to="/login">Đăng nhập</Link></div>
    </div>
  );
}

export default Register;

import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  reload,
  sendEmailVerification,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signOut,
} from 'firebase/auth';

import { auth, authErrorMessage } from '../auth/firebase';
import { exchangeFirebaseSession } from '../auth/session';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setNotice('');
    try {
      const { user } = await signInWithEmailAndPassword(auth, email.trim(), password);
      await reload(user);
      if (!user.emailVerified) {
        await signOut(auth);
        setError('Email chưa được xác minh. Hãy mở thư xác minh rồi đăng nhập lại.');
        return;
      }
      await exchangeFirebaseSession(user);
      navigate(location.state?.from || '/', { replace: true });
    } catch (err) {
      await signOut(auth).catch(() => {});
      setError(authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async () => {
    if (!email.trim()) {
      setError('Nhập email trước khi yêu cầu đặt lại mật khẩu.');
      return;
    }
    setLoading(true);
    setError('');
    setNotice('');
    try {
      await sendPasswordResetEmail(auth, email.trim());
      setNotice('Nếu email đã có tài khoản, bạn sẽ nhận được thư đặt lại mật khẩu.');
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    if (!email.trim() || !password) {
      setError('Nhập email và mật khẩu để gửi lại thư xác minh.');
      return;
    }
    setLoading(true);
    setError('');
    setNotice('');
    try {
      const { user } = await signInWithEmailAndPassword(auth, email.trim(), password);
      await reload(user);
      if (user.emailVerified) {
        setNotice('Email đã được xác minh. Bạn có thể đăng nhập.');
      } else {
        await sendEmailVerification(user);
        setNotice('Đã gửi lại thư xác minh. Hãy kiểm tra hộp thư và mục spam.');
      }
      await signOut(auth);
    } catch (err) {
      await signOut(auth).catch(() => {});
      setError(authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page glass-panel">
      <div className="auth-mark"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/></svg></div>
      <div className="auth-eyebrow">Tài khoản RiceAI Basic</div>
      <h2>Đăng nhập</h2>
      <p className="auth-subtitle">Tiếp tục với email đã xác minh để lưu và xem lại lịch sử chẩn đoán.</p>
      <form onSubmit={handleLogin} className="auth-form">
        <div>
          <label className="form-label" htmlFor="login-email">Email</label>
          <div className="input-with-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/></svg><input id="login-email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} className="form-input" placeholder="ban@example.com" /></div>
        </div>
        <div>
          <label className="form-label" htmlFor="login-password">Mật khẩu</label>
          <input id="login-password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} className="form-input" placeholder="Mật khẩu của bạn" />
        </div>
        {location.state?.notice && <div className="auth-notice" role="status">{location.state.notice}</div>}
        {notice && <div className="auth-notice" role="status">{notice}</div>}
        {error && <div className="auth-error" role="alert">{error}</div>}
        <button type="submit" className="btn-primary auth-submit" disabled={loading}>
          {loading ? 'Đang xử lý...' : 'Đăng nhập'}
        </button>
      </form>
      <div className="auth-actions">
        <button type="button" onClick={handleResetPassword} disabled={loading}>Quên mật khẩu?</button>
        <button type="button" onClick={handleResendVerification} disabled={loading}>Gửi lại thư xác minh</button>
      </div>
      <div className="auth-footer">Chưa có tài khoản? <Link to="/register">Đăng ký ngay</Link></div>
    </div>
  );
}

export default Login;

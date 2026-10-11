import React, { lazy, Suspense, useState, useEffect } from 'react';
import { Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import Home from './pages/Home';
import DiseaseLibrary from './pages/DiseaseLibrary';
import Chatbot from './components/Chatbot';
import { clearSession } from './auth/session';
import axios from 'axios';
import './App.css';

const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const History = lazy(() => import('./pages/History'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const Plans = lazy(() => import('./pages/Plans'));
const Plus = lazy(() => import('./pages/Plus'));

function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [userName, setUserName] = useState(localStorage.getItem('user_name'));
  const [verifiedRole, setVerifiedRole] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => setMenuOpen(false), [location.pathname]);

  useEffect(() => {
    const checkAuth = () => {
      setToken(localStorage.getItem('token'));
      setUserName(localStorage.getItem('user_name'));
    };
    window.addEventListener('storage', checkAuth);
    window.addEventListener('riceai-auth-changed', checkAuth);
    checkAuth();
    return () => {
      window.removeEventListener('storage', checkAuth);
      window.removeEventListener('riceai-auth-changed', checkAuth);
    };
  }, [location]);

  useEffect(() => {
    let active = true;
    setVerifiedRole(null);
    if (!token) return () => { active = false; };
    axios.get('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } })
      .then(({ data }) => {
        if (!active) return;
        setVerifiedRole(data.role);
        setUserName(data.full_name);
        localStorage.setItem('user_role', data.role);
        localStorage.setItem('user_name', data.full_name);
      })
      .catch((error) => {
        if (!active) return;
        if (error.response?.status === 401) clearSession();
        setVerifiedRole(null);
      });
    return () => { active = false; };
  }, [token, location.pathname]);

  useEffect(() => {
    if (!token) return undefined;
    let clientId = localStorage.getItem('riceai_client_id');
    if (!clientId) {
      const bytes = new Uint8Array(16);
      window.crypto.getRandomValues(bytes);
      clientId = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
      localStorage.setItem('riceai_client_id', clientId);
    }
    const report = () => {
      if (document.hidden) return;
      axios.post('/api/client/heartbeat', {
        platform: 'web', app_version: 'web-1', client_id: clientId,
      }, { headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
    };
    report();
    const timer = window.setInterval(report, 45000);
    document.addEventListener('visibilitychange', report);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', report);
    };
  }, [token]);

  const handleLogout = async () => {
    try {
      const [{ signOut }, { auth }] = await Promise.all([
        import('firebase/auth'),
        import('./auth/firebase'),
      ]);
      await signOut(auth);
    } catch {
      // Clear the local session even when Firebase is temporarily unavailable.
    } finally {
      clearSession();
      setToken(null);
      setUserName(null);
      setVerifiedRole(null);
      navigate('/login');
    }
  };

  const isActive = (path) => location.pathname === path ? 'nav-link active' : 'nav-link';

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        <img className="logo-icon" src="/riceai-logo.png" alt="" />
        <span>Rice<span className="brand-accent">AI</span><small>BASIC</small></span>
      </Link>
      <button className="navbar-menu-toggle" type="button" aria-label={menuOpen ? 'Đóng menu' : 'Mở menu'} aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>
        <span /><span /><span />
      </button>
      <div className={`navbar-links ${menuOpen ? 'is-open' : ''}`}>
        <Link to="/" className={isActive('/')}>Chẩn đoán</Link>
        <Link to="/diseases" className={isActive('/diseases')}>Thư viện bệnh</Link>
        <Link to="/plans" className={isActive('/plans')}>Gói sử dụng</Link>
        {token ? (
          <>
            <Link to="/history" className={isActive('/history')}>Lịch sử</Link>
            {['admin', 'employee'].includes(verifiedRole) && (
              <Link to="/admin" className={isActive('/admin')} style={{ fontWeight: 'bold' }}>Quản trị</Link>
            )}
            <span className="nav-user" title={userName || 'Tài khoản'}>{(userName || 'T').trim().charAt(0).toLocaleUpperCase('vi-VN')}</span>
            <button onClick={handleLogout} className="nav-btn-logout">Đăng xuất</button>
          </>
        ) : (
          <>
            <Link to="/login" className={isActive('/login')}>Đăng nhập</Link>
            <Link to="/register" className="nav-register">Bắt đầu miễn phí <span aria-hidden="true">↗</span></Link>
          </>
        )}
      </div>
    </nav>
  );
}


function App() {
  const location = useLocation();
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      <div className={location.pathname.startsWith('/admin') ? 'app-container app-container-admin' : 'app-container'}>
        <Suspense fallback={<div className="route-loading">Đang tải trang...</div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/history" element={<History />} />
            <Route path="/diseases" element={<DiseaseLibrary />} />
            <Route path="/plans" element={<Plans />} />
            <Route path="/plus" element={<Plus />} />
            <Route path="/admin" element={<AdminDashboard />} />
          </Routes>
        </Suspense>
      </div>
      {!['/admin', '/login', '/register'].includes(location.pathname) && <Chatbot />}
    </div>
  );
}

export default App;

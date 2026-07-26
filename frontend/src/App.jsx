import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import History from './pages/History';
import DiseaseLibrary from './pages/DiseaseLibrary';
import AdminDashboard from './pages/AdminDashboard';
import Chatbot from './components/Chatbot';
import './App.css';

function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [userName, setUserName] = useState(localStorage.getItem('user_name'));
  const [userRole, setUserRole] = useState(localStorage.getItem('user_role'));

  useEffect(() => {
    const checkAuth = () => {
      setToken(localStorage.getItem('token'));
      setUserName(localStorage.getItem('user_name'));
      setUserRole(localStorage.getItem('user_role'));
    };
    window.addEventListener('storage', checkAuth);
    checkAuth();
    return () => window.removeEventListener('storage', checkAuth);
  }, [location]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_name');
    localStorage.removeItem('user_role');
    setToken(null);
    setUserName(null);
    setUserRole(null);
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path ? 'nav-link active' : 'nav-link';

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-brand">
        <div className="logo-icon">🌾</div>
        <span>RiceAI</span>
      </Link>
      
      <div className="navbar-links">
        <Link to="/" className={isActive('/')}>Chẩn đoán</Link>
        <Link to="/diseases" className={isActive('/diseases')}>Thư viện bệnh</Link>
        {token ? (
          <>
            <Link to="/history" className={isActive('/history')}>Lịch sử</Link>
            {userRole === 'admin' && (
              <Link to="/admin" className={isActive('/admin')} style={{ color: '#e74c3c', fontWeight: 'bold' }}>Bảng Quản Trị</Link>
            )}
            <span className="nav-user">👤 {userName}</span>
            <button onClick={handleLogout} className="nav-btn-logout">Đăng xuất</button>
          </>
        ) : (
          <>
            <Link to="/login" className={isActive('/login')}>Đăng nhập</Link>
            <Link to="/register" className="btn-primary" style={{ padding: '8px 20px', textDecoration: 'none', fontSize: '0.9rem' }}>Đăng ký</Link>
          </>
        )}
      </div>
    </nav>
  );
}


function App() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />
      <div className="app-container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/history" element={<History />} />
          <Route path="/diseases" element={<DiseaseLibrary />} />
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </div>
      <Chatbot />
    </div>
  );
}

export default App;

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend } from 'recharts';
import { DISEASES } from './DiseaseLibrary';

function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          navigate('/login');
          return;
        }
        
        const res = await axios.get('/api/admin/stats', {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        const translatedDistribution = res.data.disease_distribution.map(item => {
          const diseaseObj = DISEASES.find(d => d.id === item.name);
          return {
            name: diseaseObj ? diseaseObj.name : item.name,
            value: item.value
          };
        });
        
        setStats({
          ...res.data,
          disease_distribution: translatedDistribution
        });
      } catch (err) {
        if (err.response?.status === 403) {
          setError("Bạn không có quyền truy cập trang này.");
        } else {
          setError("Không thể kết nối đến máy chủ.");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [navigate]);

  if (loading) return <div style={styles.centerMsg}>Đang tải dữ liệu hệ thống... ⏳</div>;
  if (error) return <div style={{...styles.centerMsg, color: '#ef4444'}}>{error} ⚠️</div>;
  if (!stats) return null;

  // Premium Light Green Color Palette (Matching index.css)
  const COLORS = ['#10b981', '#34d399', '#059669', '#f59e0b', '#fbbf24', '#3b82f6', '#8b5cf6', '#ef4444'];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={styles.tooltip}>
          <p style={{ margin: 0, fontWeight: '600', color: '#064e3b' }}>{payload[0].name}</p>
          <p style={{ margin: 0, color: payload[0].payload.fill || 'var(--primary)' }}>Số ca: {payload[0].value}</p>
        </div>
      );
    }
    return null;
  };

  const getConfidenceBadge = (confidence) => {
    if (confidence >= 0.8) return <span style={{...styles.badge, background: 'rgba(16, 185, 129, 0.2)', color: '#059669'}}>Độ tin cậy Cao</span>;
    if (confidence >= 0.5) return <span style={{...styles.badge, background: 'rgba(245, 158, 11, 0.2)', color: '#d97706'}}>Độ tin cậy Vừa</span>;
    return <span style={{...styles.badge, background: 'rgba(239, 68, 68, 0.2)', color: '#b91c1c'}}>Độ tin cậy Thấp</span>;
  };

  return (
    <div style={styles.container}>
      <div style={styles.innerContainer}>
        <div style={styles.header}>
          <h2 style={styles.title}>Quản Trị Hệ Thống <span style={{fontSize: '1.5rem'}}>⚙️</span></h2>
          <p style={styles.subtitle}>Giám sát hoạt động và tình hình dịch tễ theo thời gian thực</p>
        </div>

        {/* Dashboard Grid Layout - Making full use of width */}
        <div style={styles.mainGrid}>
          
          {/* LEFT COLUMN: KPIs and Table */}
          <div style={styles.leftColumn}>
            {/* KPI Cards Row */}
            <div style={styles.kpiGrid}>
              <div style={styles.kpiCard}>
                <div style={styles.kpiIcon}>👥</div>
                <div>
                  <h3 style={styles.kpiLabel}>Tổng Người Dùng</h3>
                  <div style={styles.kpiValue}>{stats.total_users}</div>
                </div>
              </div>
              <div style={styles.kpiCard}>
                <div style={styles.kpiIcon}>🔍</div>
                <div>
                  <h3 style={styles.kpiLabel}>Tổng Lượt Quét AI</h3>
                  <div style={styles.kpiValue}>{stats.total_scans}</div>
                </div>
              </div>
              <div style={{...styles.kpiCard, background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.05), rgba(245, 158, 11, 0.05))'}}>
                <div style={styles.kpiIcon}>🔥</div>
                <div>
                  <h3 style={styles.kpiLabel}>Bệnh Phổ Biến Nhất</h3>
                  <div style={{...styles.kpiValue, fontSize: '1.4rem', color: '#ef4444'}}>
                    {stats.disease_distribution.length > 0 ? 
                      stats.disease_distribution.sort((a,b) => b.value - a.value)[0].name : "Chưa có dữ liệu"}
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Activity Table */}
            <div style={styles.tableContainer}>
              <h3 style={styles.chartTitle}>Lịch Sử Quét Gần Nhất</h3>
              {stats.recent_scans.length === 0 ? (
                <p style={{color: '#047857'}}>Chưa có dữ liệu quét.</p>
              ) : (
                <div style={styles.tableWrapper}>
                  <table style={styles.table}>
                    <thead>
                      <tr>
                        <th style={styles.th}>Người Dùng</th>
                        <th style={styles.th}>Kết Quả Nhận Diện</th>
                        <th style={styles.th}>Độ Chính Xác</th>
                        <th style={styles.th}>Thời Gian</th>
                      </tr>
                    </thead>
                    <tbody>
                      {stats.recent_scans.map((scan) => {
                        const diseaseObj = DISEASES.find(d => d.id === scan.prediction);
                        const diseaseName = diseaseObj ? diseaseObj.name : scan.prediction;
                        const isHealthy = diseaseName.includes("Khỏe Mạnh") || scan.prediction === "normal";
                        
                        return (
                          <tr key={scan.id} style={styles.tr}>
                            <td style={styles.td}>
                              <div style={styles.userAvatar}>{scan.user.charAt(0).toUpperCase()}</div>
                              <span style={styles.userName}>{scan.user}</span>
                            </td>
                            <td style={styles.td}>
                              <span style={{color: isHealthy ? '#059669' : '#064e3b', fontWeight: '600'}}>
                                {diseaseName}
                              </span>
                            </td>
                            <td style={styles.td}>{getConfidenceBadge(scan.confidence)}</td>
                            <td style={{...styles.td, color: '#047857', fontSize: '0.9rem'}}>
                              {new Date(scan.created_at).toLocaleString('vi-VN')}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* RIGHT COLUMN: Charts */}
          <div style={styles.rightColumn}>
            {/* Pie Chart */}
            <div style={styles.chartContainer}>
              <h3 style={styles.chartTitle}>Tỉ Lệ Mắc Bệnh</h3>
              <ResponsiveContainer width="100%" height="90%">
                <PieChart>
                  <Pie
                    data={stats.disease_distribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={120}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  >
                    {stats.disease_distribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Bar Chart */}
            <div style={styles.chartContainer}>
              <h3 style={styles.chartTitle}>Tần Suất Quét</h3>
              <ResponsiveContainer width="100%" height="90%">
                <BarChart
                  data={stats.disease_distribution}
                  margin={{ top: 20, right: 30, left: -20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(16, 185, 129, 0.1)" vertical={false} />
                  <XAxis dataKey="name" tick={false} axisLine={false} />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: '#047857'}} />
                  <Tooltip content={<CustomTooltip />} cursor={{fill: 'rgba(16, 185, 129, 0.05)'}} />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                    {stats.disease_distribution.map((entry, index) => (
                      <Cell key={`bar-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

const styles = {
  centerMsg: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '60vh',
    fontSize: '1.2rem',
    color: '#064e3b',
    background: 'rgba(255, 255, 255, 0.85)',
    borderRadius: '16px',
    backdropFilter: 'blur(10px)',
    margin: '40px auto',
    maxWidth: '600px',
    boxShadow: '0 8px 32px rgba(16, 185, 129, 0.1)'
  },
  container: {
    minHeight: '100vh',
    background: 'var(--bg-main)', // Use global light green background
    width: '100vw',
    marginLeft: 'calc(-50vw + 50%)',
    padding: '40px 5vw',
    color: '#064e3b',
    fontFamily: "'Inter', sans-serif",
    boxSizing: 'border-box'
  },
  innerContainer: {
    maxWidth: '1400px', // Wide layout!
    padding: '0',
    margin: '0 auto',
  },
  header: {
    marginBottom: '30px'
  },
  title: {
    fontSize: '2.5rem',
    fontWeight: '800',
    margin: '0 0 10px 0',
    background: 'linear-gradient(90deg, #059669, #10b981)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent'
  },
  subtitle: {
    fontSize: '1.1rem',
    color: '#047857',
    margin: 0
  },
  mainGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 450px', // Right side is wider for charts
    gap: '32px',
    alignItems: 'start'
  },
  leftColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px'
  },
  rightColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px'
  },
  kpiGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '24px',
  },
  kpiCard: {
    background: 'rgba(255, 255, 255, 0.85)',
    border: '1px solid rgba(16, 185, 129, 0.2)',
    borderRadius: '20px',
    padding: '20px',
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    backdropFilter: 'blur(12px)',
    boxShadow: '0 4px 16px rgba(16, 185, 129, 0.08)',
    transition: 'transform 0.3s ease, box-shadow 0.3s ease',
    cursor: 'default'
  },
  kpiIcon: {
    fontSize: '2.5rem',
    background: 'rgba(16, 185, 129, 0.1)',
    width: '64px',
    height: '64px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '16px'
  },
  kpiLabel: {
    margin: '0 0 4px 0',
    fontSize: '0.9rem',
    color: '#047857',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  kpiValue: {
    margin: 0,
    fontSize: '2rem',
    fontWeight: '800',
    color: '#059669'
  },
  chartContainer: {
    background: 'rgba(255, 255, 255, 0.85)',
    border: '1px solid rgba(16, 185, 129, 0.2)',
    borderRadius: '20px',
    padding: '24px',
    height: '400px',
    backdropFilter: 'blur(12px)',
    boxShadow: '0 4px 16px rgba(16, 185, 129, 0.08)'
  },
  chartTitle: {
    margin: '0 0 20px 0',
    fontSize: '1.2rem',
    fontWeight: '700',
    color: '#064e3b'
  },
  tooltip: {
    background: 'rgba(255, 255, 255, 0.95)',
    border: '1px solid rgba(16, 185, 129, 0.2)',
    borderRadius: '12px',
    padding: '12px 16px',
    backdropFilter: 'blur(8px)',
    boxShadow: '0 4px 16px rgba(16, 185, 129, 0.15)'
  },
  tableContainer: {
    background: 'rgba(255, 255, 255, 0.85)',
    border: '1px solid rgba(16, 185, 129, 0.2)',
    borderRadius: '20px',
    padding: '24px',
    backdropFilter: 'blur(12px)',
    boxShadow: '0 4px 16px rgba(16, 185, 129, 0.08)',
    flexGrow: 1 // Fill remaining vertical space if needed
  },
  tableWrapper: {
    overflowX: 'auto'
  },
  table: {
    width: '100%',
    borderCollapse: 'separate',
    borderSpacing: '0 8px',
    textAlign: 'left'
  },
  th: {
    padding: '0 16px 12px 16px',
    color: '#047857',
    fontWeight: '600',
    textTransform: 'uppercase',
    fontSize: '0.85rem',
    letterSpacing: '1px',
    borderBottom: '2px solid rgba(16, 185, 129, 0.1)'
  },
  tr: {
    background: 'rgba(16, 185, 129, 0.02)',
    transition: 'background 0.2s ease',
  },
  td: {
    padding: '16px',
    borderTop: '1px solid rgba(16, 185, 129, 0.05)',
    borderBottom: '1px solid rgba(16, 185, 129, 0.05)',
  },
  userAvatar: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    background: 'linear-gradient(45deg, #10b981, #34d399)',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 'bold',
    marginRight: '12px',
    color: '#fff'
  },
  userName: {
    fontWeight: '600',
    color: '#064e3b'
  },
  badge: {
    padding: '6px 12px',
    borderRadius: '20px',
    fontSize: '0.85rem',
    fontWeight: '700',
    display: 'inline-block'
  }
};

export default AdminDashboard;

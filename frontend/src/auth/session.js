import axios from 'axios';

export async function exchangeFirebaseSession(user) {
  const idToken = await user.getIdToken(true);
  const { data } = await axios.post('/api/auth/firebase/exchange', { id_token: idToken });
  if (!data?.access_token) throw new Error('Máy chủ không trả về phiên đăng nhập.');
  localStorage.setItem('token', data.access_token);
  localStorage.setItem('user_name', data.full_name || user.displayName || user.email);
  localStorage.setItem('user_role', data.role || 'user');
  localStorage.setItem('user_email', user.email || '');
  window.dispatchEvent(new Event('riceai-auth-changed'));
  return data;
}

export function clearSession() {
  localStorage.removeItem('token');
  localStorage.removeItem('user_name');
  localStorage.removeItem('user_role');
  localStorage.removeItem('user_email');
  window.dispatchEvent(new Event('riceai-auth-changed'));
}

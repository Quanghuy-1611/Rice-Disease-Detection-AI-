import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

// Firebase web configuration is a public project identifier, shared with the Flutter app.
const firebaseConfig = {
  apiKey: 'AIzaSyAENvdfWebGZ2OnG8KhtHEjiPeCUfsQMoc',
  authDomain: 'riceai-production.firebaseapp.com',
  projectId: 'riceai-production',
  appId: '1:915835874142:web:c25b9af388dd385266fdcf',
};

export const auth = getAuth(initializeApp(firebaseConfig));

export function authErrorMessage(error) {
  const messages = {
    'auth/email-already-in-use': 'Email này đã được đăng ký.',
    'auth/invalid-email': 'Địa chỉ email không hợp lệ.',
    'auth/weak-password': 'Mật khẩu chưa đủ mạnh. Hãy dùng ít nhất 6 ký tự.',
    'auth/invalid-credential': 'Email hoặc mật khẩu không đúng.',
    'auth/user-not-found': 'Email hoặc mật khẩu không đúng.',
    'auth/wrong-password': 'Email hoặc mật khẩu không đúng.',
    'auth/too-many-requests': 'Bạn đã thử quá nhiều lần. Vui lòng chờ rồi thử lại.',
    'auth/network-request-failed': 'Không kết nối được Firebase. Hãy kiểm tra mạng.',
    'auth/operation-not-allowed': 'Đăng nhập email chưa được bật trong Firebase.',
    'auth/unauthorized-domain': 'Tên miền web chưa được cho phép trong Firebase.',
  };
  if (error?.code === 'ERR_NETWORK') return 'Không kết nối được máy chủ RiceAI. Hãy thử lại khi máy chủ hoạt động.';
  return messages[error?.code] || error?.response?.data?.detail || error?.message || 'Không thể xác thực. Vui lòng thử lại.';
}

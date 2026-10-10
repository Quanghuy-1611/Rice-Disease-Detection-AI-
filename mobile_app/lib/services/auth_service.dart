import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../core/network/api_client.dart';
import '../core/errors/api_exception.dart';

/// Xác thực bằng Firebase (email, Google hoặc khách), sau đó đổi Firebase ID
/// token lấy JWT của FastAPI. Email/mật khẩu bắt buộc xác minh email trước khi
/// được đổi token cho máy chủ.
class AuthService extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  bool _isLoading = false;
  bool _isAuthenticated = false;

  bool get isLoading => _isLoading;
  bool get isAuthenticated => _isAuthenticated;

  AuthService() {
    _restoreSession();
  }

  FirebaseAuth get _auth => FirebaseAuth.instance;

  Future<void> _restoreSession() async {
    try {
      final token = await _storage.read(key: 'jwt_token');
      final user = await _auth.authStateChanges().first;
      _isAuthenticated = token != null && user != null && user.emailVerified;
      if (!_isAuthenticated && token != null) {
        await _storage.delete(key: 'jwt_token');
      }
    } catch (error) {
      debugPrint('RiceAI session restore failed: $error');
      _isAuthenticated = false;
    }
    notifyListeners();
  }

  void _setLoading(bool value) {
    _isLoading = value;
    notifyListeners();
  }

  Future<void> signInWithEmail({
    required String email,
    required String password,
    required ValueChanged<String> onError,
    required VoidCallback onSuccess,
  }) async {
    _setLoading(true);
    try {
      final user = (await _auth.signInWithEmailAndPassword(
        email: email.trim(),
        password: password,
      ))
          .user;
      await _completeFirebaseSignIn(user);
      onSuccess();
    } on FirebaseAuthException catch (error) {
      await _clearFailedSignIn();
      onError(_firebaseErrorMessage(error));
    } on ApiException catch (error) {
      await _clearFailedSignIn();
      onError(error.message);
    } on StateError catch (error) {
      await _clearFailedSignIn();
      onError(error.message);
    } catch (error) {
      await _clearFailedSignIn();
      onError('Đăng nhập chưa hoàn tất. Vui lòng thử lại.');
    } finally {
      _setLoading(false);
    }
  }

  Future<void> registerWithEmail({
    required String fullName,
    required String email,
    required String password,
    required ValueChanged<String> onError,
    required VoidCallback onVerificationSent,
  }) async {
    _setLoading(true);
    try {
      final user = (await _auth.createUserWithEmailAndPassword(
        email: email.trim(),
        password: password,
      ))
          .user;
      if (user == null) throw StateError('Firebase không tạo được tài khoản.');
      await user.updateDisplayName(fullName.trim());
      await user.sendEmailVerification();
      await _auth.signOut();
      onVerificationSent();
    } on FirebaseAuthException catch (error) {
      await _auth.signOut();
      onError(_firebaseErrorMessage(error));
    } catch (error) {
      await _auth.signOut();
      onError('Không thể tạo tài khoản: $error');
    } finally {
      _setLoading(false);
    }
  }

  Future<void> sendPasswordReset({
    required String email,
    required ValueChanged<String> onError,
    required VoidCallback onSent,
  }) async {
    _setLoading(true);
    try {
      await _auth.sendPasswordResetEmail(email: email.trim());
      onSent();
    } on FirebaseAuthException catch (error) {
      if (error.code == 'user-not-found') {
        onSent();
      } else {
        onError(_firebaseErrorMessage(error));
      }
    } catch (error) {
      onError('Không gửi được thư đặt lại mật khẩu: $error');
    } finally {
      _setLoading(false);
    }
  }

  Future<void> resendVerificationEmail({
    required String email,
    required String password,
    required ValueChanged<String> onError,
    required ValueChanged<bool> onFinished,
  }) async {
    _setLoading(true);
    try {
      final user = (await _auth.signInWithEmailAndPassword(
        email: email.trim(),
        password: password,
      ))
          .user;
      if (user == null) throw StateError('Firebase không trả về tài khoản.');
      await user.reload();
      final verified = _auth.currentUser?.emailVerified ?? false;
      if (!verified) await _auth.currentUser!.sendEmailVerification();
      onFinished(verified);
    } on FirebaseAuthException catch (error) {
      onError(_firebaseErrorMessage(error));
    } catch (error) {
      onError('Không gửi được thư xác minh: $error');
    } finally {
      await _auth.signOut();
      _setLoading(false);
    }
  }

  Future<void> _clearFailedSignIn() async {
    await _auth.signOut();
    await _storage.delete(key: 'jwt_token');
    _isAuthenticated = false;
  }

  Future<void> signInWithGoogle({
    required ValueChanged<String> onError,
    required VoidCallback onSuccess,
  }) async {
    _setLoading(true);
    try {
      final account = await GoogleSignIn().signIn();
      if (account == null) return;
      final googleAuth = await account.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );
      final user = (await _auth.signInWithCredential(credential)).user;
      await _completeFirebaseSignIn(user);
      onSuccess();
    } on FirebaseAuthException catch (error) {
      onError(_firebaseErrorMessage(error));
    } catch (error) {
      debugPrint('RiceAI Google sign-in failed: $error');
      onError('Không thể đăng nhập Google. Hãy kiểm tra cấu hình Firebase.');
    } finally {
      _setLoading(false);
    }
  }

  Future<void> signInAsGuest({
    required ValueChanged<String> onError,
    required VoidCallback onSuccess,
  }) async {
    _setLoading(true);
    try {
      final user = (await _auth.signInAnonymously()).user;
      await _completeFirebaseSignIn(user, requireVerifiedEmail: false);
      onSuccess();
    } on FirebaseAuthException catch (error) {
      onError(_firebaseErrorMessage(error));
    } catch (error) {
      onError('Không thể mở chế độ dùng thử: $error');
    } finally {
      _setLoading(false);
    }
  }

  Future<void> _completeFirebaseSignIn(
    User? user, {
    bool requireVerifiedEmail = true,
  }) async {
    if (user == null) throw StateError('Firebase không trả về tài khoản.');
    await user.reload();
    user = _auth.currentUser;
    if (user == null) throw StateError('Phiên Firebase đã hết hạn.');
    if (requireVerifiedEmail && !user.emailVerified) {
      await _auth.signOut();
      throw StateError(
        'Email chưa được xác minh. Hãy mở email RiceAI và bấm liên kết xác minh, rồi đăng nhập lại.',
      );
    }

    try {
      final idToken = await user.getIdToken(true);
      if (idToken == null) throw StateError('Firebase không trả về ID token.');
      final response = await _apiClient.post(
        '/api/auth/firebase/exchange',
        data: <String, dynamic>{'id_token': idToken},
      );
      final accessToken =
          response is Map ? response['access_token']?.toString() : null;
      if (accessToken == null || accessToken.isEmpty) {
        throw StateError('Máy chủ không trả về phiên đăng nhập.');
      }
      await _storage.write(key: 'jwt_token', value: accessToken);
      _isAuthenticated = true;
    } catch (error) {
      _isAuthenticated = false;
      rethrow;
    }
  }

  Future<Map<String, dynamic>?> getProfile() async {
    if (!_isAuthenticated) return null;
    final response = await _apiClient.get('/api/auth/me');
    return response is Map<String, dynamic> ? response : null;
  }

  Future<Map<String, dynamic>> updateProfile({required String fullName}) async {
    final normalized = fullName.trim();
    if (normalized.length < 2) {
      throw ArgumentError('Tên hiển thị cần ít nhất 2 ký tự.');
    }
    final response = await _apiClient.put(
      '/api/auth/me',
      data: <String, dynamic>{'full_name': normalized},
    );
    if (response is Map<String, dynamic>) return response;
    throw StateError('Máy chủ trả về thông tin hồ sơ không hợp lệ.');
  }

  Future<void> logout() async {
    _setLoading(true);
    try {
      await _auth.signOut();
    } finally {
      await _storage.delete(key: 'jwt_token');
      _isAuthenticated = false;
      _setLoading(false);
    }
  }

  String _firebaseErrorMessage(FirebaseAuthException error) =>
      switch (error.code) {
        'invalid-email' => 'Email chưa đúng định dạng.',
        'user-not-found' ||
        'wrong-password' ||
        'invalid-credential' =>
          'Email hoặc mật khẩu chưa đúng.',
        'email-already-in-use' => 'Email này đã được đăng ký. Hãy đăng nhập.',
        'weak-password' => 'Mật khẩu cần có ít nhất 6 ký tự.',
        'operation-not-allowed' =>
          'Phương thức đăng nhập này chưa được bật trong Firebase.',
        'account-exists-with-different-credential' =>
          'Email này đã dùng phương thức đăng nhập khác.',
        'network-request-failed' =>
          'Không có kết nối đến Firebase. Hãy kiểm tra mạng.',
        'too-many-requests' =>
          'Bạn đã thử quá nhiều lần. Vui lòng đợi rồi thử lại.',
        _ => error.message ?? 'Firebase không thể xác thực (${error.code}).',
      };
}

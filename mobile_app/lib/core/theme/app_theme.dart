import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

abstract final class AppTheme {
  // ─────────────────────────────────────────────
  // DESIGN TOKENS – Warm Nature Tech
  // ─────────────────────────────────────────────

  /// Primary brand: Deep Moss Green
  static const Color moss = Color(0xFF173D2B);

  /// Darker shade for gradients
  static const Color mossDark = Color(0xFF0F2A1E);

  /// Mid moss used for secondary containers
  static const Color mossMid = Color(0xFF285A3D);

  /// Accent: Leaf Green – điểm nhấn sống động
  static const Color neonLeaf = Color(0xFF9ECF62);

  /// Accent bright variant
  static const Color leafBright = Color(0xFFAEEA72);

  /// Nền ứng dụng: Beige ấm Porcelain
  static const Color porcelain = Color(0xFFF7F4EB);

  /// Nền section nhẹ hơn
  static const Color beigeLight = Color(0xFFFBF9F4);

  /// Card: nền trắng ấm
  static const Color cardSolid = Color(0xFFFFFEFA);

  /// Card alt: kem nhẹ
  static const Color cardBeige = Color(0xFFF4F1E8);

  /// Border mảnh cho card
  static const Color borderMoss = Color(0x1A173D2B); // moss 10%
  static const Color borderBeige = Color(0xFFE8E2D0);

  // ─── TEXT ───────────────────────────────────
  /// Text chính: xanh rêu đậm (không dùng đen tuyệt đối)
  static const Color textPrimary = Color(0xFF1A3025);

  /// Text phụ
  static const Color textSecondary = Color(0xFF5C6B5A);

  /// Text nhạt
  static const Color textMuted = Color(0xFF9AAA95);

  // ─── STATUS ─────────────────────────────────
  static const Color safeGreen = Color(0xFF10B981);
  static const Color warningOrange = Color(0xFFF59E0B);
  static const Color dangerRed = Color(0xFFEF4444);
  static const Color errorRed = Color(0xFFDC2626);

  // ─────────────────────────────────────────────
  // THEME DATA
  // ─────────────────────────────────────────────
  static ThemeData get lightTheme {
    final ColorScheme scheme = ColorScheme.fromSeed(
      seedColor: moss,
      primary: moss,
      secondary: neonLeaf,
      surface: porcelain,
      error: errorRed,
      brightness: Brightness.light,
    );

    final TextTheme base = GoogleFonts.plusJakartaSansTextTheme().apply(
      bodyColor: textPrimary,
      displayColor: textPrimary,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: porcelain,
      textTheme: base,

      appBarTheme: AppBarTheme(
        backgroundColor: porcelain,
        foregroundColor: textPrimary,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        titleTextStyle: GoogleFonts.plusJakartaSans(
          fontSize: 17,
          fontWeight: FontWeight.w800,
          color: textPrimary,
        ),
        iconTheme: const IconThemeData(color: textPrimary, size: 22),
      ),

      // Bottom Navigation Bar
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: cardSolid,
        selectedItemColor: moss,
        unselectedItemColor: textMuted,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
        selectedLabelStyle: TextStyle(
          fontWeight: FontWeight.w700,
          fontSize: 11,
        ),
        unselectedLabelStyle: TextStyle(
          fontWeight: FontWeight.w600,
          fontSize: 11,
        ),
      ),

      // Card
      cardTheme: CardThemeData(
        elevation: 0,
        shadowColor: moss.withValues(alpha: 0.06),
        color: cardSolid,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: borderBeige, width: 1),
        ),
        margin: EdgeInsets.zero,
      ),

      // FilledButton (primary CTA)
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          elevation: 0,
          backgroundColor: moss,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
          textStyle: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.w700,
            fontSize: 15,
            letterSpacing: 0.2,
          ),
        ),
      ),

      // OutlinedButton (secondary CTA)
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: moss,
          side: const BorderSide(color: moss, width: 1.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
          textStyle: GoogleFonts.plusJakartaSans(
            fontWeight: FontWeight.w700,
            fontSize: 15,
          ),
        ),
      ),

      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: cardSolid,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: borderBeige),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: borderBeige),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: moss, width: 1.5),
        ),
      ),

      dividerTheme: const DividerThemeData(
        color: borderBeige,
        thickness: 1,
        space: 0,
      ),

      chipTheme: ChipThemeData(
        backgroundColor: cardBeige,
        selectedColor: moss,
        labelStyle: GoogleFonts.plusJakartaSans(
          fontWeight: FontWeight.w600,
          fontSize: 12,
          color: textSecondary,
        ),
        secondaryLabelStyle: GoogleFonts.plusJakartaSans(
          fontWeight: FontWeight.w700,
          fontSize: 12,
          color: Colors.white,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(100),
          side: const BorderSide(color: borderBeige),
        ),
        side: const BorderSide(color: borderBeige),
      ),
    );
  }
}

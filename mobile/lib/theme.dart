import 'package:flutter/material.dart';

/// Mugallym app-ynyň dizaýny: admin paneli bilen birmeňzeş sakin reňkler (ak/çal + indigo).
class C {
  static const primary = Color(0xFF4F46E5);
  static const primaryDark = Color(0xFF3730A3);
  static const primarySoft = Color(0xFFEEF2FF);
  static const bg = Color(0xFFF6F7F9);
  static const surface = Colors.white;
  static const border = Color(0xFFE4E7EC);
  static const text = Color(0xFF101828);
  static const muted = Color(0xFF667085);
  static const subtle = Color(0xFF98A2B3);
  static const success = Color(0xFF12B76A);
  static const warning = Color(0xFFF79009);
  static const danger = Color(0xFFF04438);

  static Color lesson(String type) => switch (type) {
        'lecture' => const Color(0xFF4F46E5),
        'lab' => const Color(0xFF0E9384),
        'seminar' => const Color(0xFFDC6803),
        _ => const Color(0xFF7A5AF8),
      };
}

ThemeData appTheme() {
  final scheme = ColorScheme.fromSeed(seedColor: C.primary, primary: C.primary, surface: C.surface, error: C.danger);
  final r10 = BorderRadius.circular(10);
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: C.bg,
    appBarTheme: const AppBarTheme(
      backgroundColor: C.surface,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      foregroundColor: C.text,
    ),
    dividerTheme: const DividerThemeData(color: C.border, space: 1, thickness: 1),
    cardTheme: CardThemeData(
      color: C.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: const BorderSide(color: C.border)),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: C.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      hintStyle: const TextStyle(color: C.subtle),
      border: OutlineInputBorder(borderRadius: r10),
      enabledBorder: OutlineInputBorder(borderRadius: r10, borderSide: const BorderSide(color: Color(0xFFD0D5DD))),
      focusedBorder: OutlineInputBorder(borderRadius: r10, borderSide: const BorderSide(color: C.primary, width: 1.6)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(50),
        shape: RoundedRectangleBorder(borderRadius: r10),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: C.surface,
      surfaceTintColor: Colors.transparent,
      indicatorColor: C.primarySoft,
      height: 64,
      labelTextStyle: WidgetStateProperty.resolveWith((s) => TextStyle(
            fontSize: 12,
            fontWeight: s.contains(WidgetState.selected) ? FontWeight.w600 : FontWeight.w500,
            color: s.contains(WidgetState.selected) ? C.primaryDark : C.muted,
          )),
      iconTheme: WidgetStateProperty.resolveWith(
          (s) => IconThemeData(color: s.contains(WidgetState.selected) ? C.primary : C.muted)),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: C.surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
    ),
    bottomSheetTheme: const BottomSheetThemeData(backgroundColor: C.surface, surfaceTintColor: Colors.transparent),
  );
}

/// Kiçi belgi (sapak görnüşi, hepde, rol).
class Tag extends StatelessWidget {
  const Tag(this.text, {super.key, this.color = C.muted});
  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(color: color.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(6)),
        child: Text(text, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color)),
      );
}

/// Boş ýa-da ýalňyş ýagdaý.
class EmptyView extends StatelessWidget {
  const EmptyView({super.key, required this.icon, required this.title, this.text});
  final IconData icon;
  final String title;
  final String? text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 56),
        child: Column(children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: C.primarySoft, borderRadius: BorderRadius.circular(14)),
            child: Icon(icon, color: C.primary, size: 28),
          ),
          const SizedBox(height: 14),
          Text(title, textAlign: TextAlign.center, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          if (text != null) ...[
            const SizedBox(height: 6),
            Text(text!, textAlign: TextAlign.center, style: const TextStyle(color: C.muted, height: 1.4)),
          ],
        ]),
      );
}

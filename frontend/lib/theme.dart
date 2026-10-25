import 'package:flutter/material.dart';

/// Programmanyň reňkleri we umumy görnüşi. Reňki üýtgetmek = diňe şu faýl.
class AppColors {
  static const primary = Color(0xFF3F51B5); // indigo
  static const secondary = Color(0xFF00A6A6); // teal
  static const accent = Color(0xFFFF7A59); // mämişi
  static const background = Color(0xFFF4F6FB);
  static const sidebarTop = Color(0xFF1E2A78);
  static const sidebarBottom = Color(0xFF0F6E7A);

  /// Menýu bölümleriniň we sahypa nyşanlarynyň reňkleri.
  static const schedule = Color(0xFF5C6BC0);
  static const structure = Color(0xFF26A69A);
  static const resources = Color(0xFFFFA726);
  static const study = Color(0xFFAB47BC);
  static const exams = Color(0xFFEF5350);

  /// Sapak görnüşleriniň reňkleri (raspisaniýe kartlary).
  static Color lesson(String type) => switch (type) {
    'lecture' => const Color(0xFF3F51B5),
    'lab' => const Color(0xFF00897B),
    'seminar' => const Color(0xFFF57C00),
    _ => const Color(0xFF8E24AA), // amaly
  };
}

ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    primary: AppColors.primary,
    secondary: AppColors.secondary,
    tertiary: AppColors.accent,
    surface: Colors.white,
  );
  final rounded = RoundedRectangleBorder(borderRadius: BorderRadius.circular(14));
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: AppColors.background,
    cardTheme: CardThemeData(
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: scheme.outlineVariant.withValues(alpha: 0.5)),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        shape: rounded,
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
        textStyle: const TextStyle(fontWeight: FontWeight.w600),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom(shape: rounded)),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      isDense: true,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: scheme.outlineVariant),
      ),
    ),
    chipTheme: ChipThemeData(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      selectedColor: scheme.primaryContainer,
      side: BorderSide(color: scheme.outlineVariant),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
    ),
    dataTableTheme: DataTableThemeData(
      headingRowColor: WidgetStatePropertyAll(scheme.primaryContainer.withValues(alpha: 0.6)),
      headingTextStyle: TextStyle(fontWeight: FontWeight.w700, color: scheme.onPrimaryContainer),
      dataRowColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.hovered) ? scheme.primaryContainer.withValues(alpha: 0.25) : null,
      ),
    ),
    segmentedButtonTheme: SegmentedButtonThemeData(
      style: SegmentedButton.styleFrom(selectedBackgroundColor: scheme.primaryContainer),
    ),
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
  );
}

/// Sahypanyň sözbaşy: reňkli nyşan, at we (bar bolsa) san.
class PageTitle extends StatelessWidget {
  const PageTitle({super.key, required this.title, required this.icon, required this.color, this.count});
  final String title;
  final IconData icon;
  final Color color;
  final int? count;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [color, Color.lerp(color, Colors.white, 0.35)!]),
            borderRadius: BorderRadius.circular(14),
            boxShadow: [BoxShadow(color: color.withValues(alpha: 0.35), blurRadius: 12, offset: const Offset(0, 4))],
          ),
          child: Icon(icon, color: Colors.white, size: 24),
        ),
        const SizedBox(width: 14),
        Text(title, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
        if (count != null) ...[
          const SizedBox(width: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
            decoration: BoxDecoration(color: color.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(20)),
            child: Text(
              '$count',
              style: TextStyle(color: color, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ],
    );
  }
}

/// Menýudaky bölüm: ady, reňki we oňa degişli sanawlar.
class NavSection {
  const NavSection(this.title, this.color, this.endpoints);
  final String title;
  final Color color;
  final List<String> endpoints;
}

const navSections = [
  NavSection('Gurluş', AppColors.structure, [
    'faculties',
    'departments',
    'specialties',
    'shifts',
    'groups',
    'subgroups',
  ]),
  NavSection('Resurslar', AppColors.resources, ['teachers', 'buildings', 'room-types', 'rooms']),
  NavSection('Okuw', AppColors.study, ['subjects', 'streams', 'curriculum']),
  NavSection('Synaglar', AppColors.exams, ['exam-sessions', 'exam-periods', 'exams']),
];

const resourceIcons = {
  'faculties': Icons.account_balance,
  'departments': Icons.apartment,
  'specialties': Icons.school,
  'shifts': Icons.schedule,
  'groups': Icons.groups,
  'subgroups': Icons.group_work,
  'teachers': Icons.person,
  'buildings': Icons.domain,
  'room-types': Icons.category,
  'rooms': Icons.meeting_room,
  'subjects': Icons.menu_book,
  'streams': Icons.merge_type,
  'curriculum': Icons.list_alt,
  'exam-sessions': Icons.event_note,
  'exam-periods': Icons.access_time,
  'exams': Icons.assignment,
};

Color sectionColor(String endpoint) =>
    navSections.firstWhere((s) => s.endpoints.contains(endpoint), orElse: () => navSections.first).color;

/// Setkanyň (raspisaniýe tablisasynyň) sözbaşy ýazgylary.
const gridHeadStyle = TextStyle(color: Colors.white, fontWeight: FontWeight.w700);

/// Sapak/synag kartasy: açyk reňkli fon, çepde galyň zolak we ýeňil kölege.
BoxDecoration lessonDecoration(Color color) => BoxDecoration(
  gradient: LinearGradient(colors: [color.withValues(alpha: 0.16), color.withValues(alpha: 0.05)]),
  border: Border(left: BorderSide(color: color, width: 4)),
  borderRadius: BorderRadius.circular(10),
  boxShadow: [BoxShadow(color: color.withValues(alpha: 0.12), blurRadius: 6, offset: const Offset(0, 2))],
);

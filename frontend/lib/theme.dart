import 'package:flutter/material.dart';

/// Programmanyň dizaýn ulgamy: reňkler, ýazgylar, umumy bölekler. Görnüşi üýtgetmek = diňe şu faýl.
/// Ýörelge: sakin bitarap fon (çal/ak), bir esasy reňk (indigo), inçe serhetler, aýdyň ýazgy derejeleri.
class AppColors {
  // Esasy
  static const primary = Color(0xFF4F46E5); // indigo-600
  static const primaryDark = Color(0xFF3730A3);
  static const primarySoft = Color(0xFFEEF2FF); // saýlanan menýu, nyşan fony
  static const secondary = Color(0xFF0E9384); // teal
  static const accent = Color(0xFFF97316); // mämişi (ünsi çekmek üçin seýrek)

  // Bitarap
  static const background = Color(0xFFF6F7F9);
  static const surface = Colors.white;
  static const border = Color(0xFFE4E7EC);
  static const borderStrong = Color(0xFFD0D5DD);
  static const text = Color(0xFF101828);
  static const textMuted = Color(0xFF667085);
  static const textSubtle = Color(0xFF98A2B3);
  static const tableHead = Color(0xFFF9FAFB);

  // Ýagdaý
  static const success = Color(0xFF12B76A);
  static const successSoft = Color(0xFFECFDF3);
  static const warning = Color(0xFFF79009);
  static const warningSoft = Color(0xFFFFFAEB);
  static const danger = Color(0xFFF04438);
  static const dangerSoft = Color(0xFFFEF3F2);

  // Köne atlar (sahypalar ulanýar) — täze reňklere baglanan.
  static const sidebarTop = Color(0xFF1D2939);
  static const sidebarBottom = Color(0xFF344054);
  static const gridHeader = Color(0xFF1D2939);

  /// Menýu bölümleriniň nyşan reňkleri (diňe kiçi nyşanlarda).
  static const schedule = Color(0xFF4F46E5);
  static const structure = Color(0xFF0E9384);
  static const resources = Color(0xFFDC6803);
  static const study = Color(0xFF7A5AF8);
  static const exams = Color(0xFFE31B54);

  /// Sapak görnüşleriniň reňkleri (raspisaniýe kartlary).
  static Color lesson(String type) => switch (type) {
        'lecture' => const Color(0xFF4F46E5),
        'lab' => const Color(0xFF0E9384),
        'seminar' => const Color(0xFFDC6803),
        _ => const Color(0xFF7A5AF8), // amaly
      };
}

ThemeData buildTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    primary: AppColors.primary,
    secondary: AppColors.secondary,
    tertiary: AppColors.accent,
    surface: AppColors.surface,
    error: AppColors.danger,
    outlineVariant: AppColors.border,
  );
  final radius8 = BorderRadius.circular(8);
  final base = ThemeData(useMaterial3: true, colorScheme: scheme);
  return base.copyWith(
    scaffoldBackgroundColor: AppColors.background,
    textTheme: base.textTheme
        .apply(bodyColor: AppColors.text, displayColor: AppColors.text)
        .copyWith(
          headlineSmall: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: AppColors.text),
          titleLarge: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.text),
          titleMedium: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.text),
          bodyMedium: const TextStyle(fontSize: 14, color: AppColors.text),
          bodySmall: const TextStyle(fontSize: 12.5, color: AppColors.textMuted),
        ),
    dividerTheme: const DividerThemeData(color: AppColors.border, thickness: 1, space: 1),
    cardTheme: CardThemeData(
      color: AppColors.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: AppColors.border),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        shape: RoundedRectangleBorder(borderRadius: radius8),
        minimumSize: const Size(0, 40),
        padding: const EdgeInsets.symmetric(horizontal: 16),
        textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        shape: RoundedRectangleBorder(borderRadius: radius8),
        minimumSize: const Size(0, 40),
        padding: const EdgeInsets.symmetric(horizontal: 14),
        foregroundColor: AppColors.text,
        side: const BorderSide(color: AppColors.borderStrong),
        textStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        shape: RoundedRectangleBorder(borderRadius: radius8),
        textStyle: const TextStyle(fontWeight: FontWeight.w600),
      ),
    ),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(foregroundColor: AppColors.textMuted, shape: RoundedRectangleBorder(borderRadius: radius8)),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface,
      isDense: true,
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      hintStyle: const TextStyle(color: AppColors.textSubtle),
      labelStyle: const TextStyle(color: AppColors.textMuted),
      border: OutlineInputBorder(borderRadius: radius8),
      enabledBorder: OutlineInputBorder(borderRadius: radius8, borderSide: const BorderSide(color: AppColors.borderStrong)),
      focusedBorder: OutlineInputBorder(borderRadius: radius8, borderSide: const BorderSide(color: AppColors.primary, width: 1.6)),
    ),
    chipTheme: ChipThemeData(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      selectedColor: AppColors.primarySoft,
      backgroundColor: AppColors.surface,
      side: const BorderSide(color: AppColors.border),
      labelStyle: const TextStyle(fontSize: 13, color: AppColors.text),
      showCheckmark: false,
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: AppColors.surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      titleTextStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppColors.text),
    ),
    popupMenuTheme: PopupMenuThemeData(
      color: AppColors.surface,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10), side: const BorderSide(color: AppColors.border)),
    ),
    dataTableTheme: DataTableThemeData(
      headingRowColor: const WidgetStatePropertyAll(AppColors.tableHead),
      headingRowHeight: 44,
      dataRowMinHeight: 52,
      dataRowMaxHeight: 64,
      dividerThickness: 1,
      headingTextStyle: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12.5, color: AppColors.textMuted),
      dataTextStyle: const TextStyle(fontSize: 14, color: AppColors.text),
      dataRowColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.hovered) ? AppColors.background : null,
      ),
    ),
    segmentedButtonTheme: SegmentedButtonThemeData(
      style: SegmentedButton.styleFrom(
        selectedBackgroundColor: AppColors.primarySoft,
        selectedForegroundColor: AppColors.primaryDark,
        side: const BorderSide(color: AppColors.borderStrong),
        shape: RoundedRectangleBorder(borderRadius: radius8),
      ),
    ),
    tooltipTheme: TooltipThemeData(
      decoration: BoxDecoration(color: AppColors.text, borderRadius: BorderRadius.circular(6)),
      textStyle: const TextStyle(color: Colors.white, fontSize: 12),
    ),
    snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? Colors.white : null),
      trackColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? AppColors.primary : null),
    ),
  );
}

// ---------------------------------------------------------------------------------------------
// Umumy bölekler
// ---------------------------------------------------------------------------------------------

/// Sahypanyň sözbaşy: nyşan, at, (bar bolsa) san we düşündiriş.
class PageTitle extends StatelessWidget {
  const PageTitle({super.key, required this.title, required this.icon, required this.color, this.count, this.subtitle});
  final String title;
  final IconData icon;
  final Color color;
  final int? count;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Container(
          padding: const EdgeInsets.all(9),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: color.withValues(alpha: 0.18)),
          ),
          child: Icon(icon, color: color, size: 22),
        ),
        const SizedBox(width: 14),
        // Flexible ýok: sözbaşy ölçegsiz (Row içindäki) ýerde hem ulanylýar.
        Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          Row(mainAxisSize: MainAxisSize.min, children: [
            Text(title, style: Theme.of(context).textTheme.headlineSmall),
            if (count != null) ...[
              const SizedBox(width: 10),
              CountBadge(count!),
            ],
          ]),
          if (subtitle != null)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text(subtitle!, style: Theme.of(context).textTheme.bodySmall),
            ),
        ]),
      ],
    );
  }
}

class CountBadge extends StatelessWidget {
  const CountBadge(this.count, {super.key});
  final int count;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: AppColors.background,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppColors.border),
        ),
        child: Text('$count', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textMuted)),
      );
}

/// Ýagdaý belgisi: "Çap edildi", "Taýýar", "Garaşýar" we ş.m.
class StatusPill extends StatelessWidget {
  const StatusPill(this.text, {super.key, this.color = AppColors.textMuted, this.icon});
  final String text;
  final Color color;
  final IconData? icon;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          if (icon != null) ...[Icon(icon, size: 13, color: color), const SizedBox(width: 4)],
          Text(text, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color)),
        ]),
      );
}

/// Boş ýagdaý: näme üçin boş we näme etmeli.
class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.title, this.text, this.action});
  final IconData icon;
  final String title;
  final String? text;
  final Widget? action;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(color: AppColors.primarySoft, borderRadius: BorderRadius.circular(14)),
                child: Icon(icon, size: 28, color: AppColors.primary),
              ),
              const SizedBox(height: 14),
              Text(title, textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleMedium),
              if (text != null) ...[
                const SizedBox(height: 6),
                Text(text!, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.textMuted)),
              ],
              if (action != null) ...[const SizedBox(height: 16), action!],
            ]),
          ),
        ),
      );
}

/// Sahypa düşündirişi (maglumat bloky): bu sahypa näme üçin, nädip ulanmaly.
class HelpNote extends StatelessWidget {
  const HelpNote(this.text, {super.key});
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: AppColors.primarySoft.withValues(alpha: 0.6),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppColors.primary.withValues(alpha: 0.12)),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.info_outline, size: 18, color: AppColors.primary),
          const SizedBox(width: 10),
          Expanded(child: Text(text, style: const TextStyle(fontSize: 13, color: AppColors.primaryDark, height: 1.4))),
        ]),
      );
}

/// Menýudaky bölüm: ady, reňki we oňa degişli sanawlar.
class NavSection {
  const NavSection(this.title, this.color, this.endpoints);
  final String title;
  final Color color;
  final List<String> endpoints;
}

/// Menýu işiň tertibine görä: gurluş -> adamlar we otaglar -> okuw meýilnamasy -> synaglar.
const navSections = [
  NavSection('Gurluş', AppColors.structure, ['faculties', 'departments', 'specialties', 'groups', 'subgroups']),
  NavSection('Mugallymlar we otaglar', AppColors.resources, ['teachers', 'buildings', 'room-types', 'rooms']),
  NavSection('Okuw meýilnamasy', AppColors.study, ['shifts', 'subjects', 'streams', 'curriculum']),
  NavSection('Synaglar', AppColors.exams, ['exam-sessions', 'exam-periods', 'exams']),
];

const resourceIcons = {
  'faculties': Icons.account_balance_outlined,
  'departments': Icons.apartment_outlined,
  'specialties': Icons.school_outlined,
  'shifts': Icons.schedule_outlined,
  'groups': Icons.groups_outlined,
  'subgroups': Icons.group_work_outlined,
  'teachers': Icons.person_outline,
  'buildings': Icons.domain_outlined,
  'room-types': Icons.category_outlined,
  'rooms': Icons.meeting_room_outlined,
  'subjects': Icons.menu_book_outlined,
  'streams': Icons.merge_type,
  'curriculum': Icons.list_alt_outlined,
  'exam-sessions': Icons.event_note_outlined,
  'exam-periods': Icons.access_time,
  'exams': Icons.assignment_outlined,
};

Color sectionColor(String endpoint) =>
    navSections.firstWhere((s) => s.endpoints.contains(endpoint), orElse: () => navSections.first).color;

/// Setkanyň (raspisaniýe tablisasynyň) sözbaşy ýazgylary.
const gridHeadStyle = TextStyle(color: Colors.white, fontWeight: FontWeight.w600, fontSize: 13);

/// Sapak/synag kartasy: açyk fon, çepde reňkli zolak.
BoxDecoration lessonDecoration(Color color) => BoxDecoration(
      color: Color.lerp(Colors.white, color, 0.07),
      border: Border(left: BorderSide(color: color, width: 3)),
      borderRadius: BorderRadius.circular(8),
    );

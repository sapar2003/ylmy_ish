import 'package:flutter/material.dart';

import 'pages/crud_page.dart';
import 'pages/exam_page.dart';
import 'pages/timetable_page.dart';
import 'resources.dart';
import 'theme.dart';

void main() => runApp(const RaspisaniyeApp());

class RaspisaniyeApp extends StatelessWidget {
  const RaspisaniyeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Raspisaniýe',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _index = 0; // 0 = raspisaniýe, 1 = synag raspisaniýesi, 2.. = sanawlar
  static const _pages = 2;

  @override
  Widget build(BuildContext context) {
    final page = switch (_index) {
      0 => const TimetablePage(),
      1 => const ExamPage(),
      _ => CrudPage(spec: resources[_index - _pages]),
    };
    return Scaffold(
      body: Row(
        children: [
          Container(
            width: 250,
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [AppColors.sidebarTop, AppColors.sidebarBottom],
              ),
            ),
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                _header(),
                _sectionTitle('Raspisaniýe', AppColors.schedule),
                _navItem(0, Icons.calendar_view_week, 'Raspisaniýe', AppColors.schedule),
                _navItem(1, Icons.fact_check, 'Synag raspisaniýesi', AppColors.exams),
                for (final s in navSections) ...[
                  _sectionTitle(s.title, s.color),
                  for (final (i, r) in resources.indexed)
                    if (s.endpoints.contains(r.endpoint))
                      _navItem(i + _pages, resourceIcons[r.endpoint] ?? Icons.list, r.title, s.color),
                ],
                const SizedBox(height: 16),
              ],
            ),
          ),
          Expanded(
            child: KeyedSubtree(key: ValueKey(_index), child: page),
          ),
        ],
      ),
    );
  }

  Widget _header() => Padding(
    padding: const EdgeInsets.fromLTRB(4, 24, 4, 12),
    child: Row(
      children: [
        Container(
          padding: const EdgeInsets.all(9),
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [AppColors.accent, Color(0xFFFFB74D)]),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(Icons.event_available, color: Colors.white),
        ),
        const SizedBox(width: 12),
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Raspisaniýe',
                style: TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w800),
              ),
              Text(
                'Halkara nebit we gaz uniwersiteti',
                style: TextStyle(color: Colors.white70, fontSize: 11),
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ],
    ),
  );

  Widget _sectionTitle(String title, Color color) => Padding(
    padding: const EdgeInsets.fromLTRB(8, 18, 8, 6),
    child: Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 8),
        Text(
          title.toUpperCase(),
          style: const TextStyle(color: Colors.white60, fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 1.2),
        ),
      ],
    ),
  );

  Widget _navItem(int index, IconData icon, String label, Color color) {
    final selected = _index == index;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Material(
        color: selected ? Colors.white : Colors.transparent,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          hoverColor: Colors.white.withValues(alpha: 0.1),
          onTap: () => setState(() => _index = index),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(5),
                  decoration: BoxDecoration(
                    color: selected ? color : color.withValues(alpha: 0.85),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(icon, size: 16, color: Colors.white),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    label,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: selected ? AppColors.sidebarTop : Colors.white,
                      fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                      fontSize: 13.5,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

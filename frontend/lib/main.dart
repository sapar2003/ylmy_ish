import 'package:flutter/material.dart';

import 'pages/crud_page.dart';
import 'pages/timetable_page.dart';
import 'resources.dart';

void main() => runApp(const RaspisaniyeApp());

class RaspisaniyeApp extends StatelessWidget {
  const RaspisaniyeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Raspisaniýe',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: const Color(0xFF1B6E4F), useMaterial3: true),
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
  int _index = 0; // 0 = raspisaniýe, 1.. = sanawlar

  static const _icons = {
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
  };

  @override
  Widget build(BuildContext context) {
    final page = _index == 0 ? const TimetablePage() : CrudPage(spec: resources[_index - 1]);
    return Scaffold(
      body: Row(children: [
        SizedBox(
          width: 230,
          child: Material(
            color: Theme.of(context).colorScheme.surfaceContainerLow,
            child: ListView(children: [
              const Padding(
                padding: EdgeInsets.fromLTRB(16, 20, 16, 12),
                child: Text('Raspisaniýe', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
              ),
              _navItem(0, Icons.calendar_view_week, 'Raspisaniýe'),
              const Divider(),
              for (final (i, r) in resources.indexed) _navItem(i + 1, _icons[r.endpoint] ?? Icons.list, r.title),
            ]),
          ),
        ),
        const VerticalDivider(width: 1),
        Expanded(child: KeyedSubtree(key: ValueKey(_index), child: page)),
      ]),
    );
  }

  Widget _navItem(int index, IconData icon, String label) => ListTile(
        dense: true,
        selected: _index == index,
        leading: Icon(icon),
        title: Text(label),
        onTap: () => setState(() => _index = index),
      );
}

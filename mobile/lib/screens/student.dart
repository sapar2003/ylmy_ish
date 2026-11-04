import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';

/// Talyp girişsiz: fakultetini we toparyny (kiçi topary bar bolsa — ony hem) saýlaýar.
/// Saýlaw telefonda ýatda saklanýar; "Topary çalyş" bilen üýtgedip bolýar.
class StudentPickScreen extends StatefulWidget {
  const StudentPickScreen({super.key, required this.server});
  final String server;

  @override
  State<StudentPickScreen> createState() => _StudentPickScreenState();
}

class _StudentPickScreenState extends State<StudentPickScreen> {
  List<Map<String, dynamic>>? _groups;
  String? _error;
  String _query = '';
  String? _faculty;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final g = await Api.instance.publicGroups(widget.server);
      if (mounted) setState(() => _groups = g);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  Future<void> _pick(Map<String, dynamic> g) async {
    final subs = (g['subgroups'] as List).cast<Map<String, dynamic>>();
    Map<String, dynamic>? sub;
    if (subs.isNotEmpty) {
      final r = await showModalBottomSheet<Map<String, dynamic>>(
        context: context,
        showDragHandle: true,
        builder: (c) => SafeArea(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
              child: Text('${g['name']}: kiçi toparyňyz', style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
            ),
            const Padding(
              padding: EdgeInsets.fromLTRB(20, 0, 20, 8),
              child: Text('Tejribe sapaklary kiçi toparlar boýunça aýratyn geçýär.', style: TextStyle(color: C.muted)),
            ),
            for (final s in subs)
              ListTile(
                leading: const Icon(Icons.group_outlined),
                title: Text('${s['name']}-nji kiçi topar'),
                onTap: () => Navigator.pop(c, s),
              ),
            ListTile(
              leading: const Icon(Icons.groups_outlined),
              title: const Text('Bilemok — ähli sapaklary görkez'),
              onTap: () => Navigator.pop(c, <String, dynamic>{}),
            ),
          ]),
        ),
      );
      if (r == null) return;
      sub = r.isEmpty ? null : r;
    }
    await Api.instance.enterStudent({
      'group_id': g['id'],
      'group': g['name'],
      'faculty': g['faculty'],
      'subgroup_id': sub?['id'],
      'subgroup': sub?['name'],
    });
    if (mounted) Navigator.of(context).popUntil((r) => r.isFirst);
  }

  @override
  Widget build(BuildContext context) {
    final groups = _groups;
    final faculties = {for (final g in groups ?? []) g['faculty'] as String?}.whereType<String>().toList()..sort();
    final q = _query.toLowerCase();
    final shown = (groups ?? [])
        .where((g) => (_faculty == null || g['faculty'] == _faculty) && '${g['name']}'.toLowerCase().contains(q))
        .toList();
    final byCourse = <int, List<Map<String, dynamic>>>{};
    for (final g in shown) {
      byCourse.putIfAbsent(g['course'] as int, () => []).add(g);
    }
    return Scaffold(
      appBar: AppBar(title: const Text('Toparyňy saýla')),
      body: groups == null
          ? (_error != null
              ? EmptyView(icon: Icons.wifi_off, title: 'Birikip bolmady', text: _error)
              : const Center(child: CircularProgressIndicator()))
          : ListView(padding: const EdgeInsets.fromLTRB(16, 8, 16, 24), children: [
              TextField(
                decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Topar gözle, meselem: 2 MH'),
                onChanged: (v) => setState(() => _query = v),
              ),
              if (faculties.length > 1) ...[
                const SizedBox(height: 12),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  ChoiceChip(label: const Text('Hemmesi'), selected: _faculty == null,
                      onSelected: (_) => setState(() => _faculty = null)),
                  for (final f in faculties)
                    ChoiceChip(label: Text(f), selected: _faculty == f, onSelected: (_) => setState(() => _faculty = f)),
                ]),
              ],
              if (shown.isEmpty) const EmptyView(icon: Icons.search_off, title: 'Topar tapylmady'),
              for (final course in byCourse.keys.toList()..sort()) ...[
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 20, 4, 8),
                  child: Text('$course-nji kurs'.toUpperCase(),
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: C.subtle, letterSpacing: 0.5)),
                ),
                Card(
                  child: Column(children: [
                    for (final (i, g) in byCourse[course]!.indexed) ...[
                      if (i > 0) const Divider(),
                      ListTile(
                        title: Text('${g['name']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                        subtitle: g['faculty'] == null ? null : Text('${g['faculty']}'),
                        trailing: const Icon(Icons.chevron_right, color: C.subtle),
                        onTap: () => _pick(g),
                      ),
                    ],
                  ]),
                ),
              ],
            ]),
    );
  }
}

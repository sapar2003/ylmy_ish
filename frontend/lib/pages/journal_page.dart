import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';
import 'dialogs.dart';
import 'journal_gradebook.dart';

/// Žurnal: çepde topar we dersler, sagda talyplar × sapak günleri. Öýjüge basyp baha goýulýar ýa-da düzedilýär.
class JournalPage extends StatefulWidget {
  const JournalPage({super.key});

  @override
  State<JournalPage> createState() => _JournalPageState();
}

class _JournalPageState extends State<JournalPage> {
  List<Map<String, dynamic>> _groups = [];
  List<Map<String, dynamic>> _courses = [];
  int? _groupId;
  int? _assignmentId;
  Map<String, dynamic>? _book;
  bool _loadingCourses = false;
  bool _loadingBook = false;
  String _courseQuery = '';

  @override
  void initState() {
    super.initState();
    Api.instance.list('groups').then((g) {
      if (!mounted) return;
      g.sort((a, b) => '${a['name']}'.compareTo('${b['name']}'));
      setState(() => _groups = g);
      if (g.isNotEmpty) _pickGroup(g.first['id'] as int);
    }).catchError((e) {
      if (mounted && e is ApiException) showError(context, e.message);
    });
  }

  Future<void> _pickGroup(int? id) async {
    setState(() {
      _groupId = id;
      _courses = [];
      _assignmentId = null;
      _book = null;
      _loadingCourses = id != null;
    });
    if (id == null) return;
    try {
      final c = (await Api.instance.get('journal/courses', {'group_id': id}) as List).cast<Map<String, dynamic>>();
      if (!mounted || _groupId != id) return;
      setState(() {
        _courses = c;
        _loadingCourses = false;
      });
      if (c.isNotEmpty) _pickCourse(c.first['assignment_id'] as int);
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _loadingCourses = false);
        showError(context, e.message);
      }
    }
  }

  Future<void> _pickCourse(int id) async {
    setState(() {
      _assignmentId = id;
      _loadingBook = true;
    });
    try {
      final b = await Api.instance.get('journal/$id') as Map<String, dynamic>;
      if (mounted && _assignmentId == id) setState(() => _book = b);
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    } finally {
      if (mounted && _assignmentId == id) setState(() => _loadingBook = false);
    }
  }

  Future<void> _demo() async {
    if (!await confirm(context, 'Talyby ýok ähli toparlara synag talyplary (türkmen atlary bilen) döredilsinmi? '
        'Soň "Talyplar" sahypasynda üýtgedip ýa-da hakyky sanaw bilen çalşyp bilersiňiz.')) {
      return;
    }
    try {
      final r = await Api.instance.post('students/demo', {}) as Map<String, dynamic>;
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${r['created']} talyp döredildi.')));
      if (_assignmentId != null) _pickCourse(_assignmentId!);
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  /// Bahany serwere ýazýar we tablisany täzeden ýüklemän şol öýjügi üýtgedýär.
  Future<void> _setMark(Map<String, dynamic> row, int col, String? value) async {
    final book = _book!;
    final column = (book['columns'] as List)[col] as Map<String, dynamic>;
    try {
      await Api.instance.put('journal/$_assignmentId', {
        'student_id': row['student']['id'],
        'day': column['day'],
        'time_slot_id': column['time_slot_id'],
        'value': value,
      });
      if (!mounted) return;
      setState(() {
        final marks = row['marks'] as List;
        marks[col] = value;
        final nums = [for (final m in marks) if (m != null && m != 'gm') int.parse('$m')];
        row['average'] = nums.isEmpty ? null : double.parse((nums.reduce((a, b) => a + b) / nums.length).toStringAsFixed(2));
        row['absent'] = marks.where((m) => m == 'gm').length;
      });
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(28, 24, 28, 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const PageTitle(
            title: 'Žurnal',
            icon: Icons.grading_outlined,
            color: AppColors.secondary,
            subtitle: 'Gündelik bahalar: 5, 4, 3, 2 we gm (gatnaşmady)',
          ),
          const SizedBox(width: 8),
          const Tooltip(
            message: 'Mugallym bahany telefonda sapakdan soň 3 günüň dowamynda goýup bilýär.\n'
                'Möhlet geçenden soň şu ýerden düzedip bolýar: öýjüge basyň. Her üýtgeşme ýazylýar.',
            child: Icon(Icons.info_outline, size: 20, color: AppColors.textSubtle),
          ),
        ]),
        const SizedBox(height: 16),
        Expanded(
          child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            SizedBox(width: 300, child: _sidebar()),
            const SizedBox(width: 16),
            Expanded(child: _content()),
          ]),
        ),
      ]),
    );
  }

  Widget _sidebar() {
    final q = _courseQuery.toLowerCase();
    final shown = _courses
        .where((c) => q.isEmpty || '${c['subject']} ${c['teacher']}'.toLowerCase().contains(q))
        .toList();
    final subjects = <String, List<Map<String, dynamic>>>{};
    for (final c in shown) {
      subjects.putIfAbsent('${c['subject']}', () => []).add(c);
    }
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
          child: Column(children: [
            DropdownButtonFormField<int>(
              key: ValueKey(_groups.length),
              initialValue: _groupId,
              isExpanded: true,
              menuMaxHeight: 420,
              decoration: const InputDecoration(labelText: 'Topar', isDense: true),
              items: [for (final g in _groups) DropdownMenuItem(value: g['id'] as int, child: Text('${g['name']}'))],
              onChanged: _pickGroup,
            ),
            const SizedBox(height: 8),
            TextField(
              decoration: const InputDecoration(prefixIcon: Icon(Icons.search, size: 20), hintText: 'Ders ýa-da mugallym', isDense: true),
              onChanged: (v) => setState(() => _courseQuery = v),
            ),
          ]),
        ),
        const Divider(height: 1),
        Expanded(
          child: _loadingCourses
              ? const Center(child: CircularProgressIndicator())
              : _courses.isEmpty
                  ? const Padding(
                      padding: EdgeInsets.all(16),
                      child: Text('Bu toparyň çap edilen raspisaniýede sapagy ýok.', style: TextStyle(color: AppColors.textMuted)),
                    )
                  : ListView(padding: const EdgeInsets.symmetric(vertical: 6), children: [
                      for (final e in subjects.entries) ...[
                        Padding(
                          padding: const EdgeInsets.fromLTRB(14, 10, 14, 4),
                          child: Text(e.key, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
                        ),
                        for (final c in e.value) _courseTile(c),
                      ],
                    ]),
        ),
      ]),
    );
  }

  Widget _courseTile(Map<String, dynamic> c) {
    final selected = _assignmentId == c['assignment_id'];
    final sub = c['subgroup'] != null ? ' · ${c['subgroup']}-nji kiçi topar' : '';
    return Material(
      color: selected ? AppColors.primarySoft : Colors.transparent,
      child: InkWell(
        onTap: () => _pickCourse(c['assignment_id'] as int),
        child: Container(
          padding: const EdgeInsets.fromLTRB(14, 7, 12, 7),
          decoration: BoxDecoration(
            border: Border(left: BorderSide(color: selected ? AppColors.primary : Colors.transparent, width: 3)),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${lessonTypeShort(c['lesson_type'])}$sub',
                style: TextStyle(fontSize: 13, fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                    color: selected ? AppColors.primaryDark : AppColors.text)),
            const SizedBox(height: 1),
            Text('${c['teacher']}', overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
          ]),
        ),
      ),
    );
  }

  Widget _content() {
    if (_book == null) {
      if (_loadingBook || _loadingCourses) return const Center(child: CircularProgressIndicator());
      return Card(
        child: EmptyState(
          icon: Icons.grading_outlined,
          title: _groups.isEmpty ? 'Topar ýok' : 'Dersi saýlaň',
          text: 'Žurnal diňe "Mugallymlara çap et" edilen raspisaniýe boýunça görkezilýär.',
        ),
      );
    }
    return Stack(children: [
      Positioned.fill(
        child: JournalGradebook(
          key: ValueKey(_book!['assignment_id']),
          book: _book!,
          onSetMark: _setMark,
          onCreateDemo: Api.instance.isDean ? null : _demo,
        ),
      ),
      if (_loadingBook) const Positioned(left: 0, right: 0, top: 0, child: LinearProgressIndicator(minHeight: 2)),
    ]);
  }
}

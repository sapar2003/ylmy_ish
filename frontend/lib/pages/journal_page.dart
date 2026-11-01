import 'package:flutter/material.dart';

import '../api.dart';
import '../resources.dart';
import '../theme.dart';
import 'dialogs.dart';

const markValues = ['5', '4', '3', '2', 'gm'];

Color markColor(String? v) => switch (v) {
      '5' => AppColors.success,
      '4' => AppColors.secondary,
      '3' => AppColors.warning,
      '2' => AppColors.danger,
      'gm' => AppColors.textMuted,
      _ => AppColors.textSubtle,
    };

/// Žurnal: topar → ders → talyplar × sapak günleri. Okuw bölümi islendik bahany goýup/düzedip bilýär.
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
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    Api.instance.list('groups').then((g) {
      if (!mounted) return;
      g.sort((a, b) => '${a['name']}'.compareTo('${b['name']}'));
      setState(() => _groups = g);
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
    });
    if (id == null) return;
    try {
      final c = (await Api.instance.get('journal/courses', {'group_id': id}) as List).cast<Map<String, dynamic>>();
      if (mounted) setState(() => _courses = c);
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  Future<void> _pickCourse(int id) async {
    setState(() {
      _assignmentId = id;
      _loading = true;
    });
    try {
      final b = await Api.instance.get('journal/$id') as Map<String, dynamic>;
      if (mounted && _assignmentId == id) setState(() => _book = b);
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
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

  Future<void> _edit(Map<String, dynamic> row, int col) async {
    final column = (_book!['columns'] as List)[col] as Map<String, dynamic>;
    final current = (row['marks'] as List)[col] as String?;
    final v = await showDialog<String>(
      context: context,
      builder: (c) => SimpleDialog(
        title: Text('${row['student']['name']}\n${column['day']} · ${column['starts_at']}',
            style: const TextStyle(fontSize: 16)),
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Wrap(spacing: 8, runSpacing: 8, children: [
              for (final m in markValues)
                ChoiceChip(
                  label: Text(m, style: TextStyle(fontWeight: FontWeight.w700, color: markColor(m))),
                  selected: current == m,
                  onSelected: (_) => Navigator.pop(c, m),
                ),
              ActionChip(label: const Text('Aýyr'), onPressed: () => Navigator.pop(c, '')),
            ]),
          ),
        ],
      ),
    );
    if (v == null || (v.isEmpty && current == null) || v == current) return;
    try {
      await Api.instance.put('journal/$_assignmentId', {
        'student_id': row['student']['id'],
        'day': column['day'],
        'time_slot_id': column['time_slot_id'],
        'value': v.isEmpty ? null : v,
      });
      await _pickCourse(_assignmentId!);
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
          const Spacer(),
          OutlinedButton.icon(onPressed: _demo, icon: const Icon(Icons.person_add_alt), label: const Text('Synag talyplary')),
        ]),
        const SizedBox(height: 16),
        const HelpNote('Mugallym bahany telefonda sapakdan soň 3 günüň dowamynda goýup bilýär. '
            'Möhlet geçenden soň diňe şu ýerden (okuw bölümi) düzedip bolýar — öýjüge basyň. Her üýtgeşme ýazylýar.'),
        const SizedBox(height: 16),
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(
            width: 220,
            child: DropdownButtonFormField<int>(
              initialValue: _groupId,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Topar', isDense: true),
              items: [for (final g in _groups) DropdownMenuItem(value: g['id'] as int, child: Text('${g['name']}'))],
              onChanged: _pickGroup,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: _groupId == null
                ? const SizedBox.shrink()
                : _courses.isEmpty
                    ? const Padding(
                        padding: EdgeInsets.only(top: 10),
                        child: Text('Bu toparyň çap edilen raspisaniýede sapagy ýok.',
                            style: TextStyle(color: AppColors.textMuted)),
                      )
                    : Wrap(spacing: 8, runSpacing: 8, children: [
                        for (final c in _courses)
                          ChoiceChip(
                            selected: _assignmentId == c['assignment_id'],
                            onSelected: (_) => _pickCourse(c['assignment_id'] as int),
                            label: Text('${c['subject']} · ${lessonTypeShort(c['lesson_type'])}'
                                '${c['subgroup'] != null ? ' · ${c['subgroup']}-nji kiçi topar' : ''}'),
                            tooltip: '${c['teacher']}',
                          ),
                      ]),
          ),
        ]),
        const SizedBox(height: 16),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _book == null
                  ? const EmptyState(
                      icon: Icons.grading_outlined,
                      title: 'Topary we dersi saýlaň',
                      text: 'Žurnal diňe "Mugallymlara çap et" edilen raspisaniýe boýunça görkezilýär.',
                    )
                  : _Gradebook(book: _book!, onTap: _edit),
        ),
      ]),
    );
  }
}

String lessonTypeShort(dynamic t) => lessonTypes['$t'] ?? '$t';

class _Gradebook extends StatelessWidget {
  const _Gradebook({required this.book, required this.onTap});
  final Map<String, dynamic> book;
  final void Function(Map<String, dynamic> row, int col) onTap;

  static const _rowH = 36.0;
  static const _cellW = 46.0;

  @override
  Widget build(BuildContext context) {
    final cols = (book['columns'] as List).cast<Map<String, dynamic>>();
    final rows = (book['rows'] as List).cast<Map<String, dynamic>>();
    if (rows.isEmpty) {
      return const EmptyState(
        icon: Icons.people_outline,
        title: 'Talyp ýok',
        text: '"Synag talyplary" düwmesi bilen döredip ýa-da "Talyplar" sahypasyndan goşup bilersiňiz.',
      );
    }
    const head = TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textMuted);
    Widget cell(Widget child, {double w = _cellW, Color? bg}) => Container(
          width: w,
          height: _rowH,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: bg,
            border: const Border(
                right: BorderSide(color: AppColors.border), bottom: BorderSide(color: AppColors.border)),
          ),
          child: child,
        );
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
          child: Text(
            '${book['subject']} · ${lessonTypeShort(book['lesson_type'])} · ${(book['groups'] as List).join(', ')}'
            '${book['subgroup'] != null ? ' (${book['subgroup']}-nji kiçi topar)' : ''} · ${book['teacher']}',
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
        const Divider(height: 1),
        Expanded(
          child: SingleChildScrollView(
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              // Talyplaryň atlary (çepde gozganmaýar).
              Column(children: [
                cell(const Text('Talyp', style: head), w: 260, bg: AppColors.tableHead),
                for (final (i, r) in rows.indexed)
                  cell(
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 10),
                      child: Row(children: [
                        SizedBox(width: 26, child: Text('${i + 1}', style: const TextStyle(color: AppColors.textSubtle))),
                        Expanded(child: Text('${r['student']['name']}', overflow: TextOverflow.ellipsis)),
                        if ((book['groups'] as List).length > 1)
                          Text('${r['group']}', style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                      ]),
                    ),
                    w: 260,
                  ),
              ]),
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Column(children: [
                    Row(children: [
                      for (final c in cols)
                        Tooltip(
                          message: '${c['day']} · ${c['starts_at']}',
                          child: cell(Text(_short('${c['day']}'), style: head), bg: AppColors.tableHead),
                        ),
                      cell(const Text('Ort.', style: head), w: 56, bg: AppColors.tableHead),
                      cell(const Text('gm', style: head), w: 46, bg: AppColors.tableHead),
                    ]),
                    for (final r in rows)
                      Row(children: [
                        for (final (j, v) in (r['marks'] as List).indexed)
                          InkWell(
                            onTap: () => onTap(r, j),
                            child: cell(Text(v == null ? '' : '$v',
                                style: TextStyle(fontWeight: FontWeight.w700, color: markColor(v as String?)))),
                          ),
                        cell(Text(r['average'] == null ? '—' : '${r['average']}',
                            style: const TextStyle(fontWeight: FontWeight.w600)), w: 56, bg: AppColors.tableHead),
                        cell(Text('${r['absent']}'), w: 46, bg: AppColors.tableHead),
                      ]),
                  ]),
                ),
              ),
            ]),
          ),
        ),
      ]),
    );
  }

  /// 2026-09-14 → 14.09
  static String _short(String iso) => iso.length >= 10 ? '${iso.substring(8, 10)}.${iso.substring(5, 7)}' : iso;
}

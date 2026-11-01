import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';
import 'home.dart' show lessonTypes, longDate, months;

const markValues = ['5', '4', '3', '2', 'gm'];

Color markColor(String? v) => switch (v) {
      '5' => C.success,
      '4' => const Color(0xFF0E9384),
      '3' => C.warning,
      '2' => C.danger,
      _ => C.muted,
    };

// ---------------------------------------------------------------------------------------------
// Sapaga baha goýmak: talyplaryň sanawy, her talyba 5/4/3/2/gm
// ---------------------------------------------------------------------------------------------

class LessonMarksScreen extends StatefulWidget {
  const LessonMarksScreen({super.key, required this.entry, required this.day});
  final Map<String, dynamic> entry;
  final DateTime day;

  @override
  State<LessonMarksScreen> createState() => _LessonMarksScreenState();
}

class _LessonMarksScreenState extends State<LessonMarksScreen> {
  Map<String, dynamic>? _lesson;
  final Map<int, String?> _marks = {}; // häzirki saýlanan bahalar
  final Map<int, String?> _saved = {}; // serwerdäki bahalar
  String? _error;
  bool _saving = false;

  bool get _dirty => _marks.entries.any((e) => _saved[e.key] != e.value);

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _apply(Map<String, dynamic> lesson) {
    _lesson = lesson;
    _marks.clear();
    _saved.clear();
    for (final s in (lesson['students'] as List)) {
      _marks[s['id'] as int] = s['mark'] as String?;
      _saved[s['id'] as int] = s['mark'] as String?;
    }
  }

  Future<void> _load() async {
    try {
      final l = await Api.instance.lesson(widget.entry['id'] as int, widget.day);
      if (mounted) setState(() => _apply(l));
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  Future<void> _save() async {
    final changed = {for (final e in _marks.entries) if (_saved[e.key] != e.value) e.key: e.value};
    setState(() => _saving = true);
    try {
      final l = await Api.instance.saveLesson(widget.entry['id'] as int, widget.day, changed);
      if (!mounted) return;
      setState(() => _apply(l));
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Bahalar ýatda saklandy.')));
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message), backgroundColor: C.danger));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<bool> _confirmLeave() async {
    if (!_dirty) return true;
    final r = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Bahalar ýatda saklanmady'),
        content: const Text('Üýtgeşmeler ýitsinmi?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Yza')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Ýitsin', style: TextStyle(color: C.danger))),
        ],
      ),
    );
    return r == true;
  }

  @override
  Widget build(BuildContext context) {
    final l = _lesson;
    final editable = l?['editable'] == true;
    final students = ((l?['students'] as List?) ?? []).cast<Map<String, dynamic>>();
    final counts = {for (final v in markValues) v: _marks.values.where((m) => m == v).length};
    final multiGroup = ((l?['groups'] as List?) ?? []).length > 1;
    return PopScope(
      canPop: !_dirty,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (await _confirmLeave() && context.mounted) Navigator.of(context).pop();
      },
      child: Scaffold(
        appBar: AppBar(title: Text('${widget.entry['subject']['name']}', overflow: TextOverflow.ellipsis)),
        body: l == null
            ? (_error != null
                ? EmptyView(icon: Icons.error_outline, title: 'Açyp bolmady', text: _error)
                : const Center(child: CircularProgressIndicator()))
            : ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 100), children: [
                Text('${longDate(widget.day)} · ${l['starts_at']}–${l['ends_at']}',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text('${(l['groups'] as List).join(', ')}'
                    '${l['subgroup'] != null ? ' · ${l['subgroup']}-nji kiçi topar' : ''}'
                    ' · ${lessonTypes[l['lesson_type']] ?? ''}',
                    style: const TextStyle(color: C.muted)),
                const SizedBox(height: 12),
                _Banner(editable: editable, day: widget.day, deadline: DateTime.parse('${l['deadline']}')),
                const SizedBox(height: 12),
                if (students.isEmpty)
                  const EmptyView(icon: Icons.people_outline, title: 'Talyp ýok',
                      text: 'Bu toparyň talyp sanawy heniz girizilmedi. Okuw bölümine ýüz tutuň.')
                else ...[
                  Wrap(spacing: 6, runSpacing: 6, children: [
                    Tag('${students.length} talyp'),
                    for (final v in markValues)
                      if (counts[v]! > 0) Tag('$v: ${counts[v]}', color: markColor(v)),
                  ]),
                  const SizedBox(height: 10),
                  Card(
                    child: Column(children: [
                      for (final (i, s) in students.indexed) ...[
                        if (i > 0) const Divider(),
                        _StudentRow(
                          index: i + 1,
                          name: '${s['name']}',
                          group: multiGroup ? '${s['group']}' : null,
                          value: _marks[s['id']],
                          enabled: editable,
                          onChanged: (v) => setState(() => _marks[s['id'] as int] = v),
                        ),
                      ],
                    ]),
                  ),
                ],
              ]),
        bottomNavigationBar: editable && students.isNotEmpty
            ? SafeArea(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                  child: FilledButton(
                    onPressed: _dirty && !_saving ? _save : null,
                    child: _saving
                        ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white))
                        : Text(_dirty ? 'Ýatda sakla' : 'Ýatda saklandy'),
                  ),
                ),
              )
            : null,
      ),
    );
  }
}

class _Banner extends StatelessWidget {
  const _Banner({required this.editable, required this.day, required this.deadline});
  final bool editable;
  final DateTime day;
  final DateTime deadline;

  @override
  Widget build(BuildContext context) {
    final future = day.isAfter(DateTime.now());
    final (color, bg, icon, text) = editable
        ? (C.primary, C.primarySoft, Icons.edit_calendar_outlined,
            'Baha goýup/üýtgedip bilersiňiz: ${deadline.day} ${months[deadline.month - 1]} aralygynda.')
        : future
            ? (C.muted, C.bg, Icons.schedule, 'Sapak heniz bolmady — baha sapak güni goýulýar.')
            : (C.warning, const Color(0xFFFFFAEB), Icons.lock_outline,
                'Möhlet geçdi (3 gün). Üýtgetmek üçin okuw bölümine ýüz tutuň.');
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(10)),
      child: Row(children: [
        Icon(icon, size: 20, color: color),
        const SizedBox(width: 10),
        Expanded(child: Text(text, style: const TextStyle(fontSize: 13.5))),
      ]),
    );
  }
}

class _StudentRow extends StatelessWidget {
  const _StudentRow({
    required this.index,
    required this.name,
    required this.value,
    required this.enabled,
    required this.onChanged,
    this.group,
  });
  final int index;
  final String name;
  final String? group;
  final String? value;
  final bool enabled;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 10, 10, 10),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          SizedBox(width: 26, child: Text('$index', style: const TextStyle(color: C.subtle))),
          Expanded(child: Text(name, style: const TextStyle(fontWeight: FontWeight.w500))),
          if (group != null) Text(group!, style: const TextStyle(fontSize: 12, color: C.muted)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          const SizedBox(width: 26),
          for (final v in markValues)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: _MarkButton(
                label: v,
                selected: value == v,
                // Saýlanan bahany gaýtadan bassaň aýrylýar.
                onTap: enabled ? () => onChanged(value == v ? null : v) : null,
              ),
            ),
        ]),
      ]),
    );
  }
}

class _MarkButton extends StatelessWidget {
  const _MarkButton({required this.label, required this.selected, this.onTap});
  final String label;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final color = markColor(label);
    return Material(
      color: selected ? color : C.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: BorderSide(color: selected ? color : C.border),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: SizedBox(
          width: label == 'gm' ? 48 : 42,
          height: 40,
          child: Center(
            child: Text(label,
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 16,
                  color: selected ? Colors.white : (onTap == null ? C.subtle : color),
                )),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------------------------
// Žurnal: mugallymyň dersleri → talyplar × sapak günleri
// ---------------------------------------------------------------------------------------------

class JournalView extends StatefulWidget {
  const JournalView({super.key});

  @override
  State<JournalView> createState() => _JournalViewState();
}

class _JournalViewState extends State<JournalView> {
  List<Map<String, dynamic>>? _courses;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await Api.instance.courses();
      if (mounted) {
        setState(() {
          _courses = r.data;
          _error = null;
        });
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 24), children: [
        if (_courses == null && _error == null)
          const Padding(padding: EdgeInsets.all(48), child: Center(child: CircularProgressIndicator()))
        else if (_courses == null)
          EmptyView(icon: Icons.wifi_off, title: 'Birikip bolmady', text: _error)
        else if (_courses!.isEmpty)
          const EmptyView(icon: Icons.grading_outlined, title: 'Sapak ýok',
              text: 'Çap edilen raspisaniýede siziň sapagyňyz ýok.')
        else ...[
          const Padding(
            padding: EdgeInsets.fromLTRB(4, 0, 4, 10),
            child: Text('Baha goýmak üçin "Raspisaniýe" bölüminde sapaga basyň. Şu ýerde ähli bahalary görüp bilersiňiz.',
                style: TextStyle(color: C.muted, fontSize: 13.5, height: 1.35)),
          ),
          for (final c in _courses!)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Card(
                child: ListTile(
                  contentPadding: const EdgeInsets.fromLTRB(14, 6, 8, 6),
                  title: Text('${c['subject']}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
                  subtitle: Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Wrap(spacing: 6, runSpacing: 4, children: [
                      Tag(lessonTypes[c['lesson_type']] ?? '${c['lesson_type']}', color: C.lesson('${c['lesson_type']}')),
                      Tag('${c['groups']}${c['subgroup'] != null ? ' · ${c['subgroup']}-nji kiçi topar' : ''}'),
                    ]),
                  ),
                  trailing: const Icon(Icons.chevron_right, color: C.subtle),
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => GradebookScreen(assignmentId: c['assignment_id'] as int, title: '${c['subject']}'))),
                ),
              ),
            ),
        ],
      ]),
    );
  }
}

class GradebookScreen extends StatefulWidget {
  const GradebookScreen({super.key, required this.assignmentId, required this.title});
  final int assignmentId;
  final String title;

  @override
  State<GradebookScreen> createState() => _GradebookScreenState();
}

class _GradebookScreenState extends State<GradebookScreen> {
  Map<String, dynamic>? _book;
  String? _error;

  @override
  void initState() {
    super.initState();
    Api.instance.journal(widget.assignmentId).then((r) {
      if (mounted) setState(() => _book = r.data);
    }).catchError((Object e) {
      if (mounted) setState(() => _error = '$e');
    });
  }

  @override
  Widget build(BuildContext context) {
    final b = _book;
    return Scaffold(
      appBar: AppBar(title: Text(widget.title, overflow: TextOverflow.ellipsis)),
      body: b == null
          ? (_error != null
              ? EmptyView(icon: Icons.error_outline, title: 'Açyp bolmady', text: _error)
              : const Center(child: CircularProgressIndicator()))
          : _table(b),
    );
  }

  Widget _table(Map<String, dynamic> b) {
    final cols = (b['columns'] as List).cast<Map<String, dynamic>>();
    final rows = (b['rows'] as List).cast<Map<String, dynamic>>();
    if (rows.isEmpty) {
      return const EmptyView(icon: Icons.people_outline, title: 'Talyp ýok');
    }
    if (cols.isEmpty) {
      return const EmptyView(icon: Icons.event_busy, title: 'Heniz sapak bolmady');
    }
    const h = 40.0, w = 42.0, nameW = 150.0;
    const head = TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600, color: C.muted);
    Widget cell(Widget child, {double width = w, Color? bg, Alignment align = Alignment.center}) => Container(
          width: width,
          height: h,
          alignment: align,
          padding: align == Alignment.centerLeft ? const EdgeInsets.symmetric(horizontal: 8) : null,
          decoration: BoxDecoration(
            color: bg,
            border: const Border(right: BorderSide(color: C.border), bottom: BorderSide(color: C.border)),
          ),
          child: child,
        );
    // Soňky sapaklar ilki görünsin diýip sütünler tersine (iň täzesi çepde).
    final order = [for (var i = cols.length - 1; i >= 0; i--) i];
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 10),
        child: Text('${(b['groups'] as List).join(', ')}'
            '${b['subgroup'] != null ? ' · ${b['subgroup']}-nji kiçi topar' : ''} · ${cols.length} sapak',
            style: const TextStyle(color: C.muted)),
      ),
      const Divider(),
      Expanded(
        child: SingleChildScrollView(
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              color: C.surface,
              child: Column(children: [
                cell(const Text('Talyp', style: head), width: nameW, bg: C.bg, align: Alignment.centerLeft),
                for (final r in rows)
                  cell(Text('${r['student']['name']}', overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
                      width: nameW, align: Alignment.centerLeft),
              ]),
            ),
            Expanded(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Container(
                  color: C.surface,
                  child: Column(children: [
                    Row(children: [
                      cell(const Text('Ort.', style: head), bg: C.bg),
                      cell(const Text('gm', style: head), bg: C.bg),
                      for (final i in order) cell(Text(_short('${cols[i]['day']}'), style: head), bg: C.bg),
                    ]),
                    for (final r in rows)
                      Row(children: [
                        cell(Text(r['average'] == null ? '—' : '${r['average']}',
                            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13))),
                        cell(Text('${r['absent']}', style: const TextStyle(fontSize: 13, color: C.muted))),
                        for (final i in order)
                          cell(Text('${(r['marks'] as List)[i] ?? ''}',
                              style: TextStyle(fontWeight: FontWeight.w700, color: markColor((r['marks'] as List)[i] as String?)))),
                      ]),
                  ]),
                ),
              ),
            ),
          ]),
        ),
      ),
    ]);
  }

  /// 2026-09-14 → 14.09
  static String _short(String iso) => '${iso.substring(8, 10)}.${iso.substring(5, 7)}';
}

/// Sapak kartasynda: şol günüň sapagyna baha goýup bolýarmy (sapak güni + 3 gün).
bool canMark(DateTime day) {
  final today = DateTime(DateTime.now().year, DateTime.now().month, DateTime.now().day);
  return !day.isAfter(today) && !today.isAfter(day.add(const Duration(days: 3)));
}

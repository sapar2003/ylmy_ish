import 'dart:async';

import 'package:flutter/material.dart';

import '../api.dart';
import '../faculties.dart';
import '../resources.dart';
import 'dialogs.dart';

enum ViewBy { group, teacher, room }

/// Raspisaniýe düzmek we görmek: topar, mugallym ýa-da otag boýunça hepdelik setka.
class TimetablePage extends StatefulWidget {
  const TimetablePage({super.key});

  @override
  State<TimetablePage> createState() => _TimetablePageState();
}

class _TimetablePageState extends State<TimetablePage> {
  List<Map<String, dynamic>> _timetables = [];
  Map<String, dynamic>? _current;
  final Map<ViewBy, List<Map<String, dynamic>>> _targets = {};
  List<Map<String, dynamic>> _slots = [];
  ViewBy _viewBy = ViewBy.group;
  int? _targetId;
  List<Map<String, dynamic>> _entries = [];
  Map<int, String> _teacherFaculty = {};
  DateTime? _weekStart; // görkezilýän hepdäniň duşenbesi (ýarymýylyň seneleri bar bolsa)
  int _week = 1; // seneleri ýok iki hepdelik raspisaniýede saýlanan hepde
  Timer? _poll;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final r = await Future.wait([
        Api.instance.get('timetables'),
        Api.instance.list('groups'),
        Api.instance.list('teachers'),
        Api.instance.list('rooms'),
        Api.instance.list('time-slots'),
      ]);
      final faculties = await loadTeacherFaculties(r[2] as List<Map<String, dynamic>>);
      if (!mounted) return;
      setState(() {
        _timetables = (r[0] as List).cast<Map<String, dynamic>>();
        _targets[ViewBy.group] = r[1] as List<Map<String, dynamic>>;
        _targets[ViewBy.teacher] = r[2] as List<Map<String, dynamic>>;
        _targets[ViewBy.room] = r[3] as List<Map<String, dynamic>>;
        _slots = r[4] as List<Map<String, dynamic>>;
        _teacherFaculty = faculties;
        _current ??= _timetables.where((t) => t['status'] == 'done').firstOrNull ?? _timetables.firstOrNull;
        _targetId ??= _targets[_viewBy]!.firstOrNull?['id'] as int?;
        _loading = false;
      });
      _watchCurrent();
      _loadEntries();
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        showError(context, e.message);
      }
    }
  }

  void _watchCurrent() {
    _poll?.cancel();
    final status = _current?['status'];
    if (status != 'pending' && status != 'running') return;
    _poll = Timer.periodic(const Duration(seconds: 1), (_) async {
      final tt = await Api.instance.get('timetables/${_current!['id']}') as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        _current = tt;
        _timetables = [for (final t in _timetables) t['id'] == tt['id'] ? tt : t];
      });
      if (tt['status'] == 'done' || tt['status'] == 'failed') {
        _poll?.cancel();
        _loadEntries();
      }
    });
  }

  Future<void> _loadEntries() async {
    final tt = _current;
    if (tt == null || tt['status'] != 'done' || _targetId == null) {
      setState(() => _entries = []);
      return;
    }
    final key = switch (_viewBy) {
      ViewBy.group => 'group_id',
      ViewBy.teacher => 'teacher_id',
      ViewBy.room => 'room_id',
    };
    final start = _semesterStart(tt);
    if (start != null) _weekStart ??= _initialWeek(tt);
    final entries = await Api.instance.get('timetables/${tt['id']}/entries', {
      key: _targetId,
      if (start != null) 'on': _iso(_weekStart!) else if (tt['weeks'] == 2) 'week': _week,
    });
    if (mounted) setState(() => _entries = (entries as List).cast<Map<String, dynamic>>());
  }

  Future<void> _generate() async {
    final checks = await Future.wait([
      for (final weeks in [1, 2]) Api.instance.get('timetables/precheck', {'weeks': weeks}),
    ]);
    if (!mounted) return;
    final now = DateTime.now();
    final autumn = now.month >= 7; // güýz ýarymýyly: 1-nji sentýabr – 31-nji dekabr; ýaz: 1-nji fewral – 30-njy iýun
    final nameCtl = TextEditingController(text: 'Raspisaniýe ${now.toString().substring(0, 16)}');
    final startCtl = TextEditingController(text: _iso(autumn ? DateTime(now.year, 9, 1) : DateTime(now.year, 2, 1)));
    final endCtl = TextEditingController(text: _iso(autumn ? DateTime(now.year, 12, 31) : DateTime(now.year, 6, 30)));
    var twoWeeks = true;
    String? dateError;
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(builder: (c, setDialog) {
        final check = checks[twoWeeks ? 1 : 0] as Map<String, dynamic>;
        final issues = (check['issues'] as List).cast<String>();
        return AlertDialog(
          title: const Text('Täze raspisaniýe düzmek'),
          content: SizedBox(
            width: 520,
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                TextField(controller: nameCtl, decoration: const InputDecoration(labelText: 'Ady')),
                const SizedBox(height: 8),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Iki hepdelik (1-nji / 2-nji hepde)'),
                  subtitle: const Text('"Iki hepdede bir" sapaklar diňe öz hepdesinde goýulýar'),
                  value: twoWeeks,
                  onChanged: (v) => setDialog(() => twoWeeks = v),
                ),
                Row(children: [
                  Expanded(
                    child: TextField(
                      controller: startCtl,
                      decoration: const InputDecoration(labelText: 'Ýarymýylyň başy', hintText: 'ÝÝÝÝ-AA-GG'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: endCtl,
                      decoration: const InputDecoration(labelText: 'Ýarymýylyň ahyry', hintText: 'ÝÝÝÝ-AA-GG'),
                    ),
                  ),
                ]),
                if (dateError != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(dateError!, style: TextStyle(color: Theme.of(c).colorScheme.error)),
                  ),
                const SizedBox(height: 16),
                Text('${check['lessons']} sapak, iki hepdede bir sapaklar bilen jemi ${check['lessons_per_week']}.'),
                const SizedBox(height: 8),
                if (issues.isEmpty)
                  const Row(children: [
                    Icon(Icons.check_circle, color: Colors.green),
                    SizedBox(width: 8),
                    Text('Barlag geçdi: maglumatlarda ýalňyşlyk tapylmady.'),
                  ])
                else ...[
                  Text('Barlagda ${issues.length} mesele tapyldy:',
                      style: const TextStyle(fontWeight: FontWeight.w600)),
                  for (final i in issues.take(8)) Text('• $i'),
                ],
              ]),
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Ýatyr')),
            FilledButton(
              onPressed: () {
                final a = DateTime.tryParse(startCtl.text.trim());
                final b = DateTime.tryParse(endCtl.text.trim());
                if (a == null || b == null || b.isBefore(a)) {
                  setDialog(() => dateError = 'Seneleri ÝÝÝÝ-AA-GG görnüşinde giriziň, ahyry başyndan soň bolsun.');
                  return;
                }
                Navigator.pop(c, true);
              },
              child: const Text('Düz'),
            ),
          ],
        );
      }),
    );
    if (ok != true) return;
    try {
      final tt = await Api.instance.post('timetables', {
        'name': nameCtl.text,
        'time_limit_seconds': twoWeeks ? 600 : 300,
        'weeks': twoWeeks ? 2 : 1,
        'starts_on': startCtl.text.trim(),
        'ends_on': endCtl.text.trim(),
      });
      setState(() {
        _current = tt as Map<String, dynamic>;
        _timetables = [tt, ..._timetables];
        _entries = [];
        _weekStart = null;
      });
      _watchCurrent();
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text('Raspisaniýe', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(width: 24),
          if (_timetables.isNotEmpty)
            DropdownButton<int>(
              value: _current?['id'] as int?,
              items: [
                for (final t in _timetables)
                  DropdownMenuItem(value: t['id'] as int, child: Text('${t['name']}  (${_statusText(t)})')),
              ],
              onChanged: (id) {
                setState(() {
                  _current = _timetables.firstWhere((t) => t['id'] == id);
                  _weekStart = null;
                });
                _watchCurrent();
                _loadEntries();
              },
            ),
          const Spacer(),
          FilledButton.icon(
            onPressed: _generate,
            icon: const Icon(Icons.auto_awesome),
            label: const Text('Awtomat düz'),
          ),
        ]),
        const SizedBox(height: 12),
        if (_current != null) _statusBanner(_current!),
        if (_current != null && _current!['status'] == 'done') _weekBar(_current!),
        const SizedBox(height: 12),
        Row(children: [
          SegmentedButton<ViewBy>(
            segments: const [
              ButtonSegment(value: ViewBy.group, label: Text('Topar'), icon: Icon(Icons.groups)),
              ButtonSegment(value: ViewBy.teacher, label: Text('Mugallym'), icon: Icon(Icons.person)),
              ButtonSegment(value: ViewBy.room, label: Text('Otag'), icon: Icon(Icons.meeting_room)),
            ],
            selected: {_viewBy},
            onSelectionChanged: (s) {
              setState(() {
                _viewBy = s.first;
                _targetId = _targets[_viewBy]!.firstOrNull?['id'] as int?;
              });
              _loadEntries();
            },
          ),
          const SizedBox(width: 16),
          DropdownButton<int>(
            value: _targetId,
            hint: const Text('Saýlaň'),
            items: [
              for (final t in _targets[_viewBy]!)
                DropdownMenuItem(
                  value: t['id'] as int,
                  child: Text(_viewBy == ViewBy.teacher ? withFaculty(t, _teacherFaculty) : '${t['name']}'),
                ),
            ],
            onChanged: (id) {
              setState(() => _targetId = id);
              _loadEntries();
            },
          ),
        ]),
        const SizedBox(height: 12),
        Expanded(child: _grid()),
      ]),
    );
  }

  // --- Hepdeler we seneler ---
  static DateTime _monday(DateTime d) => DateTime(d.year, d.month, d.day - (d.weekday - 1));

  String _iso(DateTime d) => d.toIso8601String().substring(0, 10);

  String _ddmm(DateTime d) => '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}';

  DateTime? _semesterStart(Map<String, dynamic> tt) =>
      tt['starts_on'] == null ? null : _monday(DateTime.parse(tt['starts_on']));

  DateTime? _semesterEnd(Map<String, dynamic> tt) =>
      tt['ends_on'] == null ? null : _monday(DateTime.parse(tt['ends_on']));

  /// Şu günüň hepdesi (ýarymýylyň içinde bolsa), ýogsam ýarymýylyň ilkinji hepdesi.
  DateTime _initialWeek(Map<String, dynamic> tt) {
    final start = _semesterStart(tt)!;
    final end = _semesterEnd(tt) ?? start;
    final today = _monday(DateTime.now());
    return today.isBefore(start) || today.isAfter(end) ? start : today;
  }

  /// Ýarymýylyň başyndan n-nji hepde (1-den başlap).
  int _weekIndex(Map<String, dynamic> tt, DateTime monday) =>
      monday.difference(_semesterStart(tt)!).inDays ~/ 7 + 1;

  Widget _weekBar(Map<String, dynamic> tt) {
    final start = _semesterStart(tt);
    final twoWeeks = tt['weeks'] == 2;
    if (start == null) {
      if (!twoWeeks) return const SizedBox();
      return Padding(
        padding: const EdgeInsets.only(top: 12),
        child: SegmentedButton<int>(
          segments: const [
            ButtonSegment(value: 1, label: Text('1-nji hepde')),
            ButtonSegment(value: 2, label: Text('2-nji hepde')),
          ],
          selected: {_week},
          onSelectionChanged: (s) {
            setState(() => _week = s.first);
            _loadEntries();
          },
        ),
      );
    }
    final week = _weekStart ?? _initialWeek(tt);
    final end = _semesterEnd(tt) ?? start;
    final n = _weekIndex(tt, week);
    void go(DateTime w) {
      setState(() => _weekStart = w);
      _loadEntries();
    }

    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Row(children: [
        IconButton(
          tooltip: 'Öňki hepde',
          icon: const Icon(Icons.chevron_left),
          onPressed: week.isAfter(start) ? () => go(week.subtract(const Duration(days: 7))) : null,
        ),
        Text(
          '$n-nji hepde: ${_ddmm(week)} – ${_ddmm(week.add(const Duration(days: 6)))}.${week.year}'
          '${twoWeeks ? '  ·  ${(n - 1) % 2 + 1}-nji hepdäniň raspisaniýesi' : ''}',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        IconButton(
          tooltip: 'Indiki hepde',
          icon: const Icon(Icons.chevron_right),
          onPressed: week.isBefore(end) ? () => go(week.add(const Duration(days: 7))) : null,
        ),
        const SizedBox(width: 8),
        TextButton(onPressed: () => go(_initialWeek(tt)), child: const Text('Şu hepde')),
      ]),
    );
  }

  String _statusText(Map<String, dynamic> t) => switch (t['status']) {
        'done' => 'taýýar',
        'failed' => 'şowsuz',
        'running' => 'düzülýär…',
        _ => 'nobatda',
      };

  Widget _statusBanner(Map<String, dynamic> tt) {
    final cs = Theme.of(context).colorScheme;
    final issues = (tt['issues'] as List).cast<String>();
    final (icon, color, text) = switch (tt['status']) {
      'done' => (
          Icons.check_circle,
          Colors.green,
          '${tt['entry_count']} sapak ýerleşdirildi, ${tt['seconds']} sekuntda. '
              'Mugallym, topar we otag gabat gelmeleri ýok.'
        ),
      'failed' => (Icons.error, cs.error, 'Raspisaniýe düzülmedi.'),
      _ => (Icons.hourglass_top, cs.primary, 'Raspisaniýe düzülýär, garaşyň…'),
    };
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(icon, color: color),
            const SizedBox(width: 8),
            Expanded(child: Text(text)),
            if (tt['status'] == 'running' || tt['status'] == 'pending')
              const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
          ]),
          for (final i in issues.take(6)) Padding(padding: const EdgeInsets.only(left: 32, top: 4), child: Text('• $i')),
        ]),
      ),
    );
  }

  Widget _grid() {
    if (_current == null) {
      return const Center(child: Text('Heniz raspisaniýe ýok. "Awtomat düz" düwmesine basyň.'));
    }
    if (_current!['status'] != 'done') return const SizedBox();

    // Setkanyň setirleri: wagt aralyklary. Topar üçin diňe onuň smenasy.
    Iterable<Map<String, dynamic>> slots = _slots;
    if (_viewBy == ViewBy.group) {
      final shiftId = _targets[ViewBy.group]!.where((g) => g['id'] == _targetId).firstOrNull?['shift_id'];
      if (shiftId != null) slots = slots.where((s) => s['shift_id'] == shiftId);
    }
    final times = {for (final s in slots) '${s['starts_at']}|${s['ends_at']}'}.toList()..sort();
    final days = {for (final s in slots) s['weekday'] as int}.toList()..sort();
    if (times.isEmpty) return const Center(child: Text('Wagt slotlary ýok.'));

    return SingleChildScrollView(
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Table(
          border: TableBorder.all(color: Theme.of(context).dividerColor),
          defaultColumnWidth: const FixedColumnWidth(190),
          columnWidths: const {0: FixedColumnWidth(90)},
          defaultVerticalAlignment: TableCellVerticalAlignment.top,
          children: [
            TableRow(
              decoration: BoxDecoration(color: Theme.of(context).colorScheme.surfaceContainerHighest),
              children: [
                const Padding(padding: EdgeInsets.all(8), child: Text('Wagt')),
                for (final d in days)
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: Text(
                      _weekStart == null
                          ? weekdays[d - 1]
                          : '${weekdays[d - 1]}, ${_ddmm(_weekStart!.add(Duration(days: d - 1)))}',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
              ],
            ),
            for (final t in times)
              TableRow(children: [
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: Text('${t.substring(0, 5)}\n${t.split('|')[1].substring(0, 5)}'),
                ),
                for (final d in days) _cell(d, t),
              ]),
          ],
        ),
      ),
    );
  }

  Widget _cell(int day, String time) {
    final here = _entries.where((e) => e['weekday'] == day && '${e['starts_at']}|${e['ends_at']}' == time).toList();
    return ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 72),
      child: Column(children: [for (final e in here) _lessonCard(e)]),
    );
  }

  Widget _lessonCard(Map<String, dynamic> e) {
    final type = e['lesson_type'] as String;
    final color = switch (type) {
      'lecture' => Colors.indigo,
      'lab' => Colors.teal,
      'seminar' => Colors.orange,
      _ => Colors.blueGrey,
    };
    final groups = (e['stream'] != null ? e['stream']['name'] : (e['groups'] as List).map((g) => g['name']).join(', '));
    final sub = e['subgroup'] != null ? ' · ${e['subgroup']['name']}-nji kiçi topar' : '';
    final lines = [
      if (_viewBy != ViewBy.teacher) withFaculty(e['teacher'], _teacherFaculty),
      if (_viewBy != ViewBy.group) '$groups$sub' else if (sub.isNotEmpty) sub.substring(3),
      if (_viewBy != ViewBy.room) 'Otag ${e['room']?['name'] ?? '—'}',
    ];
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.all(3),
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        border: Border(left: BorderSide(color: color, width: 3)),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${e['subject']['name']}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
        Text(
          '${lessonTypes[type] ?? type}${e['week'] != null ? ' · iki hepdede bir (${e['week']}-nji hepde)' : ''}',
          style: TextStyle(fontSize: 11, color: color),
        ),
        for (final l in lines) Text(l, style: const TextStyle(fontSize: 12)),
      ]),
    );
  }
}

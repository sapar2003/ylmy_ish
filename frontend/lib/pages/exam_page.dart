import 'dart:async';

import 'package:flutter/material.dart';

import '../api.dart';
import '../faculties.dart';
import '../resources.dart';
import 'dialogs.dart';
import 'timetable_page.dart' show ViewBy;

/// Synag raspisaniýesini düzmek we görmek: setirler synag günleri, sütünler synag wagtlary.
class ExamPage extends StatefulWidget {
  const ExamPage({super.key});

  @override
  State<ExamPage> createState() => _ExamPageState();
}

class _ExamPageState extends State<ExamPage> {
  List<Map<String, dynamic>> _sessions = [];
  Map<String, dynamic>? _session;
  List<Map<String, dynamic>> _periods = [];
  List<Map<String, dynamic>> _schedules = [];
  Map<String, dynamic>? _current;
  final Map<ViewBy, List<Map<String, dynamic>>> _targets = {};
  ViewBy _viewBy = ViewBy.group;
  int? _targetId;
  List<Map<String, dynamic>> _entries = [];
  Map<int, String> _teacherFaculty = {};
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
        Api.instance.list('exam-sessions'),
        Api.instance.list('groups'),
        Api.instance.list('teachers'),
        Api.instance.list('rooms'),
      ]);
      final faculties = await loadTeacherFaculties(r[2]);
      if (!mounted) return;
      setState(() {
        _teacherFaculty = faculties;
        _sessions = r[0];
        _targets[ViewBy.group] = r[1];
        _targets[ViewBy.teacher] = r[2];
        _targets[ViewBy.room] = r[3];
        _session ??= _sessions.lastOrNull;
        _targetId ??= _targets[_viewBy]!.firstOrNull?['id'] as int?;
        _loading = false;
      });
      await _loadSession();
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        showError(context, e.message);
      }
    }
  }

  Future<void> _loadSession() async {
    final session = _session;
    if (session == null) return;
    final r = await Future.wait([
      Api.instance.list('exam-periods', {'session_id': session['id']}),
      Api.instance.get('exam-schedules', {'session_id': session['id']}),
    ]);
    if (!mounted) return;
    setState(() {
      _periods = r[0] as List<Map<String, dynamic>>;
      _schedules = (r[1] as List).cast<Map<String, dynamic>>();
      _current = _schedules.where((t) => t['status'] == 'done').firstOrNull ?? _schedules.firstOrNull;
    });
    _watchCurrent();
    _loadEntries();
  }

  void _watchCurrent() {
    _poll?.cancel();
    final status = _current?['status'];
    if (status != 'pending' && status != 'running') return;
    _poll = Timer.periodic(const Duration(seconds: 1), (_) async {
      final sch = await Api.instance.get('exam-schedules/${_current!['id']}') as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        _current = sch;
        _schedules = [for (final t in _schedules) t['id'] == sch['id'] ? sch : t];
      });
      if (sch['status'] == 'done' || sch['status'] == 'failed') {
        _poll?.cancel();
        _loadEntries();
      }
    });
  }

  Future<void> _loadEntries() async {
    final sch = _current;
    if (sch == null || sch['status'] != 'done' || _targetId == null) {
      setState(() => _entries = []);
      return;
    }
    final key = switch (_viewBy) {
      ViewBy.group => 'group_id',
      ViewBy.teacher => 'teacher_id',
      ViewBy.room => 'room_id',
    };
    final entries = await Api.instance.get('exam-schedules/${sch['id']}/entries', {key: _targetId});
    if (mounted) setState(() => _entries = (entries as List).cast<Map<String, dynamic>>());
  }

  Future<void> _generate() async {
    final session = _session!;
    final check = await Api.instance.get('exam-schedules/precheck', {'session_id': session['id']}) as Map<String, dynamic>;
    if (!mounted) return;
    final issues = (check['issues'] as List).cast<String>();
    final nameCtl = TextEditingController(text: '${session['name']} ${DateTime.now().toString().substring(0, 16)}');
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Synag raspisaniýesini düzmek'),
        content: SizedBox(
          width: 480,
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            TextField(controller: nameCtl, decoration: const InputDecoration(labelText: 'Ady')),
            const SizedBox(height: 16),
            Text('${check['exams']} synag, ${check['days']} gün, jemi ${check['slots']} synag wagty.'),
            const SizedBox(height: 8),
            if (issues.isEmpty)
              const Row(children: [
                Icon(Icons.check_circle, color: Colors.green),
                SizedBox(width: 8),
                Text('Barlag geçdi: maglumatlarda ýalňyşlyk tapylmady.'),
              ])
            else ...[
              Text('Barlagda ${issues.length} mesele tapyldy:', style: const TextStyle(fontWeight: FontWeight.w600)),
              for (final i in issues.take(8)) Text('• $i'),
            ],
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Ýatyr')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Düz')),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final sch = await Api.instance.post('exam-schedules', {
        'session_id': session['id'],
        'name': nameCtl.text,
        'time_limit_seconds': 60,
      });
      setState(() {
        _current = sch as Map<String, dynamic>;
        _schedules = [sch, ..._schedules];
        _entries = [];
      });
      _watchCurrent();
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_sessions.isEmpty) {
      return const Center(
        child: Text('Heniz synag möwsümi ýok. Çepdäki "Synag möwsümleri", "Synag wagtlary" we "Synaglar" '
            'sanawlaryny dolduryň.'),
      );
    }
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text('Synag raspisaniýesi', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(width: 24),
          DropdownButton<int>(
            value: _session?['id'] as int?,
            items: [
              for (final s in _sessions)
                DropdownMenuItem(
                  value: s['id'] as int,
                  child: Text('${s['name']} (${examKinds[s['kind']] ?? s['kind']})'),
                ),
            ],
            onChanged: (id) {
              setState(() {
                _session = _sessions.firstWhere((s) => s['id'] == id);
                _current = null;
                _entries = [];
              });
              _loadSession();
            },
          ),
          const SizedBox(width: 16),
          if (_schedules.isNotEmpty)
            DropdownButton<int>(
              value: _current?['id'] as int?,
              items: [
                for (final t in _schedules)
                  DropdownMenuItem(value: t['id'] as int, child: Text('${t['name']}  (${_statusText(t)})')),
              ],
              onChanged: (id) {
                setState(() => _current = _schedules.firstWhere((t) => t['id'] == id));
                _watchCurrent();
                _loadEntries();
              },
            ),
          const Spacer(),
          FilledButton.icon(
            onPressed: _session == null ? null : _generate,
            icon: const Icon(Icons.auto_awesome),
            label: const Text('Awtomat düz'),
          ),
        ]),
        const SizedBox(height: 12),
        if (_current != null) _statusBanner(_current!),
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

  String _statusText(Map<String, dynamic> t) => switch (t['status']) {
        'done' => 'taýýar',
        'failed' => 'şowsuz',
        'running' => 'düzülýär…',
        _ => 'nobatda',
      };

  Widget _statusBanner(Map<String, dynamic> sch) {
    final cs = Theme.of(context).colorScheme;
    final issues = (sch['issues'] as List).cast<String>();
    final (icon, color, text) = switch (sch['status']) {
      'done' => (
          Icons.check_circle,
          Colors.green,
          '${sch['entry_count']} synag ýerleşdirildi, ${sch['seconds']} sekuntda. '
              'Mugallym, topar we otag gabat gelmeleri ýok.'
        ),
      'failed' => (Icons.error, cs.error, 'Synag raspisaniýesi düzülmedi.'),
      _ => (Icons.hourglass_top, cs.primary, 'Synag raspisaniýesi düzülýär, garaşyň…'),
    };
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(icon, color: color),
            const SizedBox(width: 8),
            Expanded(child: Text(text)),
            if (sch['status'] == 'running' || sch['status'] == 'pending')
              const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
          ]),
          for (final i in issues.take(6)) Padding(padding: const EdgeInsets.only(left: 32, top: 4), child: Text('• $i')),
        ]),
      ),
    );
  }

  /// Möwsümiň synag günleri (saýlanan hepde günleri boýunça).
  List<DateTime> _days() {
    final s = _session!;
    final allowed = (s['weekdays'] as List).cast<int>().toSet();
    final end = DateTime.parse(s['ends_on']);
    return [
      for (var d = DateTime.parse(s['starts_on']); !d.isAfter(end); d = d.add(const Duration(days: 1)))
        if (allowed.contains(d.weekday)) d,
    ];
  }

  String _iso(DateTime d) => d.toIso8601String().substring(0, 10);

  Widget _grid() {
    if (_current == null) {
      return const Center(child: Text('Bu möwsüm üçin heniz synag raspisaniýesi ýok. "Awtomat düz" düwmesine basyň.'));
    }
    if (_current!['status'] != 'done') return const SizedBox();
    if (_periods.isEmpty) return const Center(child: Text('Synag wagtlary ýok.'));
    final days = _days();

    return SingleChildScrollView(
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Table(
          border: TableBorder.all(color: Theme.of(context).dividerColor),
          defaultColumnWidth: const FixedColumnWidth(220),
          columnWidths: const {0: FixedColumnWidth(120)},
          defaultVerticalAlignment: TableCellVerticalAlignment.top,
          children: [
            TableRow(
              decoration: BoxDecoration(color: Theme.of(context).colorScheme.surfaceContainerHighest),
              children: [
                const Padding(padding: EdgeInsets.all(8), child: Text('Sene')),
                for (final p in _periods)
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: Text(
                      '${p['number']}. ${'${p['starts_at']}'.substring(0, 5)}-${'${p['ends_at']}'.substring(0, 5)}',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
              ],
            ),
            for (final d in days)
              TableRow(children: [
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: Text('${_iso(d).substring(8)}.${_iso(d).substring(5, 7)}\n${weekdays[d.weekday - 1]}'),
                ),
                for (final p in _periods) _cell(_iso(d), p['number'] as int),
              ]),
          ],
        ),
      ),
    );
  }

  Widget _cell(String day, int period) {
    final here = _entries.where((e) => e['day'] == day && e['period'] == period).toList();
    return ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 56),
      child: Column(children: [for (final e in here) _examCard(e)]),
    );
  }

  Widget _examCard(Map<String, dynamic> e) {
    const color = Colors.deepPurple;
    final groups = e['stream'] != null ? e['stream']['name'] : (e['groups'] as List).map((g) => g['name']).join(', ');
    final teachers = [
      withFaculty(e['examiner'], _teacherFaculty),
      if (e['assistant'] != null) withFaculty(e['assistant'], _teacherFaculty),
    ].join(', ');
    final lines = [
      if (_viewBy != ViewBy.group) '$groups',
      teachers, // mugallym boýunça görlende hem: uly we kiçi mugallym bilelikde görünsin
      if (_viewBy != ViewBy.room) 'Otag ${e['room']?['name'] ?? '—'}',
    ];
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.all(3),
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        border: const Border(left: BorderSide(color: color, width: 3)),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${e['subject']['name']}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
        for (final l in lines) Text(l, style: const TextStyle(fontSize: 12)),
      ]),
    );
  }
}

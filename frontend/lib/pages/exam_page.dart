import 'dart:async';

import 'package:flutter/material.dart';

import '../api.dart';
import '../faculties.dart';
import '../resources.dart';
import '../theme.dart';
import 'dialogs.dart';
import 'word_dialog.dart';
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
  // Saýlanan möwsüme degişli toparlar, mugallymlar we otaglar (saýlawda diňe şular görkezilýär)
  final Map<ViewBy, Set<int>> _inSession = {};
  Timer? _poll;
  bool _loading = true;
  bool _showArchived = false; // arhiwdäki köne wersiýalary hem görkezmek

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
      final recent = await Api.instance.get('exam-schedules') as List;
      final faculties = await loadTeacherFaculties();
      if (!mounted) return;
      setState(() {
        _teacherFaculty = faculties;
        _sessions = r[0];
        _targets[ViewBy.group] = r[1];
        _targets[ViewBy.teacher] = r[2];
        _targets[ViewBy.room] = r[3];
        // Adaty: iň soňky düzülen synag raspisaniýesiniň möwsümi
        final lastSessionId = recent.isEmpty ? null : (recent.first as Map)['session_id'];
        _session ??= _sessions.where((s) => s['id'] == lastSessionId).firstOrNull ?? _sessions.lastOrNull;
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
      Api.instance.list('exams', {'session_id': session['id']}),
    ]);
    if (!mounted) return;
    final exams = r[2] as List<Map<String, dynamic>>;
    setState(() {
      _periods = r[0] as List<Map<String, dynamic>>;
      _schedules = (r[1] as List).cast<Map<String, dynamic>>();
      final live = [for (final t in _schedules) if (t['archived'] != true) t];
      _current = live.where((t) => t['published'] == true).firstOrNull ??
          live.where((t) => t['status'] == 'done').firstOrNull ??
          live.firstOrNull ??
          _schedules.firstOrNull;
      _inSession[ViewBy.group] = {for (final e in exams) if (e['group_id'] != null) e['group_id'] as int};
      _inSession[ViewBy.teacher] = {
        for (final e in exams) ...[e['examiner_id'] as int, if (e['assistant_id'] != null) e['assistant_id'] as int],
      };
      _inSession.remove(ViewBy.room);
    });
    await _loadSessionRooms();
    _fixTarget();
    _watchCurrent();
    _loadEntries();
  }

  /// Otaglar: saýlanan raspisaniýede ulanylan otaglar.
  Future<void> _loadSessionRooms() async {
    final sch = _current;
    if (sch == null || sch['status'] != 'done') return;
    final all = await Api.instance.get('exam-schedules/${sch['id']}/entries') as List;
    if (!mounted) return;
    setState(() => _inSession[ViewBy.room] = {
          for (final e in all.cast<Map<String, dynamic>>())
            if (e['room'] != null) (e['room'] as Map)['id'] as int,
        });
  }

  List<Map<String, dynamic>> get _visibleTargets {
    final all = _targets[_viewBy] ?? const [];
    final allowed = _inSession[_viewBy];
    if (allowed == null) return all;
    return [for (final t in all) if (allowed.contains(t['id'])) t];
  }

  /// Saýlanan topar/mugallym/otag bu möwsümde ýok bolsa, birinjisini saýlaýar.
  void _fixTarget() {
    final visible = _visibleTargets;
    if (!visible.any((t) => t['id'] == _targetId)) {
      setState(() => _targetId = visible.firstOrNull?['id'] as int?);
    }
  }

  static bool _isInfo(String issue) => issue.startsWith('Beýleki möwsümleriň synaglary hasaba alyndy');

  /// "Ýarymýyllyk synaglar 2026/2027 I (YDF)" -> "YDF · Ýarymýyllyk synaglar 2026/2027 I"
  static String _sessionLabel(Map<String, dynamic> s) {
    final name = '${s['name']}';
    final m = RegExp(r'^(.*?)\s*\(([^()]+)\)\s*$').firstMatch(name);
    return m == null ? name : '${m.group(2)} · ${m.group(1)}';
  }

  /// Sanawda görünýän wersiýalar: arhiwlenmedikler (+ saýlanan), täzesi ýokarda.
  List<Map<String, dynamic>> get _shownSchedules => [
        for (final t in _schedules)
          if (_showArchived || t['archived'] != true || t['id'] == _current?['id']) t,
      ];

  int get _archivedCount => _schedules.where((t) => t['archived'] == true).length;

  /// Gysga, düşnükli at: möwsümiň uzyn ady aýrylýar, sene we ýagdaý goşulýar.
  String _scheduleLabel(Map<String, dynamic> t) {
    var name = '${t['name']}'.trim();
    final session = '${_session?['name'] ?? ''}';
    if (session.isNotEmpty && name.startsWith(session)) {
      name = name.substring(session.length).trim();
      name = name.isEmpty || RegExp(r'^\d{4}-\d{2}-\d{2}').hasMatch(name) ? 'Awtomat' : name;
    }
    final raw = '${t['created_at']}';
    // Serwer UTC wagtyny zolaksyz berýär: ýerli wagta öwürýäris
    final created = DateTime.tryParse(RegExp(r'(Z|[+-]\d{2}:?\d{2})$').hasMatch(raw) ? raw : '${raw}Z')?.toLocal();
    final when = created == null
        ? ''
        : ' · ${_two(created.day)}.${_two(created.month)} ${_two(created.hour)}:${_two(created.minute)}';
    final mark = t['published'] == true ? ' · ✓ çap edilen' : (t['archived'] == true ? ' · arhiwde' : '');
    return '$name$when · ${_statusText(t)}$mark';
  }

  static String _two(int n) => n.toString().padLeft(2, '0');

  Future<void> _scheduleAction(String action) async {
    final sch = _current;
    if (sch == null && action != 'toggle') return;
    try {
      switch (action) {
        case 'toggle':
          setState(() => _showArchived = !_showArchived);
        case 'rename':
          final ctl = TextEditingController(text: '${sch!['name']}');
          final name = await showDialog<String>(
            context: context,
            builder: (c) => AlertDialog(
              title: const Text('Adyny üýtgetmek'),
              content: SizedBox(width: 420, child: TextField(controller: ctl, autofocus: true)),
              actions: [
                TextButton(onPressed: () => Navigator.pop(c), child: const Text('Ýatyr')),
                FilledButton(onPressed: () => Navigator.pop(c, ctl.text.trim()), child: const Text('Ýatda sakla')),
              ],
            ),
          );
          if (name == null || name.isEmpty) return;
          _replace(await Api.instance.patch('exam-schedules/${sch['id']}', {'name': name}) as Map<String, dynamic>);
        case 'archive':
        case 'restore':
          _replace(await Api.instance.patch('exam-schedules/${sch!['id']}', {'archived': action == 'archive'})
              as Map<String, dynamic>);
          if (action == 'archive' && !_showArchived) {
            final next = _schedules.where((t) => t['archived'] != true && t['status'] == 'done').firstOrNull;
            if (next != null) await _select(next['id'] as int);
          }
        case 'delete':
          if (!await confirm(context,
              '"${_scheduleLabel(sch!)}" doly pozulsynmy? Muny yzyna getirip bolmaýar. (Arhiwe geçirmek howpsuzrak.)')) {
            return;
          }
          await Api.instance.delete('exam-schedules/${sch['id']}');
          setState(() => _schedules = [for (final t in _schedules) if (t['id'] != sch['id']) t]);
          final next = _shownSchedules.where((t) => t['status'] == 'done').firstOrNull ?? _shownSchedules.firstOrNull;
          if (next != null) {
            await _select(next['id'] as int);
          } else {
            setState(() {
              _current = null;
              _entries = [];
            });
          }
      }
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  void _replace(Map<String, dynamic> sch) => setState(() {
        _schedules = [for (final t in _schedules) t['id'] == sch['id'] ? sch : t];
        if (_current?['id'] == sch['id']) _current = sch;
      });

  Future<void> _select(int id) async {
    setState(() => _current = _schedules.firstWhere((t) => t['id'] == id));
    _watchCurrent();
    await _loadSessionRooms();
    _fixTarget();
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
    final all = (check['issues'] as List).cast<String>();
    final issues = [for (final i in all) if (!_isInfo(i)) i];
    final infos = [for (final i in all) if (_isInfo(i)) i];
    final now = DateTime.now();
    final nameCtl = TextEditingController(text: 'Awtomat · ${_two(now.day)}.${_two(now.month)} ${_two(now.hour)}:${_two(now.minute)}');
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
            for (final i in infos)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Icon(Icons.info_outline, color: Colors.blueGrey),
                  const SizedBox(width: 8),
                  Expanded(child: Text(i)),
                ]),
              ),
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
      padding: const EdgeInsets.fromLTRB(28, 24, 28, 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const PageTitle(
            title: 'Synag raspisaniýesi',
            icon: Icons.fact_check_outlined,
            color: AppColors.exams,
            subtitle: 'Synag möwsümi boýunça awtomat düzmek',
          ),
          const SizedBox(width: 24),
          // Uzyn atlar sygar ýaly saýlawlar galan ýeri paýlaşýar we "..." bilen gysgalýar.
          Expanded(
            flex: 2,
            child: DropdownButton<int>(
              isExpanded: true,
              value: _session?['id'] as int?,
              items: [
                for (final s in _sessions)
                  DropdownMenuItem(
                    value: s['id'] as int,
                    child: Text(
                      '${_sessionLabel(s)} (${examKinds[s['kind']] ?? s['kind']})',
                      overflow: TextOverflow.ellipsis,
                    ),
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
          ),
          const SizedBox(width: 16),
          Expanded(
            flex: 3,
            child: _schedules.isEmpty
                ? const SizedBox()
                : Row(children: [
                    Expanded(
                      child: Tooltip(
                        message: _current == null ? '' : '${_current!['name']}',
                        child: DropdownButton<int>(
                          isExpanded: true,
                          value: _current?['id'] as int?,
                          items: [
                            for (final t in _shownSchedules)
                              DropdownMenuItem(
                                value: t['id'] as int,
                                child: Tooltip(
                                  message: '${t['name']}',
                                  waitDuration: const Duration(milliseconds: 600),
                                  child: Text(
                                    _scheduleLabel(t),
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      color: t['archived'] == true ? Colors.grey : null,
                                      fontWeight: t['published'] == true ? FontWeight.w600 : null,
                                    ),
                                  ),
                                ),
                              ),
                          ],
                          onChanged: (id) => id == null ? null : _select(id),
                        ),
                      ),
                    ),
                    if (!Api.instance.isDean)
                      PopupMenuButton<String>(
                        tooltip: 'Wersiýalar',
                        icon: const Icon(Icons.more_vert),
                        onSelected: _scheduleAction,
                        itemBuilder: (_) => [
                          if (_current != null)
                            const PopupMenuItem(
                                value: 'rename',
                                child: ListTile(leading: Icon(Icons.edit_outlined), title: Text('Adyny üýtget'))),
                          if (_current != null && _current!['archived'] != true && _current!['published'] != true)
                            const PopupMenuItem(
                                value: 'archive',
                                child: ListTile(leading: Icon(Icons.archive_outlined), title: Text('Arhiwe geçir'))),
                          if (_current?['archived'] == true)
                            const PopupMenuItem(
                                value: 'restore',
                                child: ListTile(leading: Icon(Icons.unarchive_outlined), title: Text('Arhiwden yzyna getir'))),
                          PopupMenuItem(
                              value: 'toggle',
                              child: ListTile(
                                leading: Icon(_showArchived ? Icons.visibility_off_outlined : Icons.history),
                                title: Text(_showArchived
                                    ? 'Arhiwi gizle'
                                    : 'Köne wersiýalary görkez ($_archivedCount)'),
                              )),
                          if (_current != null && _current!['published'] != true)
                            const PopupMenuItem(
                                value: 'delete',
                                child: ListTile(
                                    leading: Icon(Icons.delete_outline, color: Colors.red),
                                    title: Text('Doly poz', style: TextStyle(color: Colors.red)))),
                        ],
                      ),
                  ]),
          ),
          const SizedBox(width: 16),
          if (_current?['status'] == 'done' && !Api.instance.isDean) ...[
            PublishButton(
              path: 'exam-schedules/${_current!['id']}/publish',
              published: _current!['published'] == true,
              onChanged: (v) => setState(() {
                _schedules = [
                  for (final t in _schedules) {...t, 'published': t['id'] == _current!['id'] ? v : (v ? false : t['published'])},
                ];
                _current = _schedules.firstWhere((t) => t['id'] == _current!['id']);
              }),
            ),
            const SizedBox(width: 8),
          ],
          OutlinedButton.icon(
            onPressed: _current?['status'] == 'done'
                ? () => showDialog(
                      context: context,
                      builder: (_) => WordDialog(
                        endpoint: 'exam-schedules/${_current!['id']}/docx',
                        title: 'Synag raspisaniýesini Word görnüşinde ýüklemek',
                      ),
                    )
                : null,
            icon: const Icon(Icons.description_outlined),
            label: const Text('Word'),
          ),
          if (!Api.instance.isDean) ...[
          const SizedBox(width: 8),
          FilledButton.icon(
            onPressed: _session == null ? null : _generate,
            icon: const Icon(Icons.auto_awesome),
            label: const Text('Awtomat düz'),
          ),
          ],
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
                _targetId = _visibleTargets.firstOrNull?['id'] as int?;
              });
              _loadEntries();
            },
          ),
          const SizedBox(width: 16),
          DropdownButton<int>(
            value: _targetId,
            hint: const Text('Saýlaň'),
            items: [
              for (final t in _visibleTargets)
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
          for (final i in issues.where((i) => !_isInfo(i)).take(6))
            Padding(padding: const EdgeInsets.only(left: 32, top: 4), child: Text('• $i')),
          for (final i in issues.where(_isInfo))
            Padding(
              padding: const EdgeInsets.only(left: 32, top: 4),
              child: Row(children: [
                const Icon(Icons.info_outline, size: 16, color: Colors.blueGrey),
                const SizedBox(width: 6),
                Expanded(child: Text(i, style: const TextStyle(color: Colors.blueGrey))),
              ]),
            ),
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
          border: TableBorder.all(color: AppColors.border),
          defaultColumnWidth: const FixedColumnWidth(220),
          columnWidths: const {0: FixedColumnWidth(120)},
          defaultVerticalAlignment: TableCellVerticalAlignment.top,
          children: [
            TableRow(
              decoration: const BoxDecoration(
                color: AppColors.gridHeader,
              ),
              children: [
                const Padding(padding: EdgeInsets.all(8), child: Text('Sene', style: gridHeadStyle)),
                for (final p in _periods)
                  Padding(
                    padding: const EdgeInsets.all(8),
                    child: Text(
                      '${p['number']}. ${'${p['starts_at']}'.substring(0, 5)}-${'${p['ends_at']}'.substring(0, 5)}',
                      style: gridHeadStyle,
                    ),
                  ),
              ],
            ),
            for (final d in days)
              TableRow(decoration: const BoxDecoration(color: Colors.white), children: [
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: Text('${_iso(d).substring(8)}.${_iso(d).substring(5, 7)}\n${weekdays[d.weekday - 1]}',
                      style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.exams)),
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
    const color = AppColors.exams;
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
      padding: const EdgeInsets.fromLTRB(9, 7, 8, 7),
      decoration: lessonDecoration(color),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${e['subject']['name']}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
        for (final l in lines) Text(l, style: const TextStyle(fontSize: 12)),
      ]),
    );
  }
}

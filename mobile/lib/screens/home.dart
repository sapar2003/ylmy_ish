import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';
import 'grades.dart';
import 'journal.dart';
import 'shell.dart';
import 'topic.dart';

const weekdays = ['Duşenbe', 'Sişenbe', 'Çarşenbe', 'Penşenbe', 'Anna', 'Şenbe', 'Ýekşenbe'];
const weekdaysShort = ['Du', 'Si', 'Ça', 'Pe', 'An', 'Şe', 'Ýe'];
const months = ['ýanwar', 'fewral', 'mart', 'aprel', 'maý', 'iýun', 'iýul', 'awgust', 'sentýabr', 'oktýabr', 'noýabr', 'dekabr'];
const weekNames = {1: 'Sanawjy hepde', 2: 'Maýdalawjy hepde'};
const lessonTypes = {'lecture': 'Leksiýa', 'practice': 'Amaly', 'lab': 'Tejribe', 'seminar': 'Seminar'};

String hhmm(String t) => t.substring(0, 5);
String longDate(DateTime d) => '${weekdays[d.weekday - 1]}, ${d.day} ${months[d.month - 1]}';
DateTime dayOnly(DateTime d) => DateTime(d.year, d.month, d.day);

// ---------------------------------------------------------------------------------------------
// Raspisaniýe: hepdäniň günleri (zolak) + saýlanan günüň sapaklary
// ---------------------------------------------------------------------------------------------

class ScheduleView extends StatefulWidget {
  const ScheduleView({super.key});

  @override
  State<ScheduleView> createState() => _ScheduleViewState();
}

class _ScheduleViewState extends State<ScheduleView> {
  DateTime _day = dayOnly(DateTime.now().weekday == 7 ? DateTime.now().add(const Duration(days: 1)) : DateTime.now());
  Map<String, dynamic>? _week;
  List<Map<String, dynamic>> _marks = [];
  bool _cached = false;
  bool _loading = true;
  String? _error;

  DateTime get _monday => mondayOf(_day);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final r = await Api.instance.week(_monday);
      if (Api.instance.isStudent) {
        try {
          _marks = (await Api.instance.myMarks()).data;
        } on ApiException catch (_) {} // bahasyz hem raspisaniýe görkezilýär
      }
      if (!mounted) return;
      setState(() {
        _week = r.data;
        _cached = r.cached;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _loading = false;
      });
    }
  }

  /// Talyp: şol sapagyň bahasy (sapak kartasynda görkezilýär).
  String? _markOf(Map<String, dynamic> e, DateTime day) {
    for (final c in _marks) {
      if (c['assignment_id'] != e['assignment_id']) continue;
      for (final m in (c['marks'] as List)) {
        if (m['time_slot_id'] == e['time_slot_id'] && m['day'] == isoDate(day)) return '${m['value']}';
      }
    }
    return null;
  }

  /// Sapagyň şol günki temasy (sapak: assignment + sene + wagt sloty).
  Map<String, dynamic>? _topicOf(Map<String, dynamic> e, DateTime day) =>
      ((_week?['topics'] as List?) ?? []).cast<Map<String, dynamic>>().where((t) =>
          t['assignment_id'] == e['assignment_id'] && t['time_slot_id'] == e['time_slot_id'] && t['day'] == isoDate(day)).firstOrNull;

  void _select(DateTime d) {
    final reload = mondayOf(d) != _monday;
    setState(() => _day = d);
    if (reload) _load();
  }

  List<Map<String, dynamic>> _lessons(int weekday) =>
      ((_week?['entries'] as List?) ?? []).cast<Map<String, dynamic>>().where((e) => e['weekday'] == weekday).toList()
        ..sort((a, b) => '${a['starts_at']}'.compareTo('${b['starts_at']}'));

  @override
  Widget build(BuildContext context) {
    final today = dayOnly(DateTime.now());
    final weekLabel = weekNames[_week?['week']];
    final lessons = _lessons(_day.weekday);
    final now = TimeOfDay.now();
    final nowStr = '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
    final isToday = _day == today;
    final current = isToday
        ? lessons.where((e) => hhmm(e['starts_at']).compareTo(nowStr) <= 0 && hhmm(e['ends_at']).compareTo(nowStr) > 0).firstOrNull
        : null;
    final next = isToday && current == null ? lessons.where((e) => hhmm(e['starts_at']).compareTo(nowStr) > 0).firstOrNull : null;
    final student = Api.instance.isStudent;

    return Column(children: [
      Container(
        color: C.surface,
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
        child: Column(children: [
          Row(children: [
            IconButton(onPressed: () => _select(_day.subtract(const Duration(days: 7))), icon: const Icon(Icons.chevron_left)),
            Expanded(
              child: Column(children: [
                Text('${_monday.day} ${months[_monday.month - 1]} – ${_monday.add(const Duration(days: 5)).day} '
                    '${months[_monday.add(const Duration(days: 5)).month - 1]}',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                if (weekLabel != null) ...[const SizedBox(height: 3), Tag(weekLabel, color: C.primary)],
              ]),
            ),
            IconButton(onPressed: () => _select(_day.add(const Duration(days: 7))), icon: const Icon(Icons.chevron_right)),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            for (var i = 0; i < 6; i++) Expanded(child: _dayChip(_monday.add(Duration(days: i)), today)),
          ]),
        ]),
      ),
      const Divider(),
      Expanded(
        child: RefreshIndicator(
          onRefresh: _load,
          child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 24), children: [
            Row(children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(longDate(_day), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                  if (lessons.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text('${lessons.length} sapak · ${hhmm(lessons.first['starts_at'])}–${hhmm(lessons.last['ends_at'])}',
                        style: const TextStyle(color: C.muted, fontSize: 13)),
                  ],
                ]),
              ),
              if (_day != today && !(today.weekday == 7 && _day == today.add(const Duration(days: 1))))
                TextButton(onPressed: () => _select(today.weekday == 7 ? today.add(const Duration(days: 1)) : today), child: const Text('Şu gün')),
            ]),
            if (_cached) const _OfflineNote(),
            const SizedBox(height: 8),
            if (current != null) NextLessonCard(entry: current, now: true),
            if (next != null) NextLessonCard(entry: next, now: false),
            if (student && Api.instance.student?['subgroup_id'] == null && lessons.any((e) => e['subgroup'] != null))
              const _NoSubgroupNote(),
            if (_loading && _week == null)
              const Padding(padding: EdgeInsets.all(48), child: Center(child: CircularProgressIndicator()))
            else if (_error != null && _week == null)
              EmptyView(icon: Icons.wifi_off, title: 'Birikip bolmady', text: _error)
            else if (_week?['timetable'] == null)
              const EmptyView(icon: Icons.hourglass_empty, title: 'Raspisaniýe heniz çap edilmedi',
                  text: 'Okuw bölümi raspisaniýäni çap edenden soň şu ýerde görüner.')
            else if (lessons.isEmpty)
              const EmptyView(icon: Icons.free_breakfast_outlined, title: 'Sapak ýok', text: 'Bu gün sapagyňyz ýok.')
            else
              for (final e in lessons)
                _LessonTile(
                  entry: e,
                  day: _day,
                  topic: _topicOf(e, _day),
                  mark: student ? _markOf(e, _day) : null,
                  onReturn: _load,
                  badge: identical(e, current) ? 'Häzir' : (identical(e, next) ? 'Indiki' : null),
                ),
          ]),
        ),
      ),
    ]);
  }

  Widget _dayChip(DateTime d, DateTime today) {
    final selected = d == _day;
    final isToday = d == today;
    final has = _lessons(d.weekday).isNotEmpty;
    return GestureDetector(
      onTap: () => _select(d),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 3),
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: selected ? C.primary : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: selected ? C.primary : (isToday ? C.primary.withValues(alpha: 0.4) : Colors.transparent)),
        ),
        child: Column(children: [
          Text(weekdaysShort[d.weekday - 1],
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: selected ? Colors.white70 : C.muted)),
          const SizedBox(height: 4),
          Text('${d.day}', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: selected ? Colors.white : C.text)),
          const SizedBox(height: 4),
          Container(
            width: 5,
            height: 5,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: has ? (selected ? Colors.white : C.primary) : Colors.transparent,
            ),
          ),
        ]),
      ),
    );
  }
}

class _LessonTile extends StatelessWidget {
  const _LessonTile({required this.entry, required this.day, this.badge, this.topic, this.onReturn, this.mark});
  final String? mark; // talybyň şu sapakdaky bahasy
  final Map<String, dynamic> entry;
  final DateTime day;
  final Map<String, dynamic>? topic; // mugallymyň goýan temasy we faýly
  final VoidCallback? onReturn;
  final String? badge;

  @override
  Widget build(BuildContext context) {
    final type = '${entry['lesson_type']}';
    final color = C.lesson(type);
    final groups = entry['stream'] != null
        ? '${entry['stream']['name']}'
        : (entry['groups'] as List).map((g) => g['name']).join(', ');
    final sub = entry['subgroup'] != null ? ' · ${entry['subgroup']['name']}-nji kiçi topar' : '';
    final student = Api.instance.isStudent;
    final past = !student && !day.isAfter(dayOnly(DateTime.now()));
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(
          width: 52,
          child: Padding(
            padding: const EdgeInsets.only(top: 14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(hhmm(entry['starts_at']), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
              Text(hhmm(entry['ends_at']), style: const TextStyle(color: C.subtle, fontSize: 13)),
            ]),
          ),
        ),
        Expanded(
          child: Card(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: BorderSide(color: badge != null ? color : C.border, width: badge != null ? 1.5 : 1),
            ),
            clipBehavior: Clip.antiAlias,
            // Sapaga basyp talyplaryň sanawyny açmak we baha goýmak.
            child: InkWell(
              onTap: student
                  ? null
                  : () async {
                      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => LessonMarksScreen(entry: entry, day: day)));
                      onReturn?.call(); // tema üýtgän bolsa kartany täzelemek
                    },
              child: IntrinsicHeight(
              child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Container(
                  width: 4,
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: const BorderRadius.horizontal(left: Radius.circular(12)),
                  ),
                ),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Wrap(spacing: 6, runSpacing: 4, children: [
                        Tag(lessonTypes[type] ?? type, color: color),
                        if (entry['week'] != null) Tag('diňe ${weekNames[entry['week']]!.toLowerCase()}'),
                        if (badge != null) Tag(badge!, color: C.success),
                      ]),
                      const SizedBox(height: 6),
                      Text('${entry['subject']['name']}',
                          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15, height: 1.3)),
                      const SizedBox(height: 8),
                      _info(Icons.meeting_room_outlined, 'Otag ${entry['room']?['name'] ?? '—'}', bold: true),
                      const SizedBox(height: 3),
                      if (student) ...[
                        _info(Icons.person_outline, '${entry['teacher']['name']}'),
                        if (entry['stream'] != null || sub.isNotEmpty) ...[
                          const SizedBox(height: 3),
                          _info(Icons.groups_outlined, '$groups$sub'),
                        ],
                      ] else
                        _info(Icons.groups_outlined, '$groups$sub'),
                      if (mark != null) ...[
                        const SizedBox(height: 10),
                        Row(children: [
                          const Text('Bahaňyz:', style: TextStyle(fontSize: 13.5, color: C.muted)),
                          const SizedBox(width: 8),
                          MarkBadge(mark!),
                        ]),
                      ],
                      if (topic != null) TopicLine(topic: topic!),
                      if (past) ...[
                        const SizedBox(height: 10),
                        Row(children: [
                          Icon(canMark(day) ? Icons.edit_note : Icons.visibility_outlined, size: 18, color: C.primary),
                          const SizedBox(width: 6),
                          Text(canMark(day) ? 'Baha goý' : 'Bahalary gör',
                              style: const TextStyle(color: C.primary, fontWeight: FontWeight.w600, fontSize: 13.5)),
                        ]),
                      ],
                    ]),
                  ),
                ),
              ]),
            ),
            ),
          ),
        ),
      ]),
    );
  }
}

Widget _info(IconData icon, String text, {bool bold = false}) => Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Icon(icon, size: 16, color: C.muted),
      const SizedBox(width: 6),
      Expanded(
        child: Text(text, style: TextStyle(fontSize: 13.5, color: bold ? C.text : C.muted, fontWeight: bold ? FontWeight.w600 : FontWeight.w400)),
      ),
    ]);

// ---------------------------------------------------------------------------------------------
// Synaglar: gün boýunça toparlanan, geçenler aşakda
// ---------------------------------------------------------------------------------------------

class ExamsView extends StatefulWidget {
  const ExamsView({super.key});

  @override
  State<ExamsView> createState() => _ExamsViewState();
}

class _ExamsViewState extends State<ExamsView> {
  List<Map<String, dynamic>>? _exams;
  bool _cached = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await Api.instance.exams();
      if (!mounted) return;
      setState(() {
        _exams = r.data;
        _cached = r.cached;
        _error = null;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final today = isoDate(DateTime.now());
    final upcoming = (_exams ?? []).where((x) => '${x['day']}'.compareTo(today) >= 0).toList();
    final past = (_exams ?? []).where((x) => '${x['day']}'.compareTo(today) < 0).toList();
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 24), children: [
        if (_cached) const _OfflineNote(),
        if (_exams == null && _error == null)
          const Padding(padding: EdgeInsets.all(48), child: Center(child: CircularProgressIndicator()))
        else if (_exams == null)
          EmptyView(icon: Icons.wifi_off, title: 'Birikip bolmady', text: _error)
        else if (_exams!.isEmpty)
          const EmptyView(icon: Icons.assignment_outlined, title: 'Synag ýok',
              text: 'Çap edilen synag raspisaniýesinde siziň synagyňyz ýok.')
        else ...[
          if (upcoming.isNotEmpty) ..._grouped(upcoming, false) else
            const EmptyView(icon: Icons.task_alt, title: 'Ähli synaglar geçdi'),
          if (past.isNotEmpty) ...[
            const Padding(
              padding: EdgeInsets.fromLTRB(4, 20, 4, 8),
              child: Text('GEÇEN SYNAGLAR', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: C.subtle, letterSpacing: 0.5)),
            ),
            ..._grouped(past, true),
          ],
        ],
      ]),
    );
  }

  List<Widget> _grouped(List<Map<String, dynamic>> exams, bool past) {
    final out = <Widget>[];
    String? day;
    for (final x in exams) {
      if (x['day'] != day) {
        day = '${x['day']}';
        out.add(Padding(
          padding: const EdgeInsets.fromLTRB(4, 10, 4, 8),
          child: Text(longDate(DateTime.parse(day)), style: const TextStyle(fontWeight: FontWeight.w700)),
        ));
      }
      out.add(Opacity(opacity: past ? 0.55 : 1, child: _ExamTile(exam: x)));
    }
    return out;
  }
}

class _ExamTile extends StatelessWidget {
  const _ExamTile({required this.exam});
  final Map<String, dynamic> exam;

  @override
  Widget build(BuildContext context) {
    final examiner = exam['role'] == 'examiner';
    final student = exam['role'] == 'student';
    final groups = (exam['groups'] as List).map((g) => g['name']).join(', ');
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text('${exam['starts_at']}–${exam['ends_at']}', style: const TextStyle(fontWeight: FontWeight.w700)),
              const Spacer(),
              if (!student)
                Tag(examiner ? 'Uly mugallym' : 'Kiçi mugallym', color: examiner ? C.primary : const Color(0xFF7A5AF8)),
            ]),
            const SizedBox(height: 8),
            Text('${exam['subject']['name']}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15, height: 1.3)),
            const SizedBox(height: 8),
            _info(Icons.meeting_room_outlined, 'Otag ${exam['room']?['name'] ?? '—'}', bold: true),
            const SizedBox(height: 3),
            _info(Icons.groups_outlined, groups),
            if (exam['partner'] != null) ...[
              const SizedBox(height: 3),
              _info(Icons.person_outline,
                  '${student ? 'Mugallym' : examiner ? 'Kiçi mugallym' : 'Uly mugallym'}: ${exam['partner']['name']}'),
            ],
          ]),
        ),
      ),
    );
  }
}

class _NoSubgroupNote extends StatelessWidget {
  const _NoSubgroupNote();

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(color: const Color(0xFFFFFAEB), borderRadius: BorderRadius.circular(10)),
        child: const Row(children: [
          Icon(Icons.info_outline, size: 18, color: C.warning),
          SizedBox(width: 8),
          Expanded(
            child: Text('Kiçi toparyňyz bellenmedik, şonuň üçin ähli kiçi toparlaryň sapaklary görünýär. Dekanata ýüz tutuň.',
                style: TextStyle(fontSize: 13)),
          ),
        ]),
      );
}

class _OfflineNote extends StatelessWidget {
  const _OfflineNote();

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(top: 8, bottom: 4),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(color: const Color(0xFFFFFAEB), borderRadius: BorderRadius.circular(10)),
        child: const Row(children: [
          Icon(Icons.cloud_off, size: 18, color: C.warning),
          SizedBox(width: 8),
          Expanded(child: Text('Internet ýok — soňky ýüklenen maglumat görkezilýär.', style: TextStyle(fontSize: 13))),
        ]),
      );
}

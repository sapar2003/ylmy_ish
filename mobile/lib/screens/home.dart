import 'package:flutter/material.dart';

import '../api.dart';
import 'login.dart';

const weekdays = ['Duşenbe', 'Sişenbe', 'Çarşenbe', 'Penşenbe', 'Anna', 'Şenbe', 'Ýekşenbe'];
const weekNames = {1: 'Sanawjy hepde', 2: 'Maýdalawjy hepde'};
const lessonTypes = {'lecture': 'Leksiýa', 'practice': 'Amaly', 'lab': 'Tejribe', 'seminar': 'Seminar'};
const typeColors = {
  'lecture': Color(0xFF3949AB),
  'practice': Color(0xFF8E24AA),
  'lab': Color(0xFF00897B),
  'seminar': Color(0xFFF4511E),
};

String ddmm(DateTime d) => '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}';
String hhmm(String t) => t.substring(0, 5);

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    final me = Api.instance.me ?? {};
    return Scaffold(
      appBar: AppBar(
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Meniň raspisaniýäm', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          Text('${me['teacher']?['name'] ?? me['username'] ?? ''}', style: const TextStyle(fontSize: 13)),
        ]),
        actions: [
          PopupMenuButton<String>(
            onSelected: (v) {
              if (v == 'password') {
                Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ChangePasswordScreen()));
              } else {
                Api.instance.logout();
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'password', child: Text('Paroly çalyş')),
              PopupMenuItem(value: 'logout', child: Text('Çykmak')),
            ],
          ),
        ],
      ),
      body: IndexedStack(index: _tab, children: const [DayView(), WeekView(), ExamsView()]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.today), label: 'Gün'),
          NavigationDestination(icon: Icon(Icons.view_week), label: 'Hepde'),
          NavigationDestination(icon: Icon(Icons.fact_check), label: 'Synaglar'),
        ],
      ),
    );
  }
}

/// Hepdäniň maglumatyny ýükleýän umumy bölek (Gün we Hepde görnüşleri üçin).
mixin WeekLoader<T extends StatefulWidget> on State<T> {
  Map<String, dynamic>? week;
  bool cached = false;
  bool loading = true;
  String? error;

  Future<void> loadWeek(DateTime on) async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final r = await Api.instance.week(on);
      if (!mounted) return;
      setState(() {
        week = r.data;
        cached = r.cached;
        loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        error = e.message;
        loading = false;
      });
    }
  }

  List<Map<String, dynamic>> entriesOn(int weekday) {
    final list = ((week?['entries'] as List?) ?? []).cast<Map<String, dynamic>>()
        .where((e) => e['weekday'] == weekday)
        .toList()
      ..sort((a, b) => '${a['starts_at']}'.compareTo('${b['starts_at']}'));
    return list;
  }

  String weekLabel() {
    final w = week?['week'];
    return w == null ? '' : weekNames[w] ?? '';
  }

  Widget? statusBanner() {
    if (error != null && week == null) {
      return MessageBox(icon: Icons.wifi_off, text: error!, onRetry: null);
    }
    if (week != null && week!['timetable'] == null) {
      return const MessageBox(icon: Icons.hourglass_empty,
          text: 'Raspisaniýe heniz çap edilmedi. Okuw bölümi çap edenden soň şu ýerde görüner.');
    }
    return null;
  }
}

class DayView extends StatefulWidget {
  const DayView({super.key});

  @override
  State<DayView> createState() => _DayViewState();
}

class _DayViewState extends State<DayView> with WeekLoader {
  DateTime _day = DateTime.now();

  @override
  void initState() {
    super.initState();
    loadWeek(_day);
  }

  void _go(int days) {
    final next = DateTime(_day.year, _day.month, _day.day + days);
    final reload = mondayOf(next) != mondayOf(_day);
    setState(() => _day = next);
    if (reload) loadWeek(next);
  }

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    final isToday = isoDate(_day) == isoDate(today);
    final lessons = entriesOn(_day.weekday);
    final now = '${today.hour.toString().padLeft(2, '0')}:${today.minute.toString().padLeft(2, '0')}';
    final next = isToday ? lessons.where((e) => hhmm(e['ends_at']).compareTo(now) > 0).firstOrNull : null;
    final banner = statusBanner();
    return RefreshIndicator(
      onRefresh: () => loadWeek(_day),
      child: ListView(padding: const EdgeInsets.only(bottom: 24), children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 8, 4, 4),
          child: Row(children: [
            IconButton(onPressed: () => _go(-1), icon: const Icon(Icons.chevron_left)),
            Expanded(
              child: Column(children: [
                Text('${weekdays[_day.weekday - 1]}, ${ddmm(_day)}${isToday ? ' · şu gün' : ''}',
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                if (weekLabel().isNotEmpty) Text(weekLabel(), style: TextStyle(color: Theme.of(context).colorScheme.primary)),
              ]),
            ),
            IconButton(onPressed: () => _go(1), icon: const Icon(Icons.chevron_right)),
          ]),
        ),
        if (!isToday)
          Center(child: TextButton(onPressed: () => _go(DateTime(today.year, today.month, today.day)
              .difference(DateTime(_day.year, _day.month, _day.day)).inDays), child: const Text('Şu güne gaýt'))),
        if (cached) const OfflineNote(),
        if (loading && week == null)
          const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()))
        else if (banner != null)
          banner
        else if (lessons.isEmpty)
          const MessageBox(icon: Icons.free_breakfast_outlined, text: 'Bu gün sapagyňyz ýok.')
        else
          for (final e in lessons) LessonCard(entry: e, highlight: identical(e, next)),
      ]),
    );
  }
}

class WeekView extends StatefulWidget {
  const WeekView({super.key});

  @override
  State<WeekView> createState() => _WeekViewState();
}

class _WeekViewState extends State<WeekView> with WeekLoader {
  DateTime _monday = mondayOf(DateTime.now());

  @override
  void initState() {
    super.initState();
    loadWeek(_monday);
  }

  void _go(int weeks) {
    setState(() => _monday = DateTime(_monday.year, _monday.month, _monday.day + 7 * weeks));
    loadWeek(_monday);
  }

  @override
  Widget build(BuildContext context) {
    final banner = statusBanner();
    final total = ((week?['entries'] as List?) ?? []).length;
    return RefreshIndicator(
      onRefresh: () => loadWeek(_monday),
      child: ListView(padding: const EdgeInsets.only(bottom: 24), children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 8, 4, 4),
          child: Row(children: [
            IconButton(onPressed: () => _go(-1), icon: const Icon(Icons.chevron_left)),
            Expanded(
              child: Column(children: [
                Text('${ddmm(_monday)} – ${ddmm(_monday.add(const Duration(days: 6)))}',
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                Text([weekLabel(), if (week != null && banner == null) '$total sapak'].where((s) => s.isNotEmpty).join(' · '),
                    style: TextStyle(color: Theme.of(context).colorScheme.primary)),
              ]),
            ),
            IconButton(onPressed: () => _go(1), icon: const Icon(Icons.chevron_right)),
          ]),
        ),
        if (cached) const OfflineNote(),
        if (loading && week == null)
          const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()))
        else if (banner != null)
          banner
        else
          for (var d = 1; d <= 6; d++) ...[
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 4),
              child: Text('${weekdays[d - 1]}, ${ddmm(_monday.add(Duration(days: d - 1)))}',
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
            ),
            if (entriesOn(d).isEmpty)
              const Padding(padding: EdgeInsets.fromLTRB(16, 2, 16, 4), child: Text('Sapak ýok', style: TextStyle(color: Colors.grey)))
            else
              for (final e in entriesOn(d)) LessonCard(entry: e),
          ],
      ]),
    );
  }
}

class LessonCard extends StatelessWidget {
  const LessonCard({super.key, required this.entry, this.highlight = false});
  final Map<String, dynamic> entry;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final type = '${entry['lesson_type']}';
    final color = typeColors[type] ?? Colors.blueGrey;
    final groups = entry['stream'] != null
        ? '${entry['stream']['name']}'
        : (entry['groups'] as List).map((g) => g['name']).join(', ');
    final sub = entry['subgroup'] != null ? ' · ${entry['subgroup']['name']}-nji kiçi topar' : '';
    final week = entry['week'] != null ? ' · diňe ${weekNames[entry['week']]!.toLowerCase()}' : '';
    return Card(
      elevation: highlight ? 3 : 0.5,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: highlight ? BorderSide(color: color, width: 2) : BorderSide.none,
      ),
      child: IntrinsicHeight(
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Container(width: 5, decoration: BoxDecoration(color: color, borderRadius: const BorderRadius.horizontal(left: Radius.circular(12)))),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 4, 12),
            child: SizedBox(
              width: 52,
              child: Column(children: [
                Text(hhmm(entry['starts_at']), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                Text(hhmm(entry['ends_at']), style: const TextStyle(color: Colors.grey)),
              ]),
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(8, 12, 12, 12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if (highlight)
                  Text('INDIKI SAPAK', style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w800)),
                Text('${entry['subject']['name']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15)),
                Text('${lessonTypes[type] ?? type}$week', style: TextStyle(color: color, fontSize: 12.5)),
                const SizedBox(height: 4),
                Row(children: [
                  const Icon(Icons.groups_outlined, size: 16),
                  const SizedBox(width: 4),
                  Expanded(child: Text('$groups$sub')),
                ]),
                Row(children: [
                  const Icon(Icons.meeting_room_outlined, size: 16),
                  const SizedBox(width: 4),
                  Text('Otag ${entry['room']?['name'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w600)),
                ]),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}

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
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.only(top: 8, bottom: 24), children: [
        if (_cached) const OfflineNote(),
        if (_exams == null && _error == null)
          const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()))
        else if (_exams == null)
          MessageBox(icon: Icons.wifi_off, text: _error!)
        else if (_exams!.isEmpty)
          const MessageBox(icon: Icons.fact_check_outlined, text: 'Çap edilen synag raspisaniýesinde siziň synagyňyz ýok.')
        else
          for (final x in _exams!) ExamCard(exam: x, past: '${x['day']}'.compareTo(today) < 0),
      ]),
    );
  }
}

class ExamCard extends StatelessWidget {
  const ExamCard({super.key, required this.exam, required this.past});
  final Map<String, dynamic> exam;
  final bool past;

  @override
  Widget build(BuildContext context) {
    final day = DateTime.parse('${exam['day']}');
    final examiner = exam['role'] == 'examiner';
    final color = examiner ? const Color(0xFFD81B60) : const Color(0xFF5E35B1);
    return Opacity(
      opacity: past ? 0.5 : 1,
      child: Card(
        elevation: 0.5,
        child: ListTile(
          contentPadding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
          leading: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Text(ddmm(day), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            Text(weekdays[day.weekday - 1].substring(0, 3), style: const TextStyle(color: Colors.grey)),
          ]),
          title: Text('${exam['subject']['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${exam['starts_at']}–${exam['ends_at']} · ${(exam['groups'] as List).map((g) => g['name']).join(', ')}'),
            Text('Otag ${exam['room']?['name'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w600)),
            Text('${examiner ? 'Siz — uly mugallym' : 'Siz — kiçi mugallym'}'
                '${exam['partner'] != null ? ' · bilen: ${exam['partner']['name']}' : ''}', style: TextStyle(color: color)),
            Text('${exam['session']['name']}', style: const TextStyle(fontSize: 12, color: Colors.grey)),
          ]),
        ),
      ),
    );
  }
}

class OfflineNote extends StatelessWidget {
  const OfflineNote({super.key});

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.fromLTRB(12, 4, 12, 4),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(color: Colors.amber.shade100, borderRadius: BorderRadius.circular(10)),
        child: const Row(children: [
          Icon(Icons.cloud_off, size: 18),
          SizedBox(width: 8),
          Expanded(child: Text('Serwere birikip bolmady — soňky ýüklenen raspisaniýe görkezilýär.')),
        ]),
      );
}

class MessageBox extends StatelessWidget {
  const MessageBox({super.key, required this.icon, required this.text, this.onRetry});
  final IconData icon;
  final String text;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(32),
        child: Column(children: [
          Icon(icon, size: 48, color: Colors.grey),
          const SizedBox(height: 12),
          Text(text, textAlign: TextAlign.center),
        ]),
      );
}

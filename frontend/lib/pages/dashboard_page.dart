import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';

/// Baş sahypa: esasy sanlar, mugallymlara çap edilen raspisaniýeler we ädimme-ädim taýýarlyk sanawy
/// (näme edildi, indiki näme etmeli). Her kart degişli sahypany açýar.
class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key, required this.onOpen});
  final ValueChanged<String> onOpen;

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  Map<String, int> _count = {};
  int _students = 0;
  List<Map<String, dynamic>> _timetables = [];
  List<Map<String, dynamic>> _exams = [];
  int _teacherAccounts = 0;
  bool _loading = true;
  String? _error;

  static const _endpoints = [
    'faculties', 'specialties', 'groups', 'teachers', 'rooms', 'subjects', 'curriculum', 'assignments',
    'time-slots', 'exams',
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await Future.wait([
        for (final e in _endpoints) Api.instance.get(e, {'limit': 1}),
        Api.instance.list('groups'),
        Api.instance.get('timetables'),
        Api.instance.get('exam-schedules'),
        Api.instance.get('users'),
      ]);
      if (!mounted) return;
      final n = _endpoints.length;
      setState(() {
        _count = {for (var i = 0; i < n; i++) _endpoints[i]: (r[i] as Map)['total'] as int};
        _students = (r[n] as List).fold<int>(0, (s, g) => s + ((g as Map)['student_count'] as int? ?? 0));
        _timetables = (r[n + 1] as List).cast<Map<String, dynamic>>();
        _exams = (r[n + 2] as List).cast<Map<String, dynamic>>();
        _teacherAccounts = (r[n + 3] as List).where((u) => u['role'] == 'teacher').length;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  int c(String k) => _count[k] ?? 0;

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return EmptyState(icon: Icons.cloud_off, title: 'Maglumat ýüklenmedi', text: _error,
          action: OutlinedButton(onPressed: _load, child: const Text('Gaýtadan synanyş')));
    }
    if (_loading) return const Center(child: CircularProgressIndicator());
    final publishedTt = _timetables.where((t) => t['published'] == true).firstOrNull;
    final publishedEx = _exams.where((t) => t['published'] == true).toList();
    final doneTt = _timetables.any((t) => t['status'] == 'done');
    final steps = [
      _Step('Uniwersitetiň gurluşy', 'Fakultetler, hünärler we toparlar',
          c('faculties') > 0 && c('specialties') > 0 && c('groups') > 0, 'groups', '${c('groups')} topar'),
      _Step('Mugallymlar', 'Mugallymlar we olaryň kafedralary', c('teachers') > 0, 'teachers', '${c('teachers')} mugallym'),
      _Step('Otaglar', 'Sygymy, görnüşi we fakulteti bilen', c('rooms') > 0, 'rooms', '${c('rooms')} otag'),
      _Step('Smenalar we sapak wagtlary', 'Jübütleriň başlanýan we gutarýan wagty', c('time-slots') > 0, 'shifts',
          '${c('time-slots')} wagt sloty'),
      _Step('Okuw meýilnamasy', 'Her toparyň dersleri, sagatlary we mugallymlary',
          c('curriculum') > 0 && c('assignments') > 0, 'curriculum', '${c('curriculum')} ýazgy'),
      _Step('Raspisaniýe düzmek', '"Awtomat düz" — programma özi düzýär', doneTt, 'timetable',
          '${_timetables.where((t) => t['status'] == 'done').length} wersiýa'),
      _Step('Mugallymlara çap etmek', 'Mugallymlar telefonda diňe çap edileni görýär', publishedTt != null, 'timetable',
          publishedTt == null ? 'çap edilmedi' : 'çap edildi'),
      _Step('Mugallym hasaplary', 'Telefon programmasy üçin login we parol', _teacherAccounts > 0, 'accounts',
          '$_teacherAccounts hasap'),
    ];
    final done = steps.where((s) => s.done).length;

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.fromLTRB(32, 28, 32, 32), children: [
        const PageTitle(
          title: 'Baş sahypa',
          icon: Icons.space_dashboard_outlined,
          color: AppColors.primary,
          subtitle: 'Raspisaniýäniň umumy ýagdaýy we indiki ädimler',
        ),
        const SizedBox(height: 24),
        LayoutBuilder(builder: (context, box) {
          final cols = box.maxWidth > 1100 ? 6 : (box.maxWidth > 700 ? 3 : 2);
          final w = (box.maxWidth - (cols - 1) * 16) / cols;
          return Wrap(spacing: 16, runSpacing: 16, children: [
            for (final k in [
              _Kpi('Fakultet', c('faculties'), Icons.account_balance_outlined, 'faculties'),
              _Kpi('Topar', c('groups'), Icons.groups_outlined, 'groups', '$_students talyp'),
              _Kpi('Mugallym', c('teachers'), Icons.person_outline, 'teachers'),
              _Kpi('Otag', c('rooms'), Icons.meeting_room_outlined, 'rooms'),
              _Kpi('Ders', c('subjects'), Icons.menu_book_outlined, 'subjects'),
              _Kpi('Synag', c('exams'), Icons.assignment_outlined, 'exams'),
            ])
              SizedBox(width: w, child: _kpiCard(k)),
          ]);
        }),
        const SizedBox(height: 24),
        LayoutBuilder(builder: (context, box) {
          final wide = box.maxWidth > 1000;
          final checklist = _checklist(steps, done);
          final status = _publishStatus(publishedTt, publishedEx);
          return wide
              ? Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Expanded(flex: 3, child: checklist),
                  const SizedBox(width: 20),
                  Expanded(flex: 2, child: status),
                ])
              : Column(children: [checklist, const SizedBox(height: 20), status]);
        }),
      ]),
    );
  }

  Widget _kpiCard(_Kpi k) => Card(
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () => widget.onOpen(k.page),
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Icon(k.icon, size: 18, color: AppColors.textMuted),
                const SizedBox(width: 8),
                Text(k.label, style: const TextStyle(color: AppColors.textMuted, fontWeight: FontWeight.w500)),
              ]),
              const SizedBox(height: 10),
              Text('${k.value}', style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w700)),
              Text(k.note ?? ' ', style: const TextStyle(fontSize: 12.5, color: AppColors.textMuted)),
            ]),
          ),
        ),
      );

  Widget _checklist(List<_Step> steps, int done) => Card(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Expanded(child: Text('Raspisaniýe taýýarlamak ädimleri', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700))),
              Text('$done / ${steps.length}', style: const TextStyle(fontWeight: FontWeight.w600, color: AppColors.textMuted)),
            ]),
            const SizedBox(height: 10),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: done / steps.length,
                minHeight: 6,
                backgroundColor: AppColors.background,
                color: AppColors.success,
              ),
            ),
            const SizedBox(height: 12),
            for (final (i, s) in steps.indexed) ...[
              if (i > 0) const Divider(),
              InkWell(
                onTap: () => widget.onOpen(s.page),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Row(children: [
                    Container(
                      width: 28,
                      height: 28,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: s.done ? AppColors.successSoft : AppColors.background,
                        border: Border.all(color: s.done ? AppColors.success : AppColors.borderStrong),
                      ),
                      child: s.done
                          ? const Icon(Icons.check, size: 16, color: AppColors.success)
                          : Text('${i + 1}', style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: AppColors.textMuted)),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(s.title, style: const TextStyle(fontWeight: FontWeight.w600)),
                        Text(s.subtitle, style: const TextStyle(fontSize: 12.5, color: AppColors.textMuted)),
                      ]),
                    ),
                    StatusPill(s.note, color: s.done ? AppColors.success : AppColors.textMuted),
                    const SizedBox(width: 6),
                    const Icon(Icons.chevron_right, color: AppColors.textSubtle),
                  ]),
                ),
              ),
            ],
          ]),
        ),
      );

  Widget _publishStatus(Map<String, dynamic>? tt, List<Map<String, dynamic>> exams) => Column(children: [
        _statusCard(
          icon: Icons.calendar_view_week_outlined,
          title: 'Hepdelik raspisaniýe',
          ok: tt != null,
          text: tt == null
              ? 'Mugallymlara heniz çap edilmedi. Raspisaniýe sahypasynda wersiýany saýlap "Mugallymlara çap et" basyň.'
              : '${tt['name']}\n${tt['entry_count']} sapak${tt['weeks'] == 2 ? ' · sanawjy/maýdalawjy hepde' : ''}',
          page: 'timetable',
        ),
        const SizedBox(height: 16),
        _statusCard(
          icon: Icons.fact_check_outlined,
          title: 'Synag raspisaniýesi',
          ok: exams.isNotEmpty,
          text: exams.isEmpty
              ? 'Mugallymlara heniz çap edilmedi.'
              : exams.map((e) => '${e['name']} · ${e['entry_count']} synag').join('\n'),
          page: 'exam-timetable',
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Çalt hereketler', style: TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 12),
              Wrap(spacing: 8, runSpacing: 8, children: [
                FilledButton.icon(
                  onPressed: () => widget.onOpen('timetable'),
                  icon: const Icon(Icons.auto_awesome, size: 18),
                  label: const Text('Raspisaniýe düz'),
                ),
                OutlinedButton.icon(
                  onPressed: () => widget.onOpen('exam-timetable'),
                  icon: const Icon(Icons.fact_check_outlined, size: 18),
                  label: const Text('Synag raspisaniýesi'),
                ),
                OutlinedButton.icon(
                  onPressed: () => widget.onOpen('accounts'),
                  icon: const Icon(Icons.badge_outlined, size: 18),
                  label: const Text('Mugallym hasaplary'),
                ),
              ]),
            ]),
          ),
        ),
      ]);

  Widget _statusCard({required IconData icon, required String title, required bool ok, required String text, required String page}) =>
      Card(
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () => widget.onOpen(page),
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Icon(icon, size: 20, color: AppColors.textMuted),
                const SizedBox(width: 8),
                Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w700))),
                ok
                    ? const StatusPill('Mugallymlara çap edildi', color: AppColors.success, icon: Icons.check_circle)
                    : const StatusPill('Çap edilmedi', color: AppColors.warning, icon: Icons.schedule),
              ]),
              const SizedBox(height: 10),
              Text(text, style: const TextStyle(color: AppColors.textMuted, height: 1.45)),
            ]),
          ),
        ),
      );
}

class _Kpi {
  const _Kpi(this.label, this.value, this.icon, this.page, [this.note]);
  final String label;
  final int value;
  final IconData icon;
  final String page;
  final String? note;
}

class _Step {
  const _Step(this.title, this.subtitle, this.done, this.page, this.note);
  final String title;
  final String subtitle;
  final bool done;
  final String page;
  final String note;
}

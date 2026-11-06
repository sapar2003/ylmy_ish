import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';
import 'home.dart' show lessonTypes, longDate;
import 'journal.dart' show markColor;

/// Talybyň öz bahalary: dersler boýunça ortaça baha we "gm" sany.
class GradesView extends StatefulWidget {
  const GradesView({super.key});

  @override
  State<GradesView> createState() => _GradesViewState();
}

class _GradesViewState extends State<GradesView> {
  List<Map<String, dynamic>>? _courses;
  bool _cached = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await Api.instance.myMarks();
      if (!mounted) return;
      setState(() {
        _courses = r.data;
        _cached = r.cached;
        _error = null;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final courses = _courses;
    final all = [for (final c in courses ?? <Map<String, dynamic>>[]) ...(c['marks'] as List).cast<Map<String, dynamic>>()];
    final nums = [for (final m in all) if (m['value'] != 'gm') int.parse('${m['value']}')];
    final absent = all.where((m) => m['value'] == 'gm').length;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.fromLTRB(16, 16, 16, 24), children: [
        if (courses == null && _error == null)
          const Padding(padding: EdgeInsets.all(48), child: Center(child: CircularProgressIndicator()))
        else if (courses == null)
          EmptyView(icon: Icons.wifi_off, title: 'Birikip bolmady', text: _error)
        else if (courses.isEmpty)
          const EmptyView(icon: Icons.grade_outlined, title: 'Sapak ýok', text: 'Çap edilen raspisaniýede sapagyňyz ýok.')
        else ...[
          if (_cached) const Padding(
            padding: EdgeInsets.only(bottom: 10),
            child: Text('Internet ýok — soňky ýüklenen bahalar görkezilýär.', style: TextStyle(color: C.muted, fontSize: 13)),
          ),
          Row(children: [
            Expanded(child: _Stat(nums.isEmpty ? '—' : (nums.reduce((a, b) => a + b) / nums.length).toStringAsFixed(2), 'Ortaça baha', C.primary)),
            const SizedBox(width: 10),
            Expanded(child: _Stat('${all.length}', 'Jemi baha', C.text)),
            const SizedBox(width: 10),
            Expanded(child: _Stat('$absent', 'Gatnaşmadyk (gm)', absent > 0 ? C.danger : C.text)),
          ]),
          const SizedBox(height: 14),
          for (final c in courses)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Card(
                clipBehavior: Clip.antiAlias,
                child: InkWell(
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CourseMarksScreen(course: c))),
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Row(children: [
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('${c['subject']}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15, height: 1.3)),
                          const SizedBox(height: 6),
                          Wrap(spacing: 6, runSpacing: 4, children: [
                            Tag(lessonTypes[c['lesson_type']] ?? '${c['lesson_type']}', color: C.lesson('${c['lesson_type']}')),
                            if ((c['absent'] as int) > 0) Tag('gm: ${c['absent']}', color: C.danger),
                          ]),
                          const SizedBox(height: 6),
                          Text('${c['teacher']}', style: const TextStyle(color: C.muted, fontSize: 13)),
                        ]),
                      ),
                      const SizedBox(width: 12),
                      Column(children: [
                        Text(c['average'] == null ? '—' : '${c['average']}',
                            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: C.primary)),
                        const Text('ortaça', style: TextStyle(fontSize: 12, color: C.subtle)),
                      ]),
                      const SizedBox(width: 4),
                      const Icon(Icons.chevron_right, color: C.subtle),
                    ]),
                  ),
                ),
              ),
            ),
        ],
      ]),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat(this.value, this.label, this.color);
  final String value;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
          child: Column(children: [
            Text(value, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: color)),
            const SizedBox(height: 4),
            Text(label, textAlign: TextAlign.center, style: const TextStyle(fontSize: 12, color: C.muted)),
          ]),
        ),
      );
}

/// Bir dersiň gündelik bahalary (täzesi ýokarda).
class CourseMarksScreen extends StatelessWidget {
  const CourseMarksScreen({super.key, required this.course});
  final Map<String, dynamic> course;

  @override
  Widget build(BuildContext context) {
    final marks = (course['marks'] as List).cast<Map<String, dynamic>>().reversed.toList();
    return Scaffold(
      appBar: AppBar(title: Text('${course['subject']}', overflow: TextOverflow.ellipsis)),
      body: ListView(padding: const EdgeInsets.fromLTRB(16, 12, 16, 24), children: [
        Text('${lessonTypes[course['lesson_type']] ?? ''} · ${course['teacher']}', style: const TextStyle(color: C.muted)),
        const SizedBox(height: 12),
        if (marks.isEmpty)
          const EmptyView(icon: Icons.grade_outlined, title: 'Baha ýok', text: 'Bu ders boýunça heniz baha goýulmandyr.')
        else
          Card(
            child: Column(children: [
              for (final (i, m) in marks.indexed) ...[
                if (i > 0) const Divider(),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  child: Row(children: [
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(longDate(DateTime.parse('${m['day']}')), style: const TextStyle(fontWeight: FontWeight.w500)),
                        const SizedBox(height: 2),
                        Text('${m['starts_at']}', style: const TextStyle(color: C.subtle, fontSize: 13)),
                        if (m['can_change'] == true) ...[
                          const SizedBox(height: 4),
                          const Text('Mugallym heniz üýtgedip biler', style: TextStyle(color: C.warning, fontSize: 12)),
                        ],
                      ]),
                    ),
                    MarkBadge('${m['value']}'),
                  ]),
                ),
              ],
            ]),
          ),
      ]),
    );
  }
}

class MarkBadge extends StatelessWidget {
  const MarkBadge(this.value, {super.key});
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(minWidth: 40),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        alignment: Alignment.center,
        decoration: BoxDecoration(color: markColor(value), borderRadius: BorderRadius.circular(10)),
        child: Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 16)),
      );
}

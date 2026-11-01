import 'package:flutter/material.dart';
import 'package:web/web.dart' as web;

import '../api.dart';

/// Raspisaniýäni Word (.docx) görnüşinde ýüklemek: toparlary, sahypalara bölmegi, görnüşi we
/// golaýanlaryň atlaryny saýlamak. Faýly backend döredýär (`/timetables/{id}/docx` ýa-da
/// `/exam-schedules/{id}/docx`), brauzer ony ýükleýär.
class WordDialog extends StatefulWidget {
  const WordDialog({super.key, required this.endpoint, required this.title});

  /// Meselem 'timetables/24/docx'.
  final String endpoint;
  final String title;

  @override
  State<WordDialog> createState() => _WordDialogState();
}

enum PageSplit { specialty, course, all }

class _WordDialogState extends State<WordDialog> {
  List<Map<String, dynamic>> _groups = [];
  Map<int, Map<String, dynamic>> _specialties = {};
  final Set<int> _selected = {};
  PageSplit _split = PageSplit.specialty;
  bool _mini = false;
  bool _loading = true;

  // Adaty bahalar STKF-iň Word faýllaryndan.
  final _fields = {
    'academic_year': TextEditingController(text: '2026/2027'),
    'semester': TextEditingController(text: 'I'),
    'prorector': TextEditingController(text: 'S. Hudaýwerenow'),
    'rector': TextEditingController(text: 'B. Atamanow'),
    'dean_title': TextEditingController(text: 'Fakultetiň dekanynyň w.ý.ý.'),
    'dean': TextEditingController(text: 'D. Tejenow'),
    'office_head': TextEditingController(text: 'M. Babaýew'),
  };
  static const _labels = {
    'academic_year': 'Okuw ýyly',
    'semester': 'Ýarymýyl',
    'prorector': 'Okuw işleri boýunça prorektor',
    'rector': 'Rektor',
    'dean_title': 'Dekanyň wezipesi',
    'dean': 'Dekan',
    'office_head': 'Okuw bölüminiň başlygy',
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in _fields.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    final r = await Future.wait([Api.instance.list('groups'), Api.instance.list('specialties')]);
    if (!mounted) return;
    setState(() {
      _groups = r[0]..sort((a, b) => '${a['name']}'.compareTo('${b['name']}'));
      _specialties = {for (final s in r[1]) s['id'] as int: s};
      _loading = false;
    });
  }

  bool _isMaster(Map<String, dynamic> g) => _specialties[g['specialty_id']]?['level'] == 'master';

  /// Kurs bölümleri: "1-nji kurs", ..., "Magistr".
  Map<String, List<Map<String, dynamic>>> get _byCourse {
    final out = <String, List<Map<String, dynamic>>>{};
    for (final g in _groups) {
      final key = _isMaster(g) ? 'Magistr ${g['course']}' : '${g['course']}-nji kurs';
      out.putIfAbsent(key, () => []).add(g);
    }
    return Map.fromEntries(out.entries.toList()..sort((a, b) => a.key.compareTo(b.key)));
  }

  /// Saýlanan toparlary sahypalara bölmek (her sahypa = Word-da bir tablisa).
  List<List<int>> get _pages {
    final chosen = _groups.where((g) => _selected.contains(g['id'])).toList();
    String key(Map<String, dynamic> g) => switch (_split) {
          PageSplit.specialty => '${_isMaster(g)}|${g['course']}|${_specialties[g['specialty_id']]?['code']}',
          PageSplit.course => '${_isMaster(g)}|${g['course']}',
          PageSplit.all => '',
        };
    final pages = <String, List<int>>{};
    for (final g in chosen) {
      pages.putIfAbsent(key(g), () => []).add(g['id'] as int);
    }
    return pages.values.toList();
  }

  void _download() {
    final url = Api.instance.url(widget.endpoint, {
      'page': [for (final pg in _pages) pg.join(',')],
      'mini': _mini,
      for (final e in _fields.entries) e.key: e.value.text.trim(),
    });
    web.window.open(url.toString(), '_blank');
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final pages = _pages;
    final widest = pages.fold<int>(0, (m, pg) => pg.length > m ? pg.length : m);
    return AlertDialog(
      title: Text(widget.title),
      content: SizedBox(
        width: 640,
        child: _loading
            ? const SizedBox(height: 120, child: Center(child: CircularProgressIndicator()))
            : SingleChildScrollView(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('Toparlar', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  for (final e in _byCourse.entries) ...[
                    Row(children: [
                      Text(e.key, style: const TextStyle(fontWeight: FontWeight.w600)),
                      TextButton(
                        onPressed: () => setState(() {
                          final ids = e.value.map((g) => g['id'] as int);
                          ids.every(_selected.contains) ? _selected.removeAll(ids) : _selected.addAll(ids);
                        }),
                        child: const Text('hemmesi'),
                      ),
                    ]),
                    Wrap(spacing: 6, runSpacing: 6, children: [
                      for (final g in e.value)
                        FilterChip(
                          label: Text('${g['name']}'),
                          selected: _selected.contains(g['id']),
                          onSelected: (on) => setState(
                            () => on ? _selected.add(g['id'] as int) : _selected.remove(g['id'] as int),
                          ),
                        ),
                    ]),
                    const SizedBox(height: 8),
                  ],
                  const Divider(),
                  const Text('Sahypalar', style: TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 6),
                  SegmentedButton<PageSplit>(
                    segments: const [
                      ButtonSegment(value: PageSplit.specialty, label: Text('Her hünär aýry')),
                      ButtonSegment(value: PageSplit.course, label: Text('Her kurs aýry')),
                      ButtonSegment(value: PageSplit.all, label: Text('Hemmesi bir sahypa')),
                    ],
                    selected: {_split},
                    onSelectionChanged: (s) => setState(() => _split = s.first),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _selected.isEmpty
                        ? 'Toparlary saýlaň.'
                        : '${pages.length} sahypa (tablisa)${widest > 6 ? ' — bir sahypada $widest topar köp, okamak kyn bolar' : ''}.',
                    style: TextStyle(color: widest > 6 ? Theme.of(context).colorScheme.error : null),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Mini (ykjam çap)'),
                    subtitle: const Text('Kiçi şrift we gyralar — bir sahypa sygdyrmak üçin'),
                    value: _mini,
                    onChanged: (v) => setState(() => _mini = v),
                  ),
                  ExpansionTile(
                    tilePadding: EdgeInsets.zero,
                    title: const Text('Okuw ýyly we golaýanlar'),
                    children: [
                      for (final e in _fields.entries)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: TextField(
                            controller: e.value,
                            decoration: InputDecoration(labelText: _labels[e.key], isDense: true),
                          ),
                        ),
                    ],
                  ),
                ]),
              ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Ýatyr')),
        FilledButton.icon(
          onPressed: _selected.isEmpty ? null : _download,
          icon: const Icon(Icons.download),
          label: const Text('Word ýükle'),
        ),
      ],
    );
  }
}

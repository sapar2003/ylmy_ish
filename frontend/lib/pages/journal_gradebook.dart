import 'package:flutter/material.dart';

import '../resources.dart';
import '../theme.dart';

const markValues = ['5', '4', '3', '2', 'gm'];

Color markColor(String? v) => switch (v) {
      '5' => AppColors.success,
      '4' => AppColors.secondary,
      '3' => AppColors.warning,
      '2' => AppColors.danger,
      'gm' => AppColors.textMuted,
      _ => AppColors.textSubtle,
    };

String lessonTypeShort(dynamic t) => lessonTypes['$t'] ?? '$t';

/// Bir dersiň žurnaly: ýokarda jemi san, sol tarapda gozganmaýan talyplar, sagda seneler.
class JournalGradebook extends StatefulWidget {
  const JournalGradebook({super.key, required this.book, required this.onSetMark, this.onCreateDemo});
  final Map<String, dynamic> book;
  final Future<void> Function(Map<String, dynamic> row, int col, String? value) onSetMark;
  final VoidCallback? onCreateDemo;

  @override
  State<JournalGradebook> createState() => _JournalGradebookState();
}

class _JournalGradebookState extends State<JournalGradebook> {
  static const _rowH = 42.0;
  static const _headH = 56.0;
  static const _cellW = 52.0;
  static const _nameW = 260.0;
  static const _statW = 56.0;
  static const _weekdays = ['Du', 'Si', 'Ça', 'Pe', 'An', 'Şe', 'Ýe'];

  final _left = ScrollController();
  final _right = ScrollController();
  final _horizontal = ScrollController();
  bool _syncing = false;
  String _query = '';
  Offset _tapAt = Offset.zero; // baha menýusy basylan ýerde açylýar

  @override
  void initState() {
    super.initState();
    _left.addListener(() => _sync(_left, _right));
    _right.addListener(() => _sync(_right, _left));
    // Iň täze sapaklar görünsin.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_horizontal.hasClients) _horizontal.jumpTo(_horizontal.position.maxScrollExtent);
    });
  }

  void _sync(ScrollController from, ScrollController to) {
    if (_syncing || !to.hasClients) return;
    _syncing = true;
    to.jumpTo(from.offset.clamp(0, to.position.maxScrollExtent));
    _syncing = false;
  }

  @override
  void dispose() {
    _left.dispose();
    _right.dispose();
    _horizontal.dispose();
    super.dispose();
  }

  Future<void> _openMenu(Offset at, Map<String, dynamic> row, int col) async {
    final current = (row['marks'] as List)[col] as String?;
    final size = MediaQuery.sizeOf(context);
    final v = await showMenu<String>(
      context: context,
      position: RelativeRect.fromLTRB(at.dx, at.dy, size.width - at.dx, size.height - at.dy),
      constraints: const BoxConstraints(minWidth: 150, maxWidth: 220),
      items: [
        for (final m in markValues)
          PopupMenuItem(
            value: m,
            height: 38,
            child: Row(children: [
              _MarkChip(m),
              const SizedBox(width: 10),
              Flexible(
                child: Text(m == 'gm' ? 'Gatnaşmady' : '$m baha', overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontWeight: current == m ? FontWeight.w700 : FontWeight.w400)),
              ),
            ]),
          ),
        if (current != null)
          const PopupMenuItem(
            value: '',
            height: 38,
            child: Row(children: [
              Icon(Icons.close, size: 18, color: AppColors.danger),
              SizedBox(width: 10),
              Flexible(child: Text('Bahany aýyr', overflow: TextOverflow.ellipsis, style: TextStyle(color: AppColors.danger))),
            ]),
          ),
      ],
    );
    if (v == null || v == current || (v.isEmpty && current == null)) return;
    await widget.onSetMark(row, col, v.isEmpty ? null : v);
    if (mounted) setState(() {});
  }

  static String _short(String iso) => '${iso.substring(8, 10)}.${iso.substring(5, 7)}';

  @override
  Widget build(BuildContext context) {
    final book = widget.book;
    final cols = (book['columns'] as List).cast<Map<String, dynamic>>();
    final allRows = (book['rows'] as List).cast<Map<String, dynamic>>();
    final groups = (book['groups'] as List).join(', ');
    final sub = book['subgroup'] != null ? ' · ${book['subgroup']}-nji kiçi topar' : '';
    final q = _query.toLowerCase();
    final rows = allRows.where((r) => q.isEmpty || '${r['student']['name']}'.toLowerCase().contains(q)).toList();
    final multiGroup = (book['groups'] as List).length > 1;

    final nums = [for (final r in allRows) for (final m in r['marks'] as List) if (m != null && m != 'gm') int.parse('$m')];
    final absent = [for (final r in allRows) r['absent'] as int].fold(0, (a, b) => a + b);

    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(18, 14, 14, 12),
          child: Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${book['subject']} · ${lessonTypeShort(book['lesson_type'])}$sub',
                    overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                const SizedBox(height: 3),
                Text('$groups · ${book['teacher']}', overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13, color: AppColors.textMuted)),
              ]),
            ),
            const SizedBox(width: 12),
            _Stat('${allRows.length}', 'talyp'),
            _Stat('${cols.length}', 'sapak'),
            _Stat(nums.isEmpty ? '—' : (nums.reduce((a, b) => a + b) / nums.length).toStringAsFixed(2), 'ortaça'),
            _Stat('$absent', 'gm'),
            const SizedBox(width: 12),
            SizedBox(
              width: 200,
              child: TextField(
                decoration: const InputDecoration(prefixIcon: Icon(Icons.search, size: 20), hintText: 'Talyp gözle', isDense: true),
                onChanged: (v) => setState(() => _query = v),
              ),
            ),
          ]),
        ),
        const Divider(height: 1),
        Expanded(child: allRows.isEmpty ? _noStudents() : cols.isEmpty ? _noLessons() : _table(cols, rows, multiGroup)),
      ]),
    );
  }

  Widget _noStudents() => EmptyState(
        icon: Icons.people_outline,
        title: 'Talyp ýok',
        text: 'Talyplar sahypasyndan goşuň.',
        action: widget.onCreateDemo == null
            ? null
            : OutlinedButton.icon(
                onPressed: widget.onCreateDemo,
                icon: const Icon(Icons.person_add_alt),
                label: const Text('Synag talyplaryny döret'),
              ),
      );

  Widget _noLessons() => const EmptyState(icon: Icons.event_busy, title: 'Heniz sapak bolmady');

  Widget _table(List<Map<String, dynamic>> cols, List<Map<String, dynamic>> rows, bool multiGroup) {
    const head = TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textMuted);
    const border = BorderSide(color: AppColors.border);
    final today = DateTime.now().toIso8601String().substring(0, 10);
    Widget cell(Widget child, double w, {double h = _rowH, Color? bg, bool right = true}) => Container(
          width: w,
          height: h,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: bg,
            border: Border(bottom: border, right: right ? border : BorderSide.none),
          ),
          child: child,
        );
    final pinned = Column(children: [
      Row(children: [
        cell(const Align(alignment: Alignment.centerLeft, child: Padding(padding: EdgeInsets.only(left: 14), child: Text('Talyp', style: head))),
            _nameW, h: _headH, bg: AppColors.tableHead),
        cell(const Text('Ort.', style: head), _statW, h: _headH, bg: AppColors.tableHead),
        cell(const Text('gm', style: head), _statW, h: _headH, bg: AppColors.tableHead),
      ]),
      Expanded(
        child: ListView.builder(
          controller: _left,
          itemCount: rows.length,
          itemExtent: _rowH,
          itemBuilder: (_, i) {
            final r = rows[i];
            final avg = r['average'] as num?;
            return Row(children: [
              cell(
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  child: Row(children: [
                    SizedBox(width: 28, child: Text('${i + 1}', style: const TextStyle(color: AppColors.textSubtle, fontSize: 13))),
                    Expanded(child: Text('${r['student']['name']}', overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 14))),
                    if (multiGroup) Text('${r['group']}', style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                  ]),
                ),
                _nameW,
              ),
              cell(Text(avg == null ? '—' : '$avg', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13,
                  color: avg == null ? AppColors.textSubtle : markColor('${avg.round()}'))), _statW),
              cell(Text('${r['absent']}', style: TextStyle(fontSize: 13, color: (r['absent'] as int) > 0 ? AppColors.danger : AppColors.textSubtle)), _statW),
            ]);
          },
        ),
      ),
    ]);
    final dates = Scrollbar(
      controller: _horizontal,
      thumbVisibility: true,
      child: SingleChildScrollView(
        controller: _horizontal,
        scrollDirection: Axis.horizontal,
        child: SizedBox(
          width: _cellW * cols.length,
          child: Column(children: [
            Row(children: [
              for (final c in cols)
                Tooltip(
                  message: '${c['day']} · ${c['starts_at']}',
                  child: cell(
                    Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                      Text(_short('${c['day']}'), style: head),
                      Text(_weekdays[DateTime.parse('${c['day']}').weekday - 1],
                          style: const TextStyle(fontSize: 11, color: AppColors.textSubtle)),
                    ]),
                    _cellW,
                    h: _headH,
                    bg: c['day'] == today ? AppColors.primarySoft : AppColors.tableHead,
                  ),
                ),
            ]),
            Expanded(
              child: ListView.builder(
                controller: _right,
                itemCount: rows.length,
                itemExtent: _rowH,
                itemBuilder: (_, i) {
                  final r = rows[i];
                  final marks = r['marks'] as List;
                  return Row(children: [
                    for (var j = 0; j < cols.length; j++)
                      InkWell(
                        onTapDown: (d) => _tapAt = d.globalPosition,
                        onTap: () => _openMenu(_tapAt, r, j),
                        child: cell(
                          marks[j] == null ? const SizedBox.shrink() : _MarkChip('${marks[j]}'),
                          _cellW,
                          bg: cols[j]['day'] == today ? AppColors.primarySoft.withValues(alpha: 0.5) : null,
                        ),
                      ),
                  ]);
                },
              ),
            ),
          ]),
        ),
      ),
    );
    return Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      SizedBox(width: _nameW + 2 * _statW, child: pinned),
      Expanded(child: dates),
    ]);
  }
}

class _MarkChip extends StatelessWidget {
  const _MarkChip(this.value);
  final String value;

  @override
  Widget build(BuildContext context) {
    final color = markColor(value);
    return Container(
      width: 32,
      height: 26,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: color.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(7)),
      child: Text(value, style: TextStyle(color: color, fontWeight: FontWeight.w700, fontSize: value == 'gm' ? 12 : 14)),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat(this.value, this.label);
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
          Text(label, style: const TextStyle(fontSize: 11.5, color: AppColors.textMuted)),
        ]),
      );
}

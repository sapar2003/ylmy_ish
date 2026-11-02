import 'package:flutter/material.dart';

import '../api.dart';
import '../resources.dart';
import '../theme.dart';
import 'dialogs.dart';

/// Islendik sanaw üçin umumy sahypa: düşündiriş, gözleg, süzgüç, tertiplemek, sahypalara bölmek,
/// goşmak, üýtgetmek, aýyrmak we sanawa mahsus hereketler (boş wagty, mugallymlar, wagt slotlary).
class CrudPage extends StatefulWidget {
  const CrudPage({super.key, required this.spec});
  final ResourceSpec spec;

  @override
  State<CrudPage> createState() => _CrudPageState();
}

class _CrudPageState extends State<CrudPage> {
  static const _pageSize = 25;
  static const _common = -1; // fakulteti görkezilmedik (umumy)

  /// Umumy sanawlary (fakultetler, smenalar, binalar, ...) diňe okuw bölümi üýtgedýär; dekan görýär.
  static const _shared = {'faculties', 'shifts', 'buildings', 'room-types', 'exam-sessions', 'exam-periods'};
  bool get _readOnly => Api.instance.isDean && _shared.contains(spec.endpoint);

  List<Map<String, dynamic>> _items = [];
  Map<String, List<Map<String, dynamic>>> _refs = {};
  String _query = '';
  int? _faculty = Api.instance.deanFaculty; // null: hemmesi; dekan: adaty öz fakulteti
  int? _sortColumn;
  bool _sortAsc = true;
  int _page = 0;
  bool _loading = true;
  String? _error;

  ResourceSpec get spec => widget.spec;

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
      final refNames = {
        ...spec.fields.map((f) => f.ref).whereType<String>(),
        if (spec.facultyFilter != null) ...['faculties', 'departments'],
      };
      final results = await Future.wait([
        Api.instance.list(spec.endpoint),
        for (final r in refNames) Api.instance.list(r),
      ]);
      if (!mounted) return;
      setState(() {
        _items = results.first;
        _refs = {for (final (i, r) in refNames.indexed) r: results[i + 1]};
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

  String _display(FieldSpec f, dynamic value) {
    if (value == null) return '—';
    switch (f.type) {
      case FieldType.ref:
        return _refName(f.ref!, value);
      case FieldType.refList:
        return (value as List).map((id) => _refName(f.ref!, id)).join(', ');
      case FieldType.choice:
        return f.choices![value] ?? '$value';
      case FieldType.boolean:
        return value == true ? 'Hawa' : 'Ýok';
      case FieldType.time:
        return '$value'.substring(0, 5);
      case FieldType.weekdays:
        return (value as List).map((d) => weekdays[d - 1].substring(0, 2)).join(', ');
      default:
        return '$value';
    }
  }

  /// Ýazgynyň fakulteti (otagda göni, mugallymda kafedrasy arkaly); null — umumy.
  int? _facultyOf(Map<String, dynamic> item) => switch (spec.facultyFilter) {
        FacultyVia.faculty => item['faculty_id'] as int?,
        FacultyVia.department => _refs['departments']
            ?.where((d) => d['id'] == item['department_id'])
            .firstOrNull?['faculty_id'] as int?,
        null => null,
      };

  String _refName(String ref, dynamic id) {
    final row = _refs[ref]?.where((r) => r['id'] == id).firstOrNull;
    if (row == null) return '#$id';
    return '${ref == 'faculties' ? (row['short_name'] ?? row['name']) : row['name']}';
  }

  Future<void> _edit([Map<String, dynamic>? item]) async {
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => RecordFormDialog(spec: spec, refs: _refs, initial: item),
    );
    if (saved == true) _load();
  }

  Future<void> _delete(Map<String, dynamic> item) async {
    final label = item['name'] ?? '#${item['id']}';
    if (!await confirm(context, '"$label" aýrylsynmy? Bu hereketi yzyna gaýtaryp bolmaýar.')) return;
    try {
      await Api.instance.delete('${spec.endpoint}/${item['id']}');
      _load();
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  Future<void> _action(RowAction action, Map<String, dynamic> item) async {
    final dialog = switch (action) {
      RowAction.availability => AvailabilityDialog(teacher: item),
      RowAction.assignments => AssignmentsDialog(item: item),
      RowAction.generateSlots => GenerateSlotsDialog(shift: item),
    };
    await showDialog(context: context, builder: (_) => dialog);
  }

  List<FieldSpec> get _columns => spec.fields.where((f) => f.showInTable).toList();

  List<Map<String, dynamic>> _visibleRows() {
    final q = _query.toLowerCase();
    final rows = _items.where((item) {
      if (_faculty != null && (_facultyOf(item) ?? _common) != _faculty) return false;
      if (q.isEmpty) return true;
      return _columns.any((f) => _display(f, item[f.key]).toLowerCase().contains(q));
    }).toList();
    if (_sortColumn != null) {
      final f = _columns[_sortColumn!];
      int cmp(Map<String, dynamic> a, Map<String, dynamic> b) {
        final x = a[f.key], y = b[f.key];
        if (f.type == FieldType.integer && x is num && y is num) return x.compareTo(y);
        return _display(f, x).toLowerCase().compareTo(_display(f, y).toLowerCase());
      }

      rows.sort((a, b) => _sortAsc ? cmp(a, b) : cmp(b, a));
    }
    return rows;
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(32, 28, 32, 24),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(
            child: PageTitle(
              title: spec.title,
              icon: resourceIcons[spec.endpoint] ?? Icons.list,
              color: sectionColor(spec.endpoint),
              count: _loading ? null : _items.length,
            ),
          ),
          const SizedBox(width: 16),
          if (!_readOnly)
            FilledButton.icon(
              onPressed: () => _edit(),
              icon: const Icon(Icons.add, size: 18),
              label: Text('${spec.singular} goş'),
            ),
        ]),
        if (spec.description != null) ...[const SizedBox(height: 16), HelpNote(spec.description!)],
        const SizedBox(height: 16),
        Expanded(child: Card(clipBehavior: Clip.antiAlias, child: _body())),
      ]),
    );
  }

  Widget _toolbar(int shown) {
    final faculties = _refs['faculties'] ?? [];
    final hasCommon = _items.any((i) => _facultyOf(i) == null);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
      child: Row(children: [
        SizedBox(
          width: 300,
          child: TextField(
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search, size: 20), hintText: 'Gözle...'),
            onChanged: (v) => setState(() {
              _query = v;
              _page = 0;
            }),
          ),
        ),
        if (spec.facultyFilter != null) ...[
          const SizedBox(width: 12),
          SizedBox(
            width: 220,
            child: DropdownButtonFormField<int?>(
              initialValue: _faculty,
              isExpanded: true,
              decoration: const InputDecoration(prefixIcon: Icon(Icons.filter_list, size: 20)),
              items: [
                const DropdownMenuItem<int?>(value: null, child: Text('Ähli fakultetler')),
                for (final f in faculties)
                  DropdownMenuItem<int?>(value: f['id'] as int, child: Text('${f['short_name'] ?? f['name']}')),
                if (hasCommon) const DropdownMenuItem<int?>(value: _common, child: Text('Umumy (fakultetsiz)')),
              ],
              onChanged: (v) => setState(() {
                _faculty = v;
                _page = 0;
              }),
            ),
          ),
        ],
        const Spacer(),
        Text(
          shown == _items.length ? '${_items.length} ýazgy' : '$shown / ${_items.length} ýazgy',
          style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
        ),
        const SizedBox(width: 4),
        IconButton(tooltip: 'Täzele', onPressed: _load, icon: const Icon(Icons.refresh, size: 20)),
      ]),
    );
  }

  Widget _body() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return EmptyState(icon: Icons.cloud_off, title: 'Maglumat ýüklenmedi', text: _error,
          action: OutlinedButton(onPressed: _load, child: const Text('Gaýtadan synanyş')));
    }
    if (_items.isEmpty) {
      return EmptyState(
        icon: resourceIcons[spec.endpoint] ?? Icons.inbox_outlined,
        title: 'Heniz ${spec.title.toLowerCase()} ýok',
        text: spec.description,
        action: FilledButton.icon(
          onPressed: () => _edit(),
          icon: const Icon(Icons.add, size: 18),
          label: Text('${spec.singular} goş'),
        ),
      );
    }
    final rows = _visibleRows();
    final pages = (rows.length / _pageSize).ceil().clamp(1, 1 << 30);
    final page = _page.clamp(0, pages - 1);
    final slice = rows.skip(page * _pageSize).take(_pageSize).toList();
    final columns = _columns;
    return Column(children: [
      _toolbar(rows.length),
      const Divider(),
      Expanded(
        child: rows.isEmpty
            ? const EmptyState(icon: Icons.search_off, title: 'Hiç zat tapylmady', text: 'Gözleg sözüni ýa-da süzgüji üýtgediň.')
            : LayoutBuilder(
                builder: (context, box) => SingleChildScrollView(
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: ConstrainedBox(
                      constraints: BoxConstraints(minWidth: box.maxWidth),
                      child: DataTable(
                        sortColumnIndex: _sortColumn,
                        sortAscending: _sortAsc,
                        columnSpacing: 28,
                        horizontalMargin: 16,
                        columns: [
                          for (final (i, f) in columns.indexed)
                            DataColumn(
                              label: Text(f.label.toUpperCase()),
                              numeric: f.type == FieldType.integer,
                              onSort: (_, _) => setState(() {
                                _sortAsc = _sortColumn == i ? !_sortAsc : true;
                                _sortColumn = i;
                              }),
                            ),
                          if (spec.facultyFilter == FacultyVia.department) const DataColumn(label: Text('FAKULTET')),
                          const DataColumn(label: Text('')),
                        ],
                        rows: [
                          for (final item in slice)
                            DataRow(cells: [
                              for (final (i, f) in columns.indexed)
                                DataCell(
                                  ConstrainedBox(
                                    constraints: const BoxConstraints(maxWidth: 360),
                                    child: Text(
                                      _display(f, item[f.key]),
                                      overflow: TextOverflow.ellipsis,
                                      style: i == 0 ? const TextStyle(fontWeight: FontWeight.w600) : null,
                                    ),
                                  ),
                                  onTap: () => _edit(item),
                                ),
                              if (spec.facultyFilter == FacultyVia.department)
                                DataCell(_facultyOf(item) == null
                                    ? const Text('—')
                                    : StatusPill(_refName('faculties', _facultyOf(item)), color: AppColors.primary)),
                              DataCell(Row(mainAxisSize: MainAxisSize.min, children: [
                                for (final a in spec.actions)
                                  Padding(
                                    padding: const EdgeInsets.only(right: 4),
                                    child: OutlinedButton.icon(
                                      style: OutlinedButton.styleFrom(minimumSize: const Size(0, 32),
                                          padding: const EdgeInsets.symmetric(horizontal: 10)),
                                      onPressed: () => _action(a, item),
                                      icon: Icon(actionIcon(a), size: 16),
                                      label: Text(actionLabel(a), style: const TextStyle(fontSize: 13)),
                                    ),
                                  ),
                                if (!_readOnly) PopupMenuButton<String>(
                                  tooltip: 'Hereketler',
                                  icon: const Icon(Icons.more_horiz, color: AppColors.textMuted),
                                  onSelected: (v) => v == 'edit' ? _edit(item) : _delete(item),
                                  itemBuilder: (_) => const [
                                    PopupMenuItem(value: 'edit', child: ListTile(leading: Icon(Icons.edit_outlined), title: Text('Üýtget'))),
                                    PopupMenuItem(
                                      value: 'delete',
                                      child: ListTile(
                                        leading: Icon(Icons.delete_outline, color: AppColors.danger),
                                        title: Text('Aýyr', style: TextStyle(color: AppColors.danger)),
                                      ),
                                    ),
                                  ],
                                ),
                              ])),
                            ]),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
      ),
      if (pages > 1) ...[
        const Divider(),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(children: [
            Text('${page * _pageSize + 1}–${(page * _pageSize + slice.length)} / ${rows.length}',
                style: const TextStyle(color: AppColors.textMuted, fontSize: 13)),
            const Spacer(),
            OutlinedButton.icon(
              onPressed: page > 0 ? () => setState(() => _page = page - 1) : null,
              icon: const Icon(Icons.chevron_left, size: 18),
              label: const Text('Öňki'),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Text('${page + 1} / $pages', style: const TextStyle(fontWeight: FontWeight.w600)),
            ),
            OutlinedButton.icon(
              onPressed: page < pages - 1 ? () => setState(() => _page = page + 1) : null,
              icon: const Icon(Icons.chevron_right, size: 18),
              label: const Text('Indiki'),
            ),
          ]),
        ),
      ],
    ]);
  }
}

String actionLabel(RowAction a) => switch (a) {
      RowAction.availability => 'Boş wagty',
      RowAction.assignments => 'Mugallymlar',
      RowAction.generateSlots => 'Wagt slotlary',
    };

IconData actionIcon(RowAction a) => switch (a) {
      RowAction.availability => Icons.event_available_outlined,
      RowAction.assignments => Icons.person_add_alt,
      RowAction.generateSlots => Icons.more_time,
    };

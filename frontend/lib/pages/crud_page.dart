import 'package:flutter/material.dart';

import '../api.dart';
import '../resources.dart';
import 'dialogs.dart';

/// Islendik sanaw üçin umumy sahypa: tablisa, gözleg, goşmak, üýtgetmek, aýyrmak.
class CrudPage extends StatefulWidget {
  const CrudPage({super.key, required this.spec});
  final ResourceSpec spec;

  @override
  State<CrudPage> createState() => _CrudPageState();
}

class _CrudPageState extends State<CrudPage> {
  List<Map<String, dynamic>> _items = [];
  Map<String, List<Map<String, dynamic>>> _refs = {};
  String _query = '';
  bool _loading = true;
  String? _error;

  ResourceSpec get spec => widget.spec;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(CrudPage old) {
    super.didUpdateWidget(old);
    if (old.spec.endpoint != spec.endpoint) {
      _query = '';
      _load();
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final refNames = spec.fields.map((f) => f.ref).whereType<String>().toSet();
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
      default:
        return '$value';
    }
  }

  String _refName(String ref, dynamic id) =>
      _refs[ref]?.firstWhere((r) => r['id'] == id, orElse: () => {'name': '#$id'})['name'] ?? '#$id';

  Future<void> _edit([Map<String, dynamic>? item]) async {
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => RecordFormDialog(spec: spec, refs: _refs, initial: item),
    );
    if (saved == true) _load();
  }

  Future<void> _delete(Map<String, dynamic> item) async {
    final label = item['name'] ?? '#${item['id']}';
    final ok = await confirm(context, '"$label" aýrylsynmy?');
    if (!ok) return;
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

  @override
  Widget build(BuildContext context) {
    final columns = spec.fields.where((f) => f.showInTable).toList();
    final q = _query.toLowerCase();
    final rows = _items.where((item) {
      if (q.isEmpty) return true;
      return columns.any((f) => _display(f, item[f.key]).toLowerCase().contains(q));
    }).toList();

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text(spec.title, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(width: 12),
            if (!_loading) Chip(label: Text('${_items.length}')),
            const Spacer(),
            SizedBox(
              width: 240,
              child: TextField(
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.search),
                  hintText: 'Gözle',
                  isDense: true,
                  border: OutlineInputBorder(),
                ),
                onChanged: (v) => setState(() => _query = v),
              ),
            ),
            const SizedBox(width: 12),
            FilledButton.icon(
              onPressed: () => _edit(),
              icon: const Icon(Icons.add),
              label: Text('${spec.singular} goş'),
            ),
          ]),
          const SizedBox(height: 16),
          Expanded(child: _body(columns, rows)),
        ],
      ),
    );
  }

  Widget _body(List<FieldSpec> columns, List<Map<String, dynamic>> rows) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          const SizedBox(height: 8),
          OutlinedButton(onPressed: _load, child: const Text('Gaýtadan synanyş')),
        ]),
      );
    }
    if (_items.isEmpty) {
      return Center(child: Text('Heniz ${spec.title.toLowerCase()} ýok. "${spec.singular} goş" düwmesine basyň.'));
    }
    return Card(
      clipBehavior: Clip.antiAlias,
      child: SingleChildScrollView(
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            headingRowColor: WidgetStatePropertyAll(Theme.of(context).colorScheme.surfaceContainerHighest),
            columns: [
              for (final f in columns) DataColumn(label: Text(f.label)),
              const DataColumn(label: Text('')),
            ],
            rows: [
              for (final item in rows)
                DataRow(cells: [
                  for (final f in columns) DataCell(Text(_display(f, item[f.key]))),
                  DataCell(Row(mainAxisSize: MainAxisSize.min, children: [
                    for (final a in spec.actions)
                      TextButton(onPressed: () => _action(a, item), child: Text(actionLabel(a))),
                    IconButton(tooltip: 'Üýtget', icon: const Icon(Icons.edit_outlined), onPressed: () => _edit(item)),
                    IconButton(tooltip: 'Aýyr', icon: const Icon(Icons.delete_outline), onPressed: () => _delete(item)),
                  ])),
                ]),
            ],
          ),
        ),
      ),
    );
  }
}

String actionLabel(RowAction a) => switch (a) {
      RowAction.availability => 'Boş wagty',
      RowAction.assignments => 'Mugallymlar',
      RowAction.generateSlots => 'Wagt slotlary',
    };

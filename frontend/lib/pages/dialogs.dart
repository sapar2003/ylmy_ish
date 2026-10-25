import 'package:flutter/material.dart';

import '../api.dart';
import '../resources.dart';

Future<bool> confirm(BuildContext context, String text) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (c) => AlertDialog(
      content: Text(text),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Ýok')),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Hawa')),
      ],
    ),
  );
  return ok ?? false;
}

void showError(BuildContext context, String message) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(
    content: Text(message),
    backgroundColor: Theme.of(context).colorScheme.error,
  ));
}

/// Goşmak we üýtgetmek üçin forma; meýdanlar `ResourceSpec`-den gurulýar.
class RecordFormDialog extends StatefulWidget {
  const RecordFormDialog({super.key, required this.spec, required this.refs, this.initial});
  final ResourceSpec spec;
  final Map<String, List<Map<String, dynamic>>> refs;
  final Map<String, dynamic>? initial;

  @override
  State<RecordFormDialog> createState() => _RecordFormDialogState();
}

class _RecordFormDialogState extends State<RecordFormDialog> {
  final _form = GlobalKey<FormState>();
  late final Map<String, dynamic> _values = {
    for (final f in widget.spec.fields)
      f.key: widget.initial?[f.key] ??
          switch (f.type) {
            FieldType.boolean => false,
            FieldType.refList => <int>[],
            FieldType.weekdays => [1, 2, 3, 4, 5, 6],
            _ => null,
          },
  };
  String? _error;
  bool _saving = false;

  bool get _isNew => widget.initial == null;

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    _form.currentState!.save();
    setState(() => _saving = true);
    try {
      final path = widget.spec.endpoint;
      if (_isNew) {
        await Api.instance.post(path, _values);
      } else {
        await Api.instance.patch('$path/${widget.initial!['id']}', _values);
      }
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      setState(() {
        _error = e.message;
        _saving = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isNew ? '${widget.spec.singular} goşmak' : '${widget.spec.singular} üýtgetmek'),
      content: SizedBox(
        width: 420,
        child: Form(
          key: _form,
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              for (final f in widget.spec.fields)
                Padding(padding: const EdgeInsets.only(bottom: 12), child: _field(f)),
              if (_error != null)
                Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ]),
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Ýatyr')),
        FilledButton(onPressed: _saving ? null : _save, child: const Text('Ýatda sakla')),
      ],
    );
  }

  InputDecoration _decoration(FieldSpec f) => InputDecoration(
        labelText: f.required ? f.label : '${f.label} (hökmany däl)',
        border: const OutlineInputBorder(),
        isDense: true,
      );

  String? _requiredCheck(FieldSpec f, Object? v) =>
      f.required && (v == null || (v is String && v.trim().isEmpty)) ? 'Hökmany meýdan' : null;

  Widget _field(FieldSpec f) {
    final value = _values[f.key];
    switch (f.type) {
      case FieldType.text:
      case FieldType.integer:
      case FieldType.time:
      case FieldType.date:
        final isInt = f.type == FieldType.integer;
        final isTime = f.type == FieldType.time;
        final isDate = f.type == FieldType.date;
        return TextFormField(
          initialValue: value == null ? '' : (isTime ? '$value'.substring(0, 5) : '$value'),
          decoration: _decoration(f).copyWith(
            hintText: isTime ? 'SS:MM, meselem 08:30' : (isDate ? 'ÝÝÝÝ-AA-GG, meselem 2026-11-02' : null),
          ),
          keyboardType: isInt ? TextInputType.number : TextInputType.text,
          validator: (v) {
            final missing = _requiredCheck(f, v);
            if (missing != null) return missing;
            if (v == null || v.isEmpty) return null;
            if (isInt && int.tryParse(v) == null) return 'San giriziň';
            if (isTime && !RegExp(r'^\d{1,2}:\d{2}$').hasMatch(v)) return 'SS:MM görnüşinde giriziň';
            if (isDate && (!RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(v) || DateTime.tryParse(v) == null)) {
              return 'ÝÝÝÝ-AA-GG görnüşinde giriziň';
            }
            return null;
          },
          onSaved: (v) {
            final text = v?.trim() ?? '';
            _values[f.key] = text.isEmpty ? null : (isInt ? int.parse(text) : text);
          },
        );
      case FieldType.choice:
        return DropdownButtonFormField<String>(
          initialValue: value as String?,
          isExpanded: true, // uzyn atlar meýdandan çykmasyn
          decoration: _decoration(f),
          items: [
            for (final e in f.choices!.entries)
              DropdownMenuItem(value: e.key, child: Text(e.value, overflow: TextOverflow.ellipsis)),
          ],
          validator: (v) => _requiredCheck(f, v),
          onChanged: (v) => _values[f.key] = v,
        );
      case FieldType.ref:
        final options = widget.refs[f.ref] ?? [];
        return DropdownButtonFormField<int?>(
          initialValue: value as int?,
          isExpanded: true, // uzyn atlar (meselem, dersler) meýdandan çykmasyn
          decoration: _decoration(f),
          items: [
            if (!f.required) const DropdownMenuItem<int?>(value: null, child: Text('—')),
            for (final o in options)
              DropdownMenuItem<int?>(
                value: o['id'] as int,
                child: Text('${o['name']}', overflow: TextOverflow.ellipsis),
              ),
          ],
          validator: (v) => _requiredCheck(f, v),
          onChanged: (v) => _values[f.key] = v,
        );
      case FieldType.refList:
        final options = widget.refs[f.ref] ?? [];
        final selected = (value as List).cast<int>().toSet();
        return InputDecorator(
          decoration: _decoration(f),
          child: Wrap(spacing: 6, runSpacing: 6, children: [
            for (final o in options)
              FilterChip(
                label: Text('${o['name']}'),
                selected: selected.contains(o['id']),
                onSelected: (on) => setState(() {
                  on ? selected.add(o['id'] as int) : selected.remove(o['id']);
                  _values[f.key] = selected.toList();
                }),
              ),
          ]),
        );
      case FieldType.weekdays:
        final selected = (value as List).cast<int>().toSet();
        return InputDecorator(
          decoration: _decoration(f),
          child: Wrap(spacing: 6, runSpacing: 6, children: [
            for (var d = 1; d <= 7; d++)
              FilterChip(
                label: Text(weekdays[d - 1]),
                selected: selected.contains(d),
                onSelected: (on) => setState(() {
                  on ? selected.add(d) : selected.remove(d);
                  _values[f.key] = selected.toList()..sort();
                }),
              ),
          ]),
        );
      case FieldType.boolean:
        return SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(f.label),
          value: value as bool,
          onChanged: (v) => setState(() => _values[f.key] = v),
        );
    }
  }
}

/// Mugallymyň hepdelik boş wagty: her slota basyp ýagdaýyny çalyşmak.
class AvailabilityDialog extends StatefulWidget {
  const AvailabilityDialog({super.key, required this.teacher});
  final Map<String, dynamic> teacher;

  @override
  State<AvailabilityDialog> createState() => _AvailabilityDialogState();
}

class _AvailabilityDialogState extends State<AvailabilityDialog> {
  List<Map<String, dynamic>> _slots = [];
  List<Map<String, dynamic>> _shifts = [];
  final Map<int, String> _status = {};
  bool _loading = true;

  static const _cycle = ['available', 'preferred', 'unavailable'];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final id = widget.teacher['id'];
    final results = await Future.wait([
      Api.instance.list('time-slots'),
      Api.instance.list('shifts'),
      Api.instance.get('teachers/$id/availability'),
    ]);
    if (!mounted) return;
    setState(() {
      _slots = results[0] as List<Map<String, dynamic>>;
      _shifts = results[1] as List<Map<String, dynamic>>;
      for (final a in results[2] as List) {
        _status[a['time_slot_id'] as int] = a['status'] as String;
      }
      _loading = false;
    });
  }

  Future<void> _save() async {
    final body = [
      for (final e in _status.entries)
        if (e.value != 'available') {'time_slot_id': e.key, 'status': e.value},
    ];
    try {
      await Api.instance.put('teachers/${widget.teacher['id']}/availability', body);
      if (mounted) Navigator.pop(context);
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  Color _color(String status, ColorScheme cs) => switch (status) {
        'preferred' => Colors.green.shade300,
        'unavailable' => cs.errorContainer,
        _ => cs.surfaceContainerHighest,
      };

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return AlertDialog(
      title: Text('${widget.teacher['name']}: boş wagty'),
      content: SizedBox(
        width: 720,
        child: _loading
            ? const SizedBox(height: 120, child: Center(child: CircularProgressIndicator()))
            : SingleChildScrollView(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Wrap(spacing: 12, children: [
                    _legend('Bolup bilýär', _color('available', cs)),
                    _legend('Isleýär', _color('preferred', cs)),
                    _legend('Bolmaz', _color('unavailable', cs)),
                  ]),
                  const SizedBox(height: 8),
                  const Text('Slota basyp ýagdaýyny çalyşyň.'),
                  for (final shift in _shifts) ..._shiftGrid(shift, cs),
                ]),
              ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Ýatyr')),
        FilledButton(onPressed: _loading ? null : _save, child: const Text('Ýatda sakla')),
      ],
    );
  }

  Widget _legend(String text, Color color) => Row(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 14, height: 14, color: color),
        const SizedBox(width: 4),
        Text(text),
      ]);

  List<Widget> _shiftGrid(Map<String, dynamic> shift, ColorScheme cs) {
    final slots = _slots.where((s) => s['shift_id'] == shift['id']).toList();
    if (slots.isEmpty) return [];
    final days = slots.map((s) => s['weekday'] as int).toSet().toList()..sort();
    final numbers = slots.map((s) => s['number'] as int).toSet().toList()..sort();
    return [
      const SizedBox(height: 16),
      Text('${shift['name']}', style: Theme.of(context).textTheme.titleMedium),
      const SizedBox(height: 8),
      Table(
        defaultColumnWidth: const FixedColumnWidth(92),
        columnWidths: const {0: FixedColumnWidth(60)},
        children: [
          TableRow(children: [
            const SizedBox(),
            for (final d in days) Center(child: Text(weekdays[d - 1].substring(0, 3))),
          ]),
          for (final n in numbers)
            TableRow(children: [
              Padding(padding: const EdgeInsets.all(6), child: Text('$n-nji')),
              for (final d in days) _slotCell(slots, d, n, cs),
            ]),
        ],
      ),
    ];
  }

  Widget _slotCell(List<Map<String, dynamic>> slots, int day, int number, ColorScheme cs) {
    final slot = slots.where((s) => s['weekday'] == day && s['number'] == number).firstOrNull;
    if (slot == null) return const SizedBox();
    final id = slot['id'] as int;
    final status = _status[id] ?? 'available';
    return Padding(
      padding: const EdgeInsets.all(2),
      child: InkWell(
        onTap: () => setState(() => _status[id] = _cycle[(_cycle.indexOf(status) + 1) % _cycle.length]),
        child: Container(
          height: 32,
          alignment: Alignment.center,
          color: _color(status, cs),
          child: Text('${slot['starts_at']}'.substring(0, 5), style: const TextStyle(fontSize: 12)),
        ),
      ),
    );
  }
}

/// Okuw meýilnamasynyň bir ýazgysyna mugallym bellemek (bölünýän sapakda her kiçi topara).
class AssignmentsDialog extends StatefulWidget {
  const AssignmentsDialog({super.key, required this.item});
  final Map<String, dynamic> item;

  @override
  State<AssignmentsDialog> createState() => _AssignmentsDialogState();
}

class _AssignmentsDialogState extends State<AssignmentsDialog> {
  List<Map<String, dynamic>> _assignments = [];
  List<Map<String, dynamic>> _teachers = [];
  List<Map<String, dynamic>> _subgroups = [];
  bool _loading = true;

  bool get _split => widget.item['split'] == true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final item = widget.item;
    final results = await Future.wait([
      Api.instance.list('assignments', {'curriculum_item_id': item['id']}),
      Api.instance.list('teachers'),
      if (_split) Api.instance.list('subgroups', {'group_id': item['group_id']}),
    ]);
    if (!mounted) return;
    setState(() {
      _assignments = results[0];
      _teachers = results[1];
      _subgroups = _split ? results[2] : [];
      _loading = false;
    });
  }

  Future<void> _setTeacher(int? subgroupId, int teacherId) async {
    final existing = _assignments.where((a) => a['subgroup_id'] == subgroupId).firstOrNull;
    try {
      if (existing == null) {
        await Api.instance.post('assignments', {
          'curriculum_item_id': widget.item['id'],
          'teacher_id': teacherId,
          'subgroup_id': subgroupId,
        });
      } else {
        await Api.instance.patch('assignments/${existing['id']}', {'teacher_id': teacherId});
      }
      _load();
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  Widget _row(String label, int? subgroupId) {
    final current = _assignments.where((a) => a['subgroup_id'] == subgroupId).firstOrNull;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: DropdownButtonFormField<int>(
        initialValue: current?['teacher_id'] as int?,
        decoration: InputDecoration(labelText: label, border: const OutlineInputBorder(), isDense: true),
        items: [
          for (final t in _teachers) DropdownMenuItem(value: t['id'] as int, child: Text('${t['name']}')),
        ],
        onChanged: (id) => id == null ? null : _setTeacher(subgroupId, id),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Mugallym bellemek'),
      content: SizedBox(
        width: 420,
        child: _loading
            ? const SizedBox(height: 80, child: Center(child: CircularProgressIndicator()))
            : Column(mainAxisSize: MainAxisSize.min, children: [
                if (_split && _subgroups.isEmpty) const Text('Bu toparda kiçi topar ýok.'),
                if (_split)
                  for (final s in _subgroups) _row('${s['name']}-nji kiçi topar', s['id'] as int)
                else
                  _row('Mugallym', null),
              ]),
      ),
      actions: [FilledButton(onPressed: () => Navigator.pop(context), child: const Text('Taýýar'))],
    );
  }
}

/// Smena üçin ähli günleriň wagt slotlaryny bir gezekde döretmek.
class GenerateSlotsDialog extends StatefulWidget {
  const GenerateSlotsDialog({super.key, required this.shift});
  final Map<String, dynamic> shift;

  @override
  State<GenerateSlotsDialog> createState() => _GenerateSlotsDialogState();
}

class _GenerateSlotsDialogState extends State<GenerateSlotsDialog> {
  final Set<int> _days = {1, 2, 3, 4, 5, 6};
  final List<(TextEditingController, TextEditingController)> _periods = [];
  List<Map<String, dynamic>> _existing = [];

  @override
  void initState() {
    super.initState();
    _addPeriod('${widget.shift['starts_at']}'.substring(0, 5), '');
    Api.instance.list('time-slots', {'shift_id': widget.shift['id']}).then((s) {
      if (mounted) setState(() => _existing = s);
    });
  }

  void _addPeriod([String start = '', String end = '']) {
    _periods.add((TextEditingController(text: start), TextEditingController(text: end)));
  }

  Future<void> _clearExisting() async {
    if (!await confirm(context, 'Bu smenanyň ${_existing.length} slotuny aýyrmalymy? '
        'Mugallymlaryň şol slotlardaky bellikleri hem aýrylar.')) {
      return;
    }
    try {
      for (final slot in _existing) {
        await Api.instance.delete('time-slots/${slot['id']}');
      }
      setState(() => _existing = []);
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  Future<void> _generate() async {
    try {
      await Api.instance.post('time-slots/generate', {
        'shift_id': widget.shift['id'],
        'weekdays': _days.toList()..sort(),
        'periods': [
          for (final (i, (start, end)) in _periods.indexed)
            {'number': i + 1, 'starts_at': start.text.trim(), 'ends_at': end.text.trim()},
        ],
      });
      if (mounted) Navigator.pop(context);
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('${widget.shift['name']}: wagt slotlary'),
      content: SizedBox(
        width: 460,
        child: SingleChildScrollView(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            if (_existing.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(children: [
                  Expanded(child: Text('Bu smenada eýýäm ${_existing.length} slot bar.')),
                  TextButton(onPressed: _clearExisting, child: const Text('Olary aýyr')),
                ]),
              ),
            const Text('Okuw günleri'),
            Wrap(spacing: 6, children: [
              for (var d = 1; d <= 7; d++)
                FilterChip(
                  label: Text(weekdays[d - 1]),
                  selected: _days.contains(d),
                  onSelected: (on) => setState(() => on ? _days.add(d) : _days.remove(d)),
                ),
            ]),
            const SizedBox(height: 16),
            const Text('Sapaklaryň wagty (SS:MM)'),
            const SizedBox(height: 8),
            for (final (i, (start, end)) in _periods.indexed)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(children: [
                  SizedBox(width: 60, child: Text('${i + 1}-nji')),
                  Expanded(child: TextField(controller: start, decoration: const InputDecoration(labelText: 'Başlanýar', isDense: true))),
                  const SizedBox(width: 8),
                  Expanded(child: TextField(controller: end, decoration: const InputDecoration(labelText: 'Gutarýar', isDense: true))),
                ]),
              ),
            TextButton.icon(
              onPressed: () => setState(_addPeriod),
              icon: const Icon(Icons.add),
              label: const Text('Sapak goş'),
            ),
          ]),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Ýatyr')),
        FilledButton(onPressed: _generate, child: const Text('Döret')),
      ],
    );
  }
}

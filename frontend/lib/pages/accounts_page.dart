import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../api.dart';
import '../theme.dart';
import 'dialogs.dart';

/// Mugallym hasaplary: her mugallyma login we wagtlaýyn parol (telefon programmasy üçin).
/// Parollar diňe döredilende görkezilýär — göçürip ýa-da çap edip mugallymlara paýlaň.
class AccountsPage extends StatefulWidget {
  const AccountsPage({super.key});

  @override
  State<AccountsPage> createState() => _AccountsPageState();
}

class _AccountsPageState extends State<AccountsPage> {
  List<Map<String, dynamic>> _users = [];
  int _teachersWithout = 0;
  bool _loading = true;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final r = await Future.wait([Api.instance.get('users'), Api.instance.list('teachers')]);
      final users = (r[0] as List).cast<Map<String, dynamic>>();
      final withAccount = {for (final u in users) u['teacher']?['id']};
      if (!mounted) return;
      setState(() {
        _users = users;
        _teachersWithout = (r[1] as List).where((t) => !withAccount.contains(t['id'])).length;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  Future<void> _createAll() async {
    try {
      final issued = (await Api.instance.post('users/teachers', {}) as List).cast<Map<String, dynamic>>();
      await _load();
      if (mounted) await _showIssued(issued);
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  Future<void> _reset(Map<String, dynamic> user) async {
    if (!await confirm(context, '"${user['username']}" üçin täze wagtlaýyn parol döredilsinmi?')) return;
    try {
      final issued = await Api.instance.post('users/${user['id']}/reset-password', {}) as Map<String, dynamic>;
      await _load();
      if (mounted) await _showIssued([issued]);
    } on ApiException catch (e) {
      if (mounted) showError(context, e.message);
    }
  }

  Future<void> _showIssued(List<Map<String, dynamic>> issued) {
    final text = [
      'Mugallym\tLogin\tParol',
      for (final i in issued) '${i['teacher']?['name'] ?? ''}\t${i['username']}\t${i['password']}',
    ].join('\n');
    return showDialog(
      context: context,
      builder: (c) => AlertDialog(
        title: Text('${issued.length} hasap: wagtlaýyn parollar'),
        content: SizedBox(
          width: 640,
          height: 420,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Bu parollar diňe şu gezek görkezilýär. Göçürip (Excel-e goýup) ýa-da çap edip mugallymlara '
                'paýlaň. Mugallym ilkinji girende öz parolyny belleýär.'),
            const SizedBox(height: 12),
            Expanded(
              child: SingleChildScrollView(
                child: DataTable(columns: const [
                  DataColumn(label: Text('Mugallym')),
                  DataColumn(label: Text('Login')),
                  DataColumn(label: Text('Parol')),
                ], rows: [
                  for (final i in issued)
                    DataRow(cells: [
                      DataCell(Text('${i['teacher']?['name'] ?? ''}')),
                      DataCell(SelectableText('${i['username']}')),
                      DataCell(SelectableText('${i['password']}', style: const TextStyle(fontFamily: 'monospace'))),
                    ]),
                ]),
              ),
            ),
          ]),
        ),
        actions: [
          TextButton.icon(
            onPressed: () => Clipboard.setData(ClipboardData(text: text)),
            icon: const Icon(Icons.copy),
            label: const Text('Göçür (Excel üçin)'),
          ),
          FilledButton(onPressed: () => Navigator.pop(c), child: const Text('Ýap')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final q = _query.toLowerCase();
    final rows = _users.where((u) =>
        q.isEmpty || '${u['username']} ${u['teacher']?['name'] ?? ''}'.toLowerCase().contains(q)).toList();
    return Padding(
      padding: const EdgeInsets.fromLTRB(28, 24, 28, 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const PageTitle(title: 'Mugallym hasaplary', icon: Icons.badge_outlined, color: AppColors.resources),
          const SizedBox(width: 16),
          if (!_loading) Chip(label: Text('${_users.length}')),
          const Spacer(),
          SizedBox(
            width: 220,
            child: TextField(
              decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Gözle', isDense: true),
              onChanged: (v) => setState(() => _query = v),
            ),
          ),
          const SizedBox(width: 12),
          FilledButton.icon(
            onPressed: _teachersWithout == 0 ? null : _createAll,
            icon: const Icon(Icons.person_add),
            label: Text('Hasap aç ($_teachersWithout mugallym)'),
          ),
        ]),
        const SizedBox(height: 8),
        const Text('Mugallym telefonda öz login/paroly bilen girip, diňe öz raspisaniýesini görýär '
            '(diňe "Mugallymlara çap et" edilen raspisaniýe).'),
        const SizedBox(height: 16),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : Card(
                  clipBehavior: Clip.antiAlias,
                  child: SingleChildScrollView(
                    child: SizedBox(
                      width: double.infinity,
                      child: DataTable(columns: const [
                        DataColumn(label: Text('Login')),
                        DataColumn(label: Text('Mugallym')),
                        DataColumn(label: Text('Roly')),
                        DataColumn(label: Text('Ýagdaýy')),
                        DataColumn(label: Text('')),
                      ], rows: [
                        for (final u in rows)
                          DataRow(cells: [
                            DataCell(SelectableText('${u['username']}')),
                            DataCell(Text('${u['teacher']?['name'] ?? '—'}')),
                            DataCell(Text(u['role'] == 'admin' ? 'Admin' : 'Mugallym')),
                            DataCell(Text(u['must_change_password'] == true
                                ? 'Heniz girmedi (wagtlaýyn parol)'
                                : 'Öz paroly bar')),
                            DataCell(TextButton(onPressed: () => _reset(u), child: const Text('Paroly täzele'))),
                          ]),
                      ]),
                    ),
                  ),
                ),
        ),
      ]),
    );
  }
}

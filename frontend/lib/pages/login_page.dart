import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';

/// Admin girişi. Login/parol dogry bolsa token saklanýar we programma açylýar.
/// Wagtlaýyn parol bilen ilkinji gezek girilende täze parol soralýar.
class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _user = TextEditingController();
  final _pass = TextEditingController();
  String? _error;
  bool _busy = false;

  Future<void> _login() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final r = await Api.instance.post('auth/login', {'username': _user.text.trim(), 'password': _pass.text})
          as Map<String, dynamic>;
      if (r['role'] != 'admin') {
        throw ApiException('Bu sahypa diňe admin üçin. Mugallymlar telefon programmasyny ulanýar.');
      }
      if (r['must_change_password'] == true && mounted) {
        Api.instance.setToken(r['token'] as String);
        final changed = await showDialog<bool>(
          context: context,
          barrierDismissible: false,
          builder: (_) => ChangePasswordDialog(oldPassword: _pass.text),
        );
        if (changed != true) Api.instance.setToken(null);
        return;
      }
      Api.instance.setToken(r['token'] as String);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.sidebarTop, AppColors.sidebarBottom],
          ),
        ),
        child: Center(
          child: SizedBox(
            width: 380,
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  const Icon(Icons.event_available, size: 44, color: AppColors.accent),
                  const SizedBox(height: 8),
                  const Text('Raspisaniýe', textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
                  const Text('Admin girişi', textAlign: TextAlign.center),
                  const SizedBox(height: 20),
                  TextField(controller: _user, decoration: const InputDecoration(labelText: 'Login')),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _pass,
                    obscureText: true,
                    decoration: const InputDecoration(labelText: 'Parol'),
                    onSubmitted: (_) => _login(),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  ],
                  const SizedBox(height: 20),
                  FilledButton(onPressed: _busy ? null : _login, child: const Text('Gir')),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class ChangePasswordDialog extends StatefulWidget {
  const ChangePasswordDialog({super.key, this.oldPassword});
  final String? oldPassword;

  @override
  State<ChangePasswordDialog> createState() => _ChangePasswordDialogState();
}

class _ChangePasswordDialogState extends State<ChangePasswordDialog> {
  late final _old = TextEditingController(text: widget.oldPassword ?? '');
  final _new = TextEditingController();
  final _again = TextEditingController();
  String? _error;

  Future<void> _save() async {
    if (_new.text != _again.text) {
      setState(() => _error = 'Täze parollar gabat gelmeýär.');
      return;
    }
    try {
      await Api.instance.post('auth/change-password', {'old_password': _old.text, 'new_password': _new.text});
      if (mounted) Navigator.pop(context, true);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Täze parol belläň'),
      content: SizedBox(
        width: 360,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          if (widget.oldPassword == null)
            TextField(controller: _old, obscureText: true, decoration: const InputDecoration(labelText: 'Häzirki parol')),
          TextField(controller: _new, obscureText: true,
              decoration: const InputDecoration(labelText: 'Täze parol (iň az 6 harp)')),
          TextField(controller: _again, obscureText: true,
              decoration: const InputDecoration(labelText: 'Täze parol (gaýtadan)')),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Ýatyr')),
        FilledButton(onPressed: _save, child: const Text('Ýatda sakla')),
      ],
    );
  }
}

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
      if (r['role'] != 'admin' && r['role'] != 'dean') {
        throw ApiException('Bu sahypa okuw bölümi we dekanlar üçin. Mugallymlar telefon programmasyny ulanýar.');
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
    final wide = MediaQuery.sizeOf(context).width > 900;
    final form = Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 380),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            if (!wide) ...[
              Row(children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.event_available, color: Colors.white),
                ),
                const SizedBox(width: 12),
                const Text('Raspisaniýe', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
              ]),
              const SizedBox(height: 32),
            ],
            const Text('Ulgama giriş', style: TextStyle(fontSize: 26, fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            const Text('Administratoryň login we paroly bilen giriň.', style: TextStyle(color: AppColors.textMuted)),
            const SizedBox(height: 28),
            const Text('Login', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
            const SizedBox(height: 6),
            TextField(
              controller: _user,
              autofocus: true,
              decoration: const InputDecoration(hintText: 'admin', prefixIcon: Icon(Icons.person_outline, size: 20)),
            ),
            const SizedBox(height: 16),
            const Text('Parol', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
            const SizedBox(height: 6),
            TextField(
              controller: _pass,
              obscureText: true,
              decoration: const InputDecoration(hintText: '••••••••', prefixIcon: Icon(Icons.lock_outline, size: 20)),
              onSubmitted: (_) => _login(),
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: AppColors.dangerSoft, borderRadius: BorderRadius.circular(8)),
                child: Row(children: [
                  const Icon(Icons.error_outline, size: 18, color: AppColors.danger),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_error!, style: const TextStyle(color: AppColors.danger))),
                ]),
              ),
            ],
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _busy ? null : _login,
              style: FilledButton.styleFrom(minimumSize: const Size(0, 46)),
              child: _busy
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('Gir'),
            ),
            const SizedBox(height: 20),
            const Text('Mugallymlar öz raspisaniýesini telefon programmasynda görýär.',
                textAlign: TextAlign.center, style: TextStyle(fontSize: 12.5, color: AppColors.textMuted)),
          ]),
        ),
      ),
    );
    if (!wide) return Scaffold(backgroundColor: AppColors.surface, body: form);
    return Scaffold(
      backgroundColor: AppColors.surface,
      body: Row(children: [
        Expanded(
          child: Container(
            color: AppColors.sidebarTop,
            padding: const EdgeInsets.all(48),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.event_available, color: Colors.white),
                ),
                const SizedBox(width: 12),
                const Text('Raspisaniýe', style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700)),
              ]),
              const Spacer(),
              const Text('Uniwersitetiň raspisaniýesini\nawtomat düzmek ulgamy',
                  style: TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w700, height: 1.25)),
              const SizedBox(height: 16),
              for (final line in const [
                'Hepdelik we synag raspisaniýesi — gabat gelmesiz',
                'Sanawjy we maýdalawjy hepdeler',
                'Word görnüşinde resmi nusga',
                'Mugallymlar üçin telefon programmasy',
              ])
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(children: [
                    const Icon(Icons.check_circle, size: 18, color: AppColors.success),
                    const SizedBox(width: 10),
                    Text(line, style: const TextStyle(color: Color(0xFFD0D5DD), fontSize: 15)),
                  ]),
                ),
              const Spacer(),
              const Text('Halkara nebit we gaz uniwersiteti', style: TextStyle(color: Color(0xFF98A2B3))),
            ]),
          ),
        ),
        Expanded(child: form),
      ]),
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

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../api.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _server = TextEditingController(text: Api.instance.server);
  final _user = TextEditingController();
  final _pass = TextEditingController();
  bool _busy = false;
  bool _showPass = false;
  String? _error;

  Future<void> _login() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final me = await Api.instance.login(_server.text, _user.text, _pass.text);
      if (!mounted) return;
      if (me['must_change_password'] == true) {
        final ok = await Navigator.of(context).push<bool>(
          MaterialPageRoute(builder: (_) => ChangePasswordScreen(oldPassword: _pass.text)),
        );
        if (ok != true) {
          await Api.instance.logout();
          return;
        }
      }
      Api.instance.enter();
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Icon(Icons.event_available, size: 64, color: cs.primary),
                const SizedBox(height: 8),
                const Text('Raspisaniýe', textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800)),
                const Text('Mugallymyň sapaklary we synaglary', textAlign: TextAlign.center),
                const SizedBox(height: 28),
                if (!kIsWeb) ...[
                  TextField(
                    controller: _server,
                    keyboardType: TextInputType.url,
                    decoration: const InputDecoration(
                      labelText: 'Serweriň salgysy',
                      prefixIcon: Icon(Icons.dns_outlined),
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                ],
                TextField(
                  controller: _user,
                  autocorrect: false,
                  decoration: const InputDecoration(
                    labelText: 'Login', prefixIcon: Icon(Icons.person_outline), border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _pass,
                  obscureText: !_showPass,
                  onSubmitted: (_) => _login(),
                  decoration: InputDecoration(
                    labelText: 'Parol',
                    prefixIcon: const Icon(Icons.lock_outline),
                    border: const OutlineInputBorder(),
                    suffixIcon: IconButton(
                      icon: Icon(_showPass ? Icons.visibility_off : Icons.visibility),
                      onPressed: () => setState(() => _showPass = !_showPass),
                    ),
                  ),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: TextStyle(color: cs.error)),
                ],
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: _busy ? null : _login,
                  style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 14)),
                  child: _busy
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Gir', style: TextStyle(fontSize: 16)),
                ),
                const SizedBox(height: 16),
                const Text('Login we wagtlaýyn paroly okuw bölüminden alyň.', textAlign: TextAlign.center),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

class ChangePasswordScreen extends StatefulWidget {
  const ChangePasswordScreen({super.key, this.oldPassword});
  final String? oldPassword;

  @override
  State<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends State<ChangePasswordScreen> {
  late final _old = TextEditingController(text: widget.oldPassword ?? '');
  final _new = TextEditingController();
  final _again = TextEditingController();
  String? _error;
  bool _busy = false;

  Future<void> _save() async {
    if (_new.text.length < 6) {
      setState(() => _error = 'Parol iň az 6 harp bolmaly.');
      return;
    }
    if (_new.text != _again.text) {
      setState(() => _error = 'Täze parollar gabat gelmeýär.');
      return;
    }
    setState(() => _busy = true);
    try {
      await Api.instance.changePassword(_old.text, _new.text);
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Täze parol')),
      body: ListView(padding: const EdgeInsets.all(24), children: [
        if (widget.oldPassword != null)
          const Text('Wagtlaýyn parol bilen girdiňiz. Diňe özüňiziň biljek täze parolyňyzy belläň.')
        else
          TextField(
            controller: _old,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'Häzirki parol', border: OutlineInputBorder()),
          ),
        const SizedBox(height: 16),
        TextField(
          controller: _new,
          obscureText: true,
          decoration: const InputDecoration(labelText: 'Täze parol (iň az 6 harp)', border: OutlineInputBorder()),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _again,
          obscureText: true,
          decoration: const InputDecoration(labelText: 'Täze parol (gaýtadan)', border: OutlineInputBorder()),
        ),
        if (_error != null) ...[
          const SizedBox(height: 12),
          Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
        ],
        const SizedBox(height: 20),
        FilledButton(onPressed: _busy ? null : _save, child: const Text('Ýatda sakla')),
      ]),
    );
  }
}

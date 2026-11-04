import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';
import 'student.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _user = TextEditingController();
  final _pass = TextEditingController();
  String _server = Api.instance.server;
  bool _busy = false;
  bool _showPass = false;
  String? _error;

  Future<void> _login() async {
    if (_user.text.trim().isEmpty || _pass.text.isEmpty) {
      setState(() => _error = 'Login we paroly giriziň.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final me = await Api.instance.login(_server, _user.text, _pass.text);
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

  /// Serweriň salgysy adaty ulanyja gerek däl, şonuň üçin aýratyn "Sazlamalar" penjiresinde.
  Future<void> _settings() async {
    final ctl = TextEditingController(text: _server);
    final v = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Serweriň salgysy'),
        content: TextField(
          controller: ctl,
          keyboardType: TextInputType.url,
          autocorrect: false,
          decoration: const InputDecoration(hintText: 'http://192.168.1.7:8000'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: const Text('Ýatyr')),
          TextButton(onPressed: () => Navigator.pop(c, ctl.text.trim()), child: const Text('Ýatda sakla')),
        ],
      ),
    );
    if (v != null && v.isNotEmpty) setState(() => _server = v);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C.surface,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 16),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(color: C.primary, borderRadius: BorderRadius.circular(12)),
                    child: const Icon(Icons.event_available, color: Colors.white, size: 26),
                  ),
                ),
                const SizedBox(height: 28),
                const Text('Raspisaniýe', style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700, color: C.text)),
                const SizedBox(height: 6),
                const Text('Mugallymlar giriň, talyplar toparyny saýlasyn.',
                    style: TextStyle(fontSize: 15, color: C.muted)),
                const SizedBox(height: 32),
                const _Label('Login'),
                TextField(
                  controller: _user,
                  autocorrect: false,
                  textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(hintText: 'meselem: annayew.a'),
                ),
                const SizedBox(height: 16),
                const _Label('Parol'),
                TextField(
                  controller: _pass,
                  obscureText: !_showPass,
                  onSubmitted: (_) => _login(),
                  decoration: InputDecoration(
                    hintText: '••••••••',
                    suffixIcon: IconButton(
                      icon: Icon(_showPass ? Icons.visibility_off_outlined : Icons.visibility_outlined, color: C.muted),
                      onPressed: () => setState(() => _showPass = !_showPass),
                    ),
                  ),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(color: const Color(0xFFFEF3F2), borderRadius: BorderRadius.circular(10)),
                    child: Row(children: [
                      const Icon(Icons.error_outline, color: C.danger, size: 20),
                      const SizedBox(width: 10),
                      Expanded(child: Text(_error!, style: const TextStyle(color: C.danger))),
                    ]),
                  ),
                ],
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: _busy ? null : _login,
                  child: _busy
                      ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white))
                      : const Text('Gir'),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(50)),
                  onPressed: () => Navigator.of(context)
                      .push(MaterialPageRoute(builder: (_) => StudentPickScreen(server: _server))),
                  icon: const Icon(Icons.school_outlined),
                  label: const Text('Men talyp — toparymy saýlaýaryn', style: TextStyle(fontSize: 15)),
                ),
                const SizedBox(height: 20),
                const Text('Mugallymlar: login we wagtlaýyn paroly okuw bölüminden alyň.',
                    textAlign: TextAlign.center, style: TextStyle(color: C.muted, fontSize: 13)),
                if (!kIsWeb) ...[
                  const SizedBox(height: 8),
                  Center(
                    child: TextButton.icon(
                      onPressed: _settings,
                      icon: const Icon(Icons.settings_outlined, size: 18, color: C.subtle),
                      label: Text('Serwer: ${Uri.tryParse(_server)?.host ?? _server}',
                          style: const TextStyle(color: C.subtle, fontSize: 13)),
                    ),
                  ),
                ],
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

class _Label extends StatelessWidget {
  const _Label(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Text(text, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: C.text)),
      );
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
    final first = widget.oldPassword != null;
    return Scaffold(
      backgroundColor: C.surface,
      appBar: AppBar(title: const Text('Täze parol')),
      body: SafeArea(
        child: ListView(padding: const EdgeInsets.all(24), children: [
          Text(
            first
                ? 'Siz wagtlaýyn parol bilen girdiňiz. Diňe özüňiziň biljek täze parolyňyzy belläň.'
                : 'Häzirki parolyňyzy we täze parolyňyzy giriziň.',
            style: const TextStyle(color: C.muted, fontSize: 15, height: 1.4),
          ),
          const SizedBox(height: 24),
          if (!first) ...[
            const _Label('Häzirki parol'),
            TextField(controller: _old, obscureText: true),
            const SizedBox(height: 16),
          ],
          const _Label('Täze parol'),
          TextField(controller: _new, obscureText: true, decoration: const InputDecoration(hintText: 'Iň az 6 harp')),
          const SizedBox(height: 16),
          const _Label('Täze parol (gaýtadan)'),
          TextField(controller: _again, obscureText: true, onSubmitted: (_) => _save()),
          if (_error != null) ...[
            const SizedBox(height: 14),
            Text(_error!, style: const TextStyle(color: C.danger)),
          ],
          const SizedBox(height: 24),
          FilledButton(onPressed: _busy ? null : _save, child: const Text('Ýatda sakla')),
        ]),
      ),
    );
  }
}

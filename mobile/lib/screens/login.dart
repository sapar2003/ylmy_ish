import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _phone = TextEditingController();
  final _pass = TextEditingController();
  final _code = TextEditingController();
  String _server = Api.instance.server;
  bool _withCode = false; // false: parol bilen, true: SMS kod bilen
  bool _codeSent = false;
  bool _busy = false;
  bool _showPass = false;
  String? _error;

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _setMode(bool withCode) => setState(() {
        _withCode = withCode;
        _codeSent = false;
        _error = null;
      });

  bool _needPhone() {
    if (_phone.text.trim().isNotEmpty) return false;
    setState(() => _error = 'Telefon nomerini giriziň.');
    return true;
  }

  Future<void> _loginPassword() async {
    if (_needPhone()) return;
    if (_pass.text.isEmpty) {
      setState(() => _error = 'Paroly giriziň.');
      return;
    }
    await _run(() async {
      final me = await Api.instance.phoneLogin(_server, _phone.text, _pass.text);
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
    });
  }

  Future<void> _sendCode() async {
    if (_needPhone()) return;
    await _run(() async {
      await Api.instance.requestCode(_server, _phone.text);
      setState(() => _codeSent = true);
    });
  }

  Future<void> _loginCode() async {
    if (_code.text.trim().isEmpty) {
      setState(() => _error = 'SMS kody giriziň.');
      return;
    }
    await _run(() async {
      await Api.instance.verifyCode(_server, _phone.text, _code.text.trim());
      Api.instance.enter();
    });
  }

  /// Serweriň salgysy adaty ulanyja gerek däl: nyşana uzak basyp açylýar.
  Future<void> _settings() async {
    if (kIsWeb) return;
    final ctl = TextEditingController(text: _server);
    final v = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Serweriň salgysy'),
        content: TextField(controller: ctl, keyboardType: TextInputType.url, autocorrect: false),
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
    final spinner = const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white));
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
                  child: GestureDetector(
                    onLongPress: _settings,
                    child: Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(color: C.primary, borderRadius: BorderRadius.circular(12)),
                      child: const Icon(Icons.event_available, color: Colors.white, size: 26),
                    ),
                  ),
                ),
                const SizedBox(height: 28),
                const Text('Raspisaniýe', style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700, color: C.text)),
                const SizedBox(height: 32),
                const _Label('Telefon nomeri'),
                TextField(
                  controller: _phone,
                  enabled: !_codeSent,
                  keyboardType: TextInputType.phone,
                  autocorrect: false,
                  textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(hintText: '+993 65 123456'),
                ),
                const SizedBox(height: 16),
                if (!_withCode) ...[
                  const _Label('Parol'),
                  TextField(
                    controller: _pass,
                    obscureText: !_showPass,
                    onSubmitted: (_) => _loginPassword(),
                    decoration: InputDecoration(
                      suffixIcon: IconButton(
                        icon: Icon(_showPass ? Icons.visibility_off_outlined : Icons.visibility_outlined, color: C.muted),
                        onPressed: () => setState(() => _showPass = !_showPass),
                      ),
                    ),
                  ),
                ] else if (_codeSent) ...[
                  const _Label('SMS kod'),
                  TextField(
                    controller: _code,
                    keyboardType: TextInputType.number,
                    maxLength: 6,
                    autofocus: true,
                    onSubmitted: (_) => _loginCode(),
                    decoration: const InputDecoration(hintText: '6 san', counterText: ''),
                  ),
                ],
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
                  onPressed: _busy ? null : (!_withCode ? _loginPassword : (_codeSent ? _loginCode : _sendCode)),
                  child: _busy ? spinner : Text(_withCode && !_codeSent ? 'Kod iber' : 'Gir'),
                ),
                const SizedBox(height: 12),
                if (_withCode && _codeSent)
                  TextButton(
                    onPressed: _busy ? null : () => setState(() => _codeSent = false),
                    child: const Text('Nomeri üýtget ýa-da kody täzeden iber'),
                  ),
                TextButton(
                  onPressed: _busy ? null : () => _setMode(!_withCode),
                  child: Text(_withCode ? 'Parol bilen gir' : 'SMS kod bilen gir'),
                ),
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
  const ChangePasswordScreen({super.key, this.oldPassword, this.firstPassword = false});
  final String? oldPassword;
  final bool firstPassword; // kod bilen giren, paroly ýok: häzirki parol soralmaýar

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
      if (widget.firstPassword) {
        await Api.instance.setPassword(_new.text);
      } else {
        await Api.instance.changePassword(_old.text, _new.text);
      }
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final first = widget.oldPassword != null || widget.firstPassword;
    return Scaffold(
      backgroundColor: C.surface,
      appBar: AppBar(title: const Text('Täze parol')),
      body: SafeArea(
        child: ListView(padding: const EdgeInsets.all(24), children: [
          Text(
            widget.firstPassword
                ? 'Parol goýsaňyz, indiki gezek SMS kodsuz girip bilersiňiz.'
                : first
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

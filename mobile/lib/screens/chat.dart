import 'dart:async';

import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';

String _initials(String name) =>
    name.trim().split(RegExp(r'\s+')).where((w) => w.isNotEmpty).take(2).map((w) => w[0]).join();

String _clock(DateTime d) => '${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';

/// Söhbetler sanawynda: şu gün bolsa sagady, ýogsam senesi.
String _when(String iso) {
  final d = DateTime.parse(iso).toLocal();
  final now = DateTime.now();
  if (d.year == now.year && d.month == now.month && d.day == now.day) return _clock(d);
  return '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}';
}

class _Avatar extends StatelessWidget {
  const _Avatar(this.name);
  final String name;

  @override
  Widget build(BuildContext context) => CircleAvatar(
        radius: 22,
        backgroundColor: C.primarySoft,
        child: Text(_initials(name), style: const TextStyle(color: C.primary, fontWeight: FontWeight.w700)),
      );
}

/// Çat bölümi: söhbetler, iň täzesi ýokarda.
class ChatListView extends StatefulWidget {
  const ChatListView({super.key});

  @override
  State<ChatListView> createState() => _ChatListViewState();
}

class _ChatListViewState extends State<ChatListView> {
  List<Map<String, dynamic>>? _items;
  String? _error;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
    _timer = Timer.periodic(const Duration(seconds: 20), (_) => _load());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final items = await Api.instance.chatConversations();
      if (mounted) {
        setState(() {
          _items = items;
          _error = null;
        });
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  Future<void> _open(int id, String name, String subtitle) async {
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ChatScreen(id: id, name: name, subtitle: subtitle)));
    _load();
  }

  Future<void> _newChat() async {
    final c = await Navigator.of(context).push<Map<String, dynamic>>(MaterialPageRoute(builder: (_) => const _ContactsScreen()));
    if (c != null) await _open(c['id'] as int, '${c['name']}', '${c['subtitle']}');
  }

  @override
  Widget build(BuildContext context) {
    final items = _items;
    return Scaffold(
      backgroundColor: Colors.transparent,
      floatingActionButton: FloatingActionButton(
        tooltip: 'Täze hat',
        backgroundColor: C.primary,
        foregroundColor: Colors.white,
        onPressed: _newChat,
        child: const Icon(Icons.edit_outlined),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.only(top: 8, bottom: 88), children: [
          if (items == null && _error == null)
            const Padding(padding: EdgeInsets.all(48), child: Center(child: CircularProgressIndicator()))
          else if (items == null)
            EmptyView(icon: Icons.wifi_off, title: 'Birikip bolmady', text: _error)
          else if (items.isEmpty)
            EmptyView(
              icon: Icons.chat_bubble_outline,
              title: 'Söhbet ýok',
              text: Api.instance.isStudent ? 'Mugallymyňyza ýazmak üçin aşakdaky düwmä basyň.' : 'Talybyňyza ýazmak üçin aşakdaky düwmä basyň.',
            )
          else
            for (final (i, c) in items.indexed) ...[
              if (i > 0) const Divider(indent: 72),
              ListTile(
                tileColor: C.surface,
                leading: _Avatar('${c['name']}'),
                title: Text('${c['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontWeight: (c['unread'] as int) > 0 ? FontWeight.w700 : FontWeight.w600, fontSize: 15)),
                subtitle: Text('${c['last_mine'] == true ? 'Siz: ' : ''}${c['last_text']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(color: (c['unread'] as int) > 0 ? C.text : C.muted)),
                trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Text(_when('${c['last_at']}'), style: const TextStyle(fontSize: 12, color: C.subtle)),
                  if ((c['unread'] as int) > 0) ...[
                    const SizedBox(height: 4),
                    Badge(label: Text('${c['unread']}'), backgroundColor: C.primary),
                  ],
                ]),
                onTap: () => _open(c['id'] as int, '${c['name']}', '${c['subtitle']}'),
              ),
            ],
        ]),
      ),
    );
  }
}

/// Täze hat: talyba öz mugallymlary, mugallyma öz talyplary.
class _ContactsScreen extends StatefulWidget {
  const _ContactsScreen();

  @override
  State<_ContactsScreen> createState() => _ContactsScreenState();
}

class _ContactsScreenState extends State<_ContactsScreen> {
  List<Map<String, dynamic>>? _items;
  String? _error;
  String _query = '';

  @override
  void initState() {
    super.initState();
    Api.instance.chatContacts().then((c) {
      if (mounted) setState(() => _items = c);
    }).catchError((Object e) {
      if (mounted) setState(() => _error = '$e');
    });
  }

  @override
  Widget build(BuildContext context) {
    final q = _query.toLowerCase();
    final shown = (_items ?? []).where((c) => '${c['name']} ${c['subtitle']}'.toLowerCase().contains(q)).toList();
    return Scaffold(
      appBar: AppBar(title: Text(Api.instance.isStudent ? 'Mugallymlarym' : 'Talyplarym')),
      body: _items == null
          ? (_error != null
              ? EmptyView(icon: Icons.wifi_off, title: 'Birikip bolmady', text: _error)
              : const Center(child: CircularProgressIndicator()))
          : Column(children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                child: TextField(
                  decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Gözle'),
                  onChanged: (v) => setState(() => _query = v),
                ),
              ),
              Expanded(
                child: shown.isEmpty
                    ? const EmptyView(icon: Icons.person_search_outlined, title: 'Hiç kim tapylmady',
                        text: 'Sanaw çap edilen raspisaniýe boýunça düzülýär.')
                    : ListView.separated(
                        itemCount: shown.length,
                        separatorBuilder: (_, _) => const Divider(indent: 72),
                        itemBuilder: (_, i) => ListTile(
                          tileColor: C.surface,
                          leading: _Avatar('${shown[i]['name']}'),
                          title: Text('${shown[i]['name']}', style: const TextStyle(fontWeight: FontWeight.w600)),
                          subtitle: Text('${shown[i]['subtitle']}', maxLines: 2, overflow: TextOverflow.ellipsis),
                          onTap: () => Navigator.of(context).pop(shown[i]),
                        ),
                      ),
              ),
            ]),
    );
  }
}

/// Bir adam bilen ýazyşma. Täze hatlar her 4 sekuntda barlanýar.
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key, required this.id, required this.name, required this.subtitle});
  final int id;
  final String name;
  final String subtitle;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _text = TextEditingController();
  final List<Map<String, dynamic>> _messages = [];
  Timer? _timer;
  bool _loading = true;
  bool _sending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _text.addListener(() => setState(() {}));
    _poll();
    _timer = Timer.periodic(const Duration(seconds: 4), (_) => _poll());
  }

  @override
  void dispose() {
    _timer?.cancel();
    _text.dispose();
    super.dispose();
  }

  Future<void> _poll() async {
    try {
      final after = _messages.isEmpty ? 0 : _messages.last['id'] as int;
      final fresh = await Api.instance.chatMessages(widget.id, after);
      if (!mounted) return;
      setState(() {
        final known = {for (final m in _messages) m['id']};
        _messages.addAll(fresh.where((m) => !known.contains(m['id'])));
        _loading = false;
        _error = null;
      });
    } on ApiException catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = e.message;
        });
      }
    }
  }

  Future<void> _send() async {
    final text = _text.text.trim();
    if (text.isEmpty || _sending) return;
    setState(() => _sending = true);
    try {
      final m = await Api.instance.chatSend(widget.id, text);
      if (!mounted) return;
      _text.clear();
      setState(() {
        if (!_messages.any((x) => x['id'] == m['id'])) _messages.add(m);
      });
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message), backgroundColor: C.danger));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(widget.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          if (widget.subtitle.isNotEmpty)
            Text(widget.subtitle, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: C.muted)),
        ]),
      ),
      body: Column(children: [
        if (_error != null && _messages.isNotEmpty)
          Container(
            width: double.infinity,
            color: const Color(0xFFFFFAEB),
            padding: const EdgeInsets.all(8),
            child: const Text('Serwere birikip bolmady, täzeden synanyşylýar...', textAlign: TextAlign.center, style: TextStyle(fontSize: 13)),
          ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _messages.isEmpty
                  ? (_error != null
                      ? EmptyView(icon: Icons.wifi_off, title: 'Birikip bolmady', text: _error)
                      : const EmptyView(icon: Icons.waving_hand_outlined, title: 'Ilkinji haty ýazyň'))
                  : ListView.builder(
                      reverse: true,
                      padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
                      itemCount: _messages.length,
                      itemBuilder: (_, i) => _Bubble(_messages[_messages.length - 1 - i]),
                    ),
        ),
        Container(
          decoration: const BoxDecoration(color: C.surface, border: Border(top: BorderSide(color: C.border))),
          child: SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 8, 8),
              child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Expanded(
                  child: TextField(
                    controller: _text,
                    minLines: 1,
                    maxLines: 4,
                    maxLength: 2000,
                    textCapitalization: TextCapitalization.sentences,
                    decoration: const InputDecoration(hintText: 'Hat ýazyň...', counterText: '', isDense: true),
                  ),
                ),
                const SizedBox(width: 4),
                IconButton(
                  tooltip: 'Iber',
                  onPressed: _text.text.trim().isEmpty || _sending ? null : _send,
                  icon: const Icon(Icons.send),
                  color: C.primary,
                ),
              ]),
            ),
          ),
        ),
      ]),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble(this.message);
  final Map<String, dynamic> message;

  @override
  Widget build(BuildContext context) {
    final mine = message['mine'] == true;
    final at = _clock(DateTime.parse('${message['at']}').toLocal());
    final date = _when('${message['at']}');
    final stamp = date == at ? at : '$date $at';
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.78),
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 6),
        decoration: BoxDecoration(
          color: mine ? C.primary : C.surface,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(14),
            topRight: const Radius.circular(14),
            bottomLeft: Radius.circular(mine ? 14 : 4),
            bottomRight: Radius.circular(mine ? 4 : 14),
          ),
          border: mine ? null : Border.all(color: C.border),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.end, mainAxisSize: MainAxisSize.min, children: [
          Align(
            alignment: Alignment.centerLeft,
            widthFactor: 1,
            child: Text('${message['text']}', style: TextStyle(color: mine ? Colors.white : C.text, fontSize: 15, height: 1.3)),
          ),
          const SizedBox(height: 3),
          Row(mainAxisSize: MainAxisSize.min, children: [
            Text(stamp, style: TextStyle(fontSize: 11, color: mine ? const Color(0xFFE0E7FF) : C.subtle)),
            if (mine) ...[
              const SizedBox(width: 4),
              Icon(message['read'] == true ? Icons.done_all : Icons.done, size: 14, color: const Color(0xFFE0E7FF)),
            ],
          ]),
        ]),
      ),
    );
  }
}

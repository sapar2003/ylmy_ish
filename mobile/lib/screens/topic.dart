import 'package:file_picker/file_picker.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../api.dart';
import '../theme.dart';
import 'document.dart';

const _extensions = ['pdf', 'ppt', 'pptx', 'pps', 'ppsx', 'odp', 'doc', 'docx', 'odt', 'xls', 'xlsx', 'txt', 'jpg',
    'jpeg', 'png', 'zip'];

/// Sapagyň faýlyny açmak/ýüklemek (brauzerde ýa-da telefonyň programmasynda).
Future<void> openTopicFile(BuildContext context, Map<String, dynamic> topic) async {
  final ok = await launchUrl(Api.instance.fileUri('${topic['file_url']}'), mode: LaunchMode.externalApplication);
  if (!ok && context.mounted) {
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Faýly açyp bolmady.')));
  }
}

/// Faýly app-yň içinde açýar. Brauzerdäki görnüşde PDF brauzeriň özünde açylýar; görkezip bolmaýan faýl ýüklenýär.
Future<void> openTopicPreview(BuildContext context, Map<String, dynamic> topic) async {
  final url = topic['preview_url'];
  if (url == null) return openTopicFile(context, topic);
  if (kIsWeb) {
    await launchUrl(Api.instance.fileUri('$url'));
    return;
  }
  await Navigator.of(context).push(MaterialPageRoute(builder: (_) => DocumentScreen(topic: topic)));
}

String fileSize(int? bytes) {
  if (bytes == null) return '';
  if (bytes < 1024 * 1024) return '${(bytes / 1024).ceil()} KB';
  return '${(bytes / 1024 / 1024).toStringAsFixed(1)} MB';
}

/// Sapak kartasynda: tema we faýl (talyp we mugallym üçin).
class TopicLine extends StatelessWidget {
  const TopicLine({super.key, required this.topic});
  final Map<String, dynamic> topic;

  @override
  Widget build(BuildContext context) {
    final text = '${topic['topic'] ?? ''}'.trim();
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: C.primarySoft, borderRadius: BorderRadius.circular(10)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (text.isNotEmpty)
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Icon(Icons.topic_outlined, size: 16, color: C.primary),
            const SizedBox(width: 6),
            Expanded(
              child: Text('Tema: $text', style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600, color: C.primaryDark)),
            ),
          ]),
        if (topic['note'] != null) ...[
          const SizedBox(height: 4),
          Text('${topic['note']}', style: const TextStyle(fontSize: 13, color: C.muted)),
        ],
        if (topic['file_url'] != null) ...[
          if (text.isNotEmpty || topic['note'] != null) const SizedBox(height: 8),
          InkWell(
            onTap: () => openTopicPreview(context, topic),
            borderRadius: BorderRadius.circular(8),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(color: C.surface, borderRadius: BorderRadius.circular(8), border: Border.all(color: C.border)),
              child: Row(children: [
                const Icon(Icons.slideshow_outlined, size: 18, color: C.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text('${topic['file_name']}', overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                ),
                Text(fileSize(topic['file_size'] as int?), style: const TextStyle(fontSize: 12, color: C.subtle)),
                const SizedBox(width: 6),
                Icon(topic['preview_url'] != null ? Icons.chevron_right : Icons.download_outlined, size: 18, color: C.primary),
              ]),
            ),
          ),
        ],
      ]),
    );
  }
}

/// Mugallym üçin: sapagyň temasyny ýazmak we prezentasiýa goşmak (sapakdan öň hem, soň hem bolýar).
class TopicEditor extends StatefulWidget {
  const TopicEditor({super.key, required this.entryId, required this.day});
  final int entryId;
  final DateTime day;

  @override
  State<TopicEditor> createState() => _TopicEditorState();
}

class _TopicEditorState extends State<TopicEditor> {
  final _topic = TextEditingController();
  final _note = TextEditingController();
  Map<String, dynamic>? _saved;
  bool _loading = true;
  bool _busy = false;

  bool get _dirty =>
      _topic.text.trim() != '${_saved?['topic'] ?? ''}' || _note.text.trim() != '${_saved?['note'] ?? ''}';

  @override
  void initState() {
    super.initState();
    _topic.addListener(() => setState(() {}));
    _note.addListener(() => setState(() {}));
    Api.instance.topic(widget.entryId, widget.day).then(_apply).catchError((Object e) {
      if (mounted) setState(() => _loading = false);
    });
  }

  void _apply(Map<String, dynamic>? t) {
    if (!mounted) return;
    setState(() {
      _saved = t;
      _topic.text = '${t?['topic'] ?? ''}';
      _note.text = '${t?['note'] ?? ''}';
      _loading = false;
    });
  }

  Future<void> _run(Future<Map<String, dynamic>?> Function() action, String done) async {
    setState(() => _busy = true);
    try {
      _apply(await action());
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(done)));
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message), backgroundColor: C.danger));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickFile() async {
    final f = await FilePicker.pickFile(type: FileType.custom, allowedExtensions: _extensions);
    if (f == null) return;
    if ((await f.length() ?? 0) > 30 * 1024 * 1024) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Faýl 30 MB-dan uly bolmaly däl.')));
      }
      return;
    }
    final bytes = await f.readAsBytes();
    await _run(() => Api.instance.uploadTopicFile(widget.entryId, widget.day, f.name, bytes), 'Faýl goşuldy.');
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const SizedBox(height: 60, child: Center(child: CircularProgressIndicator()));
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          const Text('Sapagyň temasy', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          const Text('Talyplar şu sapagyň temasyny we faýlyny telefonda görýär.',
              style: TextStyle(color: C.muted, fontSize: 13)),
          const SizedBox(height: 10),
          TextField(
            controller: _topic,
            maxLength: 300,
            decoration: const InputDecoration(hintText: 'Meselem: Sanawlar we massiwler', counterText: ''),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _note,
            minLines: 1,
            maxLines: 4,
            decoration: const InputDecoration(hintText: 'Bellik (hökman däl): öý işi, okamaly sahypalar...'),
          ),
          const SizedBox(height: 10),
          if (_saved?['file_url'] != null) ...[
            Row(children: [
              Expanded(child: TopicLine(topic: {'file_url': _saved!['file_url'], 'file_name': _saved!['file_name'],
                  'file_size': _saved!['file_size'], 'preview': _saved!['preview'], 'preview_url': _saved!['preview_url']})),
              IconButton(
                tooltip: 'Faýly aýyr',
                onPressed: _busy
                    ? null
                    : () => _run(() => Api.instance.deleteTopicFile(widget.entryId, widget.day), 'Faýl aýryldy.'),
                icon: const Icon(Icons.delete_outline, color: C.danger),
              ),
            ]),
            const SizedBox(height: 8),
          ],
          Row(children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _busy ? null : _pickFile,
                icon: const Icon(Icons.attach_file),
                label: Text(_saved?['file_url'] != null ? 'Faýly çalyş' : 'Prezentasiýa goş'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton(
                style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(44)),
                onPressed: _busy || !_dirty
                    ? null
                    : () => _run(() => Api.instance.saveTopic(widget.entryId, widget.day, _topic.text, _note.text),
                        'Tema ýatda saklandy.'),
                child: const Text('Temany sakla'),
              ),
            ),
          ]),
        ]),
      ),
    );
  }
}

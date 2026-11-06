import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:pdfx/pdfx.dart';

import '../api.dart';
import '../theme.dart';
import 'topic.dart';

/// Sapagyň prezentasiýasyny app-yň içinde görkezýär (PDF sahypalary ýa-da surat, ulaltmak bolýar).
class DocumentScreen extends StatefulWidget {
  const DocumentScreen({super.key, required this.topic});
  final Map<String, dynamic> topic;

  @override
  State<DocumentScreen> createState() => _DocumentScreenState();
}

class _DocumentScreenState extends State<DocumentScreen> {
  Uint8List? _bytes;
  PdfControllerPinch? _pdf;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final b = await Api.instance.downloadPreview('${widget.topic['preview_url']}');
      if (!mounted) return;
      setState(() {
        if (widget.topic['preview'] != 'image') _pdf = PdfControllerPinch(document: PdfDocument.openData(b));
        _bytes = b;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  @override
  void dispose() {
    _pdf?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bytes = _bytes;
    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.topic['file_name']}', overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 16)),
        actions: [
          IconButton(
            tooltip: 'Asyl faýly ýükle',
            icon: const Icon(Icons.download_outlined),
            onPressed: () => openTopicFile(context, widget.topic),
          ),
        ],
      ),
      backgroundColor: C.bg,
      body: _error != null
          ? Center(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                EmptyView(icon: Icons.error_outline, title: 'Faýly açyp bolmady', text: _error),
                Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  TextButton(onPressed: _load, child: const Text('Gaýtadan synan')),
                  const SizedBox(width: 8),
                  TextButton(onPressed: () => openTopicFile(context, widget.topic), child: const Text('Asyl faýly ýükle')),
                ]),
              ]),
            )
          : bytes == null
              ? const Center(
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 16),
                    Text('Faýl taýýarlanýar...', style: TextStyle(color: C.muted)),
                  ]),
                )
              : widget.topic['preview'] == 'image'
                  ? InteractiveViewer(maxScale: 5, child: Center(child: Image.memory(bytes)))
                  : PdfViewPinch(controller: _pdf!),
    );
  }
}

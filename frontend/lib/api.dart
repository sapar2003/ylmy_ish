import 'dart:convert';

import 'package:http/http.dart' as http;

/// Backend-iň salgysy. Web-de UI we API bir serwerden berilýär, şonuň üçin
/// adaty ýagdaýda sahypanyň öz salgysy ulanylýar. Başga salgy üçin:
/// `flutter run --dart-define=API_URL=http://localhost:8000`.
const _apiUrlOverride = String.fromEnvironment('API_URL');

class ApiException implements Exception {
  ApiException(this.message);
  final String message;
  @override
  String toString() => message;
}

class Api {
  Api._();
  static final Api instance = Api._();

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final base = _apiUrlOverride.isNotEmpty ? Uri.parse(_apiUrlOverride) : Uri.base;
    return base.replace(
      path: '/api/v1/$path',
      queryParameters: query?.map((k, v) => MapEntry(k, '$v')),
      fragment: '',
    );
  }

  Future<dynamic> _send(Future<http.Response> request) async {
    final http.Response res;
    try {
      res = await request;
    } catch (e) {
      throw ApiException('Serwere birikip bolmady: $e');
    }
    final body = res.body.isEmpty ? null : jsonDecode(utf8.decode(res.bodyBytes));
    if (res.statusCode >= 400) throw ApiException(_detail(body) ?? 'Ýalňyşlyk ${res.statusCode}');
    return body;
  }

  String? _detail(dynamic body) {
    if (body is! Map) return null;
    final detail = body['detail'];
    if (detail is String) return detail;
    if (detail is List) {
      return detail.map((d) {
        final loc = (d['loc'] as List?)?.where((p) => p != 'body').join('.');
        return loc == null || loc.isEmpty ? d['msg'] : '$loc: ${d['msg']}';
      }).join('\n');
    }
    return null;
  }

  static const _json = {'Content-Type': 'application/json'};

  Future<dynamic> get(String path, [Map<String, dynamic>? query]) => _send(http.get(_uri(path, query)));

  /// Sanaw endpointleri `{items, total}` gaýtarýar; bu diňe `items`-i alýar.
  Future<List<Map<String, dynamic>>> list(String path, [Map<String, dynamic>? query]) async {
    final body = await get(path, {'limit': 500, ...?query});
    final items = body is Map ? body['items'] : body;
    return (items as List).cast<Map<String, dynamic>>();
  }

  Future<dynamic> post(String path, Object data) =>
      _send(http.post(_uri(path), headers: _json, body: jsonEncode(data)));

  Future<dynamic> put(String path, Object data) =>
      _send(http.put(_uri(path), headers: _json, body: jsonEncode(data)));

  Future<dynamic> patch(String path, Object data) =>
      _send(http.patch(_uri(path), headers: _json, body: jsonEncode(data)));

  Future<void> delete(String path) => _send(http.delete(_uri(path)));
}

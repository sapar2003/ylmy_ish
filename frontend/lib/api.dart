import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:web/web.dart' as web;

/// Backend-iň salgysy. Web-de UI we API bir serwerden berilýär, şonuň üçin
/// adaty ýagdaýda sahypanyň öz salgysy ulanylýar. Başga salgy üçin:
/// `flutter run --dart-define=API_URL=http://localhost:8000`.
const _apiUrlOverride = String.fromEnvironment('API_URL');
const _tokenKey = 'raspisaniye_admin_token';

class ApiException implements Exception {
  ApiException(this.message, [this.status]);
  final String message;
  final int? status;
  @override
  String toString() => message;
}

class Api {
  Api._();
  static final Api instance = Api._();

  /// Giriş tokeni brauzeriň ýadynda saklanýar (sahypa täzelense hem galýar).
  /// Token ýok ýa-da möhleti geçen bolsa `loggedIn` false bolýar we giriş sahypasy görünýär.
  final ValueNotifier<bool> loggedIn = ValueNotifier(_readToken() != null);
  String? _token = _readToken();

  /// Girýän ulanyjy (`auth/me`): admin ýa-da dekan. Dekan diňe öz fakultetiniň maglumatlaryny görýär.
  Map<String, dynamic>? me;
  bool get isDean => me?['role'] == 'dean';
  int? get deanFaculty => isDean ? me?['faculty']?['id'] as int? : null;

  static String? _readToken() {
    try {
      return web.window.localStorage.getItem(_tokenKey);
    } catch (_) {
      return null;
    }
  }

  void setToken(String? token) {
    _token = token;
    try {
      token == null ? web.window.localStorage.removeItem(_tokenKey) : web.window.localStorage.setItem(_tokenKey, token);
    } catch (_) {}
    loggedIn.value = token != null;
  }

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final base = _apiUrlOverride.isNotEmpty ? Uri.parse(_apiUrlOverride) : Uri.base;
    return base.replace(
      path: '/api/v1/$path',
      queryParameters: query?.map((k, v) => MapEntry(k, '$v')),
      fragment: '',
    );
  }

  /// Brauzerde açmak/ýüklemek üçin doly salgy (token hem goşulýar, sebäbi brauzer sözbaşy ibermeýär).
  /// Sanaw bahalary gaýtalanýan parametr bolýar (?page=1,2&page=3).
  Uri url(String path, Map<String, dynamic> query) => _uri(path).replace(
        queryParameters: {
          ...query.map((k, v) => MapEntry(k, v is Iterable ? v.map((x) => '$x') : '$v')),
          'token': ?_token,
        },
      );

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  Future<dynamic> _send(Future<http.Response> request) async {
    final http.Response res;
    try {
      res = await request;
    } catch (e) {
      throw ApiException('Serwere birikip bolmady: $e');
    }
    final body = res.body.isEmpty ? null : jsonDecode(utf8.decode(res.bodyBytes));
    if (res.statusCode == 401 && _token != null) setToken(null); // möhleti geçdi: täzeden giriň
    if (res.statusCode >= 400) throw ApiException(_detail(body) ?? 'Ýalňyşlyk ${res.statusCode}', res.statusCode);
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

  Future<dynamic> get(String path, [Map<String, dynamic>? query]) =>
      _send(http.get(_uri(path, query), headers: _headers));

  /// Sanaw endpointleri `{items, total}` gaýtarýar; bu diňe `items`-i alýar.
  /// 500-den köp bolsa (meselem, talyplar) ähli sahypalary yzly-yzyna alýar.
  Future<List<Map<String, dynamic>>> list(String path, [Map<String, dynamic>? query]) async {
    final out = <Map<String, dynamic>>[];
    while (true) {
      final body = await get(path, {'limit': 500, 'offset': out.length, ...?query});
      if (body is! Map) return (body as List).cast<Map<String, dynamic>>();
      final items = (body['items'] as List).cast<Map<String, dynamic>>();
      out.addAll(items);
      if (items.isEmpty || out.length >= (body['total'] as int? ?? 0)) return out;
    }
  }

  Future<dynamic> post(String path, Object data) =>
      _send(http.post(_uri(path), headers: _headers, body: jsonEncode(data)));

  Future<dynamic> put(String path, Object data) =>
      _send(http.put(_uri(path), headers: _headers, body: jsonEncode(data)));

  Future<dynamic> patch(String path, Object data) =>
      _send(http.patch(_uri(path), headers: _headers, body: jsonEncode(data)));

  Future<void> delete(String path) => _send(http.delete(_uri(path), headers: _headers));
}

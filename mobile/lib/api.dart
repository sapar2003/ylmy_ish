import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.offline = false});
  final String message;
  final bool offline; // serwere birikip bolmady (internet/Wi-Fi ýok)
  @override
  String toString() => message;
}

/// Raspisaniýe serweri bilen işlemek. Mugallym diňe öz maglumatlaryny alýar (serwer tokene görä süzýär).
/// Soňky jogaplar telefonda saklanýar: internet ýok bolsa-da soňky raspisaniýe görünýär.
class Api {
  Api._();
  static final Api instance = Api._();

  /// Synag üçin adaty serwer: admin kompýuteri, şol bir Wi-Fi-da.
  static const defaultServer = 'http://192.168.1.7:8000';

  late SharedPreferences _prefs;
  String server = defaultServer;
  String? token;
  Map<String, dynamic>? me;

  /// Talyp: {group_id, group, subgroup_id, subgroup, faculty}; raspisaniýesi şol topar boýunça.
  Map<String, dynamic>? get student => me?['student'] as Map<String, dynamic>?;
  bool get isStudent => me?['role'] == 'student';

  /// Girilen ýagdaý üýtgände (giriş/çykyş) UI täzelenýär.
  final ValueNotifier<bool> loggedIn = ValueNotifier(false);

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    // Web-de app serwerden berilýär (/m/), şonuň üçin serwer — sahypanyň öz salgysy.
    server = kIsWeb ? Uri.base.origin : (_prefs.getString('server') ?? defaultServer);
    token = _prefs.getString('token');
    final saved = _prefs.getString('me');
    me = saved == null ? null : jsonDecode(saved) as Map<String, dynamic>;
    await _prefs.remove('student'); // köne wersiýanyň topar saýlawy
    loggedIn.value = token != null && me != null;
  }

  Uri _uri(String path, [Map<String, String>? query]) =>
      Uri.parse('$server/api/v1/$path').replace(queryParameters: query);

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Future<dynamic> _send(Future<http.Response> request) async {
    final http.Response res;
    try {
      res = await request.timeout(const Duration(seconds: 15));
    } catch (_) {
      throw ApiException('Serwere birikip bolmady. Wi-Fi/interneti we serweriň salgysyny barlaň.', offline: true);
    }
    final body = res.body.isEmpty ? null : jsonDecode(utf8.decode(res.bodyBytes));
    if (res.statusCode == 401 && token != null) await logout();
    if (res.statusCode >= 400) {
      final detail = body is Map ? body['detail'] : null;
      throw ApiException(detail is String ? detail : 'Ýalňyşlyk ${res.statusCode}');
    }
    return body;
  }

  Future<Map<String, dynamic>> _enter(Object response) async {
    final r = response as Map<String, dynamic>;
    if (r['role'] != 'teacher' && r['role'] != 'student') {
      throw ApiException('Bu programma mugallymlar we talyplar üçin.');
    }
    token = r['token'] as String;
    me = r..remove('token');
    await _prefs.setString('token', token!);
    await _prefs.setString('me', jsonEncode(me));
    return me!;
  }

  Future<Map<String, dynamic>> phoneLogin(String serverUrl, String phone, String password) async {
    await _useServer(serverUrl);
    return _enter(await _send(http.post(_uri('auth/phone-login'), headers: _headers,
        body: jsonEncode({'phone': phone, 'password': password}))));
  }

  /// Telefona giriş kody iberýär.
  Future<void> requestCode(String serverUrl, String phone) async {
    await _useServer(serverUrl);
    await _send(http.post(_uri('auth/otp/request'), headers: _headers, body: jsonEncode({'phone': phone})));
  }

  Future<Map<String, dynamic>> verifyCode(String serverUrl, String phone, String code) async {
    await _useServer(serverUrl);
    return _enter(await _send(http.post(_uri('auth/otp/verify'), headers: _headers,
        body: jsonEncode({'phone': phone, 'code': code}))));
  }

  /// Kod bilen girip, paroly ýok hasaba ilkinji paroly goýmak.
  Future<void> setPassword(String newPassword) async {
    me = await _send(http.post(_uri('auth/set-password'), headers: _headers,
        body: jsonEncode({'new_password': newPassword}))) as Map<String, dynamic>;
    await _prefs.setString('me', jsonEncode(me));
  }

  Future<void> changePassword(String oldPassword, String newPassword) async {
    me = await _send(http.post(_uri('auth/change-password'), headers: _headers,
        body: jsonEncode({'old_password': oldPassword, 'new_password': newPassword}))) as Map<String, dynamic>;
    await _prefs.setString('me', jsonEncode(me));
  }

  void enter() => loggedIn.value = true;

  /// Profil maglumatlaryny serwerden täzeleýär.
  Future<void> refreshMe() async {
    me = await _send(http.get(_uri('auth/me'), headers: _headers)) as Map<String, dynamic>;
    await _prefs.setString('me', jsonEncode(me));
  }

  Future<void> _useServer(String serverUrl) async {
    if (kIsWeb) return;
    server = serverUrl.trim().replaceAll(RegExp(r'/+$'), '');
    await _prefs.setString('server', server);
  }

  Future<void> logout() async {
    token = null;
    me = null;
    for (final k in _prefs.getKeys().where((k) => k != 'server').toList()) {
      await _prefs.remove(k);
    }
    loggedIn.value = false;
  }

  /// GET + telefondaky ýat: serwer jogap berse saklanýar, birikip bolmasa saklanany gaýtarýar.
  Future<({dynamic data, bool cached})> _cached(String path, [Map<String, String>? query]) async {
    final key = 'cache:$path?${query ?? ''}';
    try {
      final data = await _send(http.get(_uri(path, query), headers: _headers));
      await _prefs.setString(key, jsonEncode(data));
      return (data: data, cached: false);
    } on ApiException catch (e) {
      final saved = _prefs.getString(key);
      if (e.offline && saved != null) return (data: jsonDecode(saved), cached: true);
      rethrow;
    }
  }

  /// Hepdäniň sapaklary (`on` senäniň hepdesi; sanawjy/maýdalawjy serwerde kesgitlenýär).
  Future<({Map<String, dynamic> data, bool cached})> week(DateTime on) async {
    final r = isStudent
        ? await _cached('public/timetable', {
            'group_id': '${student!['group_id']}',
            if (student!['subgroup_id'] != null) 'subgroup_id': '${student!['subgroup_id']}',
            'on': isoDate(on),
          })
        : await _cached('me/timetable', {'on': isoDate(on)});
    return (data: r.data as Map<String, dynamic>, cached: r.cached);
  }

  Future<({List<Map<String, dynamic>> data, bool cached})> exams() async {
    final r = isStudent
        ? await _cached('public/exams', {'group_id': '${student!['group_id']}'})
        : await _cached('me/exams');
    return (data: (r.data as List).cast<Map<String, dynamic>>(), cached: r.cached);
  }

  // --- bahalar ---
  /// Sapagyň talyplary we şol günüň bahalary (`editable` — baha goýup bolýarmy).
  Future<Map<String, dynamic>> lesson(int entryId, DateTime day) async =>
      await _send(http.get(_uri('me/lesson', {'entry_id': '$entryId', 'day': isoDate(day)}), headers: _headers))
          as Map<String, dynamic>;

  /// `marks`: talybyň id-si → baha ("5", "4", "3", "2", "gm") ýa-da null (aýyrmak).
  // --- sapagyň temasy we faýly ---
  Map<String, String> _lessonQuery(int entryId, DateTime day) => {'entry_id': '$entryId', 'day': isoDate(day)};

  Future<Map<String, dynamic>?> topic(int entryId, DateTime day) async =>
      await _send(http.get(_uri('me/topic', _lessonQuery(entryId, day)), headers: _headers)) as Map<String, dynamic>?;

  Future<Map<String, dynamic>?> saveTopic(int entryId, DateTime day, String topic, String note) async =>
      await _send(http.put(_uri('me/topic'), headers: _headers, body: jsonEncode({
        'entry_id': entryId,
        'day': isoDate(day),
        'topic': topic.trim(),
        'note': note.trim().isEmpty ? null : note.trim(),
      }))) as Map<String, dynamic>?;

  /// Faýl göni sorag bedeninde iberilýär (multipart gerek däl).
  Future<Map<String, dynamic>?> uploadTopicFile(int entryId, DateTime day, String name, List<int> bytes) async =>
      await _send(http.put(_uri('me/topic/file', {..._lessonQuery(entryId, day), 'name': name}),
          headers: {..._headers, 'Content-Type': 'application/octet-stream'}, body: bytes)) as Map<String, dynamic>?;

  Future<Map<String, dynamic>?> deleteTopicFile(int entryId, DateTime day) async =>
      await _send(http.delete(_uri('me/topic/file', _lessonQuery(entryId, day)), headers: _headers))
          as Map<String, dynamic>?;

  /// Serweriň berýän faýl salgysy (/api/v1/public/files/...) -> doly salgy.
  /// Faýl brauzerde açylýar, şonuň üçin token salgyda.
  Uri fileUri(String path) => Uri.parse('$server$path').replace(queryParameters: {'token': ?token});

  Future<Map<String, dynamic>> saveLesson(int entryId, DateTime day, Map<int, String?> marks) async =>
      await _send(http.put(_uri('me/lesson'), headers: _headers, body: jsonEncode({
        'entry_id': entryId,
        'day': isoDate(day),
        'marks': [for (final e in marks.entries) {'student_id': e.key, 'value': e.value}],
      }))) as Map<String, dynamic>;

  Future<({List<Map<String, dynamic>> data, bool cached})> courses() async {
    final r = await _cached('me/courses');
    return (data: (r.data as List).cast<Map<String, dynamic>>(), cached: r.cached);
  }

  Future<({Map<String, dynamic> data, bool cached})> journal(int assignmentId) async {
    final r = await _cached('me/journal/$assignmentId');
    return (data: r.data as Map<String, dynamic>, cached: r.cached);
  }
}

String isoDate(DateTime d) =>
    '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

DateTime mondayOf(DateTime d) => DateTime(d.year, d.month, d.day - (d.weekday - 1));

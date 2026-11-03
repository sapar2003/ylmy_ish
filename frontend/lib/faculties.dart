import 'api.dart';

/// Ähli mugallymlar (başga fakultetlerden hem) — sapaga bellemek üçin saýlaw sanawy: id, ady, fakulteti.
Future<List<Map<String, dynamic>>> loadTeacherChoices() async =>
    ((await Api.instance.get('teachers/choices')) as List).cast<Map<String, dynamic>>();

/// Mugallym id -> fakultetiniň gysga ady, raspisaniýe kartlarynda görkezmek üçin.
Future<Map<int, String>> loadTeacherFaculties() async => {
      for (final t in await loadTeacherChoices())
        if (t['faculty'] != null) t['id'] as int: '${t['faculty']}',
    };

/// "Ady Familiýasy (STKF)"; fakulteti näbelli bolsa diňe at.
String withFaculty(Map<String, dynamic> teacherRef, Map<int, String> faculties) {
  final f = faculties[teacherRef['id']];
  return f == null ? '${teacherRef['name']}' : '${teacherRef['name']} ($f)';
}

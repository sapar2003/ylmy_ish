import 'api.dart';

/// Mugallym id -> fakultetiniň gysga ady (kafedrasy arkaly), raspisaniýe kartlarynda görkezmek üçin.
Future<Map<int, String>> loadTeacherFaculties(List<Map<String, dynamic>> teachers) async {
  final r = await Future.wait([Api.instance.list('departments'), Api.instance.list('faculties')]);
  final faculty = {for (final f in r[1]) f['id'] as int: '${f['short_name'] ?? f['name']}'};
  final facultyOfDepartment = {for (final d in r[0]) d['id'] as int: faculty[d['faculty_id']]};
  return {
    for (final t in teachers)
      if (facultyOfDepartment[t['department_id']] != null) t['id'] as int: facultyOfDepartment[t['department_id']]!,
  };
}

/// "Ady Familiýasy (STKF)"; fakulteti näbelli bolsa diňe at.
String withFaculty(Map<String, dynamic> teacherRef, Map<int, String> faculties) {
  final f = faculties[teacherRef['id']];
  return f == null ? '${teacherRef['name']}' : '${teacherRef['name']} ($f)';
}

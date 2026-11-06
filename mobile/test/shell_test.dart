import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mugallym/api.dart';
import 'package:mugallym/screens/shell.dart';
import 'package:mugallym/theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

Future<void> _open(WidgetTester tester, Map<String, dynamic> me) async {
  tester.view.physicalSize = const Size(1080, 2160);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  SharedPreferences.setMockInitialValues({'token': 't', 'me': jsonEncode(me)});
  await tester.runAsync(() => Api.instance.init());
  await tester.pumpWidget(MaterialApp(theme: appTheme(), home: const MainShell()));
  await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
  await tester.pump();
}

void main() {
  testWidgets('mugallym: dört bölüm we profil', (tester) async {
    await _open(tester, {
      'id': 1,
      'username': 'annayewa.a',
      'role': 'teacher',
      'has_password': true,
      'must_change_password': false,
      'teacher': {'id': 5, 'name': 'Annaýewa Aýlar Ražapowna'},
      'teacher_info': {'position': 'Mugallym-öwreniji', 'department': 'Kiberhowpsuzlyk kafedrasy', 'faculty': 'STKF', 'phone': '+99365111111'},
    });
    expect(find.text('Salam, Aýlar'), findsOneWidget);
    expect(find.text('Žurnal'), findsOneWidget);
    expect(find.byType(NavigationDestination), findsNWidgets(4));

    await tester.tap(find.text('Profil'));
    await tester.pump();
    expect(find.text('Annaýewa Aýlar Ražapowna'), findsOneWidget);
    expect(find.text('Kiberhowpsuzlyk kafedrasy'), findsOneWidget);
    expect(find.text('Paroly çalyş'), findsOneWidget);
    expect(find.text('Çykmak'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('talyp: dört bölüm, Žurnal ýerine Bahalar', (tester) async {
    await _open(tester, {
      'id': 2,
      'username': 'talyp1',
      'role': 'student',
      'has_password': false,
      'must_change_password': false,
      'teacher': null,
      'student': {'id': 1, 'name': 'Saparow Aman', 'group_id': 1, 'group': '2 MH (Ç)', 'subgroup_id': 1, 'subgroup': '2', 'faculty': 'STKF', 'course': 2},
    });
    expect(find.text('Salam, Aman'), findsOneWidget);
    expect(find.text('Žurnal'), findsNothing);
    expect(find.text('Bahalar'), findsWidgets);
    expect(find.byType(NavigationDestination), findsNWidgets(4));

    await tester.tap(find.text('Profil'));
    await tester.pump();
    expect(find.text('Parol goý'), findsOneWidget);
    expect(find.text('2-nji kurs'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

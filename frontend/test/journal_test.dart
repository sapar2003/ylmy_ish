import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:raspisaniye/pages/journal_gradebook.dart';
import 'package:raspisaniye/theme.dart';

Map<String, dynamic> _book(int students, int lessons) => {
      'assignment_id': 1,
      'subject': 'Maglumatlaryň gory we banklary',
      'lesson_type': 'lecture',
      'groups': ['2 MH (A)', '2 MH (B)'],
      'subgroup': null,
      'teacher': 'Repowa Annagözel',
      'columns': [
        for (var i = 0; i < lessons; i++)
          {'day': '2026-09-${(i % 28 + 1).toString().padLeft(2, '0')}', 'time_slot_id': i + 1, 'starts_at': '08:30'},
      ],
      'rows': [
        for (var s = 0; s < students; s++)
          {
            'student': {'id': s + 1, 'name': 'Talyp $s'},
            'group': '2 MH (A)',
            'marks': [for (var i = 0; i < lessons; i++) i == 0 ? '5' : (i == 1 ? 'gm' : null)],
            'average': 5.0,
            'absent': 1,
          },
      ],
    };

void main() {
  testWidgets('köp talyp we sapak: ýerleşiş ýalňyşsyz, baha goýmak işleýär', (tester) async {
    tester.view.physicalSize = const Size(1600, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final saved = <Object?>[];
    await tester.pumpWidget(MaterialApp(
      theme: buildTheme(),
      home: Scaffold(
        body: JournalGradebook(
          book: _book(40, 30),
          onSetMark: (row, col, value) async {
            saved.add(value);
            (row['marks'] as List)[col] = value;
          },
        ),
      ),
    ));
    await tester.pump();
    expect(tester.takeException(), isNull);
    expect(find.text('Talyp 0'), findsOneWidget);
    expect(find.text('40'), findsNWidgets(2)); // talyp sany we jemi gm

    // Gözleg.
    await tester.enterText(find.byType(TextField), 'Talyp 7');
    await tester.pump();
    expect(find.text('Talyp 7'), findsNWidgets(2)); // sanawda we gözleg meýdanynda
    expect(find.text('Talyp 0'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('öýjüge basyp bahany çalyşmak we ortaça täzelenmesi', (tester) async {
    tester.view.physicalSize = const Size(1600, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final saved = <String?>[];
    await tester.pumpWidget(MaterialApp(
      theme: buildTheme(),
      home: Scaffold(
        body: JournalGradebook(
          book: _book(1, 3),
          onSetMark: (row, col, value) async {
            saved.add(value);
            (row['marks'] as List)[col] = value;
          },
        ),
      ),
    ));
    await tester.pump();
    await tester.tap(find.text('5').first);
    await tester.pumpAndSettle();
    expect(find.text('Gatnaşmady'), findsOneWidget);
    expect(find.text('Bahany aýyr'), findsOneWidget);
    await tester.tap(find.text('4 baha'));
    await tester.pumpAndSettle();
    expect(saved, ['4']);
    expect(tester.takeException(), isNull);
  });

  testWidgets('talyp ýok: düwme görünýär', (tester) async {
    var pressed = false;
    await tester.pumpWidget(MaterialApp(
      theme: buildTheme(),
      home: Scaffold(
        body: JournalGradebook(book: _book(0, 3), onSetMark: (_, _, _) async {}, onCreateDemo: () => pressed = true),
      ),
    ));
    await tester.tap(find.text('Synag talyplaryny döret'));
    expect(pressed, isTrue);
  });
}

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mugallym/api.dart';
import 'package:mugallym/screens/chat.dart';
import 'package:mugallym/theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('çat ekrany: ýerleşiş ýalňyşsyz, serwer ýok bolsa bellik görünýär', (tester) async {
    tester.view.physicalSize = const Size(1080, 2160);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    SharedPreferences.setMockInitialValues({'token': 't', 'me': '{"role":"student"}'});
    await tester.runAsync(() => Api.instance.init());
    await tester.pumpWidget(MaterialApp(
      theme: appTheme(),
      home: const ChatScreen(id: 1, name: 'Annaýewa Aýlar Ražapowna', subtitle: 'Operasion ulgamlary'),
    ));
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 50)));
    await tester.pump();
    expect(find.text('Annaýewa Aýlar Ražapowna'), findsOneWidget);
    expect(find.byIcon(Icons.send), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

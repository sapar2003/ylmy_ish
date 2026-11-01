import 'package:flutter/material.dart';

import 'api.dart';
import 'screens/home.dart';
import 'screens/login.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Api.instance.init();
  runApp(const MugallymApp());
}

/// Mugallymyň raspisaniýesi: her mugallym öz login/paroly bilen girip, diňe öz sapaklaryny görýär.
class MugallymApp extends StatelessWidget {
  const MugallymApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Raspisaniýe — mugallym',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF3949AB),
        useMaterial3: true,
        cardTheme: const CardThemeData(margin: EdgeInsets.symmetric(horizontal: 12, vertical: 5)),
      ),
      home: ValueListenableBuilder<bool>(
        valueListenable: Api.instance.loggedIn,
        builder: (_, loggedIn, _) => loggedIn ? const HomeScreen() : const LoginScreen(),
      ),
    );
  }
}

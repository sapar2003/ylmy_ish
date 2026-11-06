import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'api.dart';
import 'screens/shell.dart';
import 'screens/login.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.dark,
    systemNavigationBarColor: Colors.white,
    systemNavigationBarIconBrightness: Brightness.dark,
  ));
  await Api.instance.init();
  runApp(const MugallymApp());
}

/// Mugallym we talyp app-y: telefon nomeri bilen girip, her kim diňe özüne degişlisini görýär.
class MugallymApp extends StatelessWidget {
  const MugallymApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Raspisaniýe',
      debugShowCheckedModeBanner: false,
      theme: appTheme(),
      home: ValueListenableBuilder<bool>(
        valueListenable: Api.instance.loggedIn,
        builder: (_, loggedIn, _) => loggedIn ? const MainShell() : const LoginScreen(),
      ),
    );
  }
}

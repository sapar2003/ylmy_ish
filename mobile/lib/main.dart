import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'api.dart';
import 'screens/home.dart';
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

/// Mugallymyň raspisaniýesi: her mugallym öz login/paroly bilen girip, diňe öz sapaklaryny görýär.
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
        builder: (_, loggedIn, _) => loggedIn ? const HomeScreen() : const LoginScreen(),
      ),
    );
  }
}

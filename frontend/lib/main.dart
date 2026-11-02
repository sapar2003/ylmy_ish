import 'package:flutter/material.dart';

import 'api.dart';
import 'pages/journal_page.dart';
import 'pages/accounts_page.dart';
import 'pages/crud_page.dart';
import 'pages/dashboard_page.dart';
import 'pages/exam_page.dart';
import 'pages/login_page.dart';
import 'pages/timetable_page.dart';
import 'resources.dart';
import 'theme.dart';

void main() => runApp(const RaspisaniyeApp());

class RaspisaniyeApp extends StatelessWidget {
  const RaspisaniyeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Raspisaniýe',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      // Girilmedik bolsa (ýa-da token möhleti geçse) giriş sahypasy.
      home: ValueListenableBuilder<bool>(
        valueListenable: Api.instance.loggedIn,
        builder: (_, loggedIn, _) => loggedIn ? const HomePage() : const LoginPage(),
      ),
    );
  }
}

/// Menýudaky bir sahypa.
class NavEntry {
  const NavEntry(this.key, this.label, this.icon, this.color);
  final String key; // 'home', 'timetable', 'exam-timetable', 'accounts' ýa-da sanawyň endpointi
  final String label;
  final IconData icon;
  final Color color;
}

class NavGroup {
  const NavGroup(this.title, this.entries);
  final String? title;
  final List<NavEntry> entries;
}

ResourceSpec? _spec(String endpoint) => resources.where((r) => r.endpoint == endpoint).firstOrNull;

/// Menýu işiň tertibine görä toparlanýar.
final List<NavGroup> navGroups = [
  const NavGroup(null, [NavEntry('home', 'Baş sahypa', Icons.space_dashboard_outlined, AppColors.primary)]),
  const NavGroup('Raspisaniýe', [
    NavEntry('timetable', 'Hepdelik raspisaniýe', Icons.calendar_view_week_outlined, AppColors.schedule),
    NavEntry('exam-timetable', 'Synag raspisaniýesi', Icons.fact_check_outlined, AppColors.exams),
  ]),
  for (final s in navSections)
    NavGroup(s.title, [
      for (final e in s.endpoints) ...[
        NavEntry(e, _spec(e)?.title ?? e, resourceIcons[e] ?? Icons.list, s.color),
        if (e == 'teachers') const NavEntry('accounts', 'Mugallym hasaplary', Icons.badge_outlined, AppColors.resources),
        if (e == 'students') const NavEntry('journal', 'Žurnal', Icons.grading_outlined, AppColors.secondary),
      ],
    ]),
];

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String _page = 'home';
  bool _collapsed = false;
  String _username = 'admin';
  bool _ready = false;

  @override
  void initState() {
    super.initState();
    Api.instance.get('auth/me').then((me) {
      Api.instance.me = me as Map<String, dynamic>;
      if (mounted) {
        setState(() {
          _username = '${me['username']}';
          _ready = true;
        });
      }
    }).catchError((_) {
      if (mounted) setState(() => _ready = true);
    });
  }

  /// Dekana görkezilmeýän bölümler (diňe okuw bölümi üçin).
  static const _adminOnly = {'accounts'};

  bool _visible(NavEntry e) => !(Api.instance.isDean && _adminOnly.contains(e.key));

  void _open(String key) => setState(() => _page = key);

  Widget _pageFor(String key) => switch (key) {
        'home' => DashboardPage(onOpen: _open),
        'timetable' => const TimetablePage(),
        'exam-timetable' => const ExamPage(),
        'accounts' => const AccountsPage(),
        'journal' => const JournalPage(),
        _ => CrudPage(spec: _spec(key)!),
      };

  @override
  Widget build(BuildContext context) {
    if (!_ready) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final narrow = MediaQuery.sizeOf(context).width < 1100;
    final collapsed = _collapsed || narrow;
    return Scaffold(
      body: Row(children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          width: collapsed ? 72 : 256,
          decoration: const BoxDecoration(
            color: AppColors.surface,
            border: Border(right: BorderSide(color: AppColors.border)),
          ),
          child: Column(children: [
            _brand(collapsed),
            const Divider(),
            Expanded(
              child: ListView(padding: const EdgeInsets.fromLTRB(10, 8, 10, 8), children: [
                for (final g in navGroups) ...[
                  if (g.title != null) _groupTitle(g.title!, collapsed),
                  for (final e in g.entries)
                    if (_visible(e)) _navItem(e, collapsed),
                ],
              ]),
            ),
            const Divider(),
            _userTile(collapsed, narrow),
          ]),
        ),
        Expanded(child: KeyedSubtree(key: ValueKey(_page), child: _pageFor(_page))),
      ]),
    );
  }

  Widget _brand(bool collapsed) => Padding(
        padding: EdgeInsets.fromLTRB(collapsed ? 16 : 18, 18, 12, 16),
        child: Row(children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(color: AppColors.primary, borderRadius: BorderRadius.circular(10)),
            child: const Icon(Icons.event_available, color: Colors.white, size: 22),
          ),
          if (!collapsed) ...[
            const SizedBox(width: 12),
            const Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('Raspisaniýe', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppColors.text)),
                Text('Halkara nebit we gaz uniwersiteti',
                    overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 11.5, color: AppColors.textMuted)),
              ]),
            ),
          ],
        ]),
      );

  Widget _groupTitle(String title, bool collapsed) => collapsed
      ? const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Divider())
      : Padding(
          padding: const EdgeInsets.fromLTRB(10, 18, 10, 6),
          child: Text(title.toUpperCase(),
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.6, color: AppColors.textSubtle)),
        );

  Widget _navItem(NavEntry e, bool collapsed) {
    final selected = _page == e.key;
    final item = Material(
      color: selected ? AppColors.primarySoft : Colors.transparent,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: () => _open(e.key),
        hoverColor: AppColors.background,
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: collapsed ? 0 : 10, vertical: 9),
          child: Row(
            mainAxisAlignment: collapsed ? MainAxisAlignment.center : MainAxisAlignment.start,
            children: [
              Icon(e.icon, size: 20, color: selected ? AppColors.primary : AppColors.textMuted),
              if (!collapsed) ...[
                const SizedBox(width: 12),
                Expanded(
                  child: Text(e.label,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                        color: selected ? AppColors.primaryDark : AppColors.text,
                      )),
                ),
              ],
            ],
          ),
        ),
      ),
    );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: collapsed ? Tooltip(message: e.label, preferBelow: false, child: item) : item,
    );
  }

  Widget _userTile(bool collapsed, bool narrow) {
    final menu = PopupMenuButton<String>(
      tooltip: 'Hasap',
      onSelected: (v) async {
        switch (v) {
          case 'password':
            await showDialog(context: context, builder: (_) => const ChangePasswordDialog());
          case 'logout':
            Api.instance.setToken(null);
          case 'collapse':
            setState(() => _collapsed = !_collapsed);
        }
      },
      itemBuilder: (_) => [
        const PopupMenuItem(value: 'password', child: ListTile(leading: Icon(Icons.key_outlined), title: Text('Paroly çalyş'))),
        if (!narrow)
          PopupMenuItem(
            value: 'collapse',
            child: ListTile(
              leading: Icon(_collapsed ? Icons.keyboard_double_arrow_right : Icons.keyboard_double_arrow_left),
              title: Text(_collapsed ? 'Menýuny giňelt' : 'Menýuny kiçelt'),
            ),
          ),
        const PopupMenuItem(value: 'logout', child: ListTile(leading: Icon(Icons.logout), title: Text('Çykmak'))),
      ],
      child: Padding(
        padding: EdgeInsets.symmetric(horizontal: collapsed ? 0 : 16, vertical: 14),
        child: Row(mainAxisAlignment: collapsed ? MainAxisAlignment.center : MainAxisAlignment.start, children: [
          CircleAvatar(
            radius: 17,
            backgroundColor: AppColors.primarySoft,
            child: Text(_username.substring(0, 1).toUpperCase(),
                style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700)),
          ),
          if (!collapsed) ...[
            const SizedBox(width: 10),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(_username, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
                Text(Api.instance.isDean ? 'Dekan · ${Api.instance.me?['faculty']?['name'] ?? ''}' : 'Administrator',
                    overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
              ]),
            ),
            const Icon(Icons.unfold_more, size: 18, color: AppColors.textMuted),
          ],
        ]),
      ),
    );
    return menu;
  }
}

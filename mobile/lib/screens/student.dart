import 'package:flutter/material.dart';

import '../api.dart';
import '../theme.dart';
import 'home.dart';
import 'login.dart';

/// Talybyň esasy ekrany: aşakda üç bölüm — Raspisaniýe, Synaglar, Profil.
class StudentHome extends StatefulWidget {
  const StudentHome({super.key});

  @override
  State<StudentHome> createState() => _StudentHomeState();
}

class _StudentHomeState extends State<StudentHome> {
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    Api.instance.refreshMe().then((_) {
      if (mounted) setState(() {});
    }).catchError((_) {}); // internet ýok: ýatda saklanan maglumat görkezilýär
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        bottom: false,
        // const däl: refreshMe-den soň salam we profil täze maglumat bilen çyzylýar.
        child: IndexedStack(index: _tab, children: [
          _Tab(header: _Greeting(), child: const ScheduleView()),
          const _Tab(header: _PageTitle('Synaglar', 'Ara we ýarymýyllyk synaglaryňyz'), child: ExamsView()),
          ProfileView(),
        ]),
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(border: Border(top: BorderSide(color: C.border))),
        child: NavigationBar(
          selectedIndex: _tab,
          onDestinationSelected: (i) => setState(() => _tab = i),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.calendar_today_outlined), selectedIcon: Icon(Icons.calendar_today), label: 'Raspisaniýe'),
            NavigationDestination(icon: Icon(Icons.assignment_outlined), selectedIcon: Icon(Icons.assignment), label: 'Synaglar'),
            NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'Profil'),
          ],
        ),
      ),
    );
  }
}

class _Tab extends StatelessWidget {
  const _Tab({required this.header, required this.child});
  final Widget header;
  final Widget child;

  @override
  Widget build(BuildContext context) => Column(children: [header, const Divider(), Expanded(child: child)]);
}

String _firstName(String fullName) {
  final parts = fullName.trim().split(RegExp(r'\s+'));
  return parts.length > 1 ? parts[1] : fullName;
}

class _Greeting extends StatelessWidget {
  const _Greeting();

  @override
  Widget build(BuildContext context) {
    final s = Api.instance.student ?? {};
    return Container(
      width: double.infinity,
      color: C.surface,
      padding: const EdgeInsets.fromLTRB(20, 14, 20, 14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Salam, ${_firstName('${s['name'] ?? ''}')}', style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
        const SizedBox(height: 4),
        Text('${s['group'] ?? ''}${s['subgroup'] != null ? ' · ${s['subgroup']}-nji kiçi topar' : ''}',
            style: const TextStyle(color: C.muted)),
      ]),
    );
  }
}

class _PageTitle extends StatelessWidget {
  const _PageTitle(this.title, this.subtitle);
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        color: C.surface,
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text(subtitle, style: const TextStyle(color: C.muted)),
        ]),
      );
}

/// Şu günüň häzirki ýa-da indiki sapagy: raspisaniýäniň ýokarsynda uly görnüşde.
class NextLessonCard extends StatelessWidget {
  const NextLessonCard({super.key, required this.entry, required this.now});
  final Map<String, dynamic> entry;
  final bool now; // true: häzir dowam edýär

  @override
  Widget build(BuildContext context) {
    const light = Color(0xFFE0E7FF);
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: C.primary, borderRadius: BorderRadius.circular(16)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(now ? 'HÄZIR' : 'INDIKI SAPAK',
            style: const TextStyle(color: light, fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 0.8)),
        const SizedBox(height: 6),
        Text('${entry['subject']['name']}',
            style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w700, height: 1.25)),
        const SizedBox(height: 10),
        Row(children: [
          const Icon(Icons.schedule, size: 16, color: light),
          const SizedBox(width: 6),
          Text('${hhmm(entry['starts_at'])} – ${hhmm(entry['ends_at'])}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
          const SizedBox(width: 16),
          const Icon(Icons.meeting_room_outlined, size: 16, color: light),
          const SizedBox(width: 6),
          Text('${entry['room']?['name'] ?? '—'}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
        ]),
        const SizedBox(height: 6),
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.person_outline, size: 16, color: light),
          const SizedBox(width: 6),
          Expanded(child: Text('${entry['teacher']['name']}', style: const TextStyle(color: light))),
        ]),
      ]),
    );
  }
}

/// Profil: talybyň maglumatlary, parol we çykmak.
class ProfileView extends StatefulWidget {
  const ProfileView({super.key});

  @override
  State<ProfileView> createState() => _ProfileViewState();
}

class _ProfileViewState extends State<ProfileView> {
  Future<void> _password() async {
    final first = Api.instance.me?['has_password'] == false;
    await Navigator.of(context).push(MaterialPageRoute(builder: (_) => ChangePasswordScreen(firstPassword: first)));
    if (mounted) setState(() {});
  }

  Future<void> _logout() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Çykmak'),
        content: const Text('Hasabyňyzdan çykmak isleýärsiňizmi?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Ýok')),
          TextButton(onPressed: () => Navigator.pop(c, true), child: const Text('Çyk', style: TextStyle(color: C.danger))),
        ],
      ),
    );
    if (yes == true) await Api.instance.logout();
  }

  @override
  Widget build(BuildContext context) {
    final s = Api.instance.student ?? {};
    final name = '${s['name'] ?? ''}';
    final initials = name.trim().split(RegExp(r'\s+')).where((w) => w.isNotEmpty).take(2).map((w) => w[0]).join();
    final first = Api.instance.me?['has_password'] == false;
    return ListView(padding: const EdgeInsets.fromLTRB(16, 24, 16, 24), children: [
      Center(
        child: CircleAvatar(
          radius: 42,
          backgroundColor: C.primary,
          child: Text(initials, style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w700)),
        ),
      ),
      const SizedBox(height: 14),
      Text(name, textAlign: TextAlign.center, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
      const SizedBox(height: 4),
      const Text('Talyp', textAlign: TextAlign.center, style: TextStyle(color: C.muted)),
      const SizedBox(height: 24),
      Card(
        child: Column(children: [
          _InfoRow(Icons.groups_outlined, 'Topar', '${s['group'] ?? '—'}'),
          const Divider(),
          _InfoRow(Icons.group_work_outlined, 'Kiçi topar', s['subgroup'] != null ? '${s['subgroup']}-nji kiçi topar' : 'Bellenmedik'),
          const Divider(),
          _InfoRow(Icons.school_outlined, 'Kurs', s['course'] != null ? '${s['course']}-nji kurs' : '—'),
          const Divider(),
          _InfoRow(Icons.account_balance_outlined, 'Fakultet', '${s['faculty'] ?? '—'}'),
          if (s['phone'] != null) ...[
            const Divider(),
            _InfoRow(Icons.phone_outlined, 'Telefon', '${s['phone']}'),
          ],
        ]),
      ),
      const SizedBox(height: 14),
      Card(
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          ListTile(
            leading: const Icon(Icons.key_outlined, color: C.primary),
            title: Text(first ? 'Parol goý' : 'Paroly çalyş'),
            subtitle: first ? const Text('Indiki gezek SMS kodsuz girmek üçin') : null,
            trailing: const Icon(Icons.chevron_right, color: C.subtle),
            onTap: _password,
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.logout, color: C.danger),
            title: const Text('Çykmak', style: TextStyle(color: C.danger)),
            onTap: _logout,
          ),
        ]),
      ),
      const SizedBox(height: 16),
      const Text('Maglumat ýalňyş bolsa, dekanata ýüz tutuň.', textAlign: TextAlign.center, style: TextStyle(color: C.subtle, fontSize: 13)),
    ]);
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow(this.icon, this.label, this.value);
  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
        child: Row(children: [
          Icon(icon, size: 20, color: C.muted),
          const SizedBox(width: 12),
          Text(label, style: const TextStyle(color: C.muted)),
          const SizedBox(width: 16),
          Expanded(child: Text(value, textAlign: TextAlign.right, style: const TextStyle(fontWeight: FontWeight.w600))),
        ]),
      );
}

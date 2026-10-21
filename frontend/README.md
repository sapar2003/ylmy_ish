# Raspisaniýe: Flutter frontend

Web administrator paneli (geljekde Windows we Android hem). Sahypalar:

- **Raspisaniýe**: "Awtomat düz" düwmesi, topar / mugallym / otag boýunça hepdelik setka.
- **Sanawlar**: fakultet, kafedra, hünär, smena, topar, kiçi topar, mugallym, bina, otag, ders, potok,
  okuw meýilnamasy. Hemmesini goşup, üýtgedip, aýryp bolýar.
- Mugallymyň **boş wagty** (slota basyp: bolup bilýär / isleýär / bolmaz), okuw meýilnamasyna
  **mugallym bellemek** (bölünýän sapakda her kiçi topara), smena üçin **wagt slotlaryny** döretmek.

Täze sanaw goşmak: `lib/resources.dart` faýlyna bir `ResourceSpec` goşmak ýeterlik.

```bash
flutter pub get
flutter run -d chrome --dart-define=API_URL=http://localhost:8000   # ösdürmek
flutter build web --no-web-resources-cdn                            # backend şu build-i berýär
```

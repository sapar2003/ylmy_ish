/// Ähli sanaw sahypalarynyň beýany. Täze sanaw goşmak = bu ýere bir `ResourceSpec`.
enum FieldType { text, integer, ref, refList, choice, boolean, time, date, weekdays }

class FieldSpec {
  const FieldSpec(
    this.key,
    this.label, {
    this.type = FieldType.text,
    this.required = true,
    this.ref,
    this.choices,
    this.showInTable = true,
  });

  final String key;
  final String label;
  final FieldType type;
  final bool required;
  final String? ref; // `ref`/`refList` üçin endpoint, meselem 'faculties'
  final Map<String, String>? choices; // `choice` üçin: baha -> ýazgy
  final bool showInTable;
}

enum RowAction { availability, assignments, generateSlots }

class ResourceSpec {
  const ResourceSpec({
    required this.endpoint,
    required this.title,
    required this.singular,
    required this.fields,
    this.actions = const [],
    this.facultyFilter,
    this.description,
  });

  final String endpoint;
  final String title;
  final String singular;
  final List<FieldSpec> fields;
  final List<RowAction> actions;

  /// Sanawy fakultet boýunça süzmek: ýazgynyň haýsy meýdany fakultete eltýär.
  final FacultyVia? facultyFilter;

  /// Sahypanyň ýokarsyndaky gysga düşündiriş: bu sanaw näme üçin, nädip doldurmaly.
  final String? description;
}

/// `faculty_id` — ýazgynyň öz meýdany (otag); `department_id` — kafedra arkaly (mugallym).
enum FacultyVia { faculty, department }

const lessonTypes = {'lecture': 'Leksiýa', 'practice': 'Amaly', 'lab': 'Tejribe', 'seminar': 'Seminar'};
const levels = {'bachelor': 'Bakalawr', 'master': 'Magistr'};
const weekdays = ['Duşenbe', 'Sişenbe', 'Çarşenbe', 'Penşenbe', 'Anna', 'Şenbe', 'Ýekşenbe'];
// Iki hepdelik raspisaniýäniň hepdeleri: 1 — sanawjy, 2 — maýdalawjy (ýarymýylyň ilkinji hepdesi sanawjy).
const weekNames = {1: 'Sanawjy', 2: 'Maýdalawjy'};
const examKinds = {
  'midterm': 'Ara synag',
  'final': 'Ýarymýyllyk synag',
  'retake': 'Gaýtadan tabşyrmak',
  'state': 'Döwlet synagy',
  'other': 'Başga',
};

const resources = <ResourceSpec>[
  ResourceSpec(endpoint: 'faculties', description: 'Uniwersitetiň fakultetleri. Kafedralar, hünärler we toparlar fakultete degişli bolýar.', title: 'Fakultetler', singular: 'Fakultet', fields: [
    FieldSpec('name', 'Ady'),
    FieldSpec('short_name', 'Gysga ady', required: false),
    FieldSpec('code', 'Kody', required: false),
  ]),
  ResourceSpec(endpoint: 'departments', description: 'Kafedralar. Mugallymlar we dersler kafedra degişli.', title: 'Kafedralar', singular: 'Kafedra', fields: [
    FieldSpec('name', 'Ady'),
    FieldSpec('faculty_id', 'Fakultet', type: FieldType.ref, ref: 'faculties'),
  ]),
  ResourceSpec(endpoint: 'specialties', description: 'Taýýarlyk ugurlary (hünärler). Her topar bir hünäre degişli.', title: 'Hünärler', singular: 'Hünär', fields: [
    FieldSpec('name', 'Ady'),
    FieldSpec('code', 'Kody', required: false),
    FieldSpec('level', 'Derejesi', type: FieldType.choice, choices: levels),
    FieldSpec('duration_years', 'Okuw ýyly', type: FieldType.integer),
    FieldSpec('department_id', 'Kafedra', type: FieldType.ref, ref: 'departments'),
  ]),
  ResourceSpec(
    endpoint: 'shifts',
    description: 'Okuw smenalary (irden, öýlän). Smenanyň setirindäki "Wagt slotlary" düwmesi bilen jübütleriň '
        'wagtlaryny dörediň.',
    title: 'Smenalar',
    singular: 'Smena',
    actions: [RowAction.generateSlots],
    fields: [
      FieldSpec('name', 'Ady'),
      FieldSpec('starts_at', 'Başlanýar', type: FieldType.time),
      FieldSpec('ends_at', 'Gutarýar', type: FieldType.time),
    ],
  ),
  ResourceSpec(endpoint: 'groups', description: 'Talyp toparlary: kursy, talyp sany we smenasy. Smena bellenmese, topar islendik wagtda okap biler.', title: 'Toparlar', singular: 'Topar', fields: [
    FieldSpec('name', 'Ady'),
    FieldSpec('course', 'Kurs', type: FieldType.integer),
    FieldSpec('student_count', 'Talyp sany', type: FieldType.integer),
    FieldSpec('specialty_id', 'Hünär', type: FieldType.ref, ref: 'specialties'),
    FieldSpec('shift_id', 'Smena', type: FieldType.ref, ref: 'shifts', required: false),
  ]),
  ResourceSpec(endpoint: 'subgroups', description: 'Kiçi toparlar: tejribe sapaklarynda topar bölünende (meselem, 1-nji we 2-nji kiçi topar).', title: 'Kiçi toparlar', singular: 'Kiçi topar', fields: [
    FieldSpec('name', 'Ady'),
    FieldSpec('student_count', 'Talyp sany', type: FieldType.integer),
    FieldSpec('group_id', 'Topar', type: FieldType.ref, ref: 'groups'),
  ]),
  ResourceSpec(
    endpoint: 'teachers',
    description: 'Mugallymlar. "Boş wagty" düwmesi bilen mugallymyň okadyp bilmeýän ýa-da isleýän wagtlaryny belläň.',
    title: 'Mugallymlar',
    singular: 'Mugallym',
    actions: [RowAction.availability],
    facultyFilter: FacultyVia.department,
    fields: [
      FieldSpec('name', 'Ady'),
      FieldSpec('position', 'Wezipesi', required: false),
      FieldSpec('department_id', 'Kafedra', type: FieldType.ref, ref: 'departments'),
      FieldSpec('max_lessons_per_day', 'Günde iň köp', type: FieldType.integer, required: false),
      FieldSpec('max_lessons_per_week', 'Hepdede iň köp', type: FieldType.integer, required: false),
    ],
  ),
  ResourceSpec(endpoint: 'buildings', description: 'Okuw binalary.', title: 'Binalar', singular: 'Bina', fields: [
    FieldSpec('name', 'Ady'),
    FieldSpec('address', 'Salgysy', required: false),
  ]),
  ResourceSpec(endpoint: 'room-types', description: 'Otag görnüşleri (okuw otagy, kompýuter otagy, laboratoriýa...). Okuw meýilnamasynda sapaga gerek otag görnüşini saýlamak üçin.', title: 'Otag görnüşleri', singular: 'Otag görnüşi', fields: [
    FieldSpec('name', 'Ady'),
  ]),
  ResourceSpec(endpoint: 'rooms', description: 'Otaglar: sygymy, görnüşi we haýsy fakultete degişlidigi. Fakulteti boş otag ähli fakultetler üçin umumy.', title: 'Otaglar', singular: 'Otag', facultyFilter: FacultyVia.faculty, fields: [
    FieldSpec('name', 'Ady'),
    FieldSpec('capacity', 'Sygymy', type: FieldType.integer),
    FieldSpec('building_id', 'Bina', type: FieldType.ref, ref: 'buildings'),
    FieldSpec('room_type_id', 'Görnüşi', type: FieldType.ref, ref: 'room-types'),
    FieldSpec('faculty_id', 'Fakultet', type: FieldType.ref, ref: 'faculties', required: false),
  ]),
  ResourceSpec(endpoint: 'subjects', description: 'Dersler. Her ders bir kafedra degişli.', title: 'Dersler', singular: 'Ders', fields: [
    FieldSpec('name', 'Ady'),
    FieldSpec('code', 'Kody', required: false),
    FieldSpec('department_id', 'Kafedra', type: FieldType.ref, ref: 'departments'),
  ]),
  ResourceSpec(endpoint: 'streams', description: 'Potoklar: leksiýany bilelikde diňleýän toparlar.', title: 'Potoklar', singular: 'Potok', fields: [
    FieldSpec('name', 'Ady'),
    FieldSpec('group_ids', 'Toparlar', type: FieldType.refList, ref: 'groups'),
  ]),
  ResourceSpec(
    endpoint: 'curriculum',
    description: 'Okuw meýilnamasy: haýsy topar haýsy dersi hepdede näçe gezek okaýar. "Mugallymlar" düwmesi bilen '
        'sapagy kim okadýanyny belläň — mugallymy bellenmedik sapak raspisaniýä girmeýär.',
    title: 'Okuw meýilnamasy',
    singular: 'Meýilnama ýazgysy',
    actions: [RowAction.assignments],
    fields: [
      FieldSpec('group_id', 'Topar', type: FieldType.ref, ref: 'groups', required: false),
      FieldSpec('stream_id', 'Potok', type: FieldType.ref, ref: 'streams', required: false),
      FieldSpec('subject_id', 'Ders', type: FieldType.ref, ref: 'subjects'),
      FieldSpec('lesson_type', 'Görnüşi', type: FieldType.choice, choices: lessonTypes),
      FieldSpec('lessons_per_week', 'Her hepde', type: FieldType.integer),
      FieldSpec('biweekly', 'Iki hepdede bir', type: FieldType.integer, required: false),
      FieldSpec('split', 'Bölünýär', type: FieldType.boolean, required: false),
      FieldSpec('room_type_id', 'Otag görnüşi', type: FieldType.ref, ref: 'room-types', required: false),
    ],
  ),
  ResourceSpec(endpoint: 'exam-sessions', description: 'Synag möwsümleri (ara synag, ýarymýyllyk synag...): başlanýan we gutarýan senesi, synag günleri.', title: 'Synag möwsümleri', singular: 'Synag möwsümi', fields: [
    FieldSpec('name', 'Ady'),
    FieldSpec('kind', 'Görnüşi', type: FieldType.choice, choices: examKinds),
    FieldSpec('starts_on', 'Başlanýar', type: FieldType.date),
    FieldSpec('ends_on', 'Gutarýar', type: FieldType.date),
    FieldSpec('weekdays', 'Synag günleri', type: FieldType.weekdays),
    FieldSpec('max_per_day', 'Toparyň günde iň köp synagy', type: FieldType.integer),
    FieldSpec('rest_days', 'Synaglaryň arasynda boş gün', type: FieldType.integer),
  ]),
  ResourceSpec(endpoint: 'exam-periods', description: 'Synag möwsüminiň synag wagtlary (meselem, 08:30, 10:00, 11:40).', title: 'Synag wagtlary', singular: 'Synag wagty', fields: [
    FieldSpec('session_id', 'Möwsüm', type: FieldType.ref, ref: 'exam-sessions'),
    FieldSpec('number', 'Belgisi', type: FieldType.integer),
    FieldSpec('starts_at', 'Başlanýar', type: FieldType.time),
    FieldSpec('ends_at', 'Gutarýar', type: FieldType.time),
  ]),
  ResourceSpec(endpoint: 'exams', description: 'Synaglar: topar, ders, uly we kiçi mugallym. "Synag raspisaniýesi" sahypasynda awtomat düzülýär.', title: 'Synaglar', singular: 'Synag', fields: [
    FieldSpec('session_id', 'Möwsüm', type: FieldType.ref, ref: 'exam-sessions'),
    FieldSpec('group_id', 'Topar', type: FieldType.ref, ref: 'groups', required: false),
    FieldSpec('stream_id', 'Potok', type: FieldType.ref, ref: 'streams', required: false),
    FieldSpec('subject_id', 'Ders', type: FieldType.ref, ref: 'subjects'),
    FieldSpec('examiner_id', 'Uly mugallym', type: FieldType.ref, ref: 'teachers'),
    FieldSpec('assistant_id', 'Kiçi mugallym', type: FieldType.ref, ref: 'teachers', required: false),
    FieldSpec('room_type_id', 'Otag görnüşi', type: FieldType.ref, ref: 'room-types', required: false),
  ]),
];

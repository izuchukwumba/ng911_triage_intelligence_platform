import type { IncidentDomain } from '@ng911/incident-schema';

// ---------------------------------------------------------------------------
// Domain keyword lists
// Each keyword match increments that domain's score during classification.
// ---------------------------------------------------------------------------

export const DOMAIN_KEYWORDS: Record<IncidentDomain, string[]> = {
  police: [
    'shot', 'shooting', 'gunshot', 'gun', 'firearm', 'rifle', 'pistol',
    'knife', 'stabbing', 'stab', 'slashing', 'slash',
    'fight', 'fighting', 'brawl', 'assault', 'attacked', 'attack', 'beating', 'hit',
    'robbery', 'robber', 'mugging', 'mugged', 'carjacking',
    'burglary', 'burglar', 'break in', 'breaking in', 'broken into',
    'theft', 'stolen', 'shoplifting',
    'domestic', 'domestic violence', 'abuse',
    'hostage', 'kidnapping', 'kidnap', 'abduction',
    'rape', 'sexual assault',
    'suspicious', 'prowler', 'trespassing', 'vandalism',
    'gang', 'drug deal', 'drug dealing',
    'drunk driver', 'dui', 'dwi', 'reckless driving',
    'hit and run', 'murder', 'homicide', 'dead body', 'body found', 'person shot',
    'shooting victim', 'armed', 'weapon',
  ],
  fire: [
    'fire', 'burning', 'on fire', 'flames', 'smoke', 'smoky',
    'explosion', 'exploded', 'blast',
    'structure fire', 'house fire', 'apartment fire', 'building fire',
    'car fire', 'vehicle fire',
    'wildfire', 'brush fire', 'grass fire', 'forest fire',
    'arson', 'arsonist',
    'collapsed', 'collapse', 'roof collapse',
  ],
  ems: [
    'heart attack', 'cardiac', 'cardiac arrest', 'heart stopped',
    'chest pain', 'chest pressure', 'chest tightness',
    'not breathing', 'stopped breathing', "isn't breathing", 'no breath',
    'unconscious', 'unresponsive', 'passed out', 'collapsed', 'not waking',
    'seizure', 'convulsion', 'convulsing', 'epileptic',
    'stroke', 'facial drooping', 'slurred speech',
    'overdose', 'od', 'drug overdose', 'alcohol poisoning',
    'bleeding', 'blood', 'hemorrhage', 'bleeding badly', 'bleeding out',
    'injured', 'injury', 'hurt', 'wound', 'wounded',
    'accident', 'car accident', 'crash', 'collision', 'vehicle collision',
    'fell', 'fall', 'fallen', 'slip and fall',
    'allergic reaction', 'anaphylaxis', 'epipen',
    'choking', 'can\'t breathe', 'cannot breathe', 'difficulty breathing',
    'breathing difficulty', 'shortness of breath', 'gasping',
    'diabetic', 'hypoglycemia', 'sugar',
    'baby', 'infant', 'birth', 'delivering baby', 'labor', 'contractions',
    'drowning', 'drowned', 'near drowning',
    'electrocuted', 'electrocution', 'shock',
    'severe pain', 'pain', 'ambulance', 'medical emergency', 'help me',
    'he died', 'she died', 'not moving',
  ],
  hazmat: [
    'chemical', 'chemicals', 'chemical spill', 'toxic', 'toxin',
    'poison', 'poisonous', 'fumes', 'toxic fumes', 'strong smell',
    'gas leak', 'natural gas', 'carbon monoxide', 'co detector', 'co alarm',
    'radiation', 'radioactive', 'nuclear',
    'biohazard', 'biological', 'biological hazard',
    'contamination', 'contaminated',
    'hazardous material', 'hazmat', 'industrial accident',
  ],
  other: [],
  unknown: [],
};

// ---------------------------------------------------------------------------
// Severity indicator keyword maps
// Each key is a named severity indicator; the value is the keyword list that
// triggers it. Indicators are attached to every incident and drive scoring.
// ---------------------------------------------------------------------------

export const SEVERITY_INDICATOR_KEYWORDS: Record<string, string[]> = {
  weapon_present: [
    'gun', 'firearm', 'rifle', 'pistol', 'shotgun', 'shot', 'shooting',
    'knife', 'stab', 'stabbing', 'blade', 'machete', 'axe',
    'armed', 'weapon',
  ],
  active_bleeding: [
    'bleeding', 'blood', 'hemorrhage', 'bleeding out', 'bleeding badly',
    'blood everywhere', 'blood all over', 'serious bleeding',
  ],
  not_breathing: [
    'not breathing', 'stopped breathing', "isn't breathing", 'no pulse',
    'no heartbeat', 'no breath', 'pulse is gone', 'heart stopped',
  ],
  unconscious: [
    'unconscious', 'unresponsive', 'passed out', 'not responding',
    'not waking', 'not waking up', 'not moving', 'collapsed and not moving',
  ],
  active_violence: [
    'fight', 'fighting', 'attacking', 'attack', 'assault', 'hitting',
    'beating', 'stabbing', 'shooting', 'brawl', 'struggle',
  ],
  multiple_victims: [
    'multiple people', 'several people', 'many people', 'people hurt',
    'multiple victims', 'crowd', 'mass casualty', 'people down',
    'group of people injured',
  ],
  child_involved: [
    'child', 'children', 'baby', 'infant', 'kid', 'kids', 'toddler',
    'minor', 'young child', 'little kid', 'my baby', 'my child',
  ],
  fire_spreading: [
    'spreading', 'out of control', 'whole building', 'entire house',
    'engulfed', 'fire is spreading', 'fire spread', 'completely on fire',
  ],
  cardiac_event: [
    'heart attack', 'cardiac arrest', 'cardiac', 'chest pain',
    'chest pressure', 'heart stopped', 'no heartbeat',
  ],
  respiratory_distress: [
    'not breathing', 'difficulty breathing', "can't breathe",
    'cannot breathe', 'choking', 'respiratory', 'gasping', 'shortness of breath',
  ],
  immediate_medical_emergency: [
    'not breathing', 'no pulse', 'cardiac arrest', 'unconscious',
    'overdose', 'seizure', 'heart stopped', 'unresponsive',
  ],
  hazardous_environment: [
    'gas leak', 'chemical spill', 'toxic', 'fumes', 'explosion',
    'carbon monoxide', 'hazmat', 'contaminated',
  ],
  possible_prank: [
    'prank', 'joke', 'fake', 'never mind', 'nevermind', 'just kidding',
    'wrong number', 'not real', 'testing',
  ],
  caller_distress_high: [
    'please help', 'please hurry', 'hurry up', "i don't know what to do",
    'oh god', 'oh my god', 'please please', 'dying', "they're dying",
    "he's dying", "she's dying",
  ],
};

// ---------------------------------------------------------------------------
// Spanish domain keyword lists  (language = 'es')
// Mirrors the English DOMAIN_KEYWORDS structure; used when language detection
// returns 'es' to supplement (not replace) English matching.
// ---------------------------------------------------------------------------

export const DOMAIN_KEYWORDS_ES: Record<IncidentDomain, string[]> = {
  police: [
    'dispararon', 'disparo', 'balazo', 'pistola', 'arma', 'armado',
    'cuchillo', 'apuñalaron', 'apuñaló', 'navaja',
    'pelea', 'golpiza', 'asalto', 'robo', 'ladrón', 'ladrones',
    'violación', 'agresión', 'secuestro', 'rehén',
    'violencia doméstica', 'me está golpeando', 'nos están atacando',
    'droga', 'narcotráfico', 'sospechoso', 'sospechosa',
    'homicidio', 'asesinato', 'cuerpo', 'cadáver',
  ],
  fire: [
    'incendio', 'fuego', 'llamas', 'humo', 'quemándose', 'se quema',
    'explosión', 'explota', 'gas', 'fuga de gas',
    'casa en llamas', 'edificio en llamas', 'se está quemando',
  ],
  ems: [
    'no respira', 'no puede respirar', 'dejó de respirar', 'sin pulso',
    'infarto', 'ataque al corazón', 'dolor de pecho',
    'inconsciente', 'desmayó', 'desmayado', 'no responde', 'no reacciona',
    'convulsiones', 'convulsionando', 'derrame cerebral',
    'sobredosis', 'sangre', 'sangrado', 'hemorragia', 'herido', 'herida',
    'accidente', 'choque', 'colisión', 'atropelló', 'atropellado',
    'cayó', 'se cayó', 'fractura',
    'reacción alérgica', 'asfixia', 'se está ahogando',
    'bebé', 'parto', 'trabajo de parto', 'contracciones',
    'ahogándose', 'electrocutado',
    'ayuda', 'auxilio', 'ambulancia', 'emergencia médica',
  ],
  hazmat: [
    'químico', 'tóxico', 'veneno', 'derrame', 'fuga',
    'fuga de gas', 'monóxido de carbono', 'gases tóxicos', 'olor fuerte',
    'radiación', 'material peligroso', 'contaminación',
  ],
  other: [],
  unknown: [],
};

// Spanish severity indicator keyword maps
export const SEVERITY_INDICATOR_KEYWORDS_ES: Record<string, string[]> = {
  weapon_present: ['pistola', 'arma', 'armado', 'cuchillo', 'navaja', 'dispararon', 'disparo'],
  active_bleeding: ['sangre', 'sangrado', 'hemorragia', 'mucha sangre', 'sangrando'],
  not_breathing: ['no respira', 'dejó de respirar', 'sin pulso', 'no tiene pulso'],
  unconscious: ['inconsciente', 'desmayado', 'no responde', 'no reacciona', 'no se despierta'],
  active_violence: ['pelea', 'golpiza', 'atacando', 'asalto', 'agresión'],
  multiple_victims: ['varias personas', 'múltiples personas', 'varios heridos', 'muchas víctimas'],
  child_involved: ['niño', 'niña', 'bebé', 'infante', 'menor', 'mi hijo', 'mi hija'],
  fire_spreading: ['se está extendiendo', 'fuera de control', 'todo en llamas', 'se propaga'],
  cardiac_event: ['infarto', 'ataque al corazón', 'paro cardíaco', 'sin pulso'],
  respiratory_distress: ['no respira', 'no puede respirar', 'asfixia', 'ahogándose'],
  immediate_medical_emergency: ['no respira', 'sin pulso', 'paro cardíaco', 'inconsciente', 'sobredosis'],
  hazardous_environment: ['fuga de gas', 'derrame químico', 'tóxico', 'gases', 'explosión'],
  possible_prank: ['broma', 'es broma', 'mentira', 'fue mentira'],
  caller_distress_high: ['por favor ayuden', 'ayúdeme', 'socorro', 'se está muriendo', 'auxilio'],
};

// ---------------------------------------------------------------------------
// Subtype classification
// Maps domain -> subtype -> keywords that trigger that subtype.
// First match wins.
// ---------------------------------------------------------------------------

export const SUBTYPE_MAP: Record<string, Record<string, string[]>> = {
  police: {
    shooting: ['shot', 'shooting', 'gunshot', 'gun', 'firearm'],
    stabbing: ['stabbing', 'stab', 'knife', 'slashing', 'slash', 'blade'],
    assault: ['assault', 'attack', 'fight', 'beating', 'hit', 'brawl'],
    robbery: ['robbery', 'robber', 'rob', 'mugging', 'mugged', 'carjacking'],
    burglary: ['burglary', 'burglar', 'break in', 'breaking in', 'broken into'],
    domestic_violence: ['domestic', 'domestic violence', 'partner', 'spouse', 'husband', 'wife', 'boyfriend', 'girlfriend'],
    suspicious_person: ['suspicious', 'prowler', 'trespassing'],
    dui: ['drunk driver', 'dui', 'dwi', 'intoxicated driver', 'drunk and driving'],
    homicide: ['murder', 'homicide', 'dead body', 'body found', 'killed'],
    kidnapping: ['hostage', 'kidnapping', 'kidnap', 'abduction', 'abducted'],
  },
  fire: {
    structure_fire: ['house fire', 'building fire', 'apartment fire', 'structure fire'],
    vehicle_fire: ['car fire', 'vehicle fire', 'truck fire', 'motorcycle fire'],
    wildfire: ['wildfire', 'brush fire', 'grass fire', 'forest fire'],
    gas_leak: ['gas leak', 'natural gas smell', 'smell of gas'],
    explosion: ['explosion', 'exploded', 'blast', 'explode'],
    carbon_monoxide: ['carbon monoxide', 'co detector', 'co alarm'],
  },
  ems: {
    cardiac_arrest: ['heart attack', 'cardiac arrest', 'no heartbeat', 'heart stopped'],
    respiratory_distress: ['not breathing', "can't breathe", 'cannot breathe', 'difficulty breathing', 'choking', 'gasping'],
    trauma: ['injured', 'injury', 'hurt', 'wound', 'bleeding', 'crash', 'accident', 'car accident', 'fell', 'fall'],
    overdose: ['overdose', 'od', 'drug overdose', 'took too many pills', 'alcohol poisoning'],
    seizure: ['seizure', 'convulsion', 'convulsing', 'epileptic'],
    stroke: ['stroke', 'facial drooping', 'slurred speech'],
    unconscious_unknown: ['unconscious', 'unresponsive', 'passed out', 'not waking'],
    allergic_reaction: ['allergic reaction', 'allergy', 'anaphylaxis', 'epipen'],
    childbirth: ['delivering baby', 'labor', 'contractions', 'baby coming', 'birth'],
  },
  hazmat: {
    chemical_spill: ['chemical spill', 'chemical', 'toxic spill'],
    gas_leak: ['gas leak', 'natural gas', 'gas smell'],
    carbon_monoxide: ['carbon monoxide', 'co alarm'],
    radiation: ['radiation', 'radioactive'],
    biological: ['biohazard', 'biological'],
  },
};

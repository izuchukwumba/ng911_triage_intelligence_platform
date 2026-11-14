"""Additions for generator 2.2 (ML layer design, section 4.3).

Generator 2.x put every cue code in *some* training family and in a test
family, but not in both training splits: ten codes had no dev family and
ten had no regression family. A model trained on dev alone therefore never
saw ten codes, and calibrating it on regression could not work for twenty
(results README, "B1e calibration on the regression split: a negative
result"). Generator 2.2 adds one family on the missing side for each of
those codes, so every labelled code is in dev, regression and test.

The phrasings are new and differ from the existing families, including the
test families. Severities follow the labelling guide (v2.1).
"""

from ntip.generator.scenarios import Situation
from ntip.generator.scenarios_v2 import D, R, S
from ntip.generator.scenarios_v21 import SITUATIONS as SITUATIONS_V21

NEW_SITUATIONS: tuple[Situation, ...] = (
    # --- Dev families for codes that had none -----------------------------------
    S(
        "street_fight",
        D,
        "police",
        "high",
        ("ACTIVE_VIOLENCE",),
        (
            "[ACTIVE_VIOLENCE|Two guys are punching each other] outside the store.",
            "[ACTIVE_VIOLENCE|A group is beating someone up] in the parking lot.",
            "[ACTIVE_VIOLENCE|Someone is kicking a man on the ground] by the bus stop.",
        ),
        denial="[ACTIVE_VIOLENCE|They stopped fighting] and walked off in different directions.",
        spanish=("[ACTIVE_VIOLENCE|Están golpeando a un hombre] en la calle.",),
        personal=False,
    ),
    S(
        "food_allergy",
        D,
        "ems",
        "high",
        ("ALLERGIC_REACTION",),
        (
            "{Who} ate peanuts and [ALLERGIC_REACTION|their lips are swelling up].",
            "{Who} [ALLERGIC_REACTION|got stung by a bee and is breaking out in hives].",
            "{Who} [ALLERGIC_REACTION|is having an allergic reaction] to shellfish.",
            "I had to [ALLERGIC_REACTION|use the EpiPen] on {who}.",
        ),
        past="{Who} [ALLERGIC_REACTION|had an allergic reaction] yesterday but is fine today.",
        spanish=("Mi hijo [ALLERGIC_REACTION|tiene la cara hinchada] por una alergia.",),
    ),
    S(
        "labour_onset",
        D,
        "ems",
        "high",
        ("CHILDBIRTH",),
        (
            "My wife [CHILDBIRTH|is in labor] and the contractions are close together.",
            "My girlfriend [CHILDBIRTH|is having contractions every two minutes].",
            "My sister [CHILDBIRTH|is about to give birth] in the car.",
        ),
        spanish=("Mi esposa [CHILDBIRTH|tiene contracciones] muy seguidas.",),
        personal=False,
    ),
    S(
        "water_rescue",
        D,
        "ems",
        "high",
        ("DROWNING",),
        (
            "{Who} [DROWNING|was pulled out of the river] and is coughing up water.",
            "{Who} [DROWNING|went under in the lake] and we just got them out.",
            "{Who} [DROWNING|was struggling in the deep end] and swallowed a lot of water.",
        ),
        spanish=("Mi hermano [DROWNING|se estaba ahogando] en el río.",),
    ),
    S(
        "electric_shock",
        D,
        "ems",
        "high",
        ("ELECTROCUTION",),
        (
            "{Who} [ELECTROCUTION|got shocked by an outlet] and their hand is numb.",
            "{Who} [ELECTROCUTION|touched a live wire] in the basement.",
            "{Who} [ELECTROCUTION|was hit by lightning] on the golf course.",
        ),
        spanish=("Mi padre [ELECTROCUTION|recibió una descarga eléctrica].",),
    ),
    S(
        "gas_explosion",
        D,
        "fire",
        "high",
        ("EXPLOSION_REPORTED",),
        (
            "[EXPLOSION_REPORTED|A gas line just blew up] down the street.",
            "[EXPLOSION_REPORTED|There was a huge blast] at the warehouse.",
            "[EXPLOSION_REPORTED|Something exploded] in the garage next door.",
        ),
        past="[EXPLOSION_REPORTED|There was an explosion] here last week, just reporting damage.",
        spanish=("[EXPLOSION_REPORTED|Explotó un tanque de gas] en el edificio.",),
        personal=False,
    ),
    S(
        "break_in_progress",
        D,
        "police",
        "high",
        ("INTRUDER_PRESENT",),
        (
            "[INTRUDER_PRESENT|Someone is climbing in through my window] right now.",
            "[INTRUDER_PRESENT|There's a stranger in my kitchen] and I'm hiding upstairs.",
            "[INTRUDER_PRESENT|I can hear someone moving around downstairs] and I live alone.",
        ),
        spanish=("[INTRUDER_PRESENT|Alguien está entrando por la ventana] de mi casa.",),
        personal=False,
    ),
    S(
        "child_not_home",
        D,
        "police",
        "elevated",
        ("MISSING_PERSON",),
        (
            "{Who} [MISSING_PERSON|hasn't come home from school] and it's dark.",
            "{Who} [MISSING_PERSON|wandered off] and we can't find them anywhere.",
            "{Who} [MISSING_PERSON|has been missing since this morning].",
        ),
        spanish=("Mi abuela [MISSING_PERSON|salió y no ha regresado].",),
    ),
    S(
        "febrile_seizure",
        D,
        "ems",
        "high",
        ("SEIZURE",),
        (
            "{Who} [SEIZURE|is shaking all over and won't stop].",
            "{Who} [SEIZURE|is having a seizure] on the floor.",
            "{Who} [SEIZURE|is jerking and their eyes are rolled back].",
        ),
        past="{Who} [SEIZURE|had a seizure] an hour ago and is sleepy now.",
        spanish=("Mi hija [SEIZURE|está teniendo una convulsión].",),
    ),
    S(
        "fallen_elderly",
        D,
        "ems",
        "elevated",
        ("UNABLE_TO_GET_UP",),
        (
            "{Who} slipped in the bathroom and [UNABLE_TO_GET_UP|can't get back up].",
            "{Who} [UNABLE_TO_GET_UP|has been stuck on the floor since last night].",
            "{Who} [UNABLE_TO_GET_UP|can't stand up] after sliding off the bed.",
        ),
        spanish=("Mi abuelo [UNABLE_TO_GET_UP|no puede pararse] del suelo.",),
    ),
    # --- Regression families for codes that had none ------------------------------
    S(
        "scald",
        R,
        "ems",
        "high",
        ("BURN_INJURY",),
        (
            "{Who} [BURN_INJURY|spilled boiling water on their arm] and it's blistering.",
            "{Who} [BURN_INJURY|burned their hand on the stove] badly.",
            "{Who} [BURN_INJURY|has burns on their legs] from the campfire.",
        ),
        spanish=("Mi hijo [BURN_INJURY|se quemó la mano] con el horno.",),
    ),
    S(
        "angina",
        R,
        "ems",
        "high",
        ("CARDIAC_SYMPTOMS",),
        (
            "{Who} [CARDIAC_SYMPTOMS|says there's a heavy weight on their chest].",
            "{Who} [CARDIAC_SYMPTOMS|has pain going down the left arm and into the chest].",
            "{Who} [CARDIAC_SYMPTOMS|thinks it's a heart attack], the chest is so tight.",
        ),
        past="{Who} [CARDIAC_SYMPTOMS|had chest pain] this morning but it went away.",
        spanish=("Mi papá [CARDIAC_SYMPTOMS|dice que le duele mucho el pecho].",),
    ),
    S(
        "low_sugar",
        R,
        "ems",
        "high",
        ("DIABETIC_EMERGENCY",),
        (
            "{Who} [DIABETIC_EMERGENCY|is diabetic and their sugar is really low].",
            "{Who} [DIABETIC_EMERGENCY|took too much insulin] and is shaky and sweaty.",
            "{Who} [DIABETIC_EMERGENCY|has a blood sugar of 40] and is confused.",
        ),
        spanish=("Mi esposo [DIABETIC_EMERGENCY|tiene el azúcar muy alta].",),
    ),
    S(
        "ladder_fall",
        R,
        "ems",
        "high",
        ("FALL_FROM_HEIGHT",),
        (
            "{Who} [FALL_FROM_HEIGHT|fell off a ladder] while cleaning the gutters.",
            "{Who} [FALL_FROM_HEIGHT|fell out of a tree] in the backyard.",
            "{Who} [FALL_FROM_HEIGHT|fell from the balcony] on the second floor.",
        ),
        spanish=("Mi tío [FALL_FROM_HEIGHT|se cayó de una escalera].",),
    ),
    S(
        "brush_fire",
        R,
        "fire",
        "high",
        ("FIRE_REPORTED", "FIRE_SPREADING"),
        (
            "[FIRE_REPORTED|The grass fire] [FIRE_SPREADING|is moving toward the houses].",
            "[FIRE_REPORTED|The barn is on fire] and [FIRE_SPREADING|it's jumping to the shed].",
            "[FIRE_REPORTED|Flames] are [FIRE_SPREADING|spreading along the fence line].",
        ),
        spanish=("[FIRE_REPORTED|El fuego] [FIRE_SPREADING|está llegando a la casa].",),
        personal=False,
    ),
    S(
        "pill_overdose",
        R,
        "ems",
        "high",
        ("OVERDOSE",),
        (
            "{Who} [OVERDOSE|took a whole bottle of sleeping pills].",
            "{Who} [OVERDOSE|used too much heroin] and is barely awake.",
            "{Who} [OVERDOSE|swallowed a handful of painkillers] on purpose.",
        ),
        spanish=("Mi hermana [OVERDOSE|tomó muchas pastillas].",),
    ),
    S(
        "household_poison",
        R,
        "ems",
        "high",
        ("POISONING",),
        (
            "{Who} [POISONING|drank some antifreeze] from the garage.",
            "{Who} [POISONING|swallowed a dishwasher pod].",
            "{Who} [POISONING|ate some rat poison] from under the sink.",
        ),
        spanish=("Mi hija [POISONING|se tomó un líquido de limpieza].",),
    ),
    S(
        "suicidal_text",
        R,
        "ems",
        "high",
        ("SELF_HARM_RISK",),
        (
            "{Who} [SELF_HARM_RISK|sent me a message saying goodbye forever].",
            "{Who} [SELF_HARM_RISK|is cutting themselves] in the bathroom.",
            "{Who} [SELF_HARM_RISK|says they want to end it all].",
        ),
        spanish=("Mi amigo [SELF_HARM_RISK|dice que se va a hacer daño].",),
    ),
    S(
        "smoke_smell",
        R,
        "fire",
        "elevated",
        ("SMOKE_REPORTED",),
        (
            "[SMOKE_REPORTED|There's smoke coming out of the vents] in the office.",
            "[SMOKE_REPORTED|I can see black smoke] rising behind the school.",
            "[SMOKE_REPORTED|The hallway is smoky] and the alarm is going off.",
        ),
        denial="[SMOKE_REPORTED|There's no smoke] anymore, it cleared up.",
        spanish=("[SMOKE_REPORTED|Hay humo negro] saliendo del garaje.",),
        personal=False,
    ),
    S(
        "face_droop",
        R,
        "ems",
        "high",
        ("STROKE_SYMPTOMS",),
        (
            "{Who} [STROKE_SYMPTOMS|has a drooping face and slurred speech].",
            "{Who} [STROKE_SYMPTOMS|suddenly can't move their right arm].",
            "{Who} [STROKE_SYMPTOMS|is talking gibberish and one side is weak].",
        ),
        spanish=("Mi mamá [STROKE_SYMPTOMS|no puede mover un lado del cuerpo].",),
    ),
)

SITUATIONS: tuple[Situation, ...] = SITUATIONS_V21 + NEW_SITUATIONS

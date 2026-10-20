"""Leçons dactylographiques françaises. Chaque groupe suit le précédent."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Lesson:
    id: int
    kind: str
    title: str
    description: str
    prompts: tuple[str, ...]
    target_cpm: int


LESSONS = [
    Lesson(1, 'Mots', 'Les premiers mots', 'Des mots courts et fréquents.',
           ('ami', 'vie', 'lune', 'salut', 'merci', 'bonjour'), 55),
    Lesson(2, 'Mots', 'Les mots du quotidien', 'Apprends à garder un rythme régulier.',
           ('maison', 'soleil', 'jardin', 'livre', 'table', 'fenêtre'), 65),
    Lesson(3, 'Mots', 'Les voyelles et les accents', 'Travaille é, è, à, ù et ç.',
           ('école', 'élève', 'père', 'français', 'où', 'déjà'), 70),
    Lesson(4, 'Mots', 'Les mots plus longs', 'Garde ta précision.',
           ('ordinateur', 'bibliothèque', 'clavier', 'apprentissage', 'électricité'), 80),
    Lesson(5, 'Mots', 'La ponctuation', 'Apprends à écrire les signes courants.',
           ('bonjour !', 'd’accord', 'merci.', 'ça va ?', 'à bientôt !'), 85),
    Lesson(6, 'Mots', 'Défi des mots', 'Enchaîne sans perdre le fil.',
           ('extraordinaire', 'ordinateur', 'vocabulaire', 'découverte', 'information', 'précision'), 95),
    Lesson(7, 'Phrases', 'Mes premières phrases', 'Découvre les espaces et les majuscules.',
           ('Je suis ici.', 'Il fait beau.', 'Tu as un livre.'), 75),
    Lesson(8, 'Phrases', 'Une journée simple', 'Tape plusieurs phrases familières.',
           ('Je me lève le matin.', 'Le café est chaud.', 'Je rentre à la maison.'), 85),
    Lesson(9, 'Phrases', 'Les accents', 'Quelques phrases avec les accents français.',
           ('L’été est agréable.', 'Mon frère va à l’école.', 'Où est passée la clé ?'), 90),
    Lesson(10, 'Phrases', 'Les petites histoires', 'Des phrases un peu plus longues.',
           ('Le chat regarde les oiseaux depuis la fenêtre.',
            'Ce matin, nous préparons un bon repas.',
            'Je prends le temps de bien placer mes doigts.'), 100),
    Lesson(11, 'Phrases', 'Ponctuation et rythme', 'Travaille les virgules, points et questions.',
           ('Bonjour, comment vas-tu ?',
            'Aujourd’hui, je découvre un nouvel exercice.',
            'Oui, je peux progresser à mon rythme !'), 110),
    Lesson(12, 'Phrases', 'Défi des phrases', 'Garde une frappe régulière.',
           ('Chaque jour, un petit entraînement aide à progresser.',
            'Je regarde mon écran et je tape sans me presser.',
            'Avec de la patience, les touches deviennent familières.'), 120),
    Lesson(13, 'Textes', 'Mon premier texte', 'Un paragraphe simple à recopier.',
           ('Bonjour ! Je m’appelle Alex. J’aime apprendre de nouvelles choses. '
            'Aujourd’hui, je découvre le clavier et je prends mon temps.' ,), 105),
    Lesson(14, 'Textes', 'Une promenade', 'Enchaîne plusieurs phrases.',
           ('Ce matin, le soleil se lève doucement. Je sors marcher dans le jardin. '
            'Les oiseaux chantent et l’air est frais. C’est une belle journée.',), 115),
    Lesson(15, 'Textes', 'Une journée à l’école', 'Travaille la fluidité sur un texte.',
           ('À l’école, nous utilisons souvent les ordinateurs. Nous écrivons des documents, '
            'cherchons des informations et préparons nos projets. Chaque exercice me permet '
            'de gagner en précision.',), 125),
    Lesson(16, 'Textes', 'Un projet informatique', 'Tape du vocabulaire technique.',
           ('Pour créer un logiciel, il faut réfléchir à son fonctionnement. '
            'On écrit du code, on réalise des tests et on corrige les erreurs. '
            'Un bon programme doit être simple à utiliser et agréable à lire.',), 135),
    Lesson(17, 'Textes', 'La régularité', 'Apprends à maintenir une bonne vitesse.',
           ('Une bonne vitesse de frappe ne vient pas en un seul jour. '
            'Il faut d’abord apprendre les positions des touches, puis pratiquer '
            'régulièrement. Avec le temps, les mouvements deviennent plus naturels.',), 145),
    Lesson(18, 'Textes', 'Le grand défi', 'Termine le parcours de découverte.',
           ('Aujourd’hui, je termine mon parcours de découverte du clavier AZERTY. '
            'Je sais écrire des mots, des phrases et des textes complets. '
            'Je fais encore quelques erreurs, mais je progresse un peu plus chaque jour. '
            'Le plus important est de continuer à pratiquer avec plaisir et régularité.',), 155),
]

assert [lesson.id for lesson in LESSONS] == list(range(1, len(LESSONS) + 1))

SPRINT_WORDS = (
    'salut', 'bonjour', 'clavier', 'ordinateur', 'maison', 'soleil',
    'école', 'jardin', 'merci', 'français', 'écrire', 'progresser',
    'apprendre', 'rapide', 'précision', 'phrase', 'texte', 'musique',
    'fenêtre', 'écran', 'aujourd’hui', 'vitesse', 'sourire', 'projet',
)

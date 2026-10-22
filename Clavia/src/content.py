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

    # Chapitre 4 : écriture utile, situations du quotidien.
    Lesson(19, 'Situations', 'Un message court', 'Rédige des messages simples et naturels.',
           ('Salut, tu es libre ce soir ?', 'Je suis en route.', 'Merci pour ton aide !'), 100),
    Lesson(20, 'Situations', 'Une liste de courses', 'Enchaîne des mots avec virgules et accents.',
           ('Pain, lait, pommes et riz.', 'Il faut du café, du thé et du sucre.',
            'Achète des œufs, des pâtes et des légumes.'), 105),
    Lesson(21, 'Situations', 'Un courriel poli', 'Travaille les formules de politesse.',
           ('Bonjour, je vous écris pour demander un renseignement.',
            'Merci pour votre réponse. Bonne journée !'), 115),
    Lesson(22, 'Situations', 'Un rendez-vous', 'Saisis dates, chiffres et informations utiles.',
           ('Rendez-vous à 14 h 30.', 'Nous sommes le 12 octobre 2026.',
            'La réunion commence à 9 h, salle 204.'), 120),
    Lesson(23, 'Situations', 'Présenter un projet', 'Écris un texte clair et structuré.',
           ('Je développe un logiciel éducatif pour apprendre le clavier. '
            'Mon objectif est de le rendre simple et accessible à tous.',), 130),
    Lesson(24, 'Situations', 'Défi de communication', 'Combine messages, politesse et ponctuation.',
           ('Bonjour, merci pour votre message. Je serai disponible demain à 10 h. '
            'Pouvez-vous me confirmer le lieu du rendez-vous ? Cordialement.',), 135),
    # Chapitre 5 : travail ciblé des difficultés du clavier français.
    Lesson(25, 'Précision', 'Accents avancés', 'Maîtrise les accents et les caractères spécifiques.',
           ('événement', 'être', 'hôpital', 'Noël', 'où', 'maïs', 'français'), 100),
    Lesson(26, 'Précision', 'Majuscules et noms propres', 'Travaille la touche Maj.',
           ('Paris', 'Normandie', 'Clavia', 'Lundi', 'Camille', 'France'), 115),
    Lesson(27, 'Précision', 'Les nombres', 'Entraîne les chiffres et les espaces.',
           ('123', '2026', '45 678', '7 jours', '12 minutes', '100 points'), 120),
    Lesson(28, 'Précision', 'Symboles courants', 'Saisis plusieurs signes du quotidien.',
           ('bonjour ?', 'attention !', '(merci)', '3 + 2 = 5', '10 %', 'oui : non'), 120),
    Lesson(29, 'Précision', 'Phrases exigeantes', 'Alterner ponctuation, chiffres et accents.',
           ('À 8 h 30, Léa prépare son café.',
            'Pourquoi faut-il écrire 100 % correctement ?',
            'Noël approche : êtes-vous prêt ?'), 135),
    Lesson(30, 'Précision', 'Défi sans fautes', 'L’exactitude passe avant la vitesse.',
           ('La précision est essentielle : prends le temps de corriger chaque erreur. '
            'Tu peux accélérer quand tes gestes deviennent plus sûrs.',), 145),
    # Chapitre 6 : maîtrise, lecture et frappe longue.
    Lesson(31, 'Maîtrise', 'Rythme régulier', 'Garde la même cadence pendant un paragraphe.',
           ('Pour écrire plus vite, il est utile de trouver un rythme constant. '
            'La régularité aide à éviter les erreurs et à rester concentré.',), 140),
    Lesson(32, 'Maîtrise', 'Science et nature', 'Explore un texte informatif accessible.',
           ('La lumière du Soleil permet aux plantes de grandir. '
            'Leurs feuilles captent cette énergie pour produire la matière '
            'dont elles ont besoin. Ce phénomène est appelé photosynthèse.',), 145),
    Lesson(33, 'Maîtrise', 'Numérique et réseaux', 'Entraîne le vocabulaire informatique.',
           ('Un réseau informatique relie des appareils afin de partager des données. '
            'Pour protéger ces échanges, il faut choisir des mots de passe solides, '
            'mettre les systèmes à jour et rester vigilant.',), 150),
    Lesson(34, 'Maîtrise', 'Récit court', 'Enchaîne les phrases d’une petite histoire.',
           ('Un matin, Lina découvre un carnet oublié dans le train. '
            'Elle lit le nom inscrit sur la première page et décide de le rendre. '
            'Grâce à son geste, le propriétaire retrouve ses notes importantes.',), 155),
    Lesson(35, 'Maîtrise', 'Texte long', 'Développe ton endurance sans négliger les fautes.',
           ('Chaque compétence se construit avec le temps. Lorsque tu écris, '
            'essaie de regarder le texte plutôt que le clavier. Commence lentement '
            'puis augmente progressivement ta vitesse. Si une erreur apparaît, '
            'corrige-la avant de poursuivre. Cette habitude rend ta frappe '
            'plus fluide et plus fiable au quotidien.',), 165),
    Lesson(36, 'Maîtrise', 'Défi final : maîtrise AZERTY', 'Termine les 36 leçons avec un dernier texte.',
           ('Tu as traversé six chapitres pour apprendre à écrire sur un clavier AZERTY. '
            'Tu as découvert les mots, les phrases, les textes, les messages utiles '
            'et les signes difficiles. Désormais, ton objectif est de progresser '
            'à ton propre rythme. Garde confiance, exerce-toi régulièrement '
            'et privilégie toujours une frappe précise et confortable.',), 175),
]

assert [lesson.id for lesson in LESSONS] == list(range(1, len(LESSONS) + 1))

SPRINT_WORDS = (
    'salut', 'bonjour', 'clavier', 'ordinateur', 'maison', 'soleil',
    'école', 'jardin', 'merci', 'français', 'écrire', 'progresser',
    'apprendre', 'rapide', 'précision', 'phrase', 'texte', 'musique',
    'fenêtre', 'écran', 'aujourd’hui', 'vitesse', 'sourire', 'projet',
    'rendez-vous', 'courriel', 'réseau', 'numérique', 'confiance',
)

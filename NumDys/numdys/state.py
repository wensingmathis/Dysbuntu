"""État partagé entre les différentes applications de NumDys."""


class AppState:
    def __init__(self):
        self.degree_mode = False  # False = radians, True = degrés
        self.last_answer = 0.0

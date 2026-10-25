"""État de session minimal, partagé entre les pages de NumDys."""
from dataclasses import dataclass


@dataclass(slots=True)
class AppState:
    degree_mode: bool = False
    last_answer: float = 0.0

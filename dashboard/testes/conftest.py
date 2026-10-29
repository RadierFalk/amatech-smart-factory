"""Cada teste recebe um banco novo, criado pelo script SQL numa pasta temporária (com os dados do enunciado)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from acesso_dados import Repositorio  # noqa: E402


@pytest.fixture
def repo(tmp_path):
    return Repositorio(tmp_path / "teste.db")


@pytest.fixture
def supervisor(repo):
    return repo.consultar_um("SELECT id_usuario FROM usuario WHERE login = 'supervisor'")["id_usuario"]

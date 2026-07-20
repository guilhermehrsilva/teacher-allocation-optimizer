from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from motor_alocacao.loader import (  # noqa: E402
    DOCENTES_SHEET,
    MAPA_SHEET,
    load_problem,
)


MAPA_HEADERS = (
    "CURSO",
    "NOME_CURSO",
    "CURRÍCULO",
    "COD_DISCIPLINA",
    "NOME_DISCIPLINA",
    "PERFIL_DISCIPLINA",
    "SINERGIA",
    "FORMATO_AULA",
    "DIA_AULA",
    "HORÁRIO",
    "ORDEM",
    "CLUSTER",
    "COORDENADOR",
    "MODELO_CONTRATO",
)

DOCENTES_HEADERS = (
    "NOME",
    "CHAPA",
    "NM_FUNCAO",
    "CH_CONTRATADA",
    "CH_LETIVA",
    "GESTOR",
    "STATUS",
    "PERFIL_DISCIPLINA",
)


def mapa_row(identifier: int = 0, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "CURSO": f"C{identifier}",
        "NOME_CURSO": f"Curso {identifier}",
        "CURRÍCULO": f"CURR{identifier}",
        "COD_DISCIPLINA": f"D{identifier}",
        "NOME_DISCIPLINA": f"Disciplina {identifier}",
        "PERFIL_DISCIPLINA": "Gestão - Administração",
        "SINERGIA": "Curso Único",
        "FORMATO_AULA": "AO VIVO",
        "DIA_AULA": "SEGUNDA",
        "HORÁRIO": "19:00",
        "ORDEM": "1ª",
        "CLUSTER": "GESTÃO",
        "COORDENADOR": "Coordenador",
        "MODELO_CONTRATO": "CLT EAD",
    }
    row.update(overrides)
    return row


def docente_row(identifier: int = 0, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "NOME": f"Docente {identifier}",
        "CHAPA": f"{identifier + 1:012d}",
        "NM_FUNCAO": "PROFESSOR REGENTE",
        "CH_CONTRATADA": 40,
        "CH_LETIVA": 4,
        "GESTOR": "Gestor",
        "STATUS": "ATIVO",
        "PERFIL_DISCIPLINA": "Gestão - Administração",
    }
    row.update(overrides)
    return row


class LoaderTests(unittest.TestCase):
    def make_workbook(
        self,
        *,
        mapa_rows: list[dict[str, object]] | None = None,
        docente_rows: list[dict[str, object]] | None = None,
        mapa_headers: tuple[str, ...] = MAPA_HEADERS,
        docentes_headers: tuple[str, ...] = DOCENTES_HEADERS,
    ) -> Path:
        workbook = Workbook()
        mapa = workbook.active
        mapa.title = MAPA_SHEET
        mapa.append(mapa_headers)
        for row in mapa_rows if mapa_rows is not None else [mapa_row()]:
            mapa.append([row.get(header) for header in mapa_headers])

        docentes = workbook.create_sheet(DOCENTES_SHEET)
        docentes.append(docentes_headers)
        for row in docente_rows if docente_rows is not None else [docente_row()]:
            docentes.append([row.get(header) for header in docentes_headers])

        path = ROOT / "tests" / f".loader-{uuid.uuid4().hex}.xlsx"
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        try:
            workbook.save(path)
        finally:
            workbook.close()
        return path

    def test_reordered_headers_ignore_sinergica_and_keep_contiguous_ids(self) -> None:
        rows = [
            mapa_row(0),
            mapa_row(
                1,
                SINERGIA="Sinérgica",
                MODELO_CONTRATO="CONTRATO IGNORADO",
            ),
            mapa_row(2, SINERGIA="Curso Responsável", HORÁRIO="20:40"),
        ]
        path = self.make_workbook(
            mapa_rows=rows,
            docente_rows=[docente_row(0), docente_row(1)],
            mapa_headers=tuple(reversed(MAPA_HEADERS)),
            docentes_headers=tuple(reversed(DOCENTES_HEADERS)),
        )

        problem = load_problem(path)

        self.assertEqual([0, 1], [teacher.id for teacher in problem.teachers])
        self.assertEqual([0, 1], [item.id for item in problem.transmissions])
        self.assertEqual([2, 4], [item.excel_row for item in problem.transmissions])
        self.assertEqual(["D0", "D2"], [item.discipline_code for item in problem.transmissions])

    def test_rejects_unknown_teacher_function(self) -> None:
        path = self.make_workbook(
            docente_rows=[docente_row(NM_FUNCAO="FUNÇÃO DESCONHECIDA")],
        )

        with self.assertRaisesRegex(ValueError, "NM_FUNCAO não suportada na linha 2"):
            load_problem(path)

    def test_accepts_but_does_not_load_input_contract_model(self) -> None:
        path = self.make_workbook(
            mapa_rows=[mapa_row(MODELO_CONTRATO="CONTRATO DESCONHECIDO")],
        )

        problem = load_problem(path)

        self.assertEqual(1, len(problem.transmissions))
        self.assertFalse(hasattr(problem.transmissions[0], "contract_model"))

    def test_input_contract_model_does_not_change_loaded_problem(self) -> None:
        first = load_problem(
            self.make_workbook(
                mapa_rows=[mapa_row(MODELO_CONTRATO="CLT EAD")],
            )
        )
        second = load_problem(
            self.make_workbook(
                mapa_rows=[mapa_row(MODELO_CONTRATO="VALOR SEM EFEITO")],
            )
        )

        self.assertEqual(first.teachers, second.teachers)
        self.assertEqual(first.transmissions, second.transmissions)

    def test_maps_valid_orders_to_module_stages(self) -> None:
        path = self.make_workbook(
            mapa_rows=[
                mapa_row(0, ORDEM="1ª"),
                mapa_row(1, ORDEM="2ª", HORÁRIO="20:40"),
                mapa_row(2, ORDEM="ESTENDIDA", DIA_AULA="TERÇA"),
            ],
        )

        problem = load_problem(path)

        self.assertEqual(
            [
                ("PRIMEIRA_ETAPA",),
                ("SEGUNDA_ETAPA",),
                ("PRIMEIRA_ETAPA", "SEGUNDA_ETAPA"),
            ],
            [item.module_stages for item in problem.transmissions],
        )

    def test_rejects_unknown_module_order(self) -> None:
        path = self.make_workbook(mapa_rows=[mapa_row(ORDEM="3ª")])

        with self.assertRaisesRegex(ValueError, "ORDEM inválida na linha 2"):
            load_problem(path)

    def test_rejects_negative_and_noninteger_loads(self) -> None:
        cases = (
            ("CH_LETIVA", -1),
            ("CH_CONTRATADA", 40.5),
        )
        for column, value in cases:
            with self.subTest(column=column, value=value):
                path = self.make_workbook(
                    docente_rows=[docente_row(**{column: value})],
                )
                with self.assertRaisesRegex(
                    ValueError,
                    rf"{column} inválida na linha 2.*inteiro não negativo",
                ):
                    load_problem(path)


if __name__ == "__main__":
    unittest.main()

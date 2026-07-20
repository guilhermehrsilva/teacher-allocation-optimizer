from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alocacao_docente.validation import (  # noqa: E402
    DOCENTES_HEADERS,
    DOCENTES_SHEET,
    MAPA_HEADERS,
    MAPA_SHEET,
    validate_workbook,
)


def valid_mapa_row() -> list[object]:
    return [
        "CURSO_1", "CURSO TESTE", "CURSO_1_2026", "DISC_1", "DISCIPLINA TESTE",
        "Gestão - Administração", 2026, 52, "1º", "1ª", "Validado",
        "5 SEMANAS", "ONLINE", "5", "N", "CLUSTER", "GESTÃO E NEGÓCIOS",
        "GESTOR TESTE", "CLT EAD", "Curso Único", "SEGUNDA", "19:00", "AO VIVO",
    ]


def valid_docente_row() -> list[object]:
    return [
        "DOCENTE TESTE", "012345678901", "PROFESSOR DE ENSINO SUPERIOR EAD",
        40, 4, "GESTOR TESTE", "ATIVO", "Gestão - Administração",
    ]


class ValidationTests(unittest.TestCase):
    def make_workbook(self, mapa_rows=None, docente_rows=None) -> Path:
        workbook = Workbook()
        mapa = workbook.active
        mapa.title = MAPA_SHEET
        mapa.append(MAPA_HEADERS)
        for row in [valid_mapa_row()] if mapa_rows is None else mapa_rows:
            mapa.append(row)
        docentes = workbook.create_sheet(DOCENTES_SHEET)
        docentes.append(DOCENTES_HEADERS)
        for row in [valid_docente_row()] if docente_rows is None else docente_rows:
            docentes.append(row)
        path = ROOT / "tests" / f".validation-{uuid.uuid4().hex}.xlsx"
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        workbook.save(path)
        return path

    def test_valid_workbook_is_approved(self):
        report = validate_workbook(self.make_workbook())
        self.assertEqual("APROVADO", report.status)
        self.assertEqual([], report.issues)

    def test_sinergica_row_is_informative(self):
        informative = valid_mapa_row()
        informative[2] = "CURSO_1_2026_APOIO"
        informative[3] = "DISC_APOIO"
        informative[4] = "DISCIPLINA INFORMATIVA"
        informative[5] = "Perfil sem docente"
        informative[19] = "Sinérgica"
        informative[21] = None

        report = validate_workbook(
            self.make_workbook(mapa_rows=[valid_mapa_row(), informative]),
        )
        codes = {issue.code for issue in report.issues}
        self.assertEqual("APROVADO", report.status)
        self.assertEqual(1, report.metadata["allocating_rows"])
        self.assertNotIn("OFERTA_SEM_HORARIO", codes)
        self.assertNotIn("PERFIL_SEM_DOCENTE_ATIVO", codes)

    def test_missing_context_field_in_sinergica_is_non_blocking(self):
        informative = valid_mapa_row()
        informative[2] = None
        informative[3] = "DISC_APOIO"
        informative[19] = "Sinérgica"

        report = validate_workbook(
            self.make_workbook(mapa_rows=[valid_mapa_row(), informative]),
        )
        issues = [
            issue
            for issue in report.issues
            if issue.code == "CAMPO_OBRIGATORIO_VAZIO"
            and issue.column == "CURRÍCULO"
        ]
        self.assertEqual("APROVADO_COM_RESSALVAS", report.status)
        self.assertEqual(1, len(issues))
        self.assertFalse(issues[0].blocking)

    def test_missing_or_invalid_order_in_informative_row_is_non_blocking(self):
        for order in (None, "3ª"):
            with self.subTest(order=order):
                informative = valid_mapa_row()
                informative[2] = "CURSO_1_2026_APOIO"
                informative[3] = "DISC_APOIO"
                informative[9] = order
                informative[19] = "Sinérgica"

                report = validate_workbook(
                    self.make_workbook(mapa_rows=[valid_mapa_row(), informative]),
                )
                issues = [issue for issue in report.issues if issue.column == "ORDEM"]

                self.assertEqual("APROVADO_COM_RESSALVAS", report.status)
                self.assertEqual(1, report.metadata["allocating_rows"])
                self.assertTrue(issues)
                self.assertTrue(all(not issue.blocking for issue in issues))

    def test_empty_mapa_sheet_is_rejected(self):
        report = validate_workbook(self.make_workbook(mapa_rows=[]))
        self.assertEqual("REPROVADO", report.status)
        self.assertTrue(any(issue.code == "ABA_SEM_DADOS" for issue in report.issues))

    def test_required_value_and_schedule_are_rejected(self):
        row = valid_mapa_row()
        row[2] = None
        row[21] = None
        report = validate_workbook(self.make_workbook(mapa_rows=[row]))
        codes = {issue.code for issue in report.issues}
        self.assertEqual("REPROVADO", report.status)
        self.assertIn("CAMPO_OBRIGATORIO_VAZIO", codes)
        self.assertIn("OFERTA_SEM_HORARIO", codes)

    def test_allocating_row_without_order_is_rejected(self):
        row = valid_mapa_row()
        row[9] = None

        report = validate_workbook(self.make_workbook(mapa_rows=[row]))
        issues = [
            issue
            for issue in report.issues
            if issue.code == "CAMPO_OBRIGATORIO_VAZIO" and issue.column == "ORDEM"
        ]

        self.assertEqual("REPROVADO", report.status)
        self.assertEqual(1, len(issues))
        self.assertEqual([2], issues[0].rows)
        self.assertTrue(issues[0].blocking)

    def test_allocating_row_with_invalid_order_is_rejected(self):
        row = valid_mapa_row()
        row[9] = "3ª"

        report = validate_workbook(self.make_workbook(mapa_rows=[row]))
        issues = [
            issue
            for issue in report.issues
            if issue.code == "VALOR_FORA_DOMINIO" and issue.column == "ORDEM"
        ]

        self.assertEqual("REPROVADO", report.status)
        self.assertEqual(1, len(issues))
        self.assertEqual([2], issues[0].rows)
        self.assertTrue(issues[0].blocking)

    def test_duplicate_teacher_badge_is_rejected(self):
        first = valid_docente_row()
        second = valid_docente_row()
        second[0] = "OUTRO DOCENTE"
        report = validate_workbook(self.make_workbook(docente_rows=[first, second]))
        self.assertTrue(any(issue.code == "CHAVE_DUPLICADA" for issue in report.issues))

    def test_profile_without_active_teacher_is_reported(self):
        row = valid_mapa_row()
        row[5] = "Perfil inexistente"
        report = validate_workbook(self.make_workbook(mapa_rows=[row]))
        self.assertEqual("APROVADO_COM_RESSALVAS", report.status)
        self.assertTrue(any(issue.code == "PERFIL_SEM_DOCENTE_ATIVO" for issue in report.issues))

    def test_comma_separated_profiles_are_alternatives(self):
        row = valid_mapa_row()
        row[5] = "Perfil inexistente, Gestão - Administração"
        report = validate_workbook(self.make_workbook(mapa_rows=[row]))
        self.assertFalse(any(issue.code == "PERFIL_SEM_DOCENTE_ATIVO" for issue in report.issues))

    def test_expected_module_mismatch_is_rejected(self):
        report = validate_workbook(self.make_workbook(), expected_module=53)
        issues = [issue for issue in report.issues if issue.code == "MODULO_DIVERGENTE"]
        self.assertEqual("REPROVADO", report.status)
        self.assertEqual(53, report.metadata["expected_module"])
        self.assertEqual([2], issues[0].rows)
        self.assertTrue(issues[0].blocking)

    def test_valid_stricto_workbook_is_approved(self):
        mapa = valid_mapa_row()
        mapa[18] = "CLT STRICTO"
        docente = valid_docente_row()
        docente[2] = "PROFESSOR DE ENSINO SUPERIOR PRESENCIAL"
        docente[3] = 0
        docente[4] = 0

        report = validate_workbook(
            self.make_workbook(mapa_rows=[mapa], docente_rows=[docente]),
        )
        self.assertEqual("APROVADO", report.status)
        self.assertEqual([], report.issues)

    def test_input_contract_model_does_not_restrict_profile_coverage(self):
        mapa = valid_mapa_row()
        mapa[18] = "CLT STRICTO"

        report = validate_workbook(self.make_workbook(mapa_rows=[mapa]))

        self.assertEqual("APROVADO", report.status)
        self.assertFalse(
            any(issue.code == "PERFIL_SEM_DOCENTE_ATIVO" for issue in report.issues)
        )

    def test_unknown_input_contract_model_is_ignored(self):
        mapa = valid_mapa_row()
        mapa[18] = "QUALQUER VALOR"

        report = validate_workbook(self.make_workbook(mapa_rows=[mapa]))

        self.assertEqual("APROVADO", report.status)
        self.assertEqual([], report.issues)

    def test_missing_input_contract_model_is_ignored(self):
        mapa = valid_mapa_row()
        mapa[18] = None

        report = validate_workbook(self.make_workbook(mapa_rows=[mapa]))

        self.assertEqual("APROVADO", report.status)
        self.assertEqual([], report.issues)

    def test_formula_in_data_is_blocking(self):
        row = valid_mapa_row()
        row[1] = '="CURSO TESTE"'

        report = validate_workbook(self.make_workbook(mapa_rows=[row]))
        issues = [issue for issue in report.issues if issue.code == "FORMULA_NA_BASE"]
        self.assertEqual("REPROVADO", report.status)
        self.assertEqual([2], issues[0].rows)
        self.assertTrue(issues[0].blocking)


if __name__ == "__main__":
    unittest.main()

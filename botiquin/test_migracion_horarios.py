"""Prueba de la migración que introduce los horarios múltiples.

Verifica que los datos anteriores (pautas con una sola hora y sus tomas
registradas) se conserven al migrar al esquema de horarios.
"""
from datetime import date, time

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigracionHorariosTests(TransactionTestCase):
    """La migración 0011_horarios_toma conserva las pautas y sus tomas."""

    migrate_from = ("botiquin", "0010_clasificacion_uso")
    migrate_to = ("botiquin", "0011_horarios_toma")

    def _estado(self, destino):
        executor = MigrationExecutor(connection)
        executor.migrate([destino])
        return executor.loader.project_state([destino]).apps

    def test_la_hora_antigua_pasa_a_ser_un_horario(self):
        # 1. Se vuelve al esquema anterior (con una sola hora por pauta).
        apps = self._estado(self.migrate_from)

        Usuario = apps.get_model("cuentas", "Usuario")
        Hogar = apps.get_model("cuentas", "Hogar")
        MiembroHogar = apps.get_model("cuentas", "MiembroHogar")
        Medicamento = apps.get_model("botiquin", "Medicamento")
        PautaToma = apps.get_model("botiquin", "PautaToma")
        TomaRegistrada = apps.get_model("botiquin", "TomaRegistrada")

        usuario = Usuario.objects.create(
            username="migracion", password="x", email="migracion@example.com"
        )
        hogar = Hogar.objects.create(nombre="Hogar de prueba")
        miembro = MiembroHogar.objects.create(
            hogar=hogar, nombre="Ana", es_principal=True
        )
        medicamento = Medicamento.objects.create(
            usuario=usuario,
            nombre="Paracetamol",
            cantidad=10,
            fecha_vencimiento=date(2031, 1, 1),
        )
        pauta = PautaToma.objects.create(
            medicamento=medicamento,
            miembro=miembro,
            frecuencia="diaria",
            fecha_inicio=date(2020, 1, 1),
            hora=time(8, 0),
        )
        TomaRegistrada.objects.create(
            pauta=pauta, fecha=date(2026, 1, 1), tomada=True
        )

        # 2. Se aplica la migración de los horarios.
        apps = self._estado(self.migrate_to)

        HorarioToma = apps.get_model("botiquin", "HorarioToma")
        TomaRegistrada = apps.get_model("botiquin", "TomaRegistrada")

        horarios = list(HorarioToma.objects.filter(pauta_id=pauta.pk))
        self.assertEqual(len(horarios), 1)
        self.assertEqual(horarios[0].hora, time(8, 0))

        # La toma registrada queda asociada a ese horario.
        toma = TomaRegistrada.objects.get(pauta_id=pauta.pk)
        self.assertEqual(toma.horario_id, horarios[0].pk)
        self.assertTrue(toma.tomada)

    def test_una_pauta_sin_hora_conserva_un_horario_sin_hora_fija(self):
        apps = self._estado(self.migrate_from)

        Usuario = apps.get_model("cuentas", "Usuario")
        Hogar = apps.get_model("cuentas", "Hogar")
        MiembroHogar = apps.get_model("cuentas", "MiembroHogar")
        Medicamento = apps.get_model("botiquin", "Medicamento")
        PautaToma = apps.get_model("botiquin", "PautaToma")

        usuario = Usuario.objects.create(
            username="migracion_sin_hora", password="x", email="sinhora@example.com"
        )
        hogar = Hogar.objects.create(nombre="Hogar sin hora")
        miembro = MiembroHogar.objects.create(
            hogar=hogar, nombre="Luis", es_principal=True
        )
        medicamento = Medicamento.objects.create(
            usuario=usuario,
            nombre="Ibuprofeno",
            cantidad=5,
            fecha_vencimiento=date(2031, 1, 1),
        )
        pauta = PautaToma.objects.create(
            medicamento=medicamento,
            miembro=miembro,
            frecuencia="diaria",
            fecha_inicio=date(2020, 1, 1),
            hora=None,
        )

        apps = self._estado(self.migrate_to)

        HorarioToma = apps.get_model("botiquin", "HorarioToma")

        horarios = list(HorarioToma.objects.filter(pauta_id=pauta.pk))
        self.assertEqual(len(horarios), 1)
        self.assertIsNone(horarios[0].hora)

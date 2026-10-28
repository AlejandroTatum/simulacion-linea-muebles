"""Une los escenarios, el modelo y la vista."""

from pathlib import Path

from modelo.configuracion import ErrorConfiguracion, cargar_escenario
from modelo.simulacion import (SimulacionLinea, cuello_de_botella,
                               resumir_linea)
from modelo.teoria import flujo_teorico_min
from vista.graficas import graficar
from vista.tablas import mostrar_resumen

RAIZ = Path(__file__).resolve().parents[1]


class ControladorSimulacion:
    """Ejecuta escenarios y guarda sus resultados."""

    def __init__(self, salida=RAIZ):
        self.salida = Path(salida)

    def ejecutar(self, rutas):
        """Valida todos los escenarios y después simula cada uno."""
        escenarios = [(Path(ruta), cargar_escenario(ruta)) for ruta in rutas]

        nombres = [ruta.stem for ruta, _ in escenarios]
        repetido = next((nombre for nombre in nombres if nombres.count(nombre) > 1), None)
        if repetido:
            raise ErrorConfiguracion(
                f"dos escenarios se llaman '{repetido}'; sus resultados se pisarían")

        self.salida.mkdir(parents=True, exist_ok=True)
        for numero, (ruta, escenario) in enumerate(escenarios):
            if numero:
                print()
            self._ejecutar_escenario(ruta, escenario)

    def _ejecutar_escenario(self, ruta, escenario):
        replicas, resumen = SimulacionLinea(escenario).correr_todas()
        nombre = ruta.stem
        ruta_replicas = self.salida / f"resultados-{nombre}.csv"
        ruta_resumen = self.salida / f"resumen-{nombre}.csv"
        ruta_grafico = self.salida / "graficos" / f"{nombre}.png"

        replicas.round(6).to_csv(ruta_replicas, index=False)
        resumen.round(6).to_csv(ruta_resumen, index=False)
        graficar(ruta_resumen, ruta_grafico)

        linea = resumir_linea(replicas)
        flujo_teorico = flujo_teorico_min(escenario["tasa_llegadas_h"],
                                          escenario["estaciones"])
        archivos = (ruta_replicas.name, ruta_resumen.name,
                    ruta_grafico.relative_to(self.salida).as_posix())
        mostrar_resumen(escenario, resumen, linea, cuello_de_botella(resumen),
                        flujo_teorico, archivos)

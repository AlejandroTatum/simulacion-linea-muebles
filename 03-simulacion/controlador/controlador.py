"""Une los escenarios, el modelo y la vista."""

from pathlib import Path

from modelo.configuracion import ErrorConfiguracion, cargar_escenario
from modelo.simulacion import (SimulacionLinea, cuello_de_botella,
                               resumir_linea)
from modelo.teoria import flujo_teorico_min
from vista.graficas import (graficar, graficar_cola, graficar_distribucion_cola,
                            graficar_escenarios, graficar_flujo, graficar_replicas,
                            graficar_utilizacion_cola)
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
        resultados = []
        for numero, (ruta, escenario) in enumerate(escenarios):
            if numero:
                print()
            resultados.append(self._ejecutar_escenario(ruta, escenario))

        # La comparación solo tiene sentido si se simuló más de un escenario.
        if len(resultados) > 1:
            ruta_comparacion = self.salida / "graficos" / "escenarios.png"
            graficar_escenarios(resultados, ruta_comparacion)
            print(f"\nComparación: {ruta_comparacion.relative_to(self.salida).as_posix()}")

    def _ejecutar_escenario(self, ruta, escenario):
        traza = []
        replicas, resumen = SimulacionLinea(escenario).correr_todas(traza=traza)
        nombre = ruta.stem
        ruta_replicas = self.salida / f"resultados-{nombre}.csv"
        ruta_resumen = self.salida / f"resumen-{nombre}.csv"
        graficos = self.salida / "graficos"

        rutas_graficos = {
            "base": graficos / f"{nombre}.png",
            "cola": graficos / f"cola-{nombre}.png",
            "utilizacion_cola": graficos / f"utilizacion-cola-{nombre}.png",
            "distribucion_cola": graficos / f"distribucion-cola-{nombre}.png",
            "replicas": graficos / f"replicas-{nombre}.png",
            "flujo": graficos / f"flujo-{nombre}.png",
        }

        replicas.round(6).to_csv(ruta_replicas, index=False)
        resumen.round(6).to_csv(ruta_resumen, index=False)
        graficar(ruta_resumen, rutas_graficos["base"])
        graficar_cola(traza, resumen, escenario, rutas_graficos["cola"])
        graficar_utilizacion_cola(resumen, rutas_graficos["utilizacion_cola"])
        graficar_distribucion_cola(traza, resumen, escenario, rutas_graficos["distribucion_cola"])
        graficar_replicas(replicas, resumen, rutas_graficos["replicas"])
        graficar_flujo(resumen, escenario, rutas_graficos["flujo"])

        linea = resumir_linea(replicas)
        cuello = cuello_de_botella(resumen)
        flujo_teorico = flujo_teorico_min(escenario["tasa_llegadas_h"],
                                          escenario["estaciones"])
        archivos = [ruta_replicas.name, ruta_resumen.name] + [
            ruta.relative_to(self.salida).as_posix() for ruta in rutas_graficos.values()]
        mostrar_resumen(escenario, resumen, linea, cuello, flujo_teorico, archivos)
        return {"nombre": nombre, "escenario": escenario, "resumen": resumen,
                "linea": linea, "cuello": cuello}

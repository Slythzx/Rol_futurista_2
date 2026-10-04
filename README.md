# Mesa de Rol en Vivo — VTT

App de Streamlit para llevar la mesa en directo: fichas sincronizadas entre todos
los conectados, iniciativa, NPCs ocultos, dados y acciones rápidas con sus costes.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Estructura

Antes todo vivía en un único `app.py` de ~1.200 líneas (conservado en
`legacy/app_v1_monolitico.py` por si hace falta comparar; se puede borrar).
Ahora está separado por capas:

| Fichero | Qué contiene |
| --- | --- |
| `app.py` | Punto de entrada: configuración de página, enrutado DM/jugador y autorefresco |
| `rolfantasia/rules.py` | Fórmulas y tablas del sistema. Módulo puro, sin Streamlit ni estado |
| `rolfantasia/store.py` | Estado global compartido por todas las sesiones + log de mesa |
| `rolfantasia/characters.py` | Fichas: alta, costes, visibilidad, import/export JSON |
| `rolfantasia/initiative.py` | Orden de turnos, estados (aturdido/ralentizado), delay |
| `rolfantasia/styles.py` | CSS de la mesa |
| `rolfantasia/ui/widgets.py` | Campos ligados a la ficha, KPIs, matriz de daños, log |
| `rolfantasia/ui/dice.py` | Tiradas libres y resolución de tiradas con modificadores |
| `rolfantasia/ui/actions.py` | Panel de acciones rápidas (PA, fatiga y tirada) |
| `rolfantasia/ui/sheet.py` | Ficha en solo lectura (espectador) y operable (DM) |
| `rolfantasia/ui/reglas.py` | Pestaña «Reglas de combate» (solo pinta el Markdown) |
| `rolfantasia/reglas_combate.md` | **Texto de la chuleta de reglas: edítalo aquí** |
| `rolfantasia/ui/player.py` | Vista del jugador |
| `rolfantasia/ui/dm.py`, `ui/dm_initiative.py` | Vista del DM |
| `rolfantasia/ui/sidebar.py` | Elección de identidad y alta de personajes |

Las fórmulas están todas en `rules.py`: tocar ahí cambia a la vez la hoja del
jugador, el monitor del DM y el log.

## Fórmulas que escalan con el nivel

**Daño Total.** El divisor del atributo depende del nivel (`DIVISOR_DANIO`):

| Nivel | Daño Total |
| --- | --- |
| 0–99 | (Atributo / 3) + Mod |
| 100–199 | (Atributo / 2) + Mod |
| 200+ | Atributo + Mod |

La ficha muestra la fórmula vigente debajo del Daño Total, así que se ve al
momento cuál se está aplicando.

**Fatiga Física base.** `8 + escalado de nivel + floor(Cuerpo_Total / 2)`, donde
el escalado es +1 cada 3 niveles hasta el 75 y, a partir de ahí, **+1 por cada
nivel adicional** (`FF_NIVEL_UMBRAL`). Por ejemplo, con Cuerpo 10: nivel 75 → 38,
nivel 76 → 39, nivel 80 → 43.

## Novedades

**Daños por estadística desde el panel del DM.** El monitor muestra el daño ya
calculado de cada ficha (T / N / L) y una columna *Daños por* para cambiar la
estadística base de ese NPC sin salir de la tabla. Debajo, *Ficha en detalle*
abre la ficha completa con la matriz de las tres estadísticas a la vez
(resaltando la seleccionada), control de PA y acciones rápidas.

**Panel de acciones rápidas** (pestaña *Acciones* del jugador y dentro de la
ficha en detalle del DM). Eliges la acción y el panel precarga su coste en PA, su
modificador a la tirada y su fatiga mental; los valores son una propuesta, se
pueden subir o bajar sin límite antes de aplicarlos. *Tirar y gastar* lanza los
dados sumando el modificador de la acción automáticamente y descuenta PA y
fatiga de una vez; *Solo coste* aplica únicamente el gasto. En el log de la mesa
queda el tipo de acción y la tirada; el gasto no se publica, porque cada uno lo
ve ya en su ficha.

**Todo el turno en una pestaña.** La pestaña *Acciones* del jugador reúne el
selector de estadística para daños (el mismo que en *Mi Ficha*, sincronizado),
los KPIs, el panel de acciones y, en una columna lateral, el log de la mesa y una
*Tirada libre* desplegable. En el *Monitor de Fichas* del DM el log va junto a la
ficha en detalle, para ver el resultado de cada tirada sin cambiar de pestaña.

Cada tipo de tirada tiene su icono para reconocerlo de un vistazo: ⚔️ cuerpo a
cuerpo y disparos, ✨ hechizos y habilidades, 🏃 movimientos, 🛡️ defensas y
🛡️⚔️ contraataques.

### Tablas implementadas

| Acción | PA | Modificador | Fatiga mental |
| --- | --- | --- | --- |
| ⚔️ CaC simple / disparo simple | 5 | −2 | — |
| ✨ Hechizo o habilidad menor | 5 | −2 | +1 a +3 |
| ⚔️ Maniobra elaborada / disparo apuntado | 10 | +0 | — |
| ✨ Hechizo o habilidad media | 10 | +0 | +4 a +6 |
| ⚔️ Maniobra superior / disparo con arma pesada | 15 | +2 | — |
| ✨ Hechizo o habilidad mayor / arriesgada | 15–20 | +2 a +3 | +8 a +12 |
| ✨ Acción extrema | 25+ | +3 a +5 | +15 a +25 |

| 🏃 Movimiento | PA |
| --- | --- |
| Corto | 5 |
| Intermedio | 10 |
| Largo / sprint | 15–20 |

| Ataque recibido | 🛡️ Esquivar/bloquear | 🛡️⚔️ Contraataque |
| --- | --- | --- |
| Simple | 3 PA | 8 PA |
| Elaborado | 5 PA | 10 PA |
| Superior / complejo | 8–10 PA | 13–15 PA |

El contraataque es la defensa equivalente + 5 PA (`CONTRAATAQUE_PA`), así que se
calcula solo a partir de la tabla de defensas.

Los valores viven en `ACCIONES` (`rolfantasia/rules.py`): para retocar un coste,
un modificador o añadir una acción nueva basta con editar esa lista.

**Pestaña «📖 Reglas de combate»** (jugador y DM): chuleta de consulta rápida con
las tablas de acciones, acción conjunta, desplazamiento, fatigas, defensa,
contraataque y proteger a un aliado. El texto está en
`rolfantasia/reglas_combate.md` — es Markdown normal, se edita ahí y los cambios
salen al recargar la página, sin tocar código.

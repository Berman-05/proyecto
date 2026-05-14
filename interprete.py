"""
interprete.py
Genera la salida narrativa de la ejecución del script RPG.

Novedades:
  · icono personalizado por personaje (apariencia.icono)
  · Arte ASCII por clase con el icono elegido integrado
  · Acciones: caminar (animación de pasos), hablar (bocadillo de texto),
    usar+objetivo (muestra daño y barras HP antes/después)
"""

# ── Paleta de clases ──────────────────────────────────────────────────────────
CLASES = {
    "guerrero": {
        "color": "#ef4444", "titulo": "GUERRERO",
        "desc": "Maestro del combate cuerpo a cuerpo.",
        "bonus_HP": 20, "bonus_MP": 0,  "bonus_dano": 10,
    },
    "mago": {
        "color": "#8b5cf6", "titulo": "MAGO",
        "desc": "Domina los arcanos y la magia elemental.",
        "bonus_HP": 0,  "bonus_MP": 30, "bonus_dano": 5,
    },
    "arquero": {
        "color": "#22c55e", "titulo": "ARQUERO",
        "desc": "Puntería letal desde la distancia.",
        "bonus_HP": 10, "bonus_MP": 5,  "bonus_dano": 15,
    },
    "sanador": {
        "color": "#10b981", "titulo": "SANADOR",
        "desc": "Restaura vida y protege a sus aliados.",
        "bonus_HP": 15, "bonus_MP": 20, "bonus_dano": 0,
    },
    "asesino": {
        "color": "#64748b", "titulo": "ASESINO",
        "desc": "Golpe letal desde las sombras.",
        "bonus_HP": 5,  "bonus_MP": 10, "bonus_dano": 25,
    },
    "paladin": {
        "color": "#f59e0b", "titulo": "PALADÍN",
        "desc": "Guerrero sagrado, fe y acero.",
        "bonus_HP": 25, "bonus_MP": 15, "bonus_dano": 5,
    },
    "hechicero": {
        "color": "#a855f7", "titulo": "HECHICERO",
        "desc": "Poder oscuro y hechizos devastadores.",
        "bonus_HP": 0,  "bonus_MP": 40, "bonus_dano": 20,
    },
    "bardo": {
        "color": "#ec4899", "titulo": "BARDO",
        "desc": "Sus melodías inspiran y debilitan enemigos.",
        "bonus_HP": 10, "bonus_MP": 15, "bonus_dano": 8,
    },
}

# Icono por defecto por clase (si el usuario no especifica icono)
ICONO_DEFECTO_CLASE = {
    "guerrero":  "⚔️",
    "mago":      "🔮",
    "arquero":   "🏹",
    "sanador":   "💚",
    "asesino":   "🗡️",
    "paladin":   "🛡️",
    "hechicero": "✨",
    "bardo":     "🎵",
}

ICONO_CATEGORIA = {
    "personaje": "🧙", "habilidad": "⚔️", "estado": "☠️",
    "objeto": "🎒",    "mision": "📜",     "combate": "⚡",
    "accion": "🎯",
}


def _barra(actual, maximo=100, largo=20,
           char_lleno="█", char_vacio="░"):
    if maximo == 0:
        return char_vacio * largo
    p = min(max(actual, 0) / maximo, 1.0)
    n = int(p * largo)
    return char_lleno * n + char_vacio * (largo - n)


def _ln(texto, tipo, **kw):
    d = {"texto": texto, "tipo": tipo}
    d.update(kw)
    return d


def _arte_personaje(icono, clase_nombre=None, nombre_personaje=None):
    """Genera arte ASCII para un personaje con su icono y nombre."""
    ic = icono or (ICONO_DEFECTO_CLASE.get(clase_nombre, "🧙") if clase_nombre else "🧙")

    # Nombre centrado sobre el personaje (máx 13 chars visibles)
    if nombre_personaje:
        nombre_corto = nombre_personaje[:13]
        padding = (13 - len(nombre_corto)) // 2
        nombre_centrado = " " * padding + nombre_corto + " " * (13 - len(nombre_corto) - padding)
    else:
        nombre_centrado = "             "

    lineas = [
        f"   ┌─────────────┐  ",
        f"   │ {nombre_centrado} │  ",
        f"   ├─────────────┤  ",
        f"   │      {ic}      │  ",
        f"   │   \\(^o^)/   │  ",
        f"   │    ║   ║    │  ",
        f"   │   /║   ║\\   │  ",
        f"   │  ╱_╝   ╚_╲  │  ",
        f"   └─────────────┘  ",
    ]
    return lineas


# ── Intérprete ────────────────────────────────────────────────────────────────

class InterpretadorRPG:

    def interpretar(self, tabla_simbolos, tokens_raw):
        self._tabla = tabla_simbolos
        salida = []

        if not tabla_simbolos:
            salida.append(_ln("  (sin declaraciones para mostrar)", "info"))
            return salida

        salida += [
            _ln("═" * 56, "sep"),
            _ln("  🎮  EJECUCIÓN DEL SCRIPT RPG", "titulo_principal"),
            _ln("═" * 56, "sep"),
            _ln("", "sep"),
        ]

        # ── Fase 1: declaraciones ─────────────────────────────────────────
        for nombre, datos in tabla_simbolos.items():
            cat   = datos.get("categoria", "?")
            vals  = datos.get("valor", {})
            icono = ICONO_CATEGORIA.get(cat, "◆")

            # Encabezado de cada entidad
            cat_upper = cat.upper()
            salida.append(_ln(f"  {icono}  {cat_upper}: {nombre}", f"cabecera_{cat}",
                              categoria=cat))
            salida.append(_ln("─" * 56, "sep_bloque"))

            fn = getattr(self, f"_render_{cat}", self._render_generico)
            fn(nombre, datos, salida)
            salida.append(_ln("", "sep"))

        # ── Fase 2: condiciones del código ────────────────────────────────
        conds = self._extraer_condiciones(tokens_raw)
        if conds:
            salida += [
                _ln("═" * 56, "sep"),
                _ln("  🔀  CONDICIONES EVALUADAS", "titulo_principal"),
                _ln("═" * 56, "sep"),
            ]
            for c in conds:
                salida.append(_ln(f"  → {c}", "condicion"))
            salida.append(_ln("", "sep"))

        return salida

    # ── Renderers ─────────────────────────────────────────────────────────

    def _render_personaje(self, nombre, datos, salida):
        vals       = datos.get("valor", {})
        apariencia = datos.get("apariencia", {})

        hp  = vals.get("HP", {}).get("valor")
        mp  = vals.get("MP", {}).get("valor")
        xp  = vals.get("XP", {}).get("valor")
        hp_actual = datos.get("HP_actual")   # calculado por semántico tras daño

        cls_val  = apariencia.get("clase",  {}).get("valor") if apariencia else None
        raza_val = apariencia.get("raza",   {}).get("valor") if apariencia else None
        niv_val  = apariencia.get("nivel",  {}).get("valor") if apariencia else None
        icon_val = apariencia.get("icono",  {}).get("valor") if apariencia else None

        cls_lower = cls_val.lower() if cls_val else None
        info_cls  = CLASES.get(cls_lower) if cls_lower else None

        # Icono efectivo: el que puso el usuario o el defecto de la clase
        icono_ef = icon_val or (ICONO_DEFECTO_CLASE.get(cls_lower) if cls_lower else "🧙")

        salida.append(_ln("", "sep"))
        arte = _arte_personaje(icono_ef, cls_lower, nombre_personaje=nombre)
        color_arte = info_cls["color"] if info_cls else "#38bdf8"
        for fila in arte:
            salida.append(_ln(f"     {fila}", "arte", color=color_arte))
        salida.append(_ln("", "sep"))

        # Apariencia
        if apariencia:
            if cls_val:
                txt_cls = info_cls["titulo"] if info_cls else cls_val.upper()
                salida.append(_ln(
                    f"  {icono_ef}  CLASE: {txt_cls}",
                    "clase_titulo", color=color_arte
                ))
                if info_cls:
                    salida.append(_ln(f"     {info_cls['desc']}", "clase_desc"))
            if raza_val:
                salida.append(_ln(f"     Raza:  {raza_val}", "prop"))
            if niv_val is not None:
                salida.append(_ln(f"     Nivel: {niv_val}", "prop"))
            if icon_val:
                salida.append(_ln(f"     Icono: {icon_val}  (personalizado)", "prop"))
            salida.append(_ln("", "sep"))

        # Stats — solo los valores escritos en el código
        if hp is not None:
            b = _barra(hp, max(hp, 1))
            salida.append(_ln(f"     HP  {b}  {hp}", "barra_hp"))
        if mp is not None:
            b = _barra(mp, max(mp, 1))
            salida.append(_ln(f"     MP  {b}  {mp}", "barra_mp"))
        if xp is not None:
            b = _barra(xp, 1000, largo=20)
            salida.append(_ln(f"     XP  {b}  {xp}/1000", "barra_xp"))


    def _render_habilidad(self, nombre, datos, salida):
        vals = datos.get("valor", {})
        dano = vals.get("dano", {}).get("valor")
        if dano is not None:
            barra_dano = "▰" * min(dano // 5, 20) + "▱" * (20 - min(dano // 5, 20))
            salida.append(_ln(f"     ⚔️  Daño base:  {barra_dano}  {dano} pts", "habilidad_dano"))
        else:
            salida.append(_ln("     (sin daño definido)", "info"))


    def _render_estado(self, nombre, datos, salida):
        vals   = datos.get("valor", {})
        efecto = vals.get("efecto", {}).get("valor")
        if efecto:
            salida.append(_ln(f"     ☠️  Efecto activo: \"{efecto}\"", "estado_efecto"))
        else:
            salida.append(_ln("     (sin efecto definido)", "info"))

    def _render_comprobar(self, nombre, datos, salida):
        vals    = datos.get("valor", {})
        obj_ref = vals.get("objetivo", {}).get("valor")
        tabla   = self._tabla

        if not obj_ref or obj_ref not in tabla:
            salida.append(_ln(f"  ⚠️  objetivo '{obj_ref}' no encontrado.", "advertencia"))
            return

        obj_datos  = tabla[obj_ref]
        apariencia = obj_datos.get("apariencia", {})
        hp_base    = obj_datos.get("valor", {}).get("HP", {}).get("valor", 0)
        hp_actual  = obj_datos.get("HP_actual", hp_base)
        recibio    = obj_datos.get("dano_recibido", [])

        cls_obj   = apariencia.get("clase", {}).get("valor") if apariencia else None
        icon_val  = apariencia.get("icono", {}).get("valor") if apariencia else None
        cls_lower = cls_obj.lower() if cls_obj else None
        info_cls  = CLASES.get(cls_lower) if cls_lower else None
        icono_obj = icon_val or (ICONO_DEFECTO_CLASE.get(cls_lower) if cls_lower else "🧙")
        color_obj = info_cls["color"] if info_cls else "#38bdf8"

        salida.append(_ln(f"  🔍  Estado de {icono_obj} {obj_ref}:", "clase_titulo",
                          color=color_obj))
        salida.append(_ln("", "sep"))

        # Barra HP actual
        b = _barra(hp_actual, max(hp_base, 1))
        tag_hp = "barra_hp_cero" if hp_actual == 0 else (
                 "barra_hp_dano" if recibio else "barra_hp")
        salida.append(_ln(f"     HP  {b}  {hp_actual}/{hp_base}", tag_hp))

        if hp_actual == 0:
            salida.append(_ln(f"     💀  ¡{obj_ref} ha sido derrotado!", "derrota"))
        elif recibio and hp_actual <= hp_base * 0.25:
            salida.append(_ln(f"     ⚠️  Estado crítico!", "advertencia"))
        elif not recibio:
            salida.append(_ln(f"     ✅  Sin daño recibido.", "ok"))

        # Historial
        if recibio:
            salida.append(_ln("", "sep"))
            salida.append(_ln("     💔  Historial de daño recibido:", "advertencia"))
            for reg in recibio:
                salida.append(_ln(
                    f"        • «{reg['accion']}» → «{reg['habilidad']}»"
                    f"  -{reg['dano']} HP  ({reg['hp_antes']} → {reg['hp_despues']})",
                    "dano_historial"
                ))
        else:
            salida.append(_ln("     (sin efecto definido)", "info"))

    def _render_objeto(self, nombre, datos, salida):
        for attr, info in datos.get("valor", {}).items():
            salida.append(_ln(f"     🎒  {attr}: {info['valor']}", "objeto_prop"))

    def _render_mision(self, nombre, datos, salida):
        for attr, info in datos.get("valor", {}).items():
            salida.append(_ln(f"     📜  {attr}: {info['valor']}", "mision_prop"))

    def _render_combate(self, nombre, datos, salida):
        for attr, info in datos.get("valor", {}).items():
            salida.append(_ln(f"     ⚡  {attr}: {info['valor']}", "combate_prop"))

    def _render_accion(self, nombre, datos, salida):
        vals   = datos.get("valor", {})
        tabla  = self._tabla

        usar_ref  = vals.get("usar",     {}).get("valor")
        obj_ref   = vals.get("objetivo", {}).get("valor")
        mens_val  = vals.get("mensaje",  {}).get("valor")
        cam_val   = vals.get("caminar",  {}).get("valor")
        hab_val   = vals.get("hablar",   {}).get("valor")

        # ── CAMINAR ──────────────────────────────────────────────────────
        if cam_val is not None:
            pasos = int(cam_val)
            huella = "👣 " * min(pasos, 10)
            salida.append(_ln(f"  🚶  CAMINAR  →  {pasos} paso(s)", "accion_tipo"))
            salida.append(_ln(f"     {huella}", "accion_pasos"))
            if pasos > 10:
                salida.append(_ln(f"     … y {pasos - 10} pasos más", "info"))
            salida.append(_ln("", "sep"))

        # ── HABLAR ───────────────────────────────────────────────────────
        if hab_val:
            ancho = max(len(hab_val) + 4, 20)
            borde = "─" * ancho
            salida.append(_ln(f"  💬  HABLAR", "accion_tipo"))
            salida.append(_ln(f"     ╭{borde}╮", "bocadillo"))
            salida.append(_ln(f"     │  {hab_val.ljust(ancho - 2)}│", "bocadillo"))
            salida.append(_ln(f"     ╰{borde}╯", "bocadillo"))
            salida.append(_ln(f"        ▲", "bocadillo"))
            salida.append(_ln("", "sep"))

        # ── MENSAJE ──────────────────────────────────────────────────────
        if mens_val:
            salida.append(_ln(f"  📢  MENSAJE: \"{mens_val}\"", "accion_mensaje"))
            salida.append(_ln("", "sep"))

        # ── USAR HABILIDAD SOBRE OBJETIVO ─────────────────────────────────
        if usar_ref and obj_ref:
            habil_datos = tabla.get(usar_ref, {})
            obj_datos   = tabla.get(obj_ref,  {})

            dano = habil_datos.get("valor", {}).get("dano", {}).get("valor")

            hp_base   = obj_datos.get("valor", {}).get("HP", {}).get("valor", 0)
            dano_regs = obj_datos.get("dano_recibido", [])
            # buscar el registro de esta acción
            reg_este  = next((r for r in dano_regs if r["accion"] == nombre), None)

            hp_antes  = reg_este["hp_antes"]   if reg_este else hp_base
            hp_despues= reg_este["hp_despues"]  if reg_este else hp_base

            cls_obj      = obj_datos.get("apariencia", {}).get("clase", {}).get("valor")
            icon_obj_val = obj_datos.get("apariencia", {}).get("icono", {}).get("valor")
            cls_lower_obj= cls_obj.lower() if cls_obj else None
            info_cls_obj = CLASES.get(cls_lower_obj) if cls_lower_obj else None
            icono_obj    = icon_obj_val or (
                ICONO_DEFECTO_CLASE.get(cls_lower_obj) if cls_lower_obj else "🧙"
            )
            color_obj    = info_cls_obj["color"] if info_cls_obj else "#38bdf8"
            # hp_max = solo el valor escrito en código
            hp_max_obj = hp_base

            salida.append(_ln(f"  ⚔️   ATAQUE con «{usar_ref}»", "accion_tipo"))
            salida.append(_ln(f"     Objetivo: {icono_obj} {obj_ref}", "accion_prop",
                              color=color_obj))

            if dano is not None:
                salida.append(_ln(
                    f"     💥 Daño aplicado: {dano} puntos", "accion_dano"
                ))
                salida.append(_ln("", "sep"))

                # Barra ANTES
                b_antes = _barra(hp_antes, max(hp_max_obj, 1))
                salida.append(_ln(
                    f"     {icono_obj} HP antes   {b_antes}  {hp_antes}/{hp_max_obj}",
                    "barra_hp"
                ))

                # Animación de golpe
                salida.append(_ln(
                    f"            ⚡⚡  ─{dano}HP ─ ⚡⚡",
                    "golpe_anim"
                ))

                # Barra DESPUÉS
                b_desp = _barra(hp_despues, max(hp_max_obj, 1))
                tag_desp = "barra_hp_cero" if hp_despues == 0 else "barra_hp_dano"
                salida.append(_ln(
                    f"     {icono_obj} HP después  {b_desp}  {hp_despues}/{hp_max_obj}",
                    tag_desp
                ))

                if hp_despues == 0:
                    salida.append(_ln(
                        f"     💀  ¡{obj_ref} ha sido derrotado!", "derrota"
                    ))
                elif hp_despues <= hp_max_obj * 0.25:
                    salida.append(_ln(
                        f"     ⚠️  ¡{obj_ref} está en estado crítico!", "advertencia"
                    ))

        elif usar_ref or obj_ref:
            salida.append(_ln("  ⚔️   ATAQUE incompleto (falta usar o objetivo)", "info"))

        if not vals:
            salida.append(_ln("     (sin parámetros definidos)", "info"))

    def _render_generico(self, nombre, datos, salida):
        for attr, info in datos.get("valor", {}).items():
            salida.append(_ln(f"     {attr}: {info['valor']} ({info['tipo']})", "prop"))

    # ── Condiciones ───────────────────────────────────────────────────────

    def _extraer_condiciones(self, tokens_raw):
        res = []
        i, n = 0, len(tokens_raw)
        while i < n:
            tok = tokens_raw[i]
            if tok["token"] == "PALABRA_RESERVADA" and tok["lexema"] in ("condicion", "condición"):
                j = i + 1
                izq = []
                while j < n and tokens_raw[j]["token"] != "OPERADOR_COMPARACION":
                    if tokens_raw[j]["lexema"] not in (";", "{", "}"):
                        izq.append(tokens_raw[j]["lexema"])
                    j += 1
                if j < n and tokens_raw[j]["token"] == "OPERADOR_COMPARACION":
                    op = tokens_raw[j]["lexema"]
                    j += 1
                    der = []
                    while j < n and tokens_raw[j]["lexema"] not in (";", "{", "}"):
                        der.append(tokens_raw[j]["lexema"])
                        j += 1
                    res.append(f"condicion  {' '.join(izq)} {op} {' '.join(der)}")
                i = j
            else:
                i += 1
        return res

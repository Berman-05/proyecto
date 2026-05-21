"""
semantico.py
Analiza semánticamente el script RPG.

Novedades:
  - apariencia { clase = "..."; raza = "..."; nivel = N; icono = "🧙"; }
  - accion NombreAccion {
        usar     = Habilidad;   -- aplica daño al objetivo
        objetivo = Personaje;
        mensaje  = "texto";
        caminar  = N;           -- pasos (int)
        hablar   = "texto";     -- dialogo
    }
  - Después de ejecutar todas las acciones, tabla_simbolos refleja
    el HP actualizado de cada personaje (campo "HP_actual").
"""

# iconos permitidos para apariencia.icono
ICONOS_VALIDOS = {
    "🧙","⚔️","🔮","🏹","💚","🗡️","🛡️","✨","🎵",
    "🐉","💀","🔥","❄️","⚡","🌿","🌑","☀️","🦊","🐺","🦅",
    "🧝","🧟","🧛","🧜","🧞","🤺","🥷","🦸","🦹","🧚"
}


class AnalizadorSemantico:
    def __init__(self):
        self.tabla_simbolos   = {}
        self.errores          = []
        self.contexto_actual  = None
        self.identificador_actual = None
        self.sub_contexto     = None

        # Propiedades válidas por categoría principal
        self.propiedades_validas = {
            "personaje": {"HP", "MP", "XP"},
            "habilidad": {"dano", "tipo", "distancia", "nivel"},
            "estado":    {"efecto"},
            "objeto":    set(),
            "mision":    set(),
            "combate":   set(),
            "accion":    {"usar", "objetivo", "mensaje", "caminar", "hablar", "enemigo"},
            "comprobar": {"objetivo"},
            "oleada":    {"enemigo"},
        }

        # Sub-bloque apariencia (dentro de personaje)
        self.propiedades_apariencia = {"clase", "raza", "nivel", "icono"}

        self.tipos_propiedades = {
            # personaje
            "HP":       "int",
            "MP":       "int",
            "XP":       "int",
            # habilidad
            "dano":     "int",
            "tipo":      "string",
            "distancia": "int",
            # estado
            "efecto":   "string",
            # apariencia
            "clase":    "string",
            "raza":     "string",
            "nivel":    "int",
            "icono":    "string",
            # accion
            "usar":     "ref_habilidad",
            "objetivo": "ref_personaje",
            "mensaje":  "string",
            "caminar":  "int",
            "hablar":   "string",
            "enemigo":   "ref_personaje",
        }

    # ── Entrada principal ─────────────────────────────────────────────────

    def analizar(self, tokens):
        self.tabla_simbolos      = {}
        self.errores             = []
        self.contexto_actual     = None
        self.identificador_actual = None
        self.sub_contexto        = None

        i = 0
        while i < len(tokens):
            tok    = tokens[i]
            lexema = tok["lexema"]
            tipo   = tok["token"]
            linea  = tok.get("linea", 1)

            # ── Declaración de entidad principal ─────────────────────────
            if tipo == "PALABRA_RESERVADA" and lexema in self.propiedades_validas:
                if i + 1 < len(tokens) and tokens[i+1]["token"] == "IDENTIFICADOR":
                    nombre = tokens[i+1]["lexema"]
                    if nombre in self.tabla_simbolos:
                        self.errores.append(self._error(linea, "E02",
                            f"Identificador '{nombre}' ya declarado"))
                        i += 2
                        continue
                    self.tabla_simbolos[nombre] = {
                        "categoria":  lexema,
                        "tipo":       lexema,
                        "valor":      {},
                        "apariencia": {},
                    }
                    self.contexto_actual      = lexema
                    self.identificador_actual = nombre
                    self.sub_contexto         = None
                    i += 2
                    continue

            # ── Sub-bloque apariencia (solo dentro de personaje) ──────────
            if (tipo == "PALABRA_RESERVADA" and lexema == "apariencia"
                    and self.contexto_actual == "personaje"):
                self.sub_contexto = "apariencia"
                i += 1
                continue

            # ── condicion ────────────────────────────────────────────────
            if tipo == "PALABRA_RESERVADA" and lexema in ("condicion", "condición"):
                _, i = self._procesar_condicion(tokens, i, linea)
                continue

            if lexema == "{":
                i += 1
                continue

            if lexema == "}":
                if self.sub_contexto == "apariencia":
                    self.sub_contexto = None
                else:
                    self.contexto_actual      = None
                    self.identificador_actual = None
                    self.sub_contexto         = None
                i += 1
                continue

            # ── Propiedades dentro de apariencia ─────────────────────────
            if self.sub_contexto == "apariencia" and tipo == "PALABRA_RESERVADA":
                if lexema in self.propiedades_apariencia:
                    i = self._procesar_prop_apariencia(tokens, i, linea, lexema)
                else:
                    self.errores.append(self._error(linea, "E04",
                        f"Propiedad '{lexema}' no válida en apariencia"))
                    i += 1
                continue

            # ── Asignación punto fuera de bloque ─────────────────────────
            if tipo == "IDENTIFICADOR" and not self.contexto_actual:
                resultado = self._intentar_asignacion_punto(tokens, i, linea)
                if resultado is not None:
                    i = resultado
                    continue
                # ── Variable global (ej: x = 5;) ─────────────────────────
                resultado = self._intentar_asignacion_variable(tokens, i, linea)
                if resultado is not None:
                    i = resultado
                    continue

            # ── Propiedades dentro de bloque normal ───────────────────────
            if tipo == "PALABRA_RESERVADA" and self.contexto_actual:
                propiedad = lexema
                props = self.propiedades_validas.get(self.contexto_actual, set())
                if propiedad not in props:
                    self.errores.append(self._error(linea, "E04",
                        f"Propiedad '{propiedad}' no válida en {self.contexto_actual}"))
                    i += 1
                    continue
                i = self._procesar_asignacion_declaracion(tokens, i, linea, propiedad)
                continue

            # ── Palabra reservada fuera de contexto ───────────────────────
            if tipo == "PALABRA_RESERVADA" and not self.contexto_actual:
                if lexema not in ("condicion", "condición"):
                    self.errores.append(self._error(linea, "E07",
                        f"'{lexema}' fuera de un bloque"))

            i += 1

        # ── Post-proceso: aplicar daño de acciones sobre personajes ───────
        self._aplicar_efectos_acciones()

        return self.errores

    # ── Variables globales (compatibilidad con proyecto original) ─────────

    def _intentar_asignacion_variable(self, tokens, i, linea):
        """Permite declarar variables globales: x = 5; o x = \"texto\";"""
        if i + 2 >= len(tokens):
            return None
        if tokens[i+1]["lexema"] != "=":
            return None
        # Evitar confundir con asignación punto (ej: obj.prop = valor)
        if i + 2 < len(tokens) and tokens[i+2]["lexema"] == ".":
            return None
        nombre = tokens[i]["lexema"]
        j = i + 2
        valor, j = self._leer_expresion_aritmetica(tokens, j, linea)
        if valor is None:
            return self._saltar_hasta_punto_coma(tokens, j)
        tipo_val  = "int" if isinstance(valor, (int, float)) else "string"
        valor_fin = int(valor) if isinstance(valor, float) and valor == int(valor) else valor
        if nombre not in self.tabla_simbolos:
            self.tabla_simbolos[nombre] = {
                "categoria":  "variable_global",
                "tipo":       tipo_val,
                "valor":      {},
                "apariencia": {},
            }
        else:
            self.tabla_simbolos[nombre]["tipo"] = tipo_val
        self.tabla_simbolos[nombre]["valor"]["_val"] = {"valor": valor_fin, "tipo": tipo_val}
        if j < len(tokens) and tokens[j]["lexema"] == ";":
            j += 1
        return j

    # ── Post-proceso de daño ──────────────────────────────────────────────

    def _aplicar_efectos_acciones(self):
        """
        Recorre todas las acciones declaradas.
        Si tienen usar+objetivo, aplica el daño de la habilidad al HP del personaje.
        Guarda el resultado en tabla_simbolos[objetivo]["HP_actual"].
        """
        for nombre, datos in self.tabla_simbolos.items():
            if datos["categoria"] != "accion":
                continue

            habil_ref = datos["valor"].get("usar",     {}).get("valor")
            obj_ref   = datos["valor"].get("objetivo", {}).get("valor")

            if not habil_ref or not obj_ref:
                continue
            if habil_ref not in self.tabla_simbolos:
                continue
            if obj_ref not in self.tabla_simbolos:
                continue

            habil_datos = self.tabla_simbolos[habil_ref]
            obj_datos   = self.tabla_simbolos[obj_ref]

            if habil_datos["categoria"] != "habilidad":
                continue
            if obj_datos["categoria"] != "personaje":
                continue

            dano_slot = habil_datos["valor"].get("dano", {})
            dano = dano_slot.get("valor", 0)

            # HP base o ya calculado
            hp_base = obj_datos["valor"].get("HP", {}).get("valor", 0)
            hp_actual = obj_datos.get("HP_actual", hp_base)
            nuevo_hp  = max(0, hp_actual - dano)

            obj_datos["HP_actual"] = nuevo_hp
            obj_datos["dano_recibido"] = obj_datos.get("dano_recibido", [])
            obj_datos["dano_recibido"].append({
                "accion":    nombre,
                "habilidad": habil_ref,
                "dano":      dano,
                "hp_antes":  hp_actual,
                "hp_despues":nuevo_hp,
            })

    # ── Procesadores de propiedades ───────────────────────────────────────

    def _procesar_prop_apariencia(self, tokens, i, linea, propiedad):
        if i + 3 > len(tokens):
            self.errores.append(self._error(linea, "E03",
                "Asignación incompleta en apariencia"))
            return i + 1

        op_tok  = tokens[i+1] if i+1 < len(tokens) else None
        val_tok = tokens[i+2] if i+2 < len(tokens) else None

        if op_tok is None or op_tok["lexema"] != "=":
            self.errores.append(self._error(linea, "E03",
                f"Se esperaba '=' después de '{propiedad}'"))
            return i + 1
        if val_tok is None:
            self.errores.append(self._error(linea, "E03", "Falta valor en apariencia"))
            return i + 2

        tipo_esp = self.tipos_propiedades.get(propiedad)
        valor    = None

        if val_tok["token"] == "CADENA":
            if tipo_esp == "int":
                self.errores.append(self._error(linea, "E05",
                    f"'{propiedad}' debe ser numérico"))
                return i + 4
            valor = val_tok["lexema"]
            # Validar icono
            if propiedad == "icono" and valor not in ICONOS_VALIDOS:
                self.errores.append(self._error(linea, "E10",
                    f"Icono '{valor}' no reconocido. "
                    f"Usa uno de: {', '.join(sorted(ICONOS_VALIDOS)[:8])} …"))
                return i + 4

        elif val_tok["token"] == "NUMERO":
            if tipo_esp == "string":
                self.errores.append(self._error(linea, "E05",
                    f"'{propiedad}' debe ser texto"))
                return i + 4
            valor = int(val_tok["lexema"])
        else:
            self.errores.append(self._error(linea, "E03",
                f"Tipo de valor no válido para '{propiedad}'"))
            return i + 4

        ident = self.identificador_actual
        if propiedad in self.tabla_simbolos[ident]["apariencia"]:
            self.errores.append(self._error(linea, "E06",
                f"'{propiedad}' ya definido en apariencia"))
            return i + 4

        self.tabla_simbolos[ident]["apariencia"][propiedad] = {
            "valor": valor,
            "tipo":  "string" if isinstance(valor, str) else "int"
        }
        return i + 4

    def _procesar_asignacion_declaracion(self, tokens, i, linea, propiedad):
        if i + 3 > len(tokens):
            self.errores.append(self._error(linea, "E03", "Asignación incompleta"))
            return i + 1

        op_tok  = tokens[i+1] if i+1 < len(tokens) else None
        val_tok = tokens[i+2] if i+2 < len(tokens) else None

        if op_tok is None or op_tok["lexema"] != "=":
            self.errores.append(self._error(linea, "E03", "Se esperaba '='"))
            return i + 1
        if val_tok is None:
            self.errores.append(self._error(linea, "E03", "Falta valor"))
            return i + 2

        tipo_esp = self.tipos_propiedades.get(propiedad)
        valor    = None

        if val_tok["token"] == "NUMERO":
            valor = int(val_tok["lexema"])
            if tipo_esp == "string":
                self.errores.append(self._error(linea, "E05",
                    f"'{propiedad}' debe ser texto"))
                return i + 4

        elif val_tok["token"] == "IDENTIFICADOR":
            nombre_ref = val_tok["lexema"]
            if tipo_esp == "string":
                valor = nombre_ref
            elif tipo_esp == "ref_habilidad":
                if nombre_ref not in self.tabla_simbolos:
                    self.errores.append(self._error(linea, "E01",
                        f"Habilidad '{nombre_ref}' no declarada"))
                    return i + 4
                if self.tabla_simbolos[nombre_ref]["categoria"] != "habilidad":
                    self.errores.append(self._error(linea, "E09",
                        f"'{nombre_ref}' no es una habilidad"))
                    return i + 4
            elif tipo_esp == "ref_personaje":
                if nombre_ref not in self.tabla_simbolos:
                    self.errores.append(self._error(linea, "E01",
                        f"Personaje '{nombre_ref}' no declarado"))
                    return i + 4
                if self.tabla_simbolos[nombre_ref]["categoria"] != "personaje":
                    self.errores.append(self._error(linea, "E09",
                        f"'{nombre_ref}' no es un personaje"))
                    return i + 4
            elif nombre_ref not in self.tabla_simbolos:
                self.errores.append(self._error(linea, "E01",
                    f"Identificador '{nombre_ref}' no declarado"))
                return i + 4
            if valor is None:
                valor = nombre_ref

        elif val_tok["token"] == "CADENA":
            valor = val_tok["lexema"]
            if tipo_esp == "int":
                self.errores.append(self._error(linea, "E05",
                    f"'{propiedad}' debe ser numérico"))
                return i + 4
        else:
            self.errores.append(self._error(linea, "E03", "Tipo de dato incompatible"))
            return i + 4

        ident = self.identificador_actual
        if propiedad == "enemigo" and self.contexto_actual == "oleada":
            enemigos = self.tabla_simbolos[ident]["valor"].setdefault(
                "enemigo", {"valor": [], "tipo": "lista_ref"}
            )
            enemigos["valor"].append(valor)
            return i + 4

        if propiedad in self.tabla_simbolos[ident]["valor"]:
            self.errores.append(self._error(linea, "E06", f"'{propiedad}' ya definida"))
            return i + 4

        tipo_val = (
            "int"    if isinstance(valor, int)
            else "string" if val_tok["token"] == "CADENA" or tipo_esp == "string"
            else "ref"
        )
        self.tabla_simbolos[ident]["valor"][propiedad] = {
            "valor": valor, "tipo": tipo_val
        }
        return i + 4

    def _intentar_asignacion_punto(self, tokens, i, linea):
        if i + 4 > len(tokens):
            return None
        t0, t1, t2, t3 = tokens[i], tokens[i+1], tokens[i+2], tokens[i+3]
        if t1["lexema"] != "." or t3["lexema"] != "=":
            return None
        if t2["token"] not in ("IDENTIFICADOR", "PALABRA_RESERVADA"):
            return None

        entidad   = t0["lexema"]
        propiedad = t2["lexema"]

        if entidad not in self.tabla_simbolos:
            self.errores.append(self._error(linea, "E01",
                f"Variable '{entidad}' no declarada"))
            return self._saltar_hasta_punto_coma(tokens, i+4)

        entrada = self.tabla_simbolos[entidad]
        props   = self.propiedades_validas.get(entrada["categoria"], set())
        if propiedad not in props:
            self.errores.append(self._error(linea, "E04",
                f"Propiedad '{propiedad}' no válida en {entrada['categoria']}"))
            return self._saltar_hasta_punto_coma(tokens, i+4)

        j = i + 4
        valor, j = self._leer_expresion_aritmetica(tokens, j, linea)
        if valor is None:
            return self._saltar_hasta_punto_coma(tokens, j)

        tipo_esp = self.tipos_propiedades.get(propiedad)
        if tipo_esp == "int" and not isinstance(valor, (int, float)):
            self.errores.append(self._error(linea, "E05",
                f"'{propiedad}' debe ser numérico"))
            return self._saltar_hasta_punto_coma(tokens, j)
        if tipo_esp == "string" and not isinstance(valor, str):
            self.errores.append(self._error(linea, "E05",
                f"'{propiedad}' debe ser texto"))
            return self._saltar_hasta_punto_coma(tokens, j)

        tipo_real   = "int" if isinstance(valor, (int, float)) else "string"
        valor_final = int(valor) if isinstance(valor, float) and valor == int(valor) else valor
        entrada["valor"][propiedad] = {"valor": valor_final, "tipo": tipo_real}

        if j < len(tokens) and tokens[j]["lexema"] == ";":
            j += 1
        return j

    # ── Condiciones ──────────────────────────────────────────────────────

    def _procesar_condicion(self, tokens, i, linea):
        j = i + 1
        izq, j = self._leer_valor_expr(tokens, j, linea)
        if izq is None:
            return None, j
        if j >= len(tokens) or tokens[j]["token"] != "OPERADOR_COMPARACION":
            return None, j + 1
        operador = tokens[j]["lexema"]
        j += 1
        der, j = self._leer_valor_expr(tokens, j, linea)
        if der is None:
            return None, j
        resultado_cond = None
        if isinstance(izq, (int, float)) and isinstance(der, (int, float)):
            resultado_cond = self._evaluar_op(izq, operador, der)
        if j < len(tokens) and tokens[j]["lexema"] == ";":
            return resultado_cond, j + 1
        if j < len(tokens) and tokens[j]["lexema"] == "{":
            j += 1
            if resultado_cond is False:
                j = self._saltar_bloque(tokens, j)
            return resultado_cond, j
        return None, j

    # ── Expresiones aritméticas ──────────────────────────────────────────

    def _leer_expresion_aritmetica(self, tokens, j, linea):
        val_izq, j = self._leer_valor_expr(tokens, j, linea)
        if val_izq is None:
            return None, j
        if (j < len(tokens)
                and tokens[j]["token"] == "OPERADOR"
                and tokens[j]["lexema"] in ("+", "-")):
            op = tokens[j]["lexema"]
            j += 1
            val_der, j = self._leer_valor_expr(tokens, j, linea)
            if val_der is None:
                return None, j
            if isinstance(val_izq, (int, float)) and isinstance(val_der, (int, float)):
                return (val_izq + val_der if op == "+" else val_izq - val_der), j
            self.errores.append(self._error(linea, "E05",
                "Operación aritmética requiere valores numéricos"))
            return None, j
        return val_izq, j

    def _leer_valor_expr(self, tokens, j, linea):
        if j >= len(tokens):
            return None, j
        tok = tokens[j]
        if tok["token"] == "NUMERO":
            return int(tok["lexema"]), j + 1
        if tok["token"] == "CADENA":
            return tok["lexema"], j + 1
        if tok["token"] in ("IDENTIFICADOR", "PALABRA_RESERVADA"):
            entidad = tok["lexema"]
            if (j + 2 < len(tokens)
                    and tokens[j+1]["lexema"] == "."
                    and tokens[j+2]["token"] in ("IDENTIFICADOR", "PALABRA_RESERVADA")):
                propiedad = tokens[j+2]["lexema"]
                valor = self._resolver_prop(entidad, propiedad, linea)
                return valor, j + 3
            return entidad, j + 1
        return None, j

    def _resolver_prop(self, entidad, propiedad, linea):
        if entidad not in self.tabla_simbolos:
            self.errores.append(self._error(linea, "E01",
                f"Variable '{entidad}' no declarada"))
            return None
        entrada = self.tabla_simbolos[entidad]
        props   = self.propiedades_validas.get(entrada["categoria"], set())
        if propiedad not in props:
            self.errores.append(self._error(linea, "E04",
                f"Propiedad '{propiedad}' no válida en {entrada['categoria']}"))
            return None
        slot = entrada["valor"].get(propiedad)
        if slot is None:
            self.errores.append(self._error(linea, "E08",
                f"'{entidad}.{propiedad}' aún no tiene valor asignado"))
            return None
        return slot["valor"]

    # ── Utilidades ───────────────────────────────────────────────────────

    @staticmethod
    def _evaluar_op(izq, op, der):
        return {">": izq > der, "<": izq < der, ">=": izq >= der,
                "<=": izq <= der, "==": izq == der, "!=": izq != der}.get(op)

    def _saltar_bloque(self, tokens, j):
        depth = 1
        while j < len(tokens) and depth > 0:
            lex = tokens[j]["lexema"]
            if lex == "{":   depth += 1
            elif lex == "}": depth -= 1
            j += 1
        return j

    @staticmethod
    def _saltar_hasta_punto_coma(tokens, j):
        while j < len(tokens) and tokens[j]["lexema"] != ";":
            j += 1
        return j + 1 if j < len(tokens) else j

    def _error(self, linea, codigo, mensaje):
        return {"linea": linea, "tipo": "SEMANTICO",
                "codigo": codigo, "mensaje": mensaje}

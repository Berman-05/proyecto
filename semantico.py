class AnalizadorSemantico:
    def __init__(self):
        self.tabla_simbolos = {}
        self.errores = []
        self.contexto_actual = None
        self.identificador_actual = None

        self.propiedades_validas = {
            "personaje": {"HP", "MP", "XP"},
            "habilidad": {"dano"},
            "estado":    {"efecto"},
            "objeto":    set(),
            "mision":    set(),
            "combate":   set()
        }

        self.tipos_propiedades = {
            "HP":     "int",
            "MP":     "int",
            "XP":     "int",
            "dano":   "int",
            "efecto": "string"
        }

    def analizar(self, tokens):
        self.tabla_simbolos = {}
        self.errores = []
        self.contexto_actual = None
        self.identificador_actual = None

        i = 0
        while i < len(tokens):
            tok    = tokens[i]
            lexema = tok["lexema"]
            tipo   = tok["token"]
            linea  = tok.get("linea", 1)

            if tipo == "PALABRA_RESERVADA" and lexema in self.propiedades_validas:
                if i + 1 < len(tokens) and tokens[i+1]["token"] == "IDENTIFICADOR":
                    nombre = tokens[i+1]["lexema"]
                    if nombre in self.tabla_simbolos:
                        self.errores.append(self._error(linea, "E02",
                            f"Identificador '{nombre}' ya declarado"))
                        i += 2
                        continue
                    self.tabla_simbolos[nombre] = {
                        "categoria": lexema,
                        "tipo":      lexema,
                        "valor":     {}
                    }
                    self.contexto_actual      = lexema
                    self.identificador_actual = nombre
                    i += 2
                    continue

            if tipo == "PALABRA_RESERVADA" and lexema in ("condicion", "condicion"):
                _, i = self._procesar_condicion(tokens, i, linea)
                continue

            if lexema == "{":
                i += 1
                continue

            if lexema == "}":
                self.contexto_actual      = None
                self.identificador_actual = None
                i += 1
                continue

            if tipo == "IDENTIFICADOR" and not self.contexto_actual:
                resultado = self._intentar_asignacion_punto(tokens, i, linea)
                if resultado is not None:
                    i = resultado
                    continue

            if tipo == "PALABRA_RESERVADA" and self.contexto_actual:
                propiedad = lexema
                if propiedad not in self.propiedades_validas[self.contexto_actual]:
                    self.errores.append(self._error(linea, "E04",
                        f"Propiedad '{propiedad}' no valida en {self.contexto_actual}"))
                    i += 1
                    continue
                i = self._procesar_asignacion_declaracion(tokens, i, linea, propiedad)
                continue

            if tipo == "PALABRA_RESERVADA" and not self.contexto_actual:
                if lexema not in ("condicion", "condicion"):
                    self.errores.append(self._error(linea, "E07",
                        f"'{lexema}' fuera de un bloque"))

            i += 1

        return self.errores

    def _procesar_condicion(self, tokens, i, linea):
        """
        Formas:
          condicion Ent.Prop OP valor ;
          condicion Ent.Prop OP Ent2.Prop2 ;
          condicion Ent.Prop OP valor { ... }
        """
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

    def _intentar_asignacion_punto(self, tokens, i, linea):
        if i + 4 >= len(tokens):
            return None

        t0 = tokens[i]
        t1 = tokens[i+1]
        t2 = tokens[i+2]
        t3 = tokens[i+3]

        if t1["lexema"] != "." or t3["lexema"] != "=":
            return None
        if t2["token"] not in ("IDENTIFICADOR", "PALABRA_RESERVADA"):
            return None

        entidad   = t0["lexema"]
        propiedad = t2["lexema"]

        if entidad not in self.tabla_simbolos:
            self.errores.append(self._error(linea, "E01",
                f"Variable '{entidad}' no declarada"))
            return self._saltar_hasta_punto_coma(tokens, i + 4)

        entrada = self.tabla_simbolos[entidad]
        props_validas = self.propiedades_validas.get(entrada["categoria"], set())

        if propiedad not in props_validas:
            self.errores.append(self._error(linea, "E04",
                f"Propiedad '{propiedad}' no valida en {entrada['categoria']}"))
            return self._saltar_hasta_punto_coma(tokens, i + 4)

        j = i + 4
        valor, j = self._leer_expresion_aritmetica(tokens, j, linea)

        if valor is None:
            return self._saltar_hasta_punto_coma(tokens, j)

        tipo_esp = self.tipos_propiedades.get(propiedad)
        if tipo_esp == "int" and not isinstance(valor, (int, float)):
            self.errores.append(self._error(linea, "E05",
                f"'{propiedad}' debe ser numerico"))
            return self._saltar_hasta_punto_coma(tokens, j)
        if tipo_esp == "string" and not isinstance(valor, str):
            self.errores.append(self._error(linea, "E05",
                f"'{propiedad}' debe ser texto"))
            return self._saltar_hasta_punto_coma(tokens, j)

        tipo_real = "int" if isinstance(valor, (int, float)) else "string"
        valor_final = int(valor) if isinstance(valor, float) and valor == int(valor) else valor
        self.tabla_simbolos[entidad]["valor"][propiedad] = {
            "valor": valor_final,
            "tipo":  tipo_real
        }

        if j < len(tokens) and tokens[j]["lexema"] == ";":
            j += 1
        return j

    def _procesar_asignacion_declaracion(self, tokens, i, linea, propiedad):
        if i + 3 >= len(tokens):
            self.errores.append(self._error(linea, "E03", "Asignacion incompleta"))
            return i + 1

        operador_tok = tokens[i+1]
        valor_token  = tokens[i+2]

        if operador_tok["lexema"] != "=":
            self.errores.append(self._error(linea, "E03", "Se esperaba '='"))
            return i + 1

        tipo_esperado = self.tipos_propiedades.get(propiedad)

        if valor_token["token"] == "NUMERO":
            valor = int(valor_token["lexema"])
            if tipo_esperado == "string":
                self.errores.append(self._error(linea, "E05",
                    f"{propiedad} debe ser texto"))
                return i + 4

        elif valor_token["token"] == "IDENTIFICADOR":
            nombre_ref = valor_token["lexema"]
            if nombre_ref not in self.tabla_simbolos:
                self.errores.append(self._error(linea, "E01",
                    f"Identificador '{nombre_ref}' no declarado"))
                return i + 4
            valor = nombre_ref

        elif valor_token["token"] == "CADENA":
            valor = valor_token["lexema"]
            if tipo_esperado == "int":
                self.errores.append(self._error(linea, "E05",
                    f"{propiedad} debe ser numerico"))
                return i + 4

        else:
            self.errores.append(self._error(linea, "E03", "Tipo de dato incompatible"))
            return i + 4

        if propiedad in self.tabla_simbolos[self.identificador_actual]["valor"]:
            self.errores.append(self._error(linea, "E06",
                f"'{propiedad}' ya definida"))
            return i + 4

        tipo_val = ("int" if isinstance(valor, int)
                    else "string" if valor_token["token"] == "CADENA"
                    else "ref")

        self.tabla_simbolos[self.identificador_actual]["valor"][propiedad] = {
            "valor": valor,
            "tipo":  tipo_val
        }
        return i + 4

    def _leer_expresion_aritmetica(self, tokens, j, linea):
        val_izq, j = self._leer_valor_expr(tokens, j, linea)
        if val_izq is None:
            return None, j

        if (j < len(tokens)
                and tokens[j]["token"] == "OPERADOR"
                and tokens[j]["lexema"] in ("+", "-")):
            op  = tokens[j]["lexema"]
            j  += 1
            val_der, j = self._leer_valor_expr(tokens, j, linea)
            if val_der is None:
                return None, j
            if isinstance(val_izq, (int, float)) and isinstance(val_der, (int, float)):
                resultado = val_izq + val_der if op == "+" else val_izq - val_der
                return resultado, j
            else:
                self.errores.append(self._error(linea, "E05",
                    "Operacion aritmetica requiere valores numericos"))
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
        props_validas = self.propiedades_validas.get(entrada["categoria"], set())

        if propiedad not in props_validas:
            self.errores.append(self._error(linea, "E04",
                f"Propiedad '{propiedad}' no valida en {entrada['categoria']}"))
            return None

        slot = entrada["valor"].get(propiedad)
        if slot is None:
            self.errores.append(self._error(linea, "E08",
                f"'{entidad}.{propiedad}' aun no tiene valor asignado"))
            return None

        return slot["valor"]

    @staticmethod
    def _evaluar_op(izq, op, der):
        ops = {
            ">":  izq > der,
            "<":  izq < der,
            ">=": izq >= der,
            "<=": izq <= der,
            "==": izq == der,
            "!=": izq != der
        }
        return ops.get(op)

    def _saltar_bloque(self, tokens, j):
        depth = 1
        while j < len(tokens) and depth > 0:
            lex = tokens[j]["lexema"]
            if lex == "{":
                depth += 1
            elif lex == "}":
                depth -= 1
            j += 1
        return j

    @staticmethod
    def _saltar_hasta_punto_coma(tokens, j):
        while j < len(tokens) and tokens[j]["lexema"] != ";":
            j += 1
        return j + 1 if j < len(tokens) else j

    def _error(self, linea, codigo, mensaje):
        return {
            "linea":   linea,
            "tipo":    "SEMANTICO",
            "codigo":  codigo,
            "mensaje": mensaje
        }
class AnalizadorSemantico:
    def __init__(self):
        self.tabla_simbolos = {}
        self.errores = []
        self.contexto_actual = None
        self.identificador_actual = None

        self.propiedades_validas = {
            "personaje": {"HP", "MP", "XP"},
            "habilidad": {"daño", "dano"},
            "estado": {"efecto"},
            "objeto": set(),
            "mision": set(),
            "combate": set()
        }

        self.tipos_propiedades = {
            "HP": "int",
            "MP": "int",
            "XP": "int",
            "daño": "int",
            "dano": "int",
            "efecto": "string"
        }

    def analizar(self, tokens):
        self.tabla_simbolos = {}
        self.errores = []
        self.contexto_actual = None
        self.identificador_actual = None

        i = 0

        while i < len(tokens):
            tok = tokens[i]
            lexema = tok["lexema"]
            tipo = tok["token"]
            linea = tok.get("linea", 1)

            if tipo == "PALABRA_RESERVADA" and lexema in self.propiedades_validas:
                if i + 1 < len(tokens) and tokens[i+1]["token"] == "IDENTIFICADOR":
                    nombre = tokens[i+1]["lexema"]

                    if nombre in self.tabla_simbolos:
                        self.errores.append(self._error(linea, "E02", f"Identificador '{nombre}' ya declarado"))
                        i += 2
                        continue

                    self.tabla_simbolos[nombre] = {
                        "categoria": lexema,
                        "tipo": lexema,
                        "valor": {}
                    }

                    self.contexto_actual = lexema
                    self.identificador_actual = nombre

                    i += 2
                    continue

            if lexema == "{":
                i += 1
                continue

            if lexema == "}":
                self.contexto_actual = None
                self.identificador_actual = None
                i += 1
                continue

            if tipo == "PALABRA_RESERVADA":
                if not self.contexto_actual:
                    self.errores.append(self._error(linea, "E07", f"'{lexema}' fuera de un bloque"))
                    i += 1
                    continue

                propiedad = lexema

                if propiedad not in self.propiedades_validas[self.contexto_actual]:
                    self.errores.append(self._error(linea, "E04", f"Propiedad '{propiedad}' no válida en {self.contexto_actual}"))
                    i += 1
                    continue

                if i + 3 >= len(tokens):
                    self.errores.append(self._error(linea, "E03", "Asignación incompleta"))
                    i += 1
                    continue

                operador = tokens[i+1]
                valor_token = tokens[i+2]

                if operador["lexema"] != "=":
                    self.errores.append(self._error(linea, "E03", "Se esperaba '='"))
                    i += 1
                    continue

                tipo_esperado = self.tipos_propiedades.get(propiedad)

                if valor_token["token"] == "NUMERO":
                    valor = int(valor_token["lexema"])
                    if tipo_esperado == "string":
                        self.errores.append(self._error(linea, "E05", f"{propiedad} debe ser texto"))
                        i += 4
                        continue

                elif valor_token["token"] == "IDENTIFICADOR":
                    nombre_ref = valor_token["lexema"]
                    if nombre_ref not in self.tabla_simbolos:
                        self.errores.append(self._error(linea, "E01", f"Identificador '{nombre_ref}' no declarado"))
                        i += 4
                        continue
                    valor = nombre_ref

                elif valor_token["token"] == "CADENA":
                    valor = valor_token["lexema"]
                    if tipo_esperado == "int":
                        self.errores.append(self._error(linea, "E05", f"{propiedad} debe ser numérico"))
                        i += 4
                        continue

                else:
                    self.errores.append(self._error(linea, "E03", "Tipo de dato incompatible"))
                    i += 4
                    continue

                if propiedad in self.tabla_simbolos[self.identificador_actual]["valor"]:
                    self.errores.append(self._error(linea, "E06", f"'{propiedad}' ya definida"))
                    i += 4
                    continue

                if isinstance(valor, int):
                    tipo_valor = "int"
                elif isinstance(valor, str) and valor_token["token"] == "CADENA":
                    tipo_valor = "string"
                else:
                    tipo_valor = "ref"

                self.tabla_simbolos[self.identificador_actual]["valor"][propiedad] = {
                    "valor": valor,
                    "tipo": tipo_valor
                }

                i += 4
                continue

            i += 1

        return self.errores

    def _error(self, linea, codigo, mensaje):
        return {
            "linea": linea,
            "tipo": "SEMÁNTICO",
            "codigo": codigo,
            "mensaje": mensaje
        }
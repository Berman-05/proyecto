class AnalizadorSintactico:
    def analizar(self, tokens):
        errores = []
        pila_llaves = []
        i = 0

        while i < len(tokens):
            tok = tokens[i]
            lexema = tok["lexema"]
            linea = tok.get("linea", 1)

            if tok["token"] == "PALABRA_RESERVADA":

                if lexema == "mision":
                    if not self._esperar(tokens, i+1, "IDENTIFICADOR"):
                        errores.append(self._error(linea, "Se esperaba nombre de misión"))
                    elif not self._esperar_lexema(tokens, i+2, "{"):
                        errores.append(self._error(linea, "Se esperaba '{' después de misión"))
                    else:
                        pila_llaves.append(tok)
                        i += 2

                elif lexema == "objeto":
                    if not self._esperar(tokens, i+1, "IDENTIFICADOR"):
                        errores.append(self._error(linea, "Se esperaba identificador después de 'objeto'"))
                    elif not self._esperar_lexema(tokens, i+2, ";"):
                        errores.append(self._error(linea, "Falta ';' después de objeto"))
                    i += 2

                elif lexema == "estado":
                    if not self._esperar(tokens, i+1, "IDENTIFICADOR"):
                        errores.append(self._error(linea, "Se esperaba identificador después de 'estado'"))
                    elif not self._esperar_lexema(tokens, i+2, "{"):
                        errores.append(self._error(linea, "Se esperaba '{' después de estado"))
                    else:
                        pila_llaves.append(tok)
                        i += 2

                elif lexema in ["condicion", "condicion"]:
                    j = i + 1
                    j = self._saltar_valor(tokens, j)
                    if j < len(tokens) and tokens[j]["token"] == "OPERADOR_COMPARACION":
                        j += 1
                        j = self._saltar_valor(tokens, j)
                    if j < len(tokens) and tokens[j]["lexema"] == "{":
                        pila_llaves.append(tok)
                        i = j  
                    elif j < len(tokens) and tokens[j]["lexema"] == ";":
                        i = j  
                    else:
                        i = j

                elif lexema in ["XP", "HP", "MP", "dano", "efecto"]:
                    if not self._esperar_lexema(tokens, i+1, "="):
                        errores.append(self._error(linea, "Se esperaba '='"))
                    else:
                        j = i + 2
                        j = self._saltar_valor(tokens, j)
                        if j < len(tokens) and tokens[j]["lexema"] == ";":
                            i = j
                        else:
                            errores.append(self._error(linea, f"Falta ';' después del valor de '{lexema}'"))
                            i = j - 1

                elif lexema in ["objetivo", "nivel", "usar", "tipo", "distancia",
                                "mensaje", "caminar", "hablar", "enemigo",
                                "clase", "raza", "icono", "apariencia"]:
                    # Propiedades asignables: palabra_reservada = valor ;
                    if self._esperar_lexema(tokens, i+1, "="):
                        j = i + 2
                        j = self._saltar_valor(tokens, j)
                        if j < len(tokens) and tokens[j]["lexema"] == ";":
                            i = j
                        else:
                            errores.append(self._error(linea, f"Falta ';' después del valor de '{lexema}'"))
                            i = j - 1

            elif lexema == "{":
                pila_llaves.append(tok)

            elif lexema == "}":
                if not pila_llaves:
                    errores.append(self._error(linea, "Llave de cierre sin apertura"))
                else:
                    pila_llaves.pop()

            elif tok["token"] == "IDENTIFICADOR":
                # Caso 1: Entidad.Propiedad = valor [op valor] ;
                if (i + 2 < len(tokens)
                        and tokens[i+1]["lexema"] == "."
                        and tokens[i+2]["token"] in ("IDENTIFICADOR", "PALABRA_RESERVADA")):
                    j = i + 3
                    if j < len(tokens) and tokens[j]["lexema"] == "=":
                        j += 1
                        j = self._saltar_valor(tokens, j)
                        if j < len(tokens) and tokens[j]["token"] == "OPERADOR":
                            j += 1
                            j = self._saltar_valor(tokens, j)
                        if j < len(tokens) and tokens[j]["lexema"] == ";":
                            i = j
                        else:
                            errores.append(self._error(linea, f"Falta ';' en asignación de '{tok['lexema']}'"))
                            i = j - 1

                # Caso 2: identificador = valor ;  (asignación simple dentro de bloque)
                elif (i + 1 < len(tokens) and tokens[i+1]["lexema"] == "="):
                    j = i + 2
                    j = self._saltar_valor(tokens, j)
                    if j < len(tokens) and tokens[j]["token"] == "OPERADOR":
                        j += 1
                        j = self._saltar_valor(tokens, j)
                    if j < len(tokens) and tokens[j]["lexema"] == ";":
                        i = j
                    else:
                        errores.append(self._error(linea, f"Falta ';' en asignación de '{tok['lexema']}'"))
                        i = j - 1

            i += 1

        if pila_llaves:
            ultimo = pila_llaves[-1]
            errores.append(self._error(
                ultimo.get("linea", 1),
                "Llave sin cerrar"
            ))

        return errores

    def _saltar_valor(self, tokens, j):
        """Avanza j sobre un valor simple o acceso Entidad.Propiedad."""
        if j >= len(tokens):
            return j
        tok = tokens[j]
        if tok["token"] == "NUMERO" or tok["token"] == "CADENA":
            return j + 1
        if tok["token"] in ("IDENTIFICADOR", "PALABRA_RESERVADA"):
            if (j + 2 < len(tokens)
                    and tokens[j+1]["lexema"] == "."
                    and tokens[j+2]["token"] in ("IDENTIFICADOR", "PALABRA_RESERVADA")):
                return j + 3
            return j + 1
        return j + 1

    def _esperar(self, tokens, index, tipo):
        return index < len(tokens) and tokens[index]["token"] == tipo

    def _esperar_lexema(self, tokens, index, lexema):
        return index < len(tokens) and tokens[index]["lexema"] == lexema

    def _esperar_stat(self, tokens, index):
        """Acepta IDENTIFICADOR normal o palabras reservadas tipo stat (HP, MP, XP)."""
        if index >= len(tokens):
            return False
        t = tokens[index]
        if t["token"] == "IDENTIFICADOR":
            return True
        if t["token"] == "PALABRA_RESERVADA" and t["lexema"] in {"HP", "MP", "XP"}:
            return True
        return False

    def _error(self, linea, mensaje):
        return {
            "linea": linea,
            "tipo": "SINTACTICO",
            "mensaje": mensaje
        }
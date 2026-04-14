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
                    
                    elif not self._esperar_lexema(tokens, i+2, ";"):
                        errores.append(self._error(linea, "Falta ';' después de estado"))
                    
                    i += 2

                elif lexema in ["condicion", "condición"]:
                    if not self._esperar(tokens, i+1, "IDENTIFICADOR"):
                        errores.append(self._error(linea, "Se esperaba variable en condición"))
                    
                    elif not self._esperar(tokens, i+2, "OPERADOR_COMPARACION"):
                        errores.append(self._error(linea, "Se esperaba operador de comparación"))
                    
                    elif not self._esperar(tokens, i+3, "NUMERO"):
                        errores.append(self._error(linea, "Se esperaba número en condición"))
                    
                    elif not self._esperar_lexema(tokens, i+4, ";"):
                        errores.append(self._error(linea, "Falta ';' en condición"))
                    
                    i += 4

                elif lexema in ["XP", "HP", "MP"]:
                    if not self._esperar_lexema(tokens, i+1, "="):
                        errores.append(self._error(linea, "Se esperaba '='"))
                    
                    elif not self._esperar(tokens, i+2, "NUMERO"):
                        errores.append(self._error(linea, "Se esperaba número"))
                    
                    elif not self._esperar_lexema(tokens, i+3, ";"):
                        errores.append(self._error(linea, "Falta ';'"))
                    
                    i += 3

            elif lexema == "{":
                pila_llaves.append(tok)

            elif lexema == "}":
                if not pila_llaves:
                    errores.append(self._error(linea, "Llave de cierre sin apertura"))
                else:
                    pila_llaves.pop()

            i += 1

        if pila_llaves:
            ultimo = pila_llaves[-1]
            errores.append(self._error(
                ultimo.get("linea", 1),
                "Llave sin cerrar"
            ))

        return errores

    def _esperar(self, tokens, index, tipo):
        return index < len(tokens) and tokens[index]["token"] == tipo

    def _esperar_lexema(self, tokens, index, lexema):
        return index < len(tokens) and tokens[index]["lexema"] == lexema

    def _error(self, linea, mensaje):
        return {
            "linea": linea,
            "tipo": "SINTÁCTICO",
            "mensaje": mensaje
        }
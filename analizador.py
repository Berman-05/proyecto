import re

class AnalizadorLexico:
    def __init__(self):
        self.palabras_reservadas = {
            'personaje', 'habilidad', 'estado', 'objeto', 'mision', 
            'combate', 'efecto', 'condición', 'condicion', 'daño', 'dano', 
            'MP', 'HP', 'XP'
        }
        
        self.reglas_lexicas = [
            ('COMENTARIO', r'--.*'),
            ('ERROR_ID_NUM',  r'\d+[a-zA-Z_][a-zA-Z0-9_]*'), 
            ('OP_COMPARACION',r'==|!=|>=|<=|>|<'),             
            ('OPERADOR',      r'[\+\-\*\/]'),               
            ('SIMBOLO',       r'[\{\}\(\)\;\:\=\,]'),       
            ('NUMERO',        r'\d+'),                      
            ('IDENTIFICADOR', r'[a-zA-Z_][a-zA-Z0-9_]*'),  
            ('ESPACIO',       r'[ \t\n]+'),                  
            ('DESCONOCIDO',   r'.')
        ]
        
        self.regex = '|'.join(f'(?P<{nombre}>{patron})' for nombre, patron in self.reglas_lexicas)

    def analizar(self, codigo_fuente):
        resultados = []
        aprobado = True
        
        for coincidencia in re.finditer(self.regex, codigo_fuente):
            tipo_token = coincidencia.lastgroup
            lexema = coincidencia.group()
            inicio = coincidencia.start()
            fin = coincidencia.end()
            
            if tipo_token == 'ESPACIO':
                continue
                
            elif tipo_token == 'ERROR_ID_NUM':
                aprobado = False
                resultados.append({
                    "lexema": lexema,
                    "token": "ERROR LÉXICO",
                    "mensaje": "Identificador inválido: no puede comenzar con un número.",
                    "rango": (inicio, fin)
                })
                
            elif tipo_token == 'DESCONOCIDO':
                aprobado = False
                resultados.append({
                    "lexema": lexema,
                    "token": "ERROR LÉXICO",
                    "mensaje": f"Símbolo '{lexema}' no reconocido en este lenguaje.",
                    "rango": (inicio, fin)
                })
                
            elif tipo_token == 'IDENTIFICADOR':
                if lexema in self.palabras_reservadas:
                    resultados.append({"lexema": lexema, "token": "PALABRA_RESERVADA"})
                else:
                    resultados.append({"lexema": lexema, "token": "IDENTIFICADOR"})
                    
            elif tipo_token == 'NUMERO':
                resultados.append({"lexema": lexema, "token": "NUMERO"})
                
            elif tipo_token == 'SIMBOLO':
                resultados.append({"lexema": lexema, "token": "SIMBOLO_ESTRUCTURAL"})
                
            elif tipo_token == 'OP_COMPARACION':
                resultados.append({"lexema": lexema, "token": "OPERADOR_COMPARACION"})
                
            elif tipo_token == 'OPERADOR':
                resultados.append({"lexema": lexema, "token": "OPERADOR"})

        return {
            "aprobado": aprobado,
            "desglose": resultados
        }
    
class AnalizadorSintactico:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.errores = []

    def obtener_token_actual(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consumir(self, tipo_esperado, lexema_esperado=None):
        token = self.obtener_token_actual()
        if token:
            match_tipo = token['token'] == tipo_esperado
            match_lexema = lexema_esperado is None or token['lexema'] == lexema_esperado
            
            if match_tipo and match_lexema:
                self.pos += 1
                return token
        
        esperado = lexema_esperado if lexema_esperado else tipo_esperado
        actual = f"'{token['lexema']}'" if token else "FIN DE ARCHIVO"
        self.errores.append(f"Error sintáctico: Se esperaba {esperado}, se encontró {actual}")
        return None

    # <programa> ::= <lista_declaraciones>
    def analizar(self):
        if not self.tokens:
            return False, ["El código está vacío."]
        
        self.lista_declaraciones()
        
        # Verificar si quedó contenido sin procesar
        if self.pos < len(self.tokens):
            self.errores.append("Error: Contenido extra después del final del programa.")
            
        es_valido = len(self.errores) == 0
        return es_valido, self.errores

    # <lista_declaraciones> ::= <declaracion> | <declaracion> <lista_declaraciones>
    def lista_declaraciones(self):
        while self.pos < len(self.tokens):
            if not self.declaracion():
                break

    # <declaracion> ::= (personaje|habilidad|estado|objeto|mision|combate) identificador <bloque>
    def declaracion(self):
        token = self.obtener_token_actual()
        palabras_inicio = {'personaje', 'habilidad', 'estado', 'objeto', 'mision', 'combate'}
        
        if token and token['lexema'] in palabras_inicio:
            self.consumir('PALABRA_RESERVADA', token['lexema'])
            if self.consumir('IDENTIFICADOR'):
                return self.bloque()
        return False

    # <bloque> ::= { <lista_propiedades> }
    def bloque(self):
        if self.consumir('SIMBOLO_ESTRUCTURAL', '{'):
            self.lista_propiedades()
            return self.consumir('SIMBOLO_ESTRUCTURAL', '}')
        return False

    # <lista_propiedades> ::= <propiedad> | <propiedad> <lista_propiedades>
    def lista_propiedades(self):
        while self.pos < len(self.tokens):
            token = self.obtener_token_actual()
            # Si encontramos '}', se termina la lista de propiedades
            if token and token['lexema'] == '}':
                break
            if not self.propiedad():
                break

    # <propiedad> ::= identificador = <valor> ; | efecto : identificador ; | condicion ( <condicion_formal> ) ;
    def propiedad(self):
        token = self.obtener_token_actual()
        if not token: return False

        if token['lexema'] == 'efecto':
            self.consumir('PALABRA_RESERVADA', 'efecto')
            self.consumir('SIMBOLO_ESTRUCTURAL', ':')
            self.consumir('IDENTIFICADOR')
            return self.consumir('SIMBOLO_ESTRUCTURAL', ';')
        
        elif token['lexema'] == 'condicion' or token['lexema'] == 'condición':
            self.consumir('PALABRA_RESERVADA', token['lexema'])
            self.consumir('SIMBOLO_ESTRUCTURAL', '(')
            self.condicion_formal()
            self.consumir('SIMBOLO_ESTRUCTURAL', ')')
            return self.consumir('SIMBOLO_ESTRUCTURAL', ';')
            
        elif token['token'] == 'IDENTIFICADOR':
            self.consumir('IDENTIFICADOR')
            self.consumir('SIMBOLO_ESTRUCTURAL', '=')
            self.valor()
            return self.consumir('SIMBOLO_ESTRUCTURAL', ';')
        
        return False

    def valor(self):
        token = self.obtener_token_actual()
        if token and token['token'] in ['NUMERO', 'IDENTIFICADOR']:
            self.pos += 1
            return True
        self.errores.append(f"Error: Se esperaba un valor (número o id), se encontró '{token['lexema'] if token else 'nada'}'")
        return False

    def condicion_formal(self):
        self.expresion()
        self.consumir('OPERADOR_COMPARACION')
        self.expresion()

    def expresion(self):
        token = self.obtener_token_actual()
        if token and token['token'] in ['NUMERO', 'IDENTIFICADOR']:
            self.pos += 1
            return True
        self.errores.append("Error: Expresión inválida en condición.")
        return False
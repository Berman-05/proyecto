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
            ('CADENA', r'"[^"\n]*"'),
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
        linea = 1
        for coincidencia in re.finditer(self.regex, codigo_fuente):
            tipo_token = coincidencia.lastgroup
            lexema = coincidencia.group()
            inicio = coincidencia.start()
            fin = coincidencia.end()
            linea_actual = linea
            linea += lexema.count('\n')
            
            if tipo_token == 'ESPACIO':
                continue
                
            elif tipo_token == 'ERROR_ID_NUM':
                aprobado = False
                resultados.append({
                    "lexema": lexema,
                    "token": "ERROR LÉXICO",
                    "mensaje": "Identificador inválido: no puede comenzar con un número.",
                    "rango": (inicio, fin),
                    "linea": linea_actual
                })
                
            elif tipo_token == 'DESCONOCIDO':
                aprobado = False
                resultados.append({
                    "lexema": lexema,
                    "token": "ERROR LÉXICO",
                    "mensaje": f"Símbolo '{lexema}' no reconocido en este lenguaje.",
                    "rango": (inicio, fin),
                    "linea": linea_actual
                })
                
            elif tipo_token == 'IDENTIFICADOR':
                if lexema in self.palabras_reservadas:
                    resultados.append({"lexema": lexema, "token": "PALABRA_RESERVADA", "linea": linea_actual})
                else:
                    resultados.append({"lexema": lexema, "token": "IDENTIFICADOR", "linea": linea_actual})

            elif tipo_token == 'NUMERO':
                resultados.append({"lexema": lexema, "token": "NUMERO", "linea": linea_actual})
                
            elif tipo_token == 'SIMBOLO':
                resultados.append({"lexema": lexema, "token": "SIMBOLO_ESTRUCTURAL", "linea": linea_actual})
                
            elif tipo_token == 'OP_COMPARACION':
                resultados.append({"lexema": lexema, "token": "OPERADOR_COMPARACION", "linea": linea_actual})
                
            elif tipo_token == 'OPERADOR':
                resultados.append({"lexema": lexema, "token": "OPERADOR", "linea": linea_actual})
            
            elif tipo_token == 'CADENA':
                resultados.append({
                    "lexema": lexema.strip('"'),
                    "token": "CADENA",
                    "linea": linea_actual
    })

        return {
            "aprobado": aprobado,
            "desglose": resultados
        }
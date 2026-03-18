import re

class AnalizadorLexico:
    def __init__(self):
        self.palabras_reservadas = {
            'personaje', 'habilidad', 'estado', 'objeto', 'mision', 
            'combate', 'efecto', 'condición', 'condicion', 'daño', 'dano', 
            'MP', 'HP', 'XP'
        }
        
        self.reglas_lexicas = [
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
            
            if tipo_token == 'ESPACIO':
                continue
                
            elif tipo_token == 'ERROR_ID_NUM':
                aprobado = False
                resultados.append({
                    "lexema": lexema,
                    "token": "ERROR LÉXICO: numero e identificador son tokens diferentes"
                })
                
            elif tipo_token == 'DESCONOCIDO':
                aprobado = False
                resultados.append({
                    "lexema": lexema,
                    "token": "ERROR LÉXICO: Símbolo no definido en el lenguaje."
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
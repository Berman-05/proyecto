from analizador import AnalizadorLexico

if __name__ == "__main__":
    analizador = AnalizadorLexico()
    
    codigo_ejemplo_d = """
    estado 2Venenos {
        dano >= 5;
    }
    """

    print("\n--- Analizando Ejemplo D (Inválido) ---")
    
    resultado_d = analizador.analizar(codigo_ejemplo_d)
    
    print(f"Aprobado: {resultado_d['aprobado']}")
    
    for item in resultado_d['desglose']:
        print(f"{item['lexema']} -> {item['token']}")
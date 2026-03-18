import tkinter as tk
from tkinter import ttk, font
from analizador import AnalizadorLexico

class AppAnalizador:
    def __init__(self, root):
        self.root = root
        self.analizador = AnalizadorLexico()
        
        self.root.title("RPG Script Lexer Pro")
        self.root.geometry("1000x650")
        self.root.configure(bg="#0f172a")

        self.fuente_mono = font.Font(family="Consolas", size=11)
        self.fuente_ui = font.Font(family="Segoe UI", size=10)
        self.fuente_titulo = font.Font(family="Segoe UI", size=14, weight="bold")

        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#1e293b", relief="flat")
        style.configure("Status.TLabel", background="#1e293b", foreground="#94a3b8", font=self.fuente_ui)

    def create_widgets(self):
        header = tk.Frame(self.root, bg="#1e293b", height=60)
        header.pack(fill="x", side="top")
        
        tk.Label(header, text="⚔️ RPG ENGINE | ANALIZADOR LÉXICO", bg="#1e293b", fg="#f8fafc", 
                 font=self.fuente_titulo).pack(side="left", padx=20, pady=15)

        self.main_container = ttk.Frame(self.root, style="TFrame")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        left_panel = ttk.Frame(self.main_container, style="TFrame")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left_panel, text="EDITOR DE SCRIPT", bg="#0f172a", fg="#38bdf8", font=self.fuente_ui).pack(anchor="w", pady=(0, 5))
        
        self.txt_input = tk.Text(left_panel, font=self.fuente_mono, bg="#1e293b", fg="#e2e8f0", 
                                 insertbackground="white", relief="flat", padx=10, pady=10, borderwidth=0)
        self.txt_input.pack(fill="both", expand=True)
        self.txt_input.insert("1.0", "personaje Guerrero {\n    HP = 100;\n    estado 2Venenos;\n    mision = 'Caceria';\n}")

        right_panel = ttk.Frame(self.main_container, style="TFrame")
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))

        tk.Label(right_panel, text="TOKENS DETECTADOS", bg="#0f172a", fg="#38bdf8", font=self.fuente_ui).pack(anchor="w", pady=(0, 5))

        self.txt_output = tk.Text(right_panel, font=self.fuente_mono, bg="#020617", fg="#10b981", 
                                  state="disabled", relief="flat", padx=10, pady=10)
        self.txt_output.pack(fill="both", expand=True)

        footer = tk.Frame(self.root, bg="#1e293b", height=50)
        footer.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(footer, text="● Sistema listo", bg="#1e293b", fg="#94a3b8", font=self.fuente_ui)
        self.lbl_status.pack(side="left", padx=20)

        self.btn_analizar = tk.Button(footer, text="EJECUTAR ANÁLISIS", command=self.ejecutar, 
                                      bg="#3b82f6", fg="white", font=("Segoe UI", 10, "bold"), 
                                      relief="flat", padx=25, pady=8, cursor="hand2",
                                      activebackground="#2563eb", activeforeground="white")
        self.btn_analizar.pack(side="right", padx=20, pady=10)

    def ejecutar(self):
        codigo = self.txt_input.get("1.0", "end-1c")
        if not codigo.strip(): return

        res = self.analizador.analizar(codigo)
        
        self.txt_output.config(state="normal")
        self.txt_output.delete("1.0", "end")
        
        self.txt_output.insert("end", f"{'TIPO':<20} | {'LEXEMA'}\n")
        self.txt_output.insert("end", "—" * 40 + "\n")

        for item in res["desglose"]:
            tag = item["token"]
            lex = item["lexema"]
            self.txt_output.insert("end", f"{tag:<20} | {lex}\n")

        if res["aprobado"]:
            self.lbl_status.config(text="● ANÁLISIS EXITOSO", fg="#10b981")
            self.btn_analizar.config(bg="#10b981")
        else:
            self.lbl_status.config(text="● ERRORES ENCONTRADOS", fg="#f43f5e")
            self.btn_analizar.config(bg="#f43f5e")

        self.txt_output.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = AppAnalizador(root)
    root.mainloop()
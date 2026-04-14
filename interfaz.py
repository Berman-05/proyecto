import tkinter as tk
from tkinter import ttk, font
from analizador import AnalizadorLexico
from sintactico import AnalizadorSintactico
from arbol import PestanaArbol, construir_arbol_desde_tokens, arbol_a_texto

class LineNumberCanvas(tk.Canvas):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        self.text_widget = None

    def redraw(self):
        self.delete("all")
        if not self.text_widget:
            return
        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(35, y, anchor="ne", text=linenum,
                             fill="#64748b", font=self.text_widget['font'])
            i = self.text_widget.index("%s+1line" % i)

class ToolTip:
    def __init__(self, widget):
        self.widget = widget
        self.tip_window = None

    def show_tip(self, text, x, y):
        if self.tip_window or not text:
            return
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=text, justify="left",
                         background="#1e293b", foreground="#f8fafc",
                         relief="flat", border=1, padx=10, pady=5,
                         font=("Segoe UI", 9))
        label.pack()

    def hide_tip(self):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class AppAnalizador:
    def __init__(self, root):
        self.root = root
        self.analizador = AnalizadorLexico()
        self.sintactico = AnalizadorSintactico()

        self.root.title("RPG Script Lexer Pro")
        self.root.geometry("1100x700")
        self.root.configure(bg="#0f172a")

        self.fuente_mono   = font.Font(family="Consolas",  size=11)
        self.fuente_ui     = font.Font(family="Segoe UI",  size=10)
        self.fuente_titulo = font.Font(family="Segoe UI",  size=14, weight="bold")
        
        self.fuente_arbol_rama = font.Font(family="Segoe UI", size=9, weight="bold")
        self.fuente_arbol_hoja = font.Font(family="Consolas", size=10)

        self.create_widgets()
        self.setup_styles()

    def resaltar_errores(self, event=None):
        self.txt_input.tag_remove("error_subrayado", "1.0", "end")
        self.txt_input.tag_remove("error_sintactico", "1.0", "end")

        codigo = self.txt_input.get("1.0", "end-1c")
        if not codigo.strip():
            return

        res = self.analizador.analizar(codigo)
        self.analizador.ultimo_resultado = res

        for item in res["desglose"]:
            if "rango" in item:
                inicio_abs, fin_abs = item["rango"]
                self.txt_input.tag_add("error_subrayado",
                                    f"1.0 + {inicio_abs} chars",
                                    f"1.0 + {fin_abs} chars")

        errores_sintacticos = self.sintactico.analizar(res["desglose"])

        for err in errores_sintacticos:
            linea = err.get("linea", 1)

            inicio = f"{linea}.0"
            fin = f"{linea}.end"

            self.txt_input.tag_add("error_sintactico", inicio, fin)
    
    def obtener_linea(self, posicion):
        texto = self.txt_input.get("1.0", "end")
        return texto[:posicion].count("\n") + 1

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TFrame",      background="#0f172a")
        self.style.configure("TNotebook",   background="#0f172a", borderwidth=0)
        self.style.configure("TNotebook.Tab",
                        background="#1e293b", foreground="#94a3b8",
                        padding=[14, 6], font=self.fuente_ui)
        self.style.map("TNotebook.Tab",
                  background=[("selected", "#0f172a")],
                  foreground=[("selected", "#38bdf8")])
        self.style.configure("Status.TLabel",
                        background="#1e293b", foreground="#94a3b8",
                        font=self.fuente_ui)
        self.style.configure("Treeview",
                        background="#020617", foreground="#e2e8f0",
                        fieldbackground="#020617", rowheight=25,
                        font=self.fuente_mono) 
        self.style.map("Treeview", background=[('selected', '#3b82f6')])
        self.style.configure("Treeview.Heading",
                        background="#1e293b", foreground="#38bdf8",
                        relief="flat", font=self.fuente_ui)
        self.tabla_tokens.tag_configure("error_lexico",   foreground="#f43f5e")
        self.txt_input.tag_configure("error_subrayado",
                                     foreground="#f43f5e", underline=True)
        self.txt_input.tag_configure("error_sintactico",
                                     foreground="#f43f5e",
                                     underline=True)

    def create_widgets(self):
        header = tk.Frame(self.root, bg="#1e293b", height=60)
        header.pack(fill="x", side="top")
        tk.Label(header,
                 text="⚔️ RPG SCRIPT LEXER | ANALIZADOR LÉXICO",
                 bg="#1e293b", fg="#f8fafc",
                 font=self.fuente_titulo).pack(side="left", padx=20, pady=15)

        frame_fuente = tk.Frame(header, bg="#1e293b")
        frame_fuente.pack(side="right", padx=20, pady=15)
        
        tk.Label(frame_fuente, text="Tamaño:", bg="#1e293b", fg="#94a3b8", 
                 font=self.fuente_ui).pack(side="left", padx=(0, 5))
        
        self.var_tamano_fuente = tk.IntVar(value=self.fuente_mono.cget("size"))
        spin_fuente = tk.Spinbox(frame_fuente, from_=8, to=48, 
                                 textvariable=self.var_tamano_fuente,
                                 width=4, font=self.fuente_ui,
                                 command=self.actualizar_fuente,
                                 bg="#0f172a", fg="#e2e8f0", bd=1, buttonbackground="#1e293b")
        spin_fuente.pack(side="left")
        spin_fuente.bind("<Return>", lambda e: self.actualizar_fuente())

        footer = tk.Frame(self.root, bg="#1e293b", height=50)
        footer.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(footer, text="● Sistema listo",
                                   bg="#1e293b", fg="#94a3b8",
                                   font=self.fuente_ui)
        self.lbl_status.pack(side="left", padx=20)

        self.btn_analizar = tk.Button(footer, text="EJECUTAR ANÁLISIS",
                                      command=self.ejecutar,
                                      bg="#3b82f6", fg="white",
                                      font=("Segoe UI", 10, "bold"),
                                      relief="flat", padx=25, pady=8,
                                      cursor="hand2",
                                      activebackground="#2563eb",
                                      activeforeground="white")
        self.btn_analizar.pack(side="right", padx=20, pady=10)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(14, 0))

        tab_editor = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(tab_editor, text="  Editor & Tokens  ")

        main_paned = ttk.PanedWindow(tab_editor, orient="horizontal")
        main_paned.pack(fill="both", expand=True, pady=14)

        left_panel = ttk.Frame(main_paned, style="TFrame")
        right_panel = ttk.Frame(main_paned, style="TFrame")

        main_paned.add(left_panel, weight=1)
        main_paned.add(right_panel, weight=1)

        tk.Label(left_panel, text="EDITOR DE SCRIPT",
                 bg="#0f172a", fg="#38bdf8",
                 font=self.fuente_ui).pack(anchor="w", pady=(0, 5))

        editor_frame = tk.Frame(left_panel, bg="#1e293b", bd=1, relief="flat")
        editor_frame.pack(fill="both", expand=True, padx=(0, 5))

        self.line_numbers = LineNumberCanvas(editor_frame, width=45,
                                             bg="#1e293b", highlightthickness=0)
        self.line_numbers.pack(side="left", fill="y")

        self.txt_input = tk.Text(editor_frame,
                                 font=self.fuente_mono,
                                 bg="#1e293b", fg="#e2e8f0",
                                 insertbackground="white",
                                 relief="flat", padx=10, pady=10,
                                 borderwidth=0, undo=True)
        self.txt_input.pack(side="left", fill="both", expand=True)

        self.line_numbers.text_widget = self.txt_input
        self.txt_input.bind("<KeyRelease>", lambda e: self.line_numbers.redraw())
        self.txt_input.bind("<MouseWheel>", lambda e: self.line_numbers.redraw())
        self.txt_input.bind("<KeyRelease>", self.resaltar_errores, add="+")
        self.txt_input.bind("<KeyRelease>", self.analizar_en_tiempo_real, add="+")

        tk.Label(right_panel, text="TOKENS DETECTADOS",
                 bg="#0f172a", fg="#38bdf8",
                 font=self.fuente_ui).pack(anchor="w", pady=(0, 5), padx=(5, 0))

        tabla_frame = tk.Frame(right_panel, bg="#020617")
        tabla_frame.pack(fill="both", expand=True, padx=(5, 0))

        columnas = ("token", "lexema")
        self.tabla_tokens = ttk.Treeview(tabla_frame, columns=columnas,
                                         show="headings", style="Treeview")
        self.tabla_tokens.heading("token",  text="TIPO DE TOKEN")
        self.tabla_tokens.heading("lexema", text="LEXEMA ENCONTRADO")
        self.tabla_tokens.column("token",  anchor="w", width=250, stretch=True)
        self.tabla_tokens.column("lexema", anchor="w", width=150, stretch=True)

        scroll_tabla = ttk.Scrollbar(tabla_frame, orient="vertical", command=self.tabla_tokens.yview)
        self.tabla_tokens.configure(yscrollcommand=scroll_tabla.set)
        self.tabla_tokens.pack(side="left", fill="both", expand=True)
        scroll_tabla.pack(side="right", fill="y")

        self.pestana_arbol = PestanaArbol(self.notebook, self.fuente_ui)
        self.notebook.add(self.pestana_arbol.frame, text="  Árbol Sintáctico  ")

        self.root.after(200, self.line_numbers.redraw)

        self.tooltip = ToolTip(self.txt_input)
        self.txt_input.bind("<Motion>", self.verificar_tooltip)

        tab_arbol_texto = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(tab_arbol_texto, text="  Árbol Texto  ")

        self.txt_arbol = tk.Text(tab_arbol_texto,
                                font=("Consolas", 10),
                                bg="#020617", fg="#e2e8f0",
                                relief="flat", padx=10, pady=10)
        self.txt_arbol.pack(fill="both", expand=True, padx=10, pady=10)
        self.txt_arbol.tag_configure("error", foreground="#f43f5e")

        frame_errores = tk.Frame(self.root, bg="#020617", height=120)
        frame_errores.pack(fill="x", padx=20, pady=(0,10))

        tk.Label(frame_errores, text="ERRORES",
                bg="#020617", fg="#f43f5e",
                font=self.fuente_ui).pack(anchor="w")

        cols = ("linea", "tipo", "descripcion")
        self.tabla_errores = ttk.Treeview(frame_errores, columns=cols, show="headings")

        self.tabla_errores.heading("linea", text="Línea")
        self.tabla_errores.heading("tipo", text="Tipo")
        self.tabla_errores.heading("descripcion", text="Descripción")

        self.tabla_errores.pack(fill="x")

    def actualizar_fuente(self):
        try:
            nuevo_tamano = self.var_tamano_fuente.get()
            
            self.fuente_mono.configure(size=nuevo_tamano)
            self.line_numbers.redraw()
            
            tamano_ui = max(9, nuevo_tamano - 1)
            self.fuente_ui.configure(size=tamano_ui)
            
            nueva_altura_fila = int(nuevo_tamano * 1.8) + 5
            self.style.configure("Treeview", rowheight=max(25, nueva_altura_fila))
            
            tamano_rama = max(8, nuevo_tamano - 1)
            self.fuente_arbol_rama.configure(size=tamano_rama)
            self.fuente_arbol_hoja.configure(size=nuevo_tamano)
            self.pestana_arbol.redibujar_con_fuente(self.fuente_arbol_rama, self.fuente_arbol_hoja)
            
        except tk.TclError:
            pass 

    def ejecutar(self):
        codigo = self.txt_input.get("1.0", "end-1c")
        if not codigo.strip():
            return

        res = self.analizador.analizar(codigo)
        errores_sintacticos = self.sintactico.analizar(res["desglose"])

        for item in self.tabla_tokens.get_children():
            self.tabla_tokens.delete(item)

        for item in res["desglose"]:
            token  = item["token"]
            lexema = item["lexema"]
            tag = ("error_lexico",) if "ERROR" in token else ()
            self.tabla_tokens.insert("", "end", values=(token, lexema), tags=tag)

        arbol = construir_arbol_desde_tokens(res)
        self.pestana_arbol.mostrar(arbol, self.fuente_arbol_rama, self.fuente_arbol_hoja)

        if res["aprobado"] and not errores_sintacticos:
            self.lbl_status.config(text="● ANÁLISIS EXITOSO", fg="#10b981")
            self.btn_analizar.config(bg="#10b981")
        else:
            self.lbl_status.config(text="● ERRORES ENCONTRADOS", fg="#f43f5e")
            self.btn_analizar.config(bg="#f43f5e")

        lineas = arbol_a_texto(arbol)

        self.txt_arbol.delete("1.0", "end")

        for texto, es_error in lineas:
            if es_error:
                self.txt_arbol.insert("end", texto + "\n", "error")
            else:
                self.txt_arbol.insert("end", texto + "\n")

        for item in self.tabla_errores.get_children():
            self.tabla_errores.delete(item)

        for item in self.tabla_errores.get_children():
            self.tabla_errores.delete(item)

        for item in res["desglose"]:
            if "ERROR" in item["token"]:
                inicio = item["rango"][0]
                linea = self.obtener_linea(inicio)

                self.tabla_errores.insert("", "end", values=(
                    linea, "LÉXICO", item["mensaje"]
                ))

        for err in errores_sintacticos:
            self.tabla_errores.insert("", "end", values=(
                err["linea"], "SINTÁCTICO", err["mensaje"]
            ))

        
        print("TOKENS:", res["desglose"])
        print("SINTÁCTICOS:", errores_sintacticos)
    
    def verificar_tooltip(self, event):
        index = self.txt_input.index(f"@{event.x},{event.y}")
        tags  = self.txt_input.tag_names(index)

        if "error_subrayado" in tags:
            linea, col = map(int, index.split('.'))
            pos_plana = len(self.txt_input.get("1.0", f"{linea}.0")) + col
            for item in self.analizador.ultimo_resultado.get("desglose", []):
                if "rango" in item:
                    inicio, fin = item["rango"]
                    if inicio <= pos_plana < fin:
                        self.tooltip.show_tip(
                            f"{item['token']}: {item['mensaje']}",
                            event.x, event.y
                        )
                        return
        self.tooltip.hide_tip()
    
    def analizar_en_tiempo_real(self, event=None):
        codigo = self.txt_input.get("1.0", "end-1c")
        if not codigo.strip():
            return

        res = self.analizador.analizar(codigo)
        errores_sintacticos = self.sintactico.analizar(res["desglose"])

        for item in self.tabla_errores.get_children():
            self.tabla_errores.delete(item)

        for item in res["desglose"]:
            if "ERROR" in item["token"]:
                linea = item.get("linea", 1)
                self.tabla_errores.insert("", "end", values=(
                    linea, "LÉXICO", item["mensaje"]
                ))

        for err in errores_sintacticos:
            self.tabla_errores.insert("", "end", values=(
                err["linea"], "SINTÁCTICO", err["mensaje"]
            ))

if __name__ == "__main__":
    root = tk.Tk()
    app  = AppAnalizador(root)
    root.mainloop()
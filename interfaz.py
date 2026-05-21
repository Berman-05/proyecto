import tkinter as tk
from tkinter import ttk, font
from analizador import AnalizadorLexico
from sintactico import AnalizadorSintactico
from arbol import PestanaArbol, construir_arbol_desde_tokens, arbol_a_texto
from semantico import AnalizadorSemantico
from interprete import InterpretadorRPG
from runtime_ascii import AsciiSideScrollerRuntime

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
        self.semantico = AnalizadorSemantico()
        self.interprete = InterpretadorRPG()
        self.visual_runtime = None

        self.root.title("RPG Script Lexer Pro")
        self.root.geometry("1100x750")
        self.root.configure(bg="#0f172a")

        self._tags_arte_creados = set()  # tags de color dinámico ya registrados

        self.fuente_mono   = font.Font(family="Consolas",  size=11)
        self.fuente_ui     = font.Font(family="Segoe UI",  size=10)
        self.fuente_titulo = font.Font(family="Segoe UI",  size=14, weight="bold")
        
        self.fuente_arbol_rama = font.Font(family="Segoe UI", size=9, weight="bold")
        self.fuente_arbol_hoja = font.Font(family="Consolas", size=10)

        self._debounce_id = None
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

        self.resaltar_sintaxis(codigo, res)

        for item in res["desglose"]:
            if "rango" in item and "ERROR" in item["token"]:
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

    def resaltar_sintaxis(self, codigo, res):
        """Aplica resaltado de colores por tipo de token al editor."""
        # Limpiar tags de resaltado previos
        for tag in ("hl_palabra_reservada", "hl_identificador", "hl_numero",
                    "hl_cadena", "hl_operador", "hl_op_comparacion",
                    "hl_simbolo", "hl_comentario"):
            self.txt_input.tag_remove(tag, "1.0", "end")

        # Resaltar comentarios primero (no están en desglose porque se omiten)
        import re as _re
        for m in _re.finditer(r'--.*', codigo):
            self.txt_input.tag_add("hl_comentario",
                                   f"1.0 + {m.start()} chars",
                                   f"1.0 + {m.end()} chars")

        # Mapa de tipo de token → tag de color
        mapa = {
            "PALABRA_RESERVADA":   "hl_palabra_reservada",
            "IDENTIFICADOR":       "hl_identificador",
            "NUMERO":              "hl_numero",
            "CADENA":              "hl_cadena",
            "OPERADOR":            "hl_operador",
            "OPERADOR_COMPARACION":"hl_op_comparacion",
            "SIMBOLO_ESTRUCTURAL": "hl_simbolo",
        }

        for item in res["desglose"]:
            token = item["token"]
            tag = mapa.get(token)
            if not tag or "ERROR" in token:
                continue
            if "rango" not in item:
                continue
            inicio_abs, fin_abs = item["rango"]
            # Para CADENA el lexema fue stripeado de comillas; ajustar al rango original
            self.txt_input.tag_add(tag,
                                   f"1.0 + {inicio_abs} chars",
                                   f"1.0 + {fin_abs} chars")
    
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
        # ── Resaltado de sintaxis (colores por tipo de token) ────────────────
        self.txt_input.tag_configure("hl_palabra_reservada", foreground="#38bdf8",
                                     font=font.Font(family="Consolas", size=self.fuente_mono.cget("size"), weight="bold"))
        self.txt_input.tag_configure("hl_identificador",     foreground="#e2e8f0")
        self.txt_input.tag_configure("hl_numero",            foreground="#fb923c")
        self.txt_input.tag_configure("hl_cadena",            foreground="#4ade80")
        self.txt_input.tag_configure("hl_operador",          foreground="#f472b6")
        self.txt_input.tag_configure("hl_op_comparacion",    foreground="#a78bfa")
        self.txt_input.tag_configure("hl_simbolo",           foreground="#94a3b8")
        self.txt_input.tag_configure("hl_comentario",        foreground="#475569",
                                     font=font.Font(family="Consolas", size=self.fuente_mono.cget("size"), slant="italic"))

    def create_widgets(self):
        # ── HEADER ──────────────────────────────────────────────────────────
        header = tk.Frame(self.root, bg="#1e293b", height=60)
        header.pack(fill="x", side="top")
        tk.Label(header,
                 text="⚔️ RPG SCRIPT COMPILER",
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

        # ── FOOTER ──────────────────────────────────────────────────────────
        footer = tk.Frame(self.root, bg="#1e293b", height=50)
        footer.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(footer, text="● Sistema listo",
                                   bg="#1e293b", fg="#94a3b8",
                                   font=self.fuente_ui)
        self.lbl_status.pack(side="left", padx=20)

        # ── CONTENEDOR PRINCIPAL (notebook + errores redimensionable) ────────
        # Usamos un PanedWindow VERTICAL para que la sección de errores
        # se pueda arrastrar hacia arriba / abajo.
        self.outer_paned = ttk.PanedWindow(self.root, orient="vertical")
        self.outer_paned.pack(fill="both", expand=True, padx=20, pady=(14, 0))

        # Parte superior: notebook con pestañas
        top_frame = ttk.Frame(self.outer_paned, style="TFrame")
        self.outer_paned.add(top_frame, weight=4)

        self.notebook = ttk.Notebook(top_frame)
        self.notebook.pack(fill="both", expand=True)

        # ── TAB: EDITOR & TOKENS ────────────────────────────────────────────
        tab_editor = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(tab_editor, text="  Editor & Tokens  ")

        # PanedWindow HORIZONTAL para editor ↔ tokens (redimensionable)
        main_paned = ttk.PanedWindow(tab_editor, orient="horizontal")
        main_paned.pack(fill="both", expand=True, pady=14)

        left_panel  = ttk.Frame(main_paned, style="TFrame")
        right_panel = ttk.Frame(main_paned, style="TFrame")

        main_paned.add(left_panel,  weight=1)
        main_paned.add(right_panel, weight=1)

        # — Panel izquierdo: editor de script —
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
        self.txt_input.bind("<KeyRelease>", self._programar_analisis, add="+")

        # — Panel derecho: tabla de tokens —
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

        # ── TAB: ÁRBOL SINTÁCTICO ────────────────────────────────────────────
        self.pestana_arbol = PestanaArbol(self.notebook, self.fuente_ui)
        self.notebook.add(self.pestana_arbol.frame, text="  Árbol Sintáctico  ")

        # ── TAB: ÁRBOL TEXTO ─────────────────────────────────────────────────
        tab_arbol_texto = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(tab_arbol_texto, text="  Árbol Texto  ")

        self.txt_arbol = tk.Text(tab_arbol_texto,
                                font=self.fuente_mono,
                                bg="#020617", fg="#e2e8f0",
                                relief="flat", padx=10, pady=10)
        self.txt_arbol.pack(fill="both", expand=True, padx=10, pady=10)
        self.txt_arbol.tag_configure("error", foreground="#f43f5e")

        # ── TAB: TABLA DE SÍMBOLOS ───────────────────────────────────────────
        tab_simbolos = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(tab_simbolos, text="  Tabla de Símbolos  ")

        cols = ("identificador", "categoria", "atributo", "valor", "tipo")
        self.tabla_simbolos = ttk.Treeview(tab_simbolos, columns=cols, show="headings")
        self.tabla_simbolos.heading("identificador", text="IDENTIFICADOR")
        self.tabla_simbolos.heading("categoria",     text="CATEGORÍA")
        self.tabla_simbolos.heading("atributo",      text="ATRIBUTO")
        self.tabla_simbolos.heading("valor",         text="VALOR")
        self.tabla_simbolos.heading("tipo",          text="TIPO")
        self.tabla_simbolos.column("identificador", width=120, stretch=False)
        self.tabla_simbolos.column("categoria",     width=130, stretch=False)
        self.tabla_simbolos.column("atributo",      width=110, stretch=False)
        self.tabla_simbolos.column("valor",         width=220, stretch=True)
        self.tabla_simbolos.column("tipo",          width=80,  stretch=False)
        self.tabla_simbolos.pack(fill="both", expand=True, padx=10, pady=10)

        # ── TAB: SALIDA / EJECUCIÓN ──────────────────────────────────────────
        tab_salida = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(tab_salida, text="  🎮 Salida  ")

        top_salida = tk.Frame(tab_salida, bg="#1e293b", height=36)
        top_salida.pack(fill="x")
        tk.Label(top_salida, text="SALIDA DE EJECUCIÓN RPG",
                 bg="#1e293b", fg="#4ade80",
                 font=self.fuente_ui).pack(side="left", padx=14, pady=8)
        tk.Button(top_salida,
                  text="Abrir mundo 2D",
                  command=self.abrir_mundo_ascii,
                  bg="#0f766e", fg="#f8fafc",
                  activebackground="#115e59", activeforeground="#f8fafc",
                  relief="flat", padx=12, pady=4,
                  font=self.fuente_ui).pack(side="right", padx=14, pady=5)

        salida_wrap = tk.Frame(tab_salida, bg="#020617")
        salida_wrap.pack(fill="both", expand=True, padx=10, pady=10)

        self.txt_salida = tk.Text(
            salida_wrap,
            font=font.Font(family="Consolas", size=11),
            bg="#020617", fg="#e2e8f0",
            relief="flat", padx=14, pady=10,
            state="disabled", borderwidth=0,
            wrap="word"
        )
        scroll_salida = ttk.Scrollbar(salida_wrap, orient="vertical",
                                      command=self.txt_salida.yview)
        self.txt_salida.configure(yscrollcommand=scroll_salida.set)
        self.txt_salida.pack(side="left", fill="both", expand=True)
        scroll_salida.pack(side="right", fill="y")

        # Tags de color para la salida del intérprete
        self.txt_salida.tag_configure("titulo_principal", foreground="#facc15",
                                      font=font.Font(family="Segoe UI", size=12, weight="bold"))
        self.txt_salida.tag_configure("cabecera_personaje", foreground="#38bdf8",
                                      font=font.Font(family="Segoe UI", size=11, weight="bold"))
        self.txt_salida.tag_configure("cabecera_habilidad", foreground="#fb923c",
                                      font=font.Font(family="Segoe UI", size=11, weight="bold"))
        self.txt_salida.tag_configure("cabecera_estado",    foreground="#a78bfa",
                                      font=font.Font(family="Segoe UI", size=11, weight="bold"))
        self.txt_salida.tag_configure("cabecera_objeto",    foreground="#4ade80",
                                      font=font.Font(family="Segoe UI", size=11, weight="bold"))
        self.txt_salida.tag_configure("cabecera_mision",    foreground="#facc15",
                                      font=font.Font(family="Segoe UI", size=11, weight="bold"))
        self.txt_salida.tag_configure("cabecera_combate",   foreground="#f43f5e",
                                      font=font.Font(family="Segoe UI", size=11, weight="bold"))
        self.txt_salida.tag_configure("cabecera_accion",    foreground="#67e8f9",
                                      font=font.Font(family="Segoe UI", size=11, weight="bold"))
        self.txt_salida.tag_configure("cabecera_comprobar", foreground="#fbbf24",
                                      font=font.Font(family="Segoe UI", size=11, weight="bold"))
        self.txt_salida.tag_configure("cabecera",           foreground="#e2e8f0",
                                      font=font.Font(family="Segoe UI", size=11, weight="bold"))
        # Arte y clase
        self.txt_salida.tag_configure("arte",         foreground="#38bdf8",
                                      font=font.Font(family="Consolas", size=11))
        self.txt_salida.tag_configure("nombre_personaje", foreground="#facc15",
                                      font=font.Font(family="Consolas", size=11, weight="bold"))
        self.txt_salida.tag_configure("clase_titulo", foreground="#e2e8f0",
                                      font=font.Font(family="Segoe UI", size=10, weight="bold"))
        self.txt_salida.tag_configure("clase_desc",   foreground="#94a3b8",
                                      font=font.Font(family="Segoe UI", size=9, slant="italic"))
        # HP / MP / XP
        self.txt_salida.tag_configure("barra_hp",      foreground="#f43f5e",
                                      font=font.Font(family="Consolas", size=11))
        self.txt_salida.tag_configure("barra_hp_dano", foreground="#fb923c",
                                      font=font.Font(family="Consolas", size=11))
        self.txt_salida.tag_configure("barra_hp_cero", foreground="#7f1d1d",
                                      font=font.Font(family="Consolas", size=11))
        self.txt_salida.tag_configure("barra_mp",      foreground="#818cf8",
                                      font=font.Font(family="Consolas", size=11))
        self.txt_salida.tag_configure("barra_xp",      foreground="#fbbf24",
                                      font=font.Font(family="Consolas", size=11))
        # Acciones
        self.txt_salida.tag_configure("accion_tipo",    foreground="#67e8f9",
                                      font=font.Font(family="Segoe UI", size=10, weight="bold"))
        self.txt_salida.tag_configure("accion_prop",    foreground="#94a3b8",
                                      font=font.Font(family="Segoe UI", size=10))
        self.txt_salida.tag_configure("accion_dano",    foreground="#f43f5e",
                                      font=font.Font(family="Segoe UI", size=10, weight="bold"))
        self.txt_salida.tag_configure("accion_pasos",   foreground="#4ade80",
                                      font=font.Font(family="Consolas", size=10))
        self.txt_salida.tag_configure("accion_mensaje", foreground="#fbbf24",
                                      font=font.Font(family="Segoe UI", size=10))
        self.txt_salida.tag_configure("golpe_anim",     foreground="#f43f5e",
                                      font=font.Font(family="Consolas", size=11, weight="bold"))
        self.txt_salida.tag_configure("bocadillo",      foreground="#a78bfa",
                                      font=font.Font(family="Consolas", size=10))
        # Estados y daño
        self.txt_salida.tag_configure("estado_efecto",  foreground="#a78bfa",
                                      font=font.Font(family="Segoe UI", size=10))
        self.txt_salida.tag_configure("habilidad_dano", foreground="#fb923c",
                                      font=font.Font(family="Consolas", size=10))
        self.txt_salida.tag_configure("derrota",        foreground="#7f1d1d",
                                      font=font.Font(family="Segoe UI", size=10, weight="bold"))
        self.txt_salida.tag_configure("dano_historial", foreground="#fb923c",
                                      font=font.Font(family="Consolas", size=10))
        # Props específicas
        self.txt_salida.tag_configure("objeto_prop",   foreground="#4ade80")
        self.txt_salida.tag_configure("mision_prop",   foreground="#facc15")
        self.txt_salida.tag_configure("combate_prop",  foreground="#f43f5e")
        # Generales
        self.txt_salida.tag_configure("ok",          foreground="#4ade80")
        self.txt_salida.tag_configure("prop",        foreground="#94a3b8")
        self.txt_salida.tag_configure("info",        foreground="#64748b")
        self.txt_salida.tag_configure("advertencia", foreground="#fb923c")
        self.txt_salida.tag_configure("condicion",   foreground="#67e8f9")
        self.txt_salida.tag_configure("sep",         foreground="#1e293b")
        self.txt_salida.tag_configure("sep_bloque",  foreground="#334155")
        self.txt_salida.tag_configure("error_ejec",  foreground="#f43f5e")
        bottom_frame = ttk.Frame(self.outer_paned, style="TFrame")
        self.outer_paned.add(bottom_frame, weight=1)

        # Etiqueta de sección errores con handle visual de redimensión
        errores_header = tk.Frame(bottom_frame, bg="#020617")
        errores_header.pack(fill="x")

        # Grip visual para indicar que se puede redimensionar
        tk.Label(errores_header, text="▲▼  ERRORES",
                 bg="#020617", fg="#f43f5e",
                 font=self.fuente_ui, cursor="sb_v_double_arrow"
                 ).pack(side="left", anchor="w", padx=6, pady=(4, 2))

        # Scrollbar + tabla de errores
        errores_tabla_frame = tk.Frame(bottom_frame, bg="#020617")
        errores_tabla_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        cols_err = ("linea", "tipo", "descripcion")
        self.tabla_errores = ttk.Treeview(errores_tabla_frame, columns=cols_err, show="headings")
        self.tabla_errores.heading("linea",       text="Línea")
        self.tabla_errores.heading("tipo",        text="Tipo")
        self.tabla_errores.heading("descripcion", text="Descripción")
        self.tabla_errores.column("linea",       width=60,  stretch=False)
        self.tabla_errores.column("tipo",        width=110, stretch=False)
        self.tabla_errores.column("descripcion", width=600, stretch=True)

        scroll_err = ttk.Scrollbar(errores_tabla_frame, orient="vertical",
                                   command=self.tabla_errores.yview)
        self.tabla_errores.configure(yscrollcommand=scroll_err.set)
        self.tabla_errores.pack(side="left", fill="both", expand=True)
        scroll_err.pack(side="right", fill="y")

        # ── TOOLTIPS & LINE NUMBERS ──────────────────────────────────────────
        self.root.after(200, self.line_numbers.redraw)

        self.tooltip = ToolTip(self.txt_input)
        self.txt_input.bind("<Motion>", self.verificar_tooltip)

    def actualizar_fuente(self):
        try:
            nuevo_tamano = self.var_tamano_fuente.get()
            self.fuente_mono.configure(size=nuevo_tamano)
            self.txt_arbol.config(font=self.fuente_mono)
            self.line_numbers.redraw()
            
            tamano_ui = max(9, nuevo_tamano - 1)
            self.fuente_ui.configure(size=tamano_ui)
            
            nueva_altura_fila = int(nuevo_tamano * 1.8) + 5
            self.style.configure("Treeview", rowheight=max(25, nueva_altura_fila))
            
            tamano_rama = max(8, nuevo_tamano - 1)
            self.fuente_arbol_rama.configure(size=tamano_rama)
            self.fuente_arbol_hoja.configure(size=nuevo_tamano)
            self.pestana_arbol.redibujar_con_fuente(self.fuente_arbol_rama, self.fuente_arbol_hoja)

            # Actualizar fuentes de tags de resaltado de sintaxis
            self.txt_input.tag_configure("hl_palabra_reservada",
                font=font.Font(family="Consolas", size=nuevo_tamano, weight="bold"))
            self.txt_input.tag_configure("hl_comentario",
                font=font.Font(family="Consolas", size=nuevo_tamano, slant="italic"))
        except tk.TclError:
            pass

    def _programar_analisis(self, event=None):
        if self._debounce_id is not None:
            self.root.after_cancel(self._debounce_id)
        self._debounce_id = self.root.after(300, self.ejecutar)

    def ejecutar(self):
        self._debounce_id = None
        codigo = self.txt_input.get("1.0", "end-1c")

        if not codigo.strip():
            for item in self.tabla_tokens.get_children():
                self.tabla_tokens.delete(item)
            for item in self.tabla_errores.get_children():
                self.tabla_errores.delete(item)
            self.tabla_simbolos.delete(*self.tabla_simbolos.get_children())
            self.txt_arbol.delete("1.0", "end")
            self.txt_salida.configure(state="normal")
            self.txt_salida.delete("1.0", "end")
            self.txt_salida.configure(state="disabled")
            self.lbl_status.config(text="● Sistema listo", fg="#94a3b8")
            return

        res = self.analizador.analizar(codigo)
        errores_sintacticos = self.sintactico.analizar(res["desglose"])
        errores_semanticos = self.semantico.analizar(res["desglose"])

        for item in self.tabla_tokens.get_children():
            self.tabla_tokens.delete(item)
        for item in res["desglose"]:
            token  = item["token"]
            lexema = item["lexema"]
            tag = ("error_lexico",) if "ERROR" in token else ()
            self.tabla_tokens.insert("", "end", values=(token, lexema), tags=tag)

        arbol = construir_arbol_desde_tokens(res)
        self.pestana_arbol.mostrar(arbol, self.fuente_arbol_rama, self.fuente_arbol_hoja)

        if res["aprobado"] and not errores_sintacticos and not errores_semanticos:
            self.lbl_status.config(text="● ANÁLISIS EXITOSO", fg="#10b981")
        else:
            self.lbl_status.config(text="● ERRORES ENCONTRADOS (ANÁLISIS DETENIDO)", fg="#f43f5e")

        lineas = arbol_a_texto(arbol)
        self.txt_arbol.delete("1.0", "end")
        for texto, es_error in lineas:
            if es_error:
                self.txt_arbol.insert("end", texto + "\n", "error")
            else:
                self.txt_arbol.insert("end", texto + "\n")

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

        for err in errores_semanticos:
            self.tabla_errores.insert("", "end", values=(
                err["linea"], "SEMÁNTICO", f"{err.get('codigo','')}: {err['mensaje']}"
            ))

        self.tabla_simbolos.delete(*self.tabla_simbolos.get_children())
        for nombre, datos in self.semantico.tabla_simbolos.items():
            categoria = datos["categoria"]

            if categoria == "variable_global":
                slot = datos["valor"].get("_val")
                if slot:
                    self.tabla_simbolos.insert("", "end", values=(
                        nombre, "variable_global", "-", slot["valor"], slot["tipo"]
                    ))

            elif categoria == "personaje":
                hp_actual = datos.get("HP_actual")

                for atributo, info in datos["valor"].items():
                    if atributo == "HP" and hp_actual is not None:
                        tag = "hp_danado" if hp_actual < info["valor"] else ""
                        self.tabla_simbolos.insert("", "end", values=(
                            nombre, categoria, "HP", hp_actual, "int"
                        ), tags=(tag,) if tag else ())
                    else:
                        self.tabla_simbolos.insert("", "end", values=(
                            nombre, categoria, atributo, info["valor"], info["tipo"]
                        ))

            else:
                for atributo, info in datos["valor"].items():
                    self.tabla_simbolos.insert("", "end", values=(
                        nombre, categoria, atributo, info["valor"], info["tipo"]
                    ))

        # Color para HP dañado
        self.tabla_simbolos.tag_configure("hp_danado", foreground="#fb923c")

        # ── Actualizar pestaña Salida ────────────────────────────────────
        self.txt_salida.configure(state="normal")
        self.txt_salida.delete("1.0", "end")
        self._tags_arte_creados.clear()

        hay_errores = (not res["aprobado"]) or errores_sintacticos or errores_semanticos

        if hay_errores:
            self.txt_salida.insert("end", "⛔  Ejecución detenida por errores.\n\n", "error_ejec")
            self.txt_salida.insert("end", "  Corrige los errores marcados en el editor\n", "info")
            self.txt_salida.insert("end", "  para ver la salida de ejecución.\n", "info")
        else:
            lineas_salida = self.interprete.interpretar(
                self.semantico.tabla_simbolos,
                res["desglose"]
            )
            for item in lineas_salida:
                tipo  = item["tipo"]
                texto = item["texto"] + "\n"
                color = item.get("color")

                if tipo == "cabecera":
                    cat = item.get("categoria", "")
                    tag = f"cabecera_{cat}" if cat else "cabecera"
                elif tipo == "arte" and color:
                    # Arte con color dinámico por clase — crear tag ad-hoc
                    tag_dyn = f"arte_{color.replace('#','')}"
                    if tag_dyn not in self._tags_arte_creados:
                        self.txt_salida.tag_configure(
                            tag_dyn,
                            foreground=color,
                            font=font.Font(family="Consolas", size=11)
                        )
                        self._tags_arte_creados.add(tag_dyn)
                    tag = tag_dyn
                elif tipo == "clase_titulo" and color:
                    tag_dyn = f"clase_titulo_{color.replace('#','')}"
                    if tag_dyn not in self._tags_arte_creados:
                        self.txt_salida.tag_configure(
                            tag_dyn,
                            foreground=color,
                            font=font.Font(family="Segoe UI", size=10, weight="bold")
                        )
                        self._tags_arte_creados.add(tag_dyn)
                    tag = tag_dyn
                elif tipo == "accion_prop" and color:
                    tag_dyn = f"accion_prop_{color.replace('#','')}"
                    if tag_dyn not in self._tags_arte_creados:
                        self.txt_salida.tag_configure(
                            tag_dyn,
                            foreground=color,
                            font=font.Font(family="Segoe UI", size=10)
                        )
                        self._tags_arte_creados.add(tag_dyn)
                    tag = tag_dyn
                else:
                    tag = tipo

                self.txt_salida.insert("end", texto, tag)

        self.txt_salida.configure(state="disabled")

    def abrir_mundo_ascii(self):
        codigo = self.txt_input.get("1.0", "end-1c")
        if not codigo.strip():
            self.lbl_status.config(text="● No hay script para visualizar", fg="#fb923c")
            return

        res = self.analizador.analizar(codigo)
        errores_sintacticos = self.sintactico.analizar(res["desglose"])
        errores_semanticos = self.semantico.analizar(res["desglose"])

        if (not res["aprobado"]) or errores_sintacticos or errores_semanticos:
            self.lbl_status.config(text="● Corrige errores antes de abrir el mundo 2D", fg="#f43f5e")
            return

        if self.visual_runtime is not None and self.visual_runtime.running:
            self.visual_runtime.stop()

        self.visual_runtime = AsciiSideScrollerRuntime.from_symbol_table(
            self.semantico.tabla_simbolos,
            res["desglose"],
            master=self.root,
        )

        # Hook directo: el interprete ejecuta acciones sobre el runtime visual.
        self.interprete.set_visual_runtime(self.visual_runtime)
        self.interprete.interpretar(self.semantico.tabla_simbolos, res["desglose"])
        self.interprete.set_visual_runtime(None)

        self.visual_runtime.start()
        self.lbl_status.config(text="● Mundo ASCII 2D ejecutándose", fg="#10b981")
    
    def verificar_tooltip(self, event):
        index = self.txt_input.index(f"@{event.x},{event.y}")
        tags  = self.txt_input.tag_names(index)

        if "error_subrayado" in tags:
            linea, col = map(int, index.split('.'))
            pos_plana = len(self.txt_input.get("1.0", f"{linea}.0")) + col
            if not hasattr(self.analizador, "ultimo_resultado"):
                return
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


if __name__ == "__main__":
    root = tk.Tk()
    app  = AppAnalizador(root)
    root.mainloop()

import tkinter as tk
from tkinter import ttk, font

class ToolTipArbol:
    def __init__(self, canvas):
        self.canvas = canvas
        self.tip_window = None
        

    def show_tip(self, text, x, y):
        if self.tip_window or not text:
            return
        x += self.canvas.winfo_rootx() + 20
        y += self.canvas.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.canvas)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=text, justify="left",
                         background="#f43f5e", foreground="#f8fafc",
                         relief="flat", border=1, padx=10, pady=5,
                         font=("Segoe UI", 9, "bold"))
        label.pack()

    def hide_tip(self):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class NodoArbol:
    def __init__(self, data):
        if isinstance(data, dict):
            self.etiqueta = data["lexema"]
            self.es_error = "ERROR" in data["token"]
            self.mensaje  = data.get("mensaje", "Error detectado")
        else:
            self.etiqueta = str(data)
            self.es_error = False
            self.mensaje  = ""
            
        self.hijos    = []
        self._x = 0
        self._y = 0
        self._w = 0

    def agregar_hijo(self, nodo):
        self.hijos.append(nodo)
        return nodo

    @property
    def es_hoja(self):
        return len(self.hijos) == 0

def construir_arbol_desde_tokens(resultado):
    tokens_raw = resultado.get("desglose", [])
    raiz = NodoArbol("Programa")
    tiene_llaves = any(t["lexema"] == "{" for t in tokens_raw)

    if tiene_llaves:
        _parsear_con_bloques(tokens_raw, raiz)
    else:
        _parsear_plano(tokens_raw, raiz)

    if not raiz.hijos:
        for tok in tokens_raw:
            raiz.agregar_hijo(NodoArbol(tok))
    return raiz

def _parsear_con_bloques(tokens, raiz):
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok["token"] == "PALABRA_RESERVADA":
            j = i + 1
            while j < n and tokens[j]["lexema"] not in ("{", "}"):
                j += 1
            hay_bloque = j < n and tokens[j]["lexema"] == "{"

            if hay_bloque:
                nodo_bloque = NodoArbol(tok)
                raiz.agregar_hijo(nodo_bloque)
                i += 1
                while i < n and tokens[i]["lexema"] != "{":
                    nodo_bloque.agregar_hijo(NodoArbol(tokens[i]))
                    i += 1
                i += 1  
                while i < n and tokens[i]["lexema"] != "}":
                    grupo = []
                    while i < n and tokens[i]["lexema"] not in (";", "}"):
                        grupo.append(tokens[i])
                        i += 1
                    if i < n and tokens[i]["lexema"] == ";":
                        i += 1  
                    if grupo:
                        _agregar_grupo(nodo_bloque, grupo)
                if i < n and tokens[i]["lexema"] == "}":
                    i += 1  
            else:
                raiz.agregar_hijo(NodoArbol(tok))
                i += 1
        else:
            if "ERROR" in tok["token"]:
                raiz.agregar_hijo(NodoArbol(tok))
            i += 1

def _parsear_plano(tokens, raiz):
    grupo = []
    for tok in tokens:
        if tok["lexema"] == ";":
            if grupo:
                _agregar_grupo(raiz, grupo)
                grupo = []
        else:
            grupo.append(tok)
    if grupo:
        _agregar_grupo(raiz, grupo)

def _agregar_grupo(padre, grupo):
    if not grupo:
        return
    nodo = NodoArbol(grupo[0])
    padre.agregar_hijo(nodo)
    nodo_actual = nodo
    for tok in grupo[1:]:
        hijo = NodoArbol(tok)
        nodo_actual.agregar_hijo(hijo)
        nodo_actual = hijo

RADIO      = 24
H_GAP      = 22
V_GAP      = 72
HOJA_PAD_X = 10

def _calc_ancho(nodo, fuente):
    if nodo.es_hoja:
        tw = fuente.measure(nodo.etiqueta) + HOJA_PAD_X * 2
        nodo._w = max(tw, RADIO * 2)
    else:
        for h in nodo.hijos:
            _calc_ancho(h, fuente)
        total = sum(h._w for h in nodo.hijos) + H_GAP * (len(nodo.hijos) - 1)
        nodo._w = max(RADIO * 2 + 8, total)

def _calc_pos(nodo, x, y):
    nodo._x = x
    nodo._y = y
    if nodo.es_hoja:
        return
    cx = x - nodo._w / 2
    for hijo in nodo.hijos:
        _calc_pos(hijo, cx + hijo._w / 2, y + V_GAP)
        cx += hijo._w + H_GAP

def _bounds(nodo):
    min_x = nodo._x - nodo._w / 2
    max_x = nodo._x + nodo._w / 2
    max_y = nodo._y + RADIO + (20 if nodo.es_hoja else 0)
    for h in nodo.hijos:
        b = _bounds(h)
        min_x = min(min_x, b[0])
        max_x = max(max_x, b[1])
        max_y = max(max_y, b[2])
    return min_x, max_x, max_y

def _shift_x(nodo, dx):
    nodo._x += dx
    for h in nodo.hijos:
        _shift_x(h, dx)

def calcular_layout(raiz, fuente, pad=40):
    _calc_ancho(raiz, fuente)
    _calc_pos(raiz, raiz._w / 2 + pad, RADIO + pad)
    min_x, max_x, max_y = _bounds(raiz)
    if min_x < pad:
        _shift_x(raiz, pad - min_x)
        min_x, max_x, max_y = _bounds(raiz)
    return int(max_x + pad + 10), int(max_y + pad + 20)

COLOR_RAIZ_FILL  = "#1e3a5f"
COLOR_RAIZ_BORDE = "#378ADD"
COLOR_RAIZ_TEXTO = "#ffffff"
COLOR_RAMA_FILL  = "#1e293b"
COLOR_RAMA_BORDE = "#38bdf8"
COLOR_RAMA_TEXTO = "#e2e8f0"
COLOR_HOJA_TEXTO = "#e2e8f0"
COLOR_HOJA_LINEA = "#38bdf8"
COLOR_ARISTA     = "#475569"
COLOR_ERROR      = "#f43f5e"

def _dibujar_aristas(canvas, nodo):
    for hijo in nodo.hijos:
        x1, y1 = nodo._x, nodo._y + RADIO
        x2 = hijo._x
        y2 = hijo._y if hijo.es_hoja else hijo._y - RADIO
        canvas.create_line(x1, y1, x2, y2, fill=COLOR_ARISTA, width=1.5)
        _dibujar_aristas(canvas, hijo)

def _dibujar_nodos(canvas, nodo, fuente_rama, fuente_hoja, es_raiz=False):
    tag_nodo = f"nodo_{id(nodo)}"
    
    if nodo.es_error:
        if not hasattr(canvas, "error_msgs"):
            canvas.error_msgs = {}
        canvas.error_msgs[tag_nodo] = nodo.mensaje
        tag_tupla = (tag_nodo, "hover_error")
    else:
        tag_tupla = (tag_nodo,)

    if nodo.es_hoja:
        x, y = nodo._x, nodo._y
        color_texto = COLOR_ERROR if nodo.es_error else COLOR_HOJA_TEXTO
        color_linea = COLOR_ERROR if nodo.es_error else COLOR_HOJA_LINEA
        
        canvas.create_text(x, y + 6, text=nodo.etiqueta,
                           fill=color_texto, font=fuente_hoja, anchor="n", tags=tag_tupla)
        tw = fuente_hoja.measure(nodo.etiqueta)
        ly = y + fuente_hoja.metrics("linespace") + 8
        canvas.create_line(x - tw/2 - 2, ly, x + tw/2 + 2, ly,
                           fill=color_linea, width=2, tags=tag_tupla)
    else:
        fill  = COLOR_RAIZ_FILL  if es_raiz else COLOR_RAMA_FILL
        borde = COLOR_ERROR if nodo.es_error else (COLOR_RAIZ_BORDE if es_raiz else COLOR_RAMA_BORDE)
        texto = COLOR_ERROR if nodo.es_error else (COLOR_RAIZ_TEXTO if es_raiz else COLOR_RAMA_TEXTO)
        
        canvas.create_oval(nodo._x - RADIO, nodo._y - RADIO,
                           nodo._x + RADIO, nodo._y + RADIO,
                           fill=fill, outline=borde, width=2, tags=tag_tupla)
        canvas.create_text(nodo._x, nodo._y, text=nodo.etiqueta,
                           fill=texto, font=fuente_rama, anchor="center", tags=tag_tupla)

    for hijo in nodo.hijos:
        _dibujar_nodos(canvas, hijo, fuente_rama, fuente_hoja, es_raiz=False)

def dibujar_arbol(canvas, raiz, fuente_rama, fuente_hoja):
    canvas.delete("all")
    canvas.error_msgs = {}
    ancho, alto = calcular_layout(raiz, fuente_hoja)
    canvas.config(scrollregion=(0, 0, ancho, alto))
    _dibujar_aristas(canvas, raiz)
    _dibujar_nodos(canvas, raiz, fuente_rama, fuente_hoja, es_raiz=True)

def arbol_a_texto(nodo, prefijo="", es_ultimo=True):
    lineas = []

    conector = "└── " if es_ultimo else "├── "
    lineas.append(prefijo + conector + nodo.etiqueta)

    nuevo_prefijo = prefijo + ("    " if es_ultimo else "│   ")

    for i, hijo in enumerate(nodo.hijos):
        es_ult = (i == len(nodo.hijos) - 1)
        lineas.extend(arbol_a_texto(hijo, nuevo_prefijo, es_ult))

    return lineas

class PestanaArbol:
    def __init__(self, parent, fuente_ui):
        self.frame = tk.Frame(parent, bg="#0f172a")
        self.raiz_actual = None 

        top = tk.Frame(self.frame, bg="#1e293b", height=36)
        top.pack(fill="x")
        
        self._lbl_titulo = tk.Label(top, text="ÁRBOL SINTÁCTICO",
                                    bg="#1e293b", fg="#38bdf8", font=fuente_ui)
        self._lbl_titulo.pack(side="left", padx=14, pady=8)
        
        self._lbl_info = tk.Label(top, text="", bg="#1e293b", fg="#64748b", font=fuente_ui)
        self._lbl_info.pack(side="right", padx=14)

        wrap = tk.Frame(self.frame, bg="#020617")
        wrap.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(wrap, bg="#020617", highlightthickness=0, scrollregion=(0, 0, 800, 600))
        sb_v = ttk.Scrollbar(wrap, orient="vertical",   command=self.canvas.yview)
        sb_h = ttk.Scrollbar(wrap, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        sb_v.pack(side="right",  fill="y")
        sb_h.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1*(e.delta//120), "units"))
        self.canvas.bind("<Shift-MouseWheel>", lambda e: self.canvas.xview_scroll(-1*(e.delta//120), "units"))

        self.canvas.create_text(300, 200, text="Ejecuta el análisis para ver el árbol",
                                fill="#334155", font=("Segoe UI", 13))

        self.tooltip = ToolTipArbol(self.canvas)
        self.canvas.bind("<Motion>", self.verificar_tooltip)

    def verificar_tooltip(self, event):
        item = self.canvas.find_withtag("current")
        if item:
            tags = self.canvas.gettags(item[0])
            for tag in tags:
                if tag.startswith("nodo_") and tag in getattr(self.canvas, "error_msgs", {}):
                    self.tooltip.show_tip(self.canvas.error_msgs[tag], event.x, event.y)
                    return
        self.tooltip.hide_tip()

    def mostrar(self, raiz, fuente_rama, fuente_hoja):
        self.raiz_actual = raiz
        dibujar_arbol(self.canvas, raiz, fuente_rama, fuente_hoja)
        n = self._contar(raiz)
        self._lbl_info.config(text=f"{n} nodos")
        
    def redibujar_con_fuente(self, fuente_rama, fuente_hoja):
        if self.raiz_actual:
             dibujar_arbol(self.canvas, self.raiz_actual, fuente_rama, fuente_hoja)

    def _contar(self, nodo):
        return 1 + sum(self._contar(h) for h in nodo.hijos)
    
    
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import difflib
import datetime
import os
import tiktoken
import re

class ComparadorOffline:
    def __init__(self, root):
        self.root = root
        self.root.title("Comparador de código - Offline Pro")
        self.root.geometry("1400x900")
        self.root.configure(bg="#f0f0f0")
        
        # Inicializar estilos para scrollbars personalizados
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Variables de estado
        self.texto_puro_orig = ""
        self.texto_puro_mod = ""
        self.respaldo_orig = "" # Para deshacer asimilación
        self.respaldo_mod = ""  # Para deshacer asimilación (mod)
        self.modo_oscuro = False
        
        self.ruta_docs = os.path.join(os.path.expanduser("~"), "Documents", "comparacodigoWeB")
        if not os.path.exists(self.ruta_docs):
            os.makedirs(self.ruta_docs)

        self.archivos_historial = []
        self.indice_historial = -1
        self.modo_edicion = True
        self.solo_modificaciones = False
        
        # Variables para asimilación selectiva
        self.decisiones_diff = {}
        self.lista_diff_crudo = []
        
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except:
            self.encoding = None

        self.setup_ui()
        self.root.update()
        ancho_total = self.paned_h.winfo_width()
        self.paned_h.sash_place(0, ancho_total // 2, 0)

    def setup_ui(self):
        # --- Barra Superior ---
        frame_top = tk.Frame(self.root, bg="#f0f0f0")
        frame_top.pack(fill=tk.X, padx=10, pady=10)
        
        frame_izq = tk.Frame(frame_top, bg="#f0f0f0")
        frame_izq.pack(side=tk.LEFT)
        
        # Inversión inicial: Negro en modo claro
        self.btn_tema = tk.Button(frame_izq, text="Modo Oscuro", bg="black", fg="white", command=self.toggle_tema)
        self.btn_tema.pack(side=tk.LEFT, padx=5)

        tk.Label(frame_izq, text="Proyecto:", font=("Arial", 9, "bold"), bg="#f0f0f0").pack(side=tk.LEFT)
        self.entry_proyecto = tk.Entry(frame_izq, font=("Arial", 10), width=15)
        self.entry_proyecto.pack(side=tk.LEFT, padx=5)
        self.entry_proyecto.insert(0, "Proyecto_1")

        self.btn_ant = tk.Button(frame_izq, text=" < ", command=self.anterior_historial)
        self.btn_ant.pack(side=tk.LEFT, padx=1)
        self.btn_historial = tk.Button(frame_izq, text="Historial", bg="#6c757d", fg="white", command=self.menu_proyectos_historial)
        self.btn_historial.pack(side=tk.LEFT, padx=1)
        self.btn_sig = tk.Button(frame_izq, text=" > ", command=self.siguiente_historial)
        self.btn_sig.pack(side=tk.LEFT, padx=1)

        frame_der = tk.Frame(frame_top, bg="#f0f0f0")
        frame_der.pack(side=tk.RIGHT)

        self.btn_asimilar = tk.Button(frame_der, text="Asimilar Modificado", bg="#28a745", fg="white", font=("Arial", 9, "bold"), 
                                      command=self.accion_asimilar, state='disabled')
        self.btn_asimilar.pack(side=tk.RIGHT, padx=5)

        self.btn_comparar = tk.Button(frame_der, text="Comparar y Guardar", bg="#007bff", fg="white", font=("Arial", 9, "bold"), 
                                  command=self.ejecutar_comparacion)
        self.btn_comparar.pack(side=tk.RIGHT, padx=5)

        self.btn_toggle = tk.Button(frame_der, text="Cambiar a Edición", bg="#17a2b8", fg="white", command=self.toggle_modo)
        
        # Botón para borrar cajas de texto
        self.btn_borrar = tk.Button(frame_der, text="Borrar Todo", bg="#dc3545", fg="white", font=("Arial", 9, "bold"), command=self.borrar_todo)
        self.btn_borrar.pack(side=tk.RIGHT, padx=5)

        frame_centro_contenedor = tk.Frame(frame_top, bg="#f0f0f0")
        frame_centro_contenedor.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        frame_centro_checks = tk.Frame(frame_centro_contenedor, bg="#f0f0f0")
        frame_centro_checks.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.var_link_scroll = tk.BooleanVar(value=True)
        self.chk_scroll_dual = tk.Checkbutton(frame_centro_checks, text="🔗 Scroll Up", variable=self.var_link_scroll, bg="#f0f0f0", padx=2, command=self.sincronizar_scrolls)
        self.chk_scroll_dual.pack(side=tk.LEFT)

        self.var_link_triple = tk.BooleanVar(value=False)
        self.chk_scroll_triple = tk.Checkbutton(frame_centro_checks, text="🔗 Scroll All", variable=self.var_link_triple, bg="#f0f0f0", padx=2, command=self.sincronizar_scrolls)
        self.chk_scroll_triple.pack(side=tk.LEFT)

        # --- PanedWindow Principal ---
        self.paned_v = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg="#ccc", sashwidth=4)
        self.paned_v.pack(fill=tk.BOTH, expand=True, padx=10)

        frame_superior_maestro = tk.Frame(self.paned_v, bg="#f0f0f0")
        self.paned_v.add(frame_superior_maestro, height=500)

        frame_contadores_fijos = tk.Frame(frame_superior_maestro, bg="#f0f0f0")
        frame_contadores_fijos.pack(side=tk.BOTTOM, fill=tk.X)

        frame_info_izq = tk.Frame(frame_contadores_fijos, bg="#f0f0f0")
        frame_info_izq.pack(side=tk.LEFT, padx=5, pady=2)
        self.lbl_info_orig = tk.Label(frame_info_izq, text="Líneas: 0 | Tokens: 0 | Chars: 0", bg="#f0f0f0", font=("Arial", 8, "italic"))
        self.lbl_info_orig.pack(side=tk.LEFT)
        self.btn_cargar_orig = tk.Button(frame_info_izq, text="Cargar", font=("Arial", 7), command=self.cargar_archivo_orig)
        self.btn_cargar_orig.pack(side=tk.LEFT, padx=5)

        frame_info_der = tk.Frame(frame_contadores_fijos, bg="#f0f0f0")
        frame_info_der.pack(side=tk.RIGHT, padx=5, pady=2)
        self.btn_cargar_mod = tk.Button(frame_info_der, text="Cargar", font=("Arial", 7), command=self.cargar_archivo_mod)
        self.btn_cargar_mod.pack(side=tk.LEFT, padx=5)
        self.lbl_info_mod = tk.Label(frame_info_der, text="Líneas: 0 | Tokens: 0 | Chars: 0", bg="#f0f0f0", font=("Arial", 8, "italic"))
        self.lbl_info_mod.pack(side=tk.LEFT)

        self.paned_h = tk.PanedWindow(frame_superior_maestro, orient=tk.HORIZONTAL, bg="#ccc", sashwidth=4)
        self.paned_h.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        frame_izq_cont = tk.Frame(self.paned_h, bg="#f0f0f0")
        self.paned_h.add(frame_izq_cont, stretch="always")
        self.txt_orig, self.ln_orig, self.sc_orig = self.crear_editor(frame_izq_cont, "Código Original")

        frame_der_cont = tk.Frame(self.paned_h, bg="#f0f0f0")
        self.paned_h.add(frame_der_cont, stretch="always")
        self.txt_mod, self.ln_mod, self.sc_mod = self.crear_editor(frame_der_cont, "Código Modificado")

        # --- Panel Inferior: Informe ---
        frame_res = tk.Frame(self.paned_v, bg="#f0f0f0")
        self.paned_v.add(frame_res)
        
        tk.Label(frame_res, text="Informe de Diferencias:", bg="#f0f0f0", font=("Arial", 9, "bold")).pack(anchor="w")
        
        frame_res_scroll = tk.Frame(frame_res, bg="#f0f0f0")
        frame_res_scroll.pack(fill=tk.BOTH, expand=True)
        
        self.scr_res_v = ttk.Scrollbar(frame_res_scroll, orient=tk.VERTICAL)
        self.scr_res_v.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.scr_res_h = ttk.Scrollbar(frame_res_scroll, orient=tk.HORIZONTAL)
        self.scr_res_h.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.txt_res = tk.Text(frame_res_scroll, height=10, font=("Courier", 10), state='disabled', wrap="none")
        self.txt_res.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.txt_res.bind("<Triple-Button-1>", self.seleccionar_todo)
        
        def sync_res_yview(*args):
            self.gestionar_scroll(self.txt_res, *args)
            
        self.scr_res_v.config(command=sync_res_yview)
        self.scr_res_h.config(command=self.txt_res.xview)
        
        self.txt_res.config(yscrollcommand=self.proxyset_res, xscrollcommand=self.scr_res_h.set)
        
        # Conectar mousewheel al txt_res para el Triple Scroll
        def on_mousewheel_res(event):
            mov = -1 if (event.num == 4 or event.delta > 0) else 1
            if self.solo_modificaciones:
                top_idx = self.txt_res.index("@0,0")
                current_line = int(top_idx.split('.')[0])
                step = 1 if mov > 0 else -1
                target_line = current_line
                max_lines = int(self.txt_res.index('end-1c').split('.')[0])
                
                lines_to_scroll = 3
                while lines_to_scroll > 0 and 1 <= target_line + step <= max_lines:
                    target_line += step
                    if 'oculto' not in self.txt_res.tag_names(f"{target_line}.0"):
                        lines_to_scroll -= 1
                self.txt_res.yview(f"{target_line}.0")
            else:
                self.gestionar_scroll(self.txt_res, 'scroll', mov, 'units')
            return "break"
            
        self.txt_res.bind("<MouseWheel>", on_mousewheel_res)
        self.txt_res.bind("<Button-4>", on_mousewheel_res)
        self.txt_res.bind("<Button-5>", on_mousewheel_res)
        
        frame_footer = tk.Frame(frame_res, bg="#f0f0f0")
        frame_footer.pack(fill=tk.X)

        self.lbl_lineas_diff = tk.Label(frame_footer, text="Líneas Modificadas: 0", bg="#f0f0f0", font=("Arial", 8, "bold"))
        self.lbl_lineas_diff.pack(side=tk.LEFT, padx=10)

        # Botón de Visibilidad centrado - Ahora usa los colores del sistema sin override
        self.btn_visibilidad = tk.Button(frame_footer, text="Completo", font=("Arial", 9, "bold"), state='disabled', command=self.toggle_visibilidad_lineas)
        self.btn_visibilidad.pack(side=tk.LEFT, expand=True)

        self.btn_copiar = tk.Button(frame_footer, text="Copiar Cambios", font=("Arial", 9, "bold"), state='disabled', command=self.copiar_cambios)
        self.btn_copiar.pack(side=tk.LEFT, expand=True)

        self.lbl_res_chars = tk.Label(frame_footer, text="Total Modificados: 0 | Borrados: 0 | Añadidos: 0", bg="#f0f0f0", font=("Arial", 8, "bold"))
        self.lbl_res_chars.pack(side=tk.RIGHT, padx=5, pady=2)
        
        self.configurar_tags()

    def detectar_lenguaje(self, texto):
        if not texto.strip(): 
            return ""
        # Detección básica por patrones
        if re.search(r'\b(def|class|import|from|if __name__ ==)\b', texto): 
            return "python"
        if re.search(r'\b(function|const|let|var|console\.log|document\.)\b', texto): 
            return "javascript"
        if re.search(r'(<html|<!DOCTYPE|<div|<script|<body)', texto, re.I): 
            return "html"
        if re.search(r'(@media|background-color|margin:|padding:|color: #)', texto): 
            return "css"
        if re.search(r'\b(public class|System\.out\.println|public static void main)\b', texto): 
            return "java"
        if re.search(r'\b(using System;|namespace|Console\.WriteLine)\b', texto): 
            return "csharp"
        if re.search(r'(<\?php|\$this->|echo ")', texto): 
            return "php"
        if re.search(r'\b(SELECT|FROM|WHERE|INSERT INTO|UPDATE|DELETE)\b', texto, re.I): 
            return "sql"
        return "texto"

    def actualizar_titulos_lenguaje(self):
        txt_o = self.txt_orig.get("1.0", tk.END)
        txt_m = self.txt_mod.get("1.0", tk.END)
        lang = self.detectar_lenguaje(txt_o)
        if lang == "texto": 
            lang = self.detectar_lenguaje(txt_m)
        sufijo = f" en {lang}" if lang and lang != "texto" else ""
        self.lbl_tit_orig.config(text=f"Código Original{sufijo}")
        self.lbl_tit_mod.config(text=f"Código Modificado{sufijo}")

    def proxyset_orig(self, *args):
        self.sc_orig.set(*args)
        self.ln_orig.yview_moveto(args[0])

    def proxyset_mod(self, *args):
        self.sc_mod.set(*args)
        self.ln_mod.yview_moveto(args[0])

    def proxyset_res(self, *args):
        self.scr_res_v.set(*args)

    def seleccionar_todo(self, event):
        event.widget.tag_add("sel", "1.0", "end")
        return "break"

    def crear_editor(self, parent, titulo):
        lbl = tk.Label(parent, text=titulo, font=("Arial", 9, "bold"), bg="#f0f0f0")
        lbl.pack(anchor="w")
        if "Original" in titulo: 
            self.lbl_tit_orig = lbl
        else: 
            self.lbl_tit_mod = lbl
            
        subframe = tk.Frame(parent)
        subframe.pack(fill=tk.BOTH, expand=True)
        
        scr_v = ttk.Scrollbar(subframe, orient=tk.VERTICAL)
        scr_v.pack(side=tk.RIGHT, fill=tk.Y)
        
        scr_h = ttk.Scrollbar(subframe, orient=tk.HORIZONTAL)
        scr_h.pack(side=tk.BOTTOM, fill=tk.X)
        
        lineas = tk.Text(subframe, width=5, padx=3, border=0, background="#e0e0e0", state='disabled', font=("Courier", 10))
        lineas.pack(side=tk.LEFT, fill=tk.Y)
        
        texto = tk.Text(subframe, font=("Courier", 10), undo=True, wrap="none")
        texto.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        texto.bind('<Triple-Button-1>', self.seleccionar_todo)
        
        def sync_yview(*args):
            self.gestionar_scroll(texto, *args)
            
        scr_v.config(command=sync_yview)
        scr_h.config(command=texto.xview)
        
        if "Original" in titulo:
            texto.config(yscrollcommand=self.proxyset_orig, xscrollcommand=scr_h.set)
        else:
            texto.config(yscrollcommand=self.proxyset_mod, xscrollcommand=scr_h.set)
            
        lineas.config(yscrollcommand=scr_v.set)
        
        def on_mousewheel(event):
            mov = -1 if (event.num == 4 or event.delta > 0) else 1
            self.gestionar_scroll(texto, 'scroll', mov, 'units')
            return "break"
            
        texto.bind("<MouseWheel>", on_mousewheel)
        texto.bind("<Button-4>", on_mousewheel)
        texto.bind("<Button-5>", on_mousewheel)
        lineas.bind("<MouseWheel>", on_mousewheel)
        lineas.bind("<Button-4>", on_mousewheel)
        lineas.bind("<Button-5>", on_mousewheel)
        
        texto.bind('<KeyRelease>', lambda e, t=texto: self.on_key_release(t))
        
        return texto, lineas, scr_v

    def on_key_release(self, txt_widget):
        self.actualizar_contadores()
        if self.modo_edicion:
            self.actualizar_titulos_lenguaje()
            self.resaltar_sintaxis(txt_widget)

    def resaltar_sintaxis(self, text_widget):
        contenido = text_widget.get("1.0", tk.END)
        for tag in ['kw', 'str', 'com', 'num', 'built']:
            text_widget.tag_remove(tag, "1.0", tk.END)
            
        es_python = any(re.search(p, contenido) for p in [r'\bdef\s+\w+\(', r'\bclass\s+\w+[:\(]', r'\bself\.', r'\bimport\s+\w+', r'\belif\s', r'if\s+__name__\s+==', r'#\s*!/usr/bin'])
        es_jk = any(re.search(p, contenido) for p in [r'\bpublic\s+class\b', r'\bfun\s+\w+\(', r'\bval\s+\w+', r'\bvar\s+\w+', r'\bpackage\s+\w+', r'\{\s*\n', r';\s*\n'])

        patrones = None
        if es_python and not es_jk:
            patrones = {
                'kw': r'\b(and|as|assert|async|await|break|class|continue|def|del|elif|else|except|False|finally|for|from|global|if|import|in|is|lambda|None|nonlocal|not|or|pass|raise|return|True|try|while|with|yield)\b',
                'built': r'\b(print|len|range|str|int|float|list|dict|set|tuple|open|type|enumerate|zip|sum|min|max)\b',
                'num': r'\b\d+\b',
                'str': r'(".*?"|\'.*?\')',
                'com': r'(#.*)'
            }
        elif es_jk and not es_python:
            patrones = {
                'kw': r'\b(abstract|assert|break|case|catch|class|const|continue|default|do|else|enum|extends|final|finally|for|goto|if|implements|import|instanceof|interface|native|new|package|private|protected|public|return|short|static|strictfp|super|switch|synchronized|this|throw|throws|transient|try|void|volatile|while|fun|val|var|when|init|object|companion|override|sealed|data|internal|expect|actual)\b',
                'built': r'\b(String|Int|Boolean|Float|Double|Long|List|Set|Map|println|print|Any|Unit|Nothing)\b',
                'num': r'\b\d+\b',
                'str': r'(".*?"|\'.*?\')',
                'com': r'(//.*)'
            }
        
        if patrones:
            for tag, patron in patrones.items():
                for match in re.finditer(patron, contenido):
                    start_idx = f"1.0 + {match.start()} chars"
                    end_idx = f"1.0 + {match.end()} chars"
                    text_widget.tag_add(tag, start_idx, end_idx)

    def sincronizar_scrolls(self):
        pos = self.txt_orig.yview()[0]
        if self.var_link_triple.get():
            self.txt_mod.yview_moveto(pos)
            self.txt_res.yview_moveto(pos)
            self.ln_orig.yview_moveto(pos)
            self.ln_mod.yview_moveto(pos)
        elif self.var_link_scroll.get():
            self.txt_mod.yview_moveto(pos)
            self.ln_orig.yview_moveto(pos)
            self.ln_mod.yview_moveto(pos)

    def gestionar_scroll(self, widget_origen, *args):
        if self.var_link_triple.get():
            self.txt_orig.yview(*args)
            self.ln_orig.yview(*args)
            self.txt_mod.yview(*args)
            self.ln_mod.yview(*args)
            self.txt_res.yview(*args)
        elif self.var_link_scroll.get():
            if widget_origen in [self.txt_orig, self.ln_orig, self.txt_mod, self.ln_mod]:
                self.txt_orig.yview(*args)
                self.ln_orig.yview(*args)
                self.txt_mod.yview(*args)
                self.ln_mod.yview(*args)
            else:
                widget_origen.yview(*args)
        else:
            widget_origen.yview(*args)
            if widget_origen == self.txt_orig:
                self.ln_orig.yview(*args)
            elif widget_origen == self.txt_mod:
                self.ln_mod.yview(*args)

    def actualizar_contadores(self):
        if not self.modo_edicion:
            textos = [(self.texto_puro_orig, self.lbl_info_orig, self.ln_orig),
                      (self.texto_puro_mod, self.lbl_info_mod, self.ln_mod)]
            for contenido, lbl, ln in textos:
                lineas_lista = contenido.splitlines()
                num_lineas = len(lineas_lista) if contenido else 0
                num_tokens = len(self.encoding.encode(contenido)) if self.encoding else 0
                num_chars = len(contenido)
                lbl.config(text=f"Líneas: {num_lineas} | Tokens: {num_tokens} | Chars: {num_chars}")
        else:
            for txt, lbl, ln in [(self.txt_orig, self.lbl_info_orig, self.ln_orig), 
                                 (self.txt_mod, self.lbl_info_mod, self.ln_mod)]:
                
                contenido = txt.get("1.0", "end-1c")
                lineas_lista = contenido.splitlines()
                num_lineas = len(lineas_lista) if contenido else 0
                num_tokens = len(self.encoding.encode(contenido)) if self.encoding else 0
                num_chars = len(contenido)
                
                lbl.config(text=f"Líneas: {num_lineas} | Tokens: {num_tokens} | Chars: {num_chars}")
                
                if self.modo_edicion:
                    ln.config(state='normal')
                    ln.delete('1.0', tk.END)
                    ln.insert('1.0', "\n".join(str(i) for i in range(1, num_lineas + 1)))
                    ln.config(state='disabled')

    def configurar_tags(self):
        self.txt_res.tag_config('eliminado', background='#ffe6e6', foreground='#cc0000')
        self.txt_res.tag_config('agregado', background='#e6ffe6', foreground='#008000')
        self.txt_res.tag_config('modificado', background='#ffffe6', foreground='#b3b300')
        self.txt_orig.tag_config('vacio', background='#e0e0e0')
        self.txt_mod.tag_config('vacio', background='#e0e0e0')
        self.txt_orig.tag_config('quitar', background='#ffe6e6')
        self.txt_mod.tag_config('poner', background='#e6ffe6')
        # Tag para ocultar líneas
        self.txt_res.tag_config('oculto', elide=True)

        # Tags para decisiones de asimilación selectiva
        self.txt_res.tag_config('dec_conservar', background='#c3e6cb', foreground='#155724', font=("Courier", 10, "bold"))
        self.txt_res.tag_config('dec_descartar', background='#f5c6cb', foreground='#721c24', font=("Courier", 10, "bold"))

        # Colores de sintaxis (Light Theme VS Code)
        self.txt_orig.tag_config('kw', foreground='#0000ff')
        self.txt_orig.tag_config('str', foreground='#a31515')
        self.txt_orig.tag_config('com', foreground='#008000')
        self.txt_orig.tag_config('num', foreground='#098658')
        self.txt_orig.tag_config('built', foreground='#795e26')
        
        self.txt_mod.tag_config('kw', foreground='#0000ff')
        self.txt_mod.tag_config('str', foreground='#a31515')
        self.txt_mod.tag_config('com', foreground='#008000')
        self.txt_mod.tag_config('num', foreground='#098658')
        self.txt_mod.tag_config('built', foreground='#795e26')

    def borrar_todo(self):
        self.texto_puro_orig = ""
        self.texto_puro_mod = ""
        self.txt_orig.config(state='normal')
        self.txt_orig.delete("1.0", tk.END)
        self.txt_mod.config(state='normal')
        self.txt_mod.delete("1.0", tk.END)
        self.txt_res.config(state='normal')
        self.txt_res.delete("1.0", tk.END)
        self.txt_res.config(state='disabled')
        
        self.lbl_lineas_diff.config(text="Líneas Modificadas: 0")
        self.lbl_res_chars.config(text="Total Modificados: 0 | Borrados: 0 | Añadidos: 0")
        
        self.lbl_tit_orig.config(text="Código Original")
        self.lbl_tit_mod.config(text="Código Modificado")
        
        self.btn_toggle.pack_forget()
        
        self.actualizar_contadores()
        
        if not self.modo_edicion:
            self.modo_edicion = True
            self.btn_toggle.config(text="Cambiar a Comparación", bg="#17a2b8", fg="white")
            self.btn_asimilar.config(state='disabled', text="Asimilar Modificado", bg="#28a745", fg="white")
            self.btn_visibilidad.config(text="Completo", state='disabled')
            self.btn_copiar.config(state='disabled')
            self.solo_modificaciones = False
            self.chk_scroll_triple.config(state='normal')
            self.txt_res.tag_remove('oculto', '1.0', tk.END)

    def toggle_modo(self):
        if self.modo_edicion:
            self.texto_puro_orig = self.txt_orig.get("1.0", 'end-1c')
            self.texto_puro_mod = self.txt_mod.get("1.0", 'end-1c')
            self.modo_edicion = False
            self.actualizar_vista_comparativa()
            self.btn_toggle.config(text="Cambiar a Edición", bg="#ffc107", fg="black")
            self.btn_asimilar.config(state='normal', text="Asimilar Modificado", bg="#28a745", fg="white")
            self.btn_visibilidad.config(state='normal')
            self.btn_copiar.config(state='normal')
        else:
            self.solo_modificaciones = False
            self.btn_visibilidad.config(text="Completo", state='disabled')
            self.btn_copiar.config(state='disabled')
            self.chk_scroll_triple.config(state='normal')
            self.txt_res.tag_remove('oculto', '1.0', tk.END)
            self.txt_orig.config(state='normal')
            self.txt_mod.config(state='normal')
            self.txt_orig.delete("1.0", tk.END)
            self.txt_orig.insert("1.0", self.texto_puro_orig)
            self.txt_mod.delete("1.0", tk.END)
            self.txt_mod.insert("1.0", self.texto_puro_mod)
            self.btn_toggle.config(text="Cambiar a Comparación", bg="#17a2b8", fg="white")
            self.btn_asimilar.config(state='disabled', text="Asimilar Modificado", bg="#28a745", fg="white")
            self.modo_edicion = True
            
            self.actualizar_contadores()
            self.actualizar_titulos_lenguaje()
            self.resaltar_sintaxis(self.txt_orig)
            self.resaltar_sintaxis(self.txt_mod)
            
            if hasattr(self, 'tooltip') and self.tooltip:
                self.tooltip.withdraw()

    def ejecutar_comparacion(self):
        self.texto_puro_orig = self.txt_orig.get("1.0", 'end-1c')
        self.texto_puro_mod = self.txt_mod.get("1.0", 'end-1c')
        self.modo_edicion = False
        self.actualizar_vista_comparativa()
        self.guardar_automatico()
        self.btn_toggle.config(text="Cambiar a Edición", bg="#ffc107", fg="black")
        self.btn_toggle.pack(side=tk.RIGHT, padx=5)
        self.btn_asimilar.config(state='normal', text="Asimilar Modificado", bg="#28a745", fg="white")
        self.btn_visibilidad.config(state='normal')
        self.btn_copiar.config(state='normal')

    def accion_asimilar(self):
        estado = self.btn_asimilar.cget("text")
        
        if estado == "Asimilar Modificado":
            self.btn_asimilar.config(text="Finalizar", bg="#17a2b8", fg="white")
            self.decisiones_diff = {}
            self.crear_tooltip_si_no_existe()
            self.txt_res.bind("<Motion>", self.on_hover_txt_res)
            self.txt_res.bind("<Leave>", self.schedule_hide_tooltip)
            messagebox.showinfo("Modo Asimilación", "Estado 'Finalizar' activo.\n\nPasa el ratón sobre las líneas modificadas en el informe de diferencias para elegir 'Conservar' o 'Descartar'. Al terminar, pulsa el botón Finalizar.")
            
        elif estado == "Finalizar":
            self.respaldo_orig = self.texto_puro_orig
            self.respaldo_mod = self.texto_puro_mod
            
            num_keeps = sum(1 for v in self.decisiones_diff.values() if v == 'conservar')
            nuevo_texto = []
            
            for i, linea in enumerate(self.lista_diff_crudo):
                line_num_res = i + 1
                prefix = linea[:2]
                contenido = linea[2:]
                
                decision = self.decisiones_diff.get(line_num_res)
                if num_keeps > 0:
                    keep_this = (decision == 'conservar')
                else:
                    keep_this = (decision != 'descartar')
                    
                if prefix == '  ':
                    nuevo_texto.append(contenido)
                elif prefix == '- ':
                    if not keep_this: 
                        nuevo_texto.append(contenido)
                elif prefix == '+ ':
                    if keep_this: 
                        nuevo_texto.append(contenido)
            
            self.texto_puro_orig = "\n".join(nuevo_texto)
            self.texto_puro_mod = ""
            
            self.txt_orig.config(state='normal')
            self.txt_mod.config(state='normal')
            self.txt_orig.delete("1.0", tk.END)
            self.txt_orig.insert("1.0", self.texto_puro_orig)
            self.txt_mod.delete("1.0", tk.END)
            self.txt_mod.insert("1.0", self.texto_puro_mod)
            
            self.txt_res.config(state='normal')
            self.txt_res.delete("1.0", tk.END)
            self.txt_res.config(state='disabled')
            
            self.btn_toggle.config(text="Cambiar a Comparación", bg="#17a2b8", fg="white")
            self.btn_visibilidad.config(text="Completo", state='disabled')
            self.btn_copiar.config(state='disabled')
            self.modo_edicion = True
            
            self.lbl_lineas_diff.config(text="Líneas Modificadas: 0")
            self.lbl_res_chars.config(text="Total Modificados: 0 | Borrados: 0 | Añadidos: 0")
            
            self.btn_asimilar.config(text="Deshacer Asimilado", bg="#ffc107", fg="black")
            
            self.actualizar_contadores()
            self.actualizar_titulos_lenguaje()
            self.resaltar_sintaxis(self.txt_orig)
            self.resaltar_sintaxis(self.txt_mod)
            
            self.txt_res.unbind("<Motion>")
            self.txt_res.unbind("<Leave>")
            if hasattr(self, 'tooltip') and self.tooltip:
                self.tooltip.withdraw()

        elif estado == "Deshacer Asimilado":
            self.texto_puro_orig = self.respaldo_orig
            self.texto_puro_mod = self.respaldo_mod
            self.decisiones_diff = {}
            self.btn_asimilar.config(text="Asimilar Modificado", bg="#28a745", fg="white")
            self.modo_edicion = False
            self.actualizar_vista_comparativa()
            self.btn_toggle.config(text="Cambiar a Edición", bg="#ffc107", fg="black")
            self.btn_visibilidad.config(state='normal')
            self.btn_copiar.config(state='normal')

    def crear_tooltip_si_no_existe(self):
        if hasattr(self, 'tooltip') and self.tooltip.winfo_exists():
            return
        self.tooltip = tk.Toplevel(self.root)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.withdraw()
        self.tooltip.attributes('-topmost', True)
        self.linea_hover_actual = -1
        self.hide_id = None
        
        self.tooltip.bind("<Enter>", self.cancel_hide_tooltip)
        self.tooltip.bind("<Leave>", self.schedule_hide_tooltip)
        
        f_tt = tk.Frame(self.tooltip, bg="#ffffff", bd=1, relief="solid")
        f_tt.pack()
        
        self.btn_cons = tk.Button(f_tt, text="Conservar", bg="#d4edda", fg="#155724", font=("Arial", 8, "bold"), 
                                  command=lambda: self.registrar_decision('conservar'))
        self.btn_cons.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.btn_desc = tk.Button(f_tt, text="Descartar", bg="#f8d7da", fg="#721c24", font=("Arial", 8, "bold"), 
                                  command=lambda: self.registrar_decision('descartar'))
        self.btn_desc.pack(side=tk.LEFT, padx=2, pady=2)

    def schedule_hide_tooltip(self, event=None):
        self.hide_id = self.root.after(300, self.ocultar_tooltip)

    def cancel_hide_tooltip(self, event=None):
        if hasattr(self, 'hide_id') and self.hide_id:
            self.root.after_cancel(self.hide_id)
            self.hide_id = None

    def ocultar_tooltip(self):
        self.tooltip.withdraw()
        self.linea_hover_actual = -1

    def on_hover_txt_res(self, event):
        self.cancel_hide_tooltip()
        idx = self.txt_res.index(f"@{event.x},{event.y}")
        line_num = int(idx.split('.')[0])
        tags = self.txt_res.tag_names(f"{line_num}.0")
        
        if any(t in ['eliminado', 'agregado', 'modificado'] for t in tags):
            if line_num != self.linea_hover_actual:
                self.linea_hover_actual = line_num
                x_root = event.x_root + 15
                y_root = event.y_root - 10
                self.tooltip.geometry(f"+{x_root}+{y_root}")
                self.tooltip.deiconify()
        else:
            self.schedule_hide_tooltip()

    def registrar_decision(self, decision):
        line_num = self.linea_hover_actual
        self.decisiones_diff[line_num] = decision
        
        self.txt_res.config(state='normal')
        self.txt_res.tag_remove('dec_conservar', f"{line_num}.0", f"{line_num}.end")
        self.txt_res.tag_remove('dec_descartar', f"{line_num}.0", f"{line_num}.end")
        
        if decision == 'conservar':
            self.txt_res.tag_add('dec_conservar', f"{line_num}.0", f"{line_num}.end")
        else:
            self.txt_res.tag_add('dec_descartar', f"{line_num}.0", f"{line_num}.end")
            
        self.txt_res.config(state='disabled')
        self.ocultar_tooltip()

    def actualizar_vista_comparativa(self):
        raw_orig = self.texto_puro_orig.splitlines()
        raw_mod = self.texto_puro_mod.splitlines()
        
        sm = difflib.SequenceMatcher(None, raw_orig, raw_mod)
        c_lineas_diff = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'replace':
                c_lineas_diff += max(i2 - i1, j2 - j1)
            elif tag == 'delete':
                c_lineas_diff += i2 - i1
            elif tag == 'insert':
                c_lineas_diff += j2 - j1

        self.lista_diff_crudo = list(difflib.ndiff(raw_orig, raw_mod))
        diff = self.lista_diff_crudo
        
        self.txt_res.config(state='normal')
        self.txt_res.delete("1.0", tk.END)
        self.txt_orig.config(state='normal')
        self.txt_mod.config(state='normal')
        self.txt_orig.delete("1.0", tk.END)
        self.txt_mod.delete("1.0", tk.END)

        num_izq, num_der = 1, 1
        ln_izq_str, ln_der_str = "", ""
        
        c_borrados = 0
        c_añadidos = 0
        c_modificados = 0

        for i, linea in enumerate(diff):
            prefix, contenido = linea[:2], linea[2:]
            if prefix == '  ':
                self.txt_res.insert(tk.END, f"{num_izq:3}|{num_der:3}|  {contenido}\n")
                self.txt_orig.insert(tk.END, contenido + "\n")
                self.txt_mod.insert(tk.END, contenido + "\n")
                ln_izq_str += f"{num_izq}\n"
                ln_der_str += f"{num_der}\n"
                num_izq += 1
                num_der += 1
            elif prefix == '- ':
                self.txt_res.insert(tk.END, f"{num_izq:3}|   | - {contenido}\n", 'eliminado')
                self.txt_orig.insert(tk.END, contenido + "\n", 'quitar')
                self.txt_mod.insert(tk.END, "\n", 'vacio')
                ln_izq_str += f"{num_izq}\n"
                ln_der_str += "\n"
                num_izq += 1
                
                if not (i + 1 < len(diff) and diff[i+1].startswith('? ')):
                    c_borrados += len(contenido)
            elif prefix == '+ ':
                self.txt_res.insert(tk.END, f"   |{num_der:3}| + {contenido}\n", 'agregado')
                self.txt_orig.insert(tk.END, "\n", 'vacio')
                self.txt_mod.insert(tk.END, contenido + "\n", 'poner')
                ln_izq_str += "\n"
                ln_der_str += f"{num_der}\n"
                num_der += 1
                
                if not (i + 1 < len(diff) and diff[i+1].startswith('? ')):
                    c_añadidos += len(contenido)
            elif prefix == '? ':
                self.txt_res.insert(tk.END, f"   |   | ? {contenido}\n", 'modificado')
                c_añadidos += contenido.count('+')
                c_borrados += contenido.count('-')
                c_modificados += contenido.count('^')

        self.lbl_res_chars.config(text=f"Total Modificados: {int(c_modificados/2)} | Borrados: {c_borrados} | Añadidos: {c_añadidos}")
        self.lbl_lineas_diff.config(text=f"Líneas Modificadas: {int(c_lineas_diff)}")

        self.txt_res.config(state='disabled')
        self.txt_orig.config(state='disabled')
        self.txt_mod.config(state='disabled')
        self.forzar_numeracion(ln_izq_str, ln_der_str)
        self.actualizar_contadores()

    def toggle_visibilidad_lineas(self):
        self.solo_modificaciones = not self.solo_modificaciones
        self.txt_res.config(state='normal')
        if self.solo_modificaciones:
            self.btn_visibilidad.config(text="Modificaciones")
            self.var_link_triple.set(False)
            self.chk_scroll_triple.config(state='disabled')
            
            total_lines = int(self.txt_res.index('end-1c').split('.')[0])
            for i in range(1, total_lines + 1):
                start = f"{i}.0"
                end = f"{i+1}.0"
                tags = self.txt_res.tag_names(start)
                if not any(t in ['eliminado', 'agregado', 'modificado'] for t in tags):
                    self.txt_res.tag_add('oculto', start, end)
        else:
            self.btn_visibilidad.config(text="Completo")
            self.chk_scroll_triple.config(state='normal')
            self.txt_res.tag_remove('oculto', '1.0', tk.END)
        self.txt_res.config(state='disabled')

    def copiar_cambios(self):
        texto_copiar = []
        total_lines = int(self.txt_res.index('end-1c').split('.')[0])
        for i in range(1, total_lines + 1):
            tags = self.txt_res.tag_names(f"{i}.0")
            if any(t in ['eliminado', 'agregado', 'modificado'] for t in tags):
                line_text = self.txt_res.get(f"{i}.0", f"{i}.end")
                texto_copiar.append(line_text)
        
        if texto_copiar:
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(texto_copiar))
            
            original_bg = self.btn_copiar.cget("background")
            original_fg = self.btn_copiar.cget("foreground")
            self.btn_copiar.config(text="¡Copiado!", bg="#28a745", fg="white")
            self.root.after(1500, lambda: self.btn_copiar.config(text="Copiar Cambios", bg=original_bg, fg=original_fg))

    def forzar_numeracion(self, str_izq, str_der):
        for widget, content in [(self.ln_orig, str_izq), (self.ln_mod, str_der)]:
            widget.config(state='normal')
            widget.delete('1.0', tk.END)
            widget.insert('1.0', content)
            widget.config(state='disabled')

    def guardar_automatico(self):
        nombre = self.entry_proyecto.get().strip() or "Sin_Nombre"
        fecha = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.ruta_docs, f"{nombre}_{fecha}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"PROYECTO: {nombre}\nORIGINAL:\n{self.texto_puro_orig}\n{'='*20}\nMODIFICADO:\n{self.texto_puro_mod}\n{'='*20}\nINFORME:\n{self.txt_res.get('1.0', tk.END)}")
        except Exception as e: print(f"Error al guardar: {e}")

    def menu_proyectos_historial(self):
        try:
            archivos = os.listdir(self.ruta_docs)
            proyectos = sorted(list(set([f.split('_20')[0] for f in archivos if '_20' in f])))
            if not proyectos:
                messagebox.showinfo("Historial", "No se encontraron proyectos guardados.")
                return
            menu = tk.Menu(self.root, tearoff=0)
            for p in proyectos:
                menu.add_command(label=p, command=lambda proy=p: self.cambiar_proyecto_desde_menu(proy))
            menu.post(self.root.winfo_pointerx(), self.root.winfo_pointery())
        except Exception as e: print(f"Error al cargar menú: {e}")

    def cambiar_proyecto_desde_menu(self, nombre_proy):
        self.entry_proyecto.delete(0, tk.END)
        self.entry_proyecto.insert(0, nombre_proy)
        self.cargar_lista_historial()

    def cargar_lista_historial(self):
        nombre_proyecto = self.entry_proyecto.get().strip()
        archivos = [f for f in os.listdir(self.ruta_docs) if f.startswith(nombre_proyecto)]
        self.archivos_historial = sorted(archivos)
        if self.archivos_historial:
            self.indice_historial = len(self.archivos_historial) - 1
            self.mostrar_archivo_historial()
        else:
            messagebox.showinfo("Historial", f"No hay archivos para el proyecto: {nombre_proyecto}")

    def mostrar_archivo_historial(self):
        if not self.archivos_historial: return
        path = os.path.join(self.ruta_docs, self.archivos_historial[self.indice_historial])
        try:
            with open(path, "r", encoding="utf-8") as f:
                partes = f.read().split('='*20)
                if len(partes) >= 3:
                    self.texto_puro_orig = partes[0].split("ORIGINAL:\n")[-1].strip()
                    self.texto_puro_mod = partes[1].split("MODIFICADO:\n")[-1].strip()
                    self.modo_edicion = False
                    self.actualizar_vista_comparativa()
                    self.btn_toggle.config(text="Cambiar a Edición", bg="#ffc107", fg="black")
                    self.btn_toggle.pack(side=tk.RIGHT, padx=5)
                    self.btn_asimilar.config(state='normal', text="Asimilar Modificado", bg="#28a745", fg="white")
                    self.btn_visibilidad.config(state='normal')
                    self.btn_copiar.config(state='normal')
                    self.actualizar_titulos_lenguaje()
        except Exception as e: print(f"Error al leer historial: {e}")

    def siguiente_historial(self):
        if self.indice_historial < len(self.archivos_historial) - 1:
            self.indice_historial += 1
            self.mostrar_archivo_historial()

    def anterior_historial(self):
        if self.indice_historial > 0:
            self.indice_historial -= 1
            self.mostrar_archivo_historial()

    def cargar_archivo_orig(self):
        ruta = filedialog.askopenfilename(title="Cargar Código Original", filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")])
        if ruta:
            try:
                with open(ruta, "r", encoding="utf-8", errors="replace") as f:
                    contenido = f.read()
                self.txt_orig.config(state='normal')
                self.txt_orig.delete("1.0", tk.END)
                self.txt_orig.insert("1.0", contenido)
                self.actualizar_contadores()
                if self.modo_edicion:
                    self.actualizar_titulos_lenguaje()
                    self.resaltar_sintaxis(self.txt_orig)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar el archivo:\n{e}")

    def cargar_archivo_mod(self):
        ruta = filedialog.askopenfilename(title="Cargar Código Modificado", filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")])
        if ruta:
            try:
                with open(ruta, "r", encoding="utf-8", errors="replace") as f:
                    contenido = f.read()
                self.txt_mod.config(state='normal')
                self.txt_mod.delete("1.0", tk.END)
                self.txt_mod.insert("1.0", contenido)
                self.actualizar_contadores()
                if self.modo_edicion:
                    self.actualizar_titulos_lenguaje()
                    self.resaltar_sintaxis(self.txt_mod)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar el archivo:\n{e}")

    def toggle_tema(self):
        self.modo_oscuro = not self.modo_oscuro
        
        if self.modo_oscuro:
            bg_main = "#000000"
            fg_main = "#ffffff"
            bg_txt = "#000000"
            bg_ln = "#000000"
        else:
            bg_main = "#f0f0f0"
            fg_main = "black"
            bg_txt = "white"
            bg_ln = "#e0e0e0"
            
        if self.modo_oscuro:
            self.style.configure("Vertical.TScrollbar", gripcount=4, background="#4f4f4f", troughcolor="#2c2c2c", bordercolor="#2c2c2c", arrowcolor="white")
            self.style.configure("Horizontal.TScrollbar", gripcount=4, background="#4f4f4f", troughcolor="#2c2c2c", bordercolor="#2c2c2c", arrowcolor="white")
            self.style.map("Vertical.TScrollbar", background=[('active', '#666666')])
            self.style.map("Horizontal.TScrollbar", background=[('active', '#666666')])
            self.btn_tema.config(text="Modo Claro", bg="#6c757d", fg="white")
        else:
            self.style.configure("Vertical.TScrollbar", gripcount=4, background="#d9d9d9", troughcolor="#f0f0f0", bordercolor="#cccccc", arrowcolor="black")
            self.style.configure("Horizontal.TScrollbar", gripcount=4, background="#d9d9d9", troughcolor="#f0f0f0", bordercolor="#cccccc", arrowcolor="black")
            self.style.map("Vertical.TScrollbar", background=[('active', '#e6e6e6')])
            self.style.map("Horizontal.TScrollbar", background=[('active', '#e6e6e6')])
            self.btn_tema.config(text="Modo Oscuro", bg="black", fg="white")

        self.root.configure(bg=bg_main)
        
        def update_colors(widget):
            try:
                wt = widget.winfo_class()
                if wt in ('TScrollbar'): return
                if widget in [self.btn_asimilar, self.btn_toggle, self.btn_comparar, self.btn_historial, self.btn_borrar, self.btn_copiar]: pass 
                elif wt in ('Frame', 'Tk', 'Toplevel', 'PanedWindow'): widget.configure(bg=bg_main)
                elif wt == 'Label': widget.configure(bg=bg_main, fg=fg_main)
                elif wt == 'Checkbutton': widget.configure(bg=bg_main, fg=fg_main, selectcolor=bg_main, activebackground=bg_main, activeforeground=fg_main)
                elif wt == 'Button': 
                    if widget != self.btn_tema: widget.configure(bg=bg_main, fg=fg_main)
                elif wt == 'Entry': widget.configure(bg=bg_txt, fg=fg_main, insertbackground=fg_main)
                elif wt == 'Text':
                    if widget in [self.ln_orig, self.ln_mod]: widget.configure(bg=bg_ln, fg=fg_main)
                    else: widget.configure(bg=bg_txt, fg=fg_main, insertbackground=fg_main)
            except Exception: pass
            for child in widget.winfo_children(): update_colors(child)
                
        update_colors(self.root)
        
        if self.modo_oscuro:
            self.txt_res.tag_config('eliminado', background='#5c0000', foreground='#ff9999')
            self.txt_res.tag_config('agregado', background='#004d00', foreground='#99ff99')
            self.txt_res.tag_config('modificado', background='#333300', foreground='#ffff99')
            self.txt_orig.tag_config('vacio', background='#1a1a1a')
            self.txt_mod.tag_config('vacio', background='#1a1a1a')
            self.txt_orig.tag_config('quitar', background='#5c0000')
            self.txt_mod.tag_config('poner', background='#004d00')
            
            self.txt_res.tag_config('dec_conservar', background='#1e4d28', foreground='#d4edda', font=("Courier", 10, "bold"))
            self.txt_res.tag_config('dec_descartar', background='#4d1e1e', foreground='#f8d7da', font=("Courier", 10, "bold"))
            
            # Colores Sintaxis Dark Theme (VS Code)
            self.txt_orig.tag_config('kw', foreground='#569cd6')
            self.txt_orig.tag_config('str', foreground='#ce9178')
            self.txt_orig.tag_config('com', foreground='#6a9955')
            self.txt_orig.tag_config('num', foreground='#b5cea8')
            self.txt_orig.tag_config('built', foreground='#4ec9b0')
            
            self.txt_mod.tag_config('kw', foreground='#569cd6')
            self.txt_mod.tag_config('str', foreground='#ce9178')
            self.txt_mod.tag_config('com', foreground='#6a9955')
            self.txt_mod.tag_config('num', foreground='#b5cea8')
            self.txt_mod.tag_config('built', foreground='#4ec9b0')
        else:
            self.configurar_tags()

if __name__ == "__main__":
    root = tk.Tk()
    app = ComparadorOffline(root)
    root.mainloop()

import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
import json
import copy
import random

# PNG export
HAS_PIL = False
try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    pass

class MatrixState:
    def __init__(self, rows=15, cols=20, default_char="", default_bg="#FFFFFF"):
        self.rows = rows
        self.cols = cols
        self.default_char = default_char
        self.default_bg = default_bg
        self.grid = []
        self.init_grid()
        self.undo_stack = []
        self.redo_stack = []

    def init_grid(self):
        self.grid = [
            [{"char": self.default_char, "bg": self.default_bg} for _ in range(self.cols)]
            for _ in range(self.rows)
        ]

    def resize(self, new_rows, new_cols):
        current_rows = len(self.grid)
        current_cols = len(self.grid[0]) if current_rows > 0 else 0
        new_grid = []
        for r in range(new_rows):
            row_data = []
            for c in range(new_cols):
                if r < current_rows and c < current_cols:
                    row_data.append(copy.deepcopy(self.grid[r][c]))
                else:
                    row_data.append({"char": self.default_char, "bg": self.default_bg})
            new_grid.append(row_data)
        self.grid = new_grid
        self.rows = new_rows
        self.cols = new_cols

    def push_state(self):
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.undo_stack.append({
            "grid": copy.deepcopy(self.grid),
            "rows": self.rows,
            "cols": self.cols
        })
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack: return False
        self.redo_stack.append({"grid": copy.deepcopy(self.grid), "rows": self.rows, "cols": self.cols})
        state = self.undo_stack.pop()
        self.grid, self.rows, self.cols = state["grid"], state["rows"], state["cols"]
        return True

    def redo(self):
        if not self.redo_stack: return False
        self.undo_stack.append({"grid": copy.deepcopy(self.grid), "rows": self.rows, "cols": self.cols})
        state = self.redo_stack.pop()
        self.grid, self.rows, self.cols = state["grid"], state["rows"], state["cols"]
        return True

    def set_cell(self, r, c, char, bg, lock_char=None):
        if 0 <= r < self.rows and 0 <= c < self.cols:
            cell = self.grid[r][c]
            if lock_char and cell["char"] == lock_char:
                return False
            cell["char"], cell["bg"] = char, bg
            return True
        return False

class PixelMatrixEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Pro Pixel Matrix Editor v4.1")
        self.root.geometry("1150x800")
        
        self.cell_size = 30
        self.current_tool = "pen"
        self.primary_color = "#3498db"
        
        self.var_rows = tk.IntVar(value=15)
        self.var_cols = tk.IntVar(value=20)
        self.var_char = tk.StringVar(value="X")
        self.var_lock_char = tk.StringVar(value="")
        
        self.state = MatrixState(self.var_rows.get(), self.var_cols.get())
        self.start_cell = None
        
        self.setup_ui()
        self.update_canvas_dims()
        self.redraw_grid()
        
        self.root.bind("<Control-z>", lambda e: self.perform_undo())
        self.root.bind("<Control-y>", lambda e: self.perform_redo())

    def setup_ui(self):
        # --- Top Toolbar ---
        top_bar = ttk.Frame(self.root, padding=5)
        top_bar.pack(side=tk.TOP, fill=tk.X)
        
        ttk.Label(top_bar, text="Rows:").pack(side=tk.LEFT)
        ttk.Entry(top_bar, textvariable=self.var_rows, width=4).pack(side=tk.LEFT, padx=2)
        ttk.Label(top_bar, text="Cols:").pack(side=tk.LEFT)
        ttk.Entry(top_bar, textvariable=self.var_cols, width=4).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_bar, text="Resize", command=self.apply_resize).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(top_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Button(top_bar, text="Import Text", command=self.import_text_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_bar, text="Export Text", command=self.export_text).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_bar, text="Save JSON", command=self.save_json).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_bar, text="Load JSON", command=self.load_json).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_bar, text="Export PNG", command=self.export_png).pack(side=tk.LEFT, padx=2)

        # --- Sidebar ---
        sidebar = ttk.Frame(self.root, padding=5)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        tool_frame = ttk.LabelFrame(sidebar, text="Tools")
        tool_frame.pack(fill=tk.X, pady=5)
        tools = [("Pen", "pen"), ("Eraser", "eraser"), ("Line", "line"), 
                 ("Rect", "rect"), ("Circle", "circle")]
        for text, mode in tools:
            ttk.Button(tool_frame, text=text, command=lambda m=mode: self.set_tool(m)).pack(fill=tk.X, pady=1)
            
        attr_frame = ttk.LabelFrame(sidebar, text="Attributes")
        attr_frame.pack(fill=tk.X, pady=10)
        ttk.Label(attr_frame, text="Active Char:").pack(anchor="w", padx=5)
        ttk.Entry(attr_frame, textvariable=self.var_char, width=5).pack(fill=tk.X, padx=5, pady=2)
        
        self.btn_color = tk.Button(attr_frame, text="Color Picker", bg=self.primary_color, fg="white", command=self.pick_color)
        self.btn_color.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(attr_frame, text="Lock Char:").pack(anchor="w", padx=5, pady=(5,0))
        ttk.Entry(attr_frame, textvariable=self.var_lock_char, width=5).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(sidebar, text="Undo (Ctrl+Z)", command=self.perform_undo).pack(fill=tk.X, pady=2)
        ttk.Button(sidebar, text="Redo (Ctrl+Y)", command=self.perform_redo).pack(fill=tk.X, pady=2)
        ttk.Button(sidebar, text="Clear All", command=self.clear_canvas).pack(fill=tk.X, pady=10)

        # --- Canvas ---
        self.canvas_frame = ttk.Frame(self.root, relief="sunken", borderwidth=1)
        self.canvas_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=5, pady=5)
        self.h_scroll = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.v_scroll = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)
        self.canvas = tk.Canvas(self.canvas_frame, bg="#f0f0f0", xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    # --- Logic ---
    def set_tool(self, tool_name): self.current_tool = tool_name
    def pick_color(self):
        color = colorchooser.askcolor(color=self.primary_color)[1]
        if color: self.primary_color = color; self.btn_color.config(bg=color)

    def apply_resize(self):
        self.state.push_state()
        self.state.resize(self.var_rows.get(), self.var_cols.get())
        self.update_canvas_dims(); self.redraw_grid()

    def update_canvas_dims(self):
        w, h = self.state.cols * self.cell_size, self.state.rows * self.cell_size
        self.canvas.config(scrollregion=(0, 0, w, h))

    def draw_cell(self, r, c):
        cell = self.state.grid[r][c]
        x1, y1 = c * self.cell_size, r * self.cell_size
        x2, y2 = x1 + self.cell_size, y1 + self.cell_size
        tag = f"cell_{r}_{c}"
        self.canvas.delete(tag)
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=cell["bg"], outline="#ccc", tags=("grid", tag))
        if cell["char"]:
            self.canvas.create_text((x1+x2)/2, (y1+y2)/2, text=cell["char"], font=("Arial", 10, "bold"), tags=("grid", tag))

    def redraw_grid(self):
        self.canvas.delete("all")
        for r in range(self.state.rows):
            for c in range(self.state.cols): self.draw_cell(r, c)

    def get_grid_pos(self, event):
        return int(self.canvas.canvasy(event.y) // self.cell_size), int(self.canvas.canvasx(event.x) // self.cell_size)

    def on_mouse_down(self, event):
        r, c = self.get_grid_pos(event)
        if not (0 <= r < self.state.rows and 0 <= c < self.state.cols): return
        self.start_cell = (r, c)
        self.state.push_state()
        if self.current_tool == "pen": self.paint_cell(r, c)
        elif self.current_tool == "eraser": self.erase_cell(r, c)

    def on_mouse_drag(self, event):
        if not self.start_cell: return
        r, c = self.get_grid_pos(event)
        if self.current_tool == "pen": self.paint_cell(r, c)
        elif self.current_tool == "eraser": self.erase_cell(r, c)
        else:
            self.canvas.delete("preview")
            pts = self.get_shape_pts(self.start_cell, (r, c), self.current_tool)
            for pr, pc in pts:
                if 0 <= pr < self.state.rows and 0 <= pc < self.state.cols:
                    x1, y1 = pc * self.cell_size, pr * self.cell_size
                    self.canvas.create_rectangle(x1, y1, x1+self.cell_size, y1+self.cell_size, fill=self.primary_color, stipple="gray50", tags="preview")

    def on_mouse_up(self, event):
        if self.start_cell and self.current_tool not in ["pen", "eraser"]:
            r, c = self.get_grid_pos(event)
            pts = self.get_shape_pts(self.start_cell, (r, c), self.current_tool)
            for pr, pc in pts: self.paint_cell(pr, pc, batch=True)
            self.redraw_grid()
        self.canvas.delete("preview"); self.start_cell = None

    def paint_cell(self, r, c, batch=False):
        if self.state.set_cell(r, c, self.var_char.get(), self.primary_color, self.var_lock_char.get()) and not batch:
            self.draw_cell(r, c)

    def erase_cell(self, r, c):
        if self.state.set_cell(r, c, "", "#FFFFFF", self.var_lock_char.get()): self.draw_cell(r, c)

    def get_shape_pts(self, start, end, tool):
        r1, c1 = start; r2, c2 = end; pts = set()
        if tool == "line":
            dr, dc = abs(r2-r1), abs(c2-c1); sr, sc = (1 if r1<r2 else -1), (1 if c1<c2 else -1); err = dr-dc
            while True:
                pts.add((r1, c1))
                if r1==r2 and c1==c2: break
                e2 = 2*err
                if e2 > -dc: err-=dc; r1+=sr
                if e2 < dr: err+=dr; c1+=sc
        elif tool == "rect":
            for r in range(min(r1, r2), max(r1, r2)+1):
                for c in range(min(c1, c2), max(c1, c2)+1): pts.add((r, c))
        elif tool == "circle":
            mr, mc = (r1+r2)/2, (c1+c2)/2; rad_r, rad_c = abs(r2-r1)/2, abs(c2-c1)/2
            for r in range(min(r1, r2), max(r1, r2)+1):
                for c in range(min(c1, c2), max(c1, c2)+1):
                    if rad_r and rad_c and ((r-mr)**2/rad_r**2 + (c-mc)**2/rad_c**2) <= 1.1: pts.add((r, c))
        return pts

    def import_text_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Matrix Text Import")
        win.geometry("500x500")
        win.transient(self.root)
        win.grab_set()

        ttk.Label(win, text="Paste the matrix text (columns separated by spaces):", font=("Arial", 9, "bold")).pack(pady=10)
        txt_input = tk.Text(win, font=("Consolas", 10))
        txt_input.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

        # Renk paleti
        palette = ["#3498db", "#e74c3c", "#2ecc71", "#f1c40f", "#9b59b6", "#1abc9c", "#e67e22", "#34495e", "#d35400", "#c0392b"]

        def process_import():
            content = txt_input.get("1.0", tk.END).strip()
            if not content: return

            lines = [l.strip() for l in content.split('\n') if l.strip()]
            data = [l.split() for l in lines]
            if not data: return
            
            self.state.push_state()
            new_rows = len(data)
            new_cols = max(len(row) for row in data)
            
            # Resize
            self.state.resize(new_rows, new_cols)
            self.var_rows.set(new_rows)
            self.var_cols.set(new_cols)

            # char color mapping
            char_map = {}
            color_idx = 0

            for r in range(new_rows):
                for c in range(new_cols):
                    if c < len(data[r]):
                        char_val = data[r][c]
                        if char_val not in ["0", "."]: # If it is not a null character
                            if char_val not in char_map:
                                if color_idx < len(palette):
                                    char_map[char_val] = palette[color_idx]
                                    color_idx += 1
                                else:
                                    char_map[char_val] = "#%06x" % random.randint(0, 0xFFFFFF)
                            
                            color = char_map[char_val]
                        else:
                            color = "#FFFFFF" # Null color
                        
                        self.state.set_cell(r, c, char_val, color)
                    else:
                        self.state.set_cell(r, c, "", "#FFFFFF")

            self.update_canvas_dims()
            self.redraw_grid()
            win.destroy()

        ttk.Button(win, text="Create and Size the Matrix", command=process_import).pack(pady=15)

    def export_text(self):
        out = "\n".join([" ".join([c["char"] if c["char"] else "0" for c in row]) for row in self.state.grid])
        win = tk.Toplevel(self.root); txt = tk.Text(win); txt.pack(); txt.insert("1.0", out)

    def perform_undo(self): 
        if self.state.undo(): 
            self.var_rows.set(self.state.rows); self.var_cols.set(self.state.cols)
            self.update_canvas_dims(); self.redraw_grid()
            
    def perform_redo(self): 
        if self.state.redo(): 
            self.var_rows.set(self.state.rows); self.var_cols.set(self.state.cols)
            self.update_canvas_dims(); self.redraw_grid()
            
    def clear_canvas(self):
        if messagebox.askyesno("Okay", "Should the entire matrix be cleaned?"):
            self.state.push_state()
            self.state.init_grid()
            self.redraw_grid()

    def save_json(self):
        f = filedialog.asksaveasfilename(defaultextension=".json")
        if f: 
            with open(f, "w") as file:
                json.dump({"rows": self.state.rows, "cols": self.state.cols, "grid": self.state.grid}, file)

    def load_json(self):
        f = filedialog.askopenfilename()
        if f:
            with open(f, "r") as file:
                d = json.load(file)
                self.state.push_state()
                self.state.rows, self.state.cols, self.state.grid = d["rows"], d["cols"], d["grid"]
                self.var_rows.set(self.state.rows); self.var_cols.set(self.state.cols)
                self.update_canvas_dims(); self.redraw_grid()

    def export_png(self):
        if not HAS_PIL:
            messagebox.showerror("Error", "Please install the pillow library: pip install pillow")
            return

        from tkinter import simpledialog
        from PIL import Image, ImageDraw, ImageFont

        scale = simpledialog.askinteger(
            "Quality",
            "Resolution multiplier (1=Normally, 2=HD, 4=4K, 8=Ultra):",
            minvalue=1,
            initialvalue=4
        )

        if not scale:
            return

        f = filedialog.asksaveasfilename(defaultextension=".png")
        if not f:
            return

        width = self.state.cols * self.cell_size * scale
        height = self.state.rows * self.cell_size * scale

        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)

        # Font (uses TrueType if available)
        try:
            font = ImageFont.truetype("arial.ttf", int(self.cell_size/3 * scale))
        except:
            font = ImageFont.load_default()

        for r in range(self.state.rows):
            for c in range(self.state.cols):
                cell = self.state.grid[r][c]

                x1 = c * self.cell_size * scale
                y1 = r * self.cell_size * scale
                x2 = (c+1) * self.cell_size * scale
                y2 = (r+1) * self.cell_size * scale

                draw.rectangle([x1, y1, x2, y2], fill=cell["bg"], outline="#000")

                # Yazı ortalama
                text = cell["char"]
                bbox = draw.textbbox((0,0), text, font=font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]

                tx = x1 + (self.cell_size*scale - tw) / 2
                ty = y1 + (self.cell_size*scale - th) / 2

                draw.text((tx, ty), text, fill="white", font=font)

        img.save(f, "PNG", dpi=(300,300))
        messagebox.showinfo("Başarılı", f"{scale}x High-quality PNG saved!")

if __name__ == "__main__":
    root = tk.Tk()
    app = PixelMatrixEditor(root)
    root.mainloop()

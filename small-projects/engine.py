import tkinter as tk
import math
import json
from tkinter import filedialog
import re
import time


class GameObject:
    COLORS = {
        "player": "#4caf50",
        "wall": "#9e9e9e",
        "box": "#4fc3f7",
        "sign": "#ffeb3b",
        "scale_trigger": "#e91e63",
        "boost_panel": "#00e5ff",
        "reset_trigger": "#ff1744"
    }

    def __init__(self, x, y, w, h, type="box", text="", visible=True):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.type = type
        self.text = text
        self.visible = visible
        self.script = ""
        
        self.script_trigger_type = "collision"
        self.script_one_shot = True
        self.script_activated = False

        self.target_w = w
        self.target_h = h
        self.scale_speed = 0.1

        self.boost_angle = 90
        self.boost_power = 15
        
        self.move_target_x = x
        self.move_target_y = y
        self.move_start_x = x
        self.move_start_y = y
        self.move_duration = 0
        self.move_elapsed = 0
        self.is_moving = False
        
        self.size_target_w = w
        self.size_target_h = h
        self.size_start_w = w
        self.size_start_h = h
        self.size_duration = 0
        self.size_elapsed = 0
        self.is_resizing = False
        
        self.wait_time = 0
        self.wait_start = 0
        self.is_waiting = False

    def copy(self):
        o = GameObject(self.x, self.y, self.w, self.h, self.type, self.text, self.visible)
        o.__dict__.update(self.__dict__)
        return o

    def to_dict(self):
        return self.__dict__.copy()

    @staticmethod
    def from_dict(d):
        o = GameObject(d["x"], d["y"], d["w"], d["h"], d["type"], d.get("text", ""), d.get("visible", True))
        o.__dict__.update(d)
        return o

    def contains(self, x, y):
        return self.x <= x <= self.x + self.w and self.y <= y <= self.y + self.h

    def draw(self, canvas, cx, cy, zoom, selected=False, is_editor=True):
        if not self.visible:
            return
        x = (self.x - cx) * zoom
        y = (self.y - cy) * zoom
        w = self.w * zoom
        h = self.h * zoom
        canvas.create_rectangle(
            x, y, x + w, y + h,
            fill=self.COLORS.get(self.type, "white"),
            outline="yellow" if selected else "black",
            width=2
        )
        if is_editor and self.script and self.script.strip():
            canvas.create_text(x + w/2, y + h/2, text="S", fill="red", font=("Arial", 10, "bold"))
            
    def update_animation(self, delta_time):
        if self.is_moving:
            self.move_elapsed += delta_time
            if self.move_elapsed >= self.move_duration:
                self.x = self.move_target_x
                self.y = self.move_target_y
                self.is_moving = False
            else:
                progress = self.move_elapsed / self.move_duration
                self.x = self.move_start_x + (self.move_target_x - self.move_start_x) * progress
                self.y = self.move_start_y + (self.move_target_y - self.move_start_y) * progress
        
        if self.is_resizing:
            self.size_elapsed += delta_time
            if self.size_elapsed >= self.size_duration:
                self.w = self.size_target_w
                self.h = self.size_target_h
                self.is_resizing = False
            else:
                progress = self.size_elapsed / self.size_duration
                self.w = self.size_start_w + (self.size_target_w - self.size_start_w) * progress
                self.h = self.size_start_h + (self.size_target_h - self.size_start_h) * progress
        
        if self.is_waiting:
            if time.time() - self.wait_start >= self.wait_time / 1000.0:
                self.is_waiting = False


class ScriptEditor:
    def __init__(self, parent, initial_script="", on_save=None):
        self.window = tk.Toplevel(parent)
        self.window.title("Script Editor")
        self.window.geometry("600x400")
        
        self.on_save = on_save
        
        self.text_area = tk.Text(self.window, wrap="word", font=("Consolas", 10), bg="#1e1e1e", fg="white")
        self.text_area.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.text_area.insert("1.0", initial_script)
        
        self.setup_syntax_highlighting()
        
        button_frame = tk.Frame(self.window)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Button(button_frame, text="Save", command=self.save).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=self.window.destroy).pack(side="left", padx=5)
        
        info_btn = tk.Button(button_frame, text="Help", command=self.show_help)
        info_btn.pack(side="right", padx=5)
        
    def setup_syntax_highlighting(self):
        keywords = ["Object", "Player", "Snow", "World", "loop", "if", "elif", "else", "then", "var", "Text", "wait"]
        self.text_area.tag_configure("keyword", foreground="#569cd6")
        self.text_area.tag_configure("comment", foreground="#6a9955")
        self.text_area.tag_configure("string", foreground="#ce9178")
        
        self.text_area.bind("<KeyRelease>", self.highlight_syntax)
        
    def highlight_syntax(self, event=None):
        for tag in ["keyword", "comment", "string"]:
            self.text_area.tag_remove(tag, "1.0", "end")
        
        content = self.text_area.get("1.0", "end-1c")
        lines = content.split('\n')
        
        line_num = 1
        for line in lines:
            if line.strip().startswith("--"):
                start = f"{line_num}.0"
                end = f"{line_num}.{len(line)}"
                self.text_area.tag_add("comment", start, end)
            line_num += 1
        
        long_comment_pattern = r'-\\[\s\S]*?\\-'
        for match in re.finditer(long_comment_pattern, content, re.MULTILINE):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("comment", start, end)
        
        keywords = ["Object", "Player", "Snow", "World", "loop", "if", "elif", "else", "then", "var", "Text", "wait"]
        for keyword in keywords:
            pattern = rf'\b{keyword}\b'
            for match in re.finditer(pattern, content):
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                self.text_area.tag_add("keyword", start, end)
        
        string_pattern = r'"[^"]*"'
        for match in re.finditer(string_pattern, content):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text_area.tag_add("string", start, end)
    
    def save(self):
        script = self.text_area.get("1.0", "end-1c")
        if self.on_save:
            self.on_save(script)
        self.window.destroy()
    
    def show_help(self):
        help_window = tk.Toplevel(self.window)
        help_window.title("Script Language Help")
        help_window.geometry("500x400")
        
        text = tk.Text(help_window, wrap="word", font=("Consolas", 10))
        text.pack(fill="both", expand=True, padx=5, pady=5)
        
        help_text = """Available Commands:

Object.AddMove(x, y, t)     - Add movement to object over t ms
Object.SetPos(x, y, t)      - Set object position over t ms
Object.AddSize(w, h, t)     - Add size change over t ms
Object.SetSize(w, h, t)     - Set size over t ms
Object.Visible(true/false)  - Object visibility

Player.WalkSpeed(speed)     - Walking speed
Player.JumpPower(power)     - Jump power
Player.Size(w, h, t)        - Player size over t ms

Snow.Text(txt, t)          - Snow text

World.reset                - World reset
World.gravity(VelX, VelY)  - Gravity

var Text = Text            - Variable declaration

wait(t)                    - Wait for t milliseconds

loop:{                     - Infinite loop
-- code
}

if var = text then:{       - Condition
-- code
}

elif var = text then:{     - Else if
-- code
}

else:{                     - Else
-- code
}

-- single line comment

-\
multiline comment
\- 

t - time in milliseconds
"""
        text.insert("1.0", help_text)
        text.config(state="disabled")


class Engine:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Editor + Game")

        self.settings = {"speed": 4.0, "gravity": 0.8, "jump": 12.0}

        self.cam_x = 0
        self.cam_y = 0
        self.zoom = 1.0
        self.cam_drag = None

        self.main = tk.Frame(self.root)
        self.main.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.main, width=700, height=600, bg="#1e1e1e")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.ui = tk.Frame(self.main, width=220)
        self.ui.pack(side="right", fill="y")

        self.props = {}
        for p in ["x", "y", "w", "h"]:
            f = tk.Frame(self.ui)
            f.pack()
            tk.Label(f, text=p).pack(side="left")
            e = tk.Entry(f, width=7)
            e.pack(side="right")
            self.props[p] = e

        self.visible_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self.ui, text="Visible", variable=self.visible_var).pack()

        self.text_entry = tk.Entry(self.ui)
        self.text_entry.pack_forget()

        self.scale_props = {}
        for p in ["target_w", "target_h", "scale_speed"]:
            f = tk.Frame(self.ui)
            tk.Label(f, text=p).pack(side="left")
            e = tk.Entry(f, width=7)
            e.pack(side="right")
            self.scale_props[p] = (f, e)
            f.pack_forget()

        self.boost_props = {}
        for p in ["boost_angle", "boost_power"]:
            f = tk.Frame(self.ui)
            tk.Label(f, text=p).pack(side="left")
            e = tk.Entry(f, width=7)
            e.pack(side="right")
            self.boost_props[p] = (f, e)
            f.pack_forget()

        self.script_trigger_props = {}
        script_trigger_frame = tk.Frame(self.ui)
        self.script_trigger_props["frame"] = script_trigger_frame
        
        tk.Label(script_trigger_frame, text="Script Trigger:").pack()
        self.script_trigger_type_var = tk.StringVar(value="collision")
        tk.OptionMenu(script_trigger_frame, self.script_trigger_type_var, "collision", "always", "once").pack()
        
        self.script_one_shot_var = tk.BooleanVar(value=True)
        tk.Checkbutton(script_trigger_frame, text="One Shot", variable=self.script_one_shot_var).pack()
        
        self.script_trigger_props["type"] = self.script_trigger_type_var
        self.script_trigger_props["one_shot"] = self.script_one_shot_var

        self.type_var = tk.StringVar(value="box")
        type_menu = tk.OptionMenu(
            self.ui,
            self.type_var,
            "box", "wall", "player", "sign",
            "scale_trigger", "boost_panel", "reset_trigger"
        )
        type_menu.pack()

        tk.Label(self.ui, text="--- Scripts ---", font=("Arial", 10, "bold")).pack(pady=5)
        tk.Button(self.ui, text="Add Script", command=self.add_script).pack(fill="x", pady=2)
        tk.Button(self.ui, text="Edit Script", command=self.edit_script).pack(fill="x", pady=2)
        tk.Button(self.ui, text="Delete Script", command=self.delete_script).pack(fill="x", pady=2)
        
        self.script_indicator = tk.Label(self.ui, text="Script: none", fg="red")
        self.script_indicator.pack(pady=2)

        tk.Label(self.ui, text="--- Objects ---", font=("Arial", 10, "bold")).pack(pady=5)
        tk.Button(self.ui, text="Apply", command=self.apply_props).pack(fill="x")
        tk.Button(self.ui, text="Add Box", command=lambda: self.add_obj("box")).pack(fill="x")
        tk.Button(self.ui, text="Add Wall", command=lambda: self.add_obj("wall")).pack(fill="x")
        tk.Button(self.ui, text="Add Player", command=lambda: self.add_obj("player")).pack(fill="x")
        tk.Button(self.ui, text="Add Sign", command=lambda: self.add_obj("sign")).pack(fill="x")
        tk.Button(self.ui, text="Add Boost", command=lambda: self.add_obj("boost_panel")).pack(fill="x")
        tk.Button(self.ui, text="Add Reset", command=lambda: self.add_obj("reset_trigger")).pack(fill="x")
        tk.Button(self.ui, text="Add Scale", command=lambda: self.add_obj("scale_trigger")).pack(fill="x")

        tk.Button(self.ui, text="Import JSON", command=self.import_json).pack(fill="x")
        tk.Button(self.ui, text="Export JSON", command=self.export_json).pack(fill="x")
        tk.Button(self.ui, text="Export PY Game", command=self.export_python_game).pack(fill="x")

        tk.Button(self.ui, text="Delete", command=self.delete_selected).pack(fill="x")
        tk.Button(self.ui, text="Play", command=self.start_game).pack(fill="x")

        self.objects = []
        self.selected = None
        self.drag_offset = (0, 0)

        self.canvas.bind("<Button-1>", self.select_object)
        self.canvas.bind("<B1-Motion>", self.drag_object)
        self.canvas.bind("<Button-3>", self.start_cam_drag)
        self.canvas.bind("<B3-Motion>", self.drag_cam)
        self.canvas.bind("<MouseWheel>", self.zoom_cam)

        self.editor_loop()
        self.root.mainloop()

    def add_obj(self, type):
        self.objects.append(GameObject(self.cam_x + 100, self.cam_y + 100, 60, 60, type))

    def delete_selected(self):
        if self.selected in self.objects:
            self.objects.remove(self.selected)
            self.selected = None
            self.sync_ui()

    def screen_to_world(self, x, y):
        return x / self.zoom + self.cam_x, y / self.zoom + self.cam_y

    def select_object(self, event):
        wx, wy = self.screen_to_world(event.x, event.y)
        for o in reversed(self.objects):
            if o.contains(wx, wy):
                self.selected = o
                self.drag_offset = (wx - o.x, wy - o.y)
                self.sync_ui()
                return
        self.selected = None
        self.sync_ui()

    def drag_object(self, event):
        if self.selected:
            wx, wy = self.screen_to_world(event.x, event.y)
            self.selected.x = wx - self.drag_offset[0]
            self.selected.y = wy - self.drag_offset[1]
            self.sync_ui()

    def start_cam_drag(self, event):
        self.cam_drag = (event.x, event.y)

    def drag_cam(self, event):
        if self.cam_drag:
            dx = (event.x - self.cam_drag[0]) / self.zoom
            dy = (event.y - self.cam_drag[1]) / self.zoom
            self.cam_x -= dx
            self.cam_y -= dy
            self.cam_drag = (event.x, event.y)

    def zoom_cam(self, event):
        factor = 1.1 if event.delta > 0 else 0.9
        mx, my = self.screen_to_world(event.x, event.y)
        self.zoom *= factor
        self.cam_x = mx - event.x / self.zoom
        self.cam_y = my - event.y / self.zoom

    def sync_ui(self):
        if self.selected:
            if self.selected.script and self.selected.script.strip():
                self.script_indicator.config(text="Script: yes", fg="green")
            else:
                self.script_indicator.config(text="Script: no", fg="red")
        else:
            self.script_indicator.config(text="Script: no", fg="red")
        
        if not self.selected:
            return

        self.text_entry.pack_forget()
        for f, _ in self.scale_props.values():
            f.pack_forget()
        for f, _ in self.boost_props.values():
            f.pack_forget()
        self.script_trigger_props["frame"].pack_forget()

        for k in self.props:
            self.props[k].delete(0, tk.END)
            self.props[k].insert(0, int(getattr(self.selected, k)))

        self.visible_var.set(self.selected.visible)
        self.type_var.set(self.selected.type)

        if self.selected.type == "sign":
            self.text_entry.pack()
            self.text_entry.delete(0, tk.END)
            self.text_entry.insert(0, self.selected.text)

        if self.selected.type == "scale_trigger":
            for k, (f, e) in self.scale_props.items():
                f.pack()
                e.delete(0, tk.END)
                e.insert(0, getattr(self.selected, k))

        if self.selected.type == "boost_panel":
            for k, (f, e) in self.boost_props.items():
                f.pack()
                e.delete(0, tk.END)
                e.insert(0, getattr(self.selected, k))
                
        if self.selected.script and self.selected.script.strip():
            self.script_trigger_props["frame"].pack()
            self.script_trigger_type_var.set(self.selected.script_trigger_type)
            self.script_one_shot_var.set(self.selected.script_one_shot)

    def apply_props(self):
        if not self.selected:
            return
        for k in self.props:
            setattr(self.selected, k, float(self.props[k].get()))
        self.selected.type = self.type_var.get()
        self.selected.visible = self.visible_var.get()

        if self.selected.type == "sign":
            self.selected.text = self.text_entry.get()

        if self.selected.type == "scale_trigger":
            for k, (_, e) in self.scale_props.items():
                setattr(self.selected, k, float(e.get()))

        if self.selected.type == "boost_panel":
            for k, (_, e) in self.boost_props.items():
                setattr(self.selected, k, float(e.get()))
                
        if self.selected.script and self.selected.script.strip():
            self.selected.script_trigger_type = self.script_trigger_type_var.get()
            self.selected.script_one_shot = self.script_one_shot_var.get()

    def add_script(self):
        if not self.selected:
            return
        self.edit_script()

    def edit_script(self):
        if not self.selected:
            return
        
        current_script = getattr(self.selected, 'script', '')
        
        def save_script(new_script):
            self.selected.script = new_script
            self.sync_ui()
        
        editor = ScriptEditor(self.root, current_script, save_script)

    def delete_script(self):
        if not self.selected:
            return
        
        self.selected.script = ""
        self.sync_ui()

    def export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump([o.to_dict() for o in self.objects], f, indent=2)

    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.objects = [GameObject.from_dict(d) for d in data]
        self.selected = None
        self.sync_ui()

    def editor_loop(self):
        self.canvas.delete("all")
        for o in self.objects:
            o.draw(self.canvas, self.cam_x, self.cam_y, self.zoom, o is self.selected, is_editor=True)
        self.root.after(16, self.editor_loop)

    def start_game(self):
        game = tk.Toplevel(self.root)
        canvas = tk.Canvas(game, width=700, height=600, bg="black")
        canvas.pack()

        objs = [o.copy() for o in self.objects]
        player_obj = next((o for o in objs if o.type == "player"), None)
        if not player_obj:
            return
            
        walls = [o for o in objs if o.type == "wall"]
        boosts = [o for o in objs if o.type == "boost_panel"]
        resets = [o for o in objs if o.type == "reset_trigger"]
        scales = [o for o in objs if o.type == "scale_trigger"]
        signs = [o for o in objs if o.type == "sign"]
        script_objs = [o for o in objs if o.script and o.script.strip()]

        player_start = dict(x=player_obj.x, y=player_obj.y, w=player_obj.w, h=player_obj.h)

        keys = set()
        game.bind("<KeyPress>", lambda e: keys.add(e.keysym))
        game.bind("<KeyRelease>", lambda e: keys.discard(e.keysym))

        vx = vy = 0
        on_ground = False
        
        script_variables = {}
        script_states = {}
        
        for obj in script_objs:
            script_states[obj] = {
                'lines': obj.script.split('\n'),
                'current_line': 0,
                'in_loop': False,
                'loop_start': 0,
                'in_if': False,
                'skip_until_else': False,
                'skip_until_end': False,
                'executing': False
            }

        def collide(a, b):
            return not (
                a.x + a.w <= b.x or
                a.x >= b.x + b.w or
                a.y + a.h <= b.y or
                a.y >= b.y + b.h
            )
            
        def parse_params(param_str):
            params = []
            current = ""
            in_string = False
            for char in param_str:
                if char == '"' and not in_string:
                    in_string = True
                    current += char
                elif char == '"' and in_string:
                    in_string = False
                    current += char
                elif char == ',' and not in_string:
                    params.append(current.strip())
                    current = ""
                else:
                    current += char
            if current:
                params.append(current.strip())
            return params
            
        def execute_script_line(line, owner):
            line = line.strip()
            if not line or line.startswith("--") or line.startswith("-\\") or line.startswith("\\-"):
                return "continue"
                
            if line.startswith("wait("):
                try:
                    params = parse_params(line[5:-1])
                    if params:
                        wait_time = float(params[0])
                        owner.is_waiting = True
                        owner.wait_time = wait_time
                        owner.wait_start = time.time()
                        return "wait"
                except:
                    pass
                return "continue"
                
            elif line.startswith("Object."):
                cmd = line[7:].split("(")[0]
                param_str = line[line.find("(")+1:line.find(")")]
                params = parse_params(param_str)
                
                if cmd == "AddMove":
                    if len(params) == 3:
                        dx = float(params[0])
                        dy = float(params[1])
                        duration = float(params[2])
                        owner.move_start_x = owner.x
                        owner.move_start_y = owner.y
                        owner.move_target_x = owner.x + dx
                        owner.move_target_y = owner.y + dy
                        owner.move_duration = max(duration, 1)
                        owner.move_elapsed = 0
                        owner.is_moving = True
                        return "animation"
                        
                elif cmd == "SetPos":
                    if len(params) == 3:
                        target_x = float(params[0])
                        target_y = float(params[1])
                        duration = float(params[2])
                        owner.move_start_x = owner.x
                        owner.move_start_y = owner.y
                        owner.move_target_x = target_x
                        owner.move_target_y = target_y
                        owner.move_duration = max(duration, 1)
                        owner.move_elapsed = 0
                        owner.is_moving = True
                        return "animation"
                        
                elif cmd == "AddSize":
                    if len(params) == 3:
                        dw = float(params[0])
                        dh = float(params[1])
                        duration = float(params[2])
                        owner.size_start_w = owner.w
                        owner.size_start_h = owner.h
                        owner.size_target_w = owner.w + dw
                        owner.size_target_h = owner.h + dh
                        owner.size_duration = max(duration, 1)
                        owner.size_elapsed = 0
                        owner.is_resizing = True
                        return "animation"
                        
                elif cmd == "SetSize":
                    if len(params) == 3:
                        target_w = float(params[0])
                        target_h = float(params[1])
                        duration = float(params[2])
                        owner.size_start_w = owner.w
                        owner.size_start_h = owner.h
                        owner.size_target_w = target_w
                        owner.size_target_h = target_h
                        owner.size_duration = max(duration, 1)
                        owner.size_elapsed = 0
                        owner.is_resizing = True
                        return "animation"
                        
                elif cmd == "Visible":
                    if "true" in line.lower():
                        owner.visible = True
                    elif "false" in line.lower():
                        owner.visible = False
                        
            elif line.startswith("Player."):
                cmd = line[7:].split("(")[0]
                param_str = line[line.find("(")+1:line.find(")")]
                params = parse_params(param_str)
                
                if cmd == "WalkSpeed":
                    if params:
                        self.settings["speed"] = float(params[0])
                        
                elif cmd == "JumpPower":
                    if params:
                        self.settings["jump"] = float(params[0])
                        
                elif cmd == "Size":
                    if len(params) == 3:
                        target_w = float(params[0])
                        target_h = float(params[1])
                        duration = float(params[2])
                        player_obj.size_start_w = player_obj.w
                        player_obj.size_start_h = player_obj.h
                        player_obj.size_target_w = target_w
                        player_obj.size_target_h = target_h
                        player_obj.size_duration = max(duration, 1)
                        player_obj.size_elapsed = 0
                        player_obj.is_resizing = True
                        return "animation"
                        
            elif line.startswith("World."):
                cmd = line[6:].split("(")[0]
                
                if cmd == "reset":
                    player_obj.x = player_start["x"]
                    player_obj.y = player_start["y"]
                    player_obj.w = player_start["w"]
                    player_obj.h = player_start["h"]
                    return "continue"
                    
                elif cmd == "gravity":
                    param_str = line[line.find("(")+1:line.find(")")]
                    params = parse_params(param_str)
                    if len(params) == 2:
                        self.settings["gravity"] = float(params[1])
                        
            elif line.startswith("var "):
                parts = line[4:].split("=")
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    var_value = parts[1].strip().strip('"')
                    script_variables[var_name] = var_value
                    
            elif line.startswith("loop:{"):
                state = script_states[owner]
                state['in_loop'] = True
                state['loop_start'] = state['current_line']
                
            elif line.startswith("if"):
                state = script_states[owner]
                condition = line.split("then:")[0][2:].strip()
                result = False
                
                if "=" in condition:
                    left, right = condition.split("=")
                    left = left.strip()
                    right = right.strip().strip('"')
                    if left in script_variables and script_variables[left] == right:
                        result = True
                        state['in_if'] = True
                        state['skip_until_else'] = False
                        state['skip_until_end'] = False
                    else:
                        state['skip_until_else'] = True
                        state['skip_until_end'] = True
                        
            elif line.startswith("elif"):
                state = script_states[owner]
                if state['skip_until_else']:
                    condition = line.split("then:")[0][4:].strip()
                    if "=" in condition:
                        left, right = condition.split("=")
                        left = left.strip()
                        right = right.strip().strip('"')
                        if left in script_variables and script_variables[left] == right:
                            state['skip_until_else'] = False
                            state['skip_until_end'] = False
                            
            elif line.startswith("else:{"):
                state = script_states[owner]
                if state['skip_until_end']:
                    state['skip_until_end'] = False
                    state['skip_until_else'] = False
                    
            elif line == "}":
                state = script_states[owner]
                if state['in_loop']:
                    state['current_line'] = state['loop_start']
                else:
                    state['in_if'] = False
                    state['skip_until_else'] = False
                    state['skip_until_end'] = False
                    
            return "continue"
            
        def update_script_execution(obj, delta_time):
            state = script_states[obj]
            
            if obj.is_waiting:
                if time.time() - obj.wait_start < obj.wait_time / 1000.0:
                    return True
                else:
                    obj.is_waiting = False
                    
            if obj.is_moving or obj.is_resizing:
                return True
                
            while state['current_line'] < len(state['lines']):
                line = state['lines'][state['current_line']]
                state['current_line'] += 1
                
                if state['skip_until_end'] or state['skip_until_else']:
                    if line.strip() == "}" or line.strip().startswith("else:") or line.strip().startswith("elif"):
                        state['skip_until_end'] = False
                        state['skip_until_else'] = False
                    continue
                    
                result = execute_script_line(line, obj)
                
                if result == "wait" or result == "animation":
                    return True
                    
            if state['in_loop']:
                state['current_line'] = state['loop_start']
                return True
                
            return False

        def loop():
            nonlocal vx, vy, on_ground
            canvas.delete("all")
            
            delta_time = 16

            for obj in objs:
                obj.update_animation(delta_time)
            
            for obj in script_objs:
                if obj.script and obj.script.strip():
                    should_execute = False
                    
                    if obj.script_trigger_type == "collision":
                        if collide(player_obj, obj):
                            should_execute = True
                    elif obj.script_trigger_type == "always":
                        should_execute = True
                    elif obj.script_trigger_type == "once":
                        if not obj.script_activated:
                            should_execute = True
                            obj.script_activated = True
                    
                    if should_execute:
                        if obj not in script_states:
                            script_states[obj] = {
                                'lines': obj.script.split('\n'),
                                'current_line': 0,
                                'in_loop': False,
                                'loop_start': 0,
                                'in_if': False,
                                'skip_until_else': False,
                                'skip_until_end': False,
                                'executing': False
                            }
                        
                        update_script_execution(obj, delta_time)
                        
                        if obj.script_one_shot:
                            obj.script_activated = True

            vx = 0
            if 'a' in keys: vx = -self.settings["speed"]
            if 'd' in keys: vx = self.settings["speed"]

            player_obj.x += vx
            for w in walls:
                if collide(player_obj, w):
                    player_obj.x = w.x - player_obj.w if vx > 0 else w.x + w.w

            vy += self.settings["gravity"]
            if 'space' in keys and on_ground:
                vy = -self.settings["jump"]

            player_obj.y += vy
            on_ground = False

            for w in walls:
                if collide(player_obj, w) and vy > 0:
                    player_obj.y = w.y - player_obj.h
                    vy = 0
                    on_ground = True

            for s in scales:
                if collide(player_obj, s):
                    player_obj.w += (s.target_w - player_obj.w) * s.scale_speed
                    player_obj.h += (s.target_h - player_obj.h) * s.scale_speed

            for b in boosts:
                if collide(player_obj, b):
                    r = math.radians(b.boost_angle)
                    vx = math.cos(r) * b.boost_power
                    vy = -math.sin(r) * b.boost_power

            for r in resets:
                if collide(player_obj, r):
                    player_obj.x = player_start["x"]
                    player_obj.y = player_start["y"]
                    player_obj.w = player_start["w"]
                    player_obj.h = player_start["h"]
                    vx = vy = 0
                    break

            for s in signs:
                if collide(player_obj, s):
                    canvas.create_text(350, 50, text=s.text, fill="white", font=("Arial", 16))

            for o in objs:
                if o.visible:
                    o.draw(canvas, player_obj.x - 350, player_obj.y - 300, 1, is_editor=False)

            game.after(16, loop)

        loop()

    def export_python_game(self):
        path = filedialog.asksaveasfilename(defaultextension=".py")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write("# standalone game export is not implemented yet\n")


if __name__ == "__main__":
    Engine()

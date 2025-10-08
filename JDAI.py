import json, os, re, math, threading, requests
from datetime import datetime
from functools import partial
from kivy.config import Config
Config.set('kivy','keyboard_mode','systemandmulti')
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.image import AsyncImage
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle

# ---------- Storage ----------
DATA_DIR = os.path.join(os.path.expanduser("~"), "local_ai_data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
KB_FILE = os.path.join(DATA_DIR, "knowledge.json")
USER_FILE = os.path.join(DATA_DIR, "user.json")
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

DEFAULT_KB = {
    "what is your name":"I am JD AI, your online assistant.",
    "hello":"Hello! How can I help you today?",
    "how are you":"I'm always running fine!",
    "help":"Try: math expressions, teach:Q=>A, show knowledge, save conversation.",
    "your location":"Gujarat-Bhavnagar-Sidsar Road",
    "your owner name":"Jaydipsinh Revar",
    "your college name":"GMIU"
}

def load_json(path, default):
    try:
        with open(path,"r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path,data):
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=2,ensure_ascii=False)

knowledge = load_json(KB_FILE, DEFAULT_KB.copy())
history = load_json(HISTORY_FILE, [])
user = load_json(USER_FILE, {})
if "name" not in user: user["name"] = None
if "wallpaper" not in user: user["wallpaper"] = None
save_json(USER_FILE, user)

# ---------- Math ----------
SAFE_MATH = {
    "sin": math.sin,"cos": math.cos,"tan": math.tan,"asin": math.asin,"acos": math.acos,"atan": math.atan,
    "sqrt": math.sqrt,"log": math.log,"ln": math.log,"log10": math.log10,"factorial": math.factorial,
    "pi": math.pi,"e": math.e,"abs": abs,"round": round,"pow": pow
}

def _safe_eval(expr):
    expr = expr.replace("^","**")
    expr = re.sub(r'(\d+)!', r'factorial(\1)', expr)
    try:
        return str(eval(expr, {"__builtins__":None}, SAFE_MATH))
    except Exception as e:
        return "Math error: "+str(e)

# ---------- AI ----------
def normalize(txt):
    return re.sub(r'[^a-z0-9\s]', '', txt.lower().strip())

def respond(text):
    n=normalize(text)
    if user["name"] is None:
        user["name"]=text.strip().title()
        save_json(USER_FILE,user)
        return f"Nice to meet you {user['name']}! I will remember your name."
    if text.lower().startswith("teach:"):
        try:
            q,a=text[6:].split("=>",1)
            knowledge[normalize(q)]=a.strip()
            save_json(KB_FILE,knowledge)
            return f"Learned: '{q.strip()}' → '{a.strip()}'"
        except:
            return "Teach format: teach:question=>answer"
    if n in ("show knowledge","knowledge","show kb"):
        return "\n".join([f"{q} → {a}" for q,a in knowledge.items()])
    if "save conversation" in n:
        save_json(HISTORY_FILE, history)
        save_json(KB_FILE, knowledge)
        save_json(USER_FILE, user)
        return "Saved."
    math_expr = re.fullmatch(r'[0-9\.\+\-\*\/\(\)\s%^!eEpi]+', text)
    if text.lower().startswith("calc "):
        return _safe_eval(text[5:])
    elif math_expr:
        return _safe_eval(text)
    if n in knowledge:
        return knowledge[n]
    if any(w in n for w in ["hello","hi","hey"]):
        return f"Hello {user.get('name','')}! Ask 'help'."
    if "time" in n:
        return datetime.now().strftime("%H:%M:%S")
    if "date" in n:
        return datetime.now().strftime("%A, %d %B %Y")
    return f"Sorry {user.get('name','')}, I don't understand. Try 'help'."

# ---------- Wallpapers ----------
WALLPAPERS = [
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&w=800&q=80",
    "https://images.unsplash.com/photo-1493558103817-58b2924bce98?auto=format&fit=crop&w=800&q=80",
    "https://images.unsplash.com/photo-1519125323398-675f0ddb6308?auto=format&fit=crop&w=800&q=80"
]

# ---------- Wallpaper Downloader ----------
def download_all_wallpapers():
    def download(url):
        try:
            local_path = os.path.join(DATA_DIR, os.path.basename(url))
            r = requests.get(url, stream=True, timeout=10)
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
        except:
            pass
    for url in WALLPAPERS:
        t = threading.Thread(target=download, args=(url,))
        t.start()

# ---------- UI ----------
class Bubble(Label):
    def __init__(self, text, who, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.size_hint_y = None
        self.halign = "left" if who=="ai" else "right"
        self.valign = "middle"
        self.padding = (12,10)
        self.text_size = (Window.width*0.7, None)
        self.bind(texture_size=self.setter("size"))
        with self.canvas.before:
            if who=="ai":
                Color(0.12, 0.56, 1, 0.85)
            else:
                Color(0.2, 0.8, 0.3, 0.85)
            self.bg = Rectangle(size=self.size,pos=self.pos)
        self.bind(pos=self.update_bg, size=self.update_bg)

    def update_bg(self,*a):
        self.bg.pos=self.pos
        self.bg.size=self.size

class ChatUI(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bg_image = AsyncImage(source=user.get("wallpaper") or WALLPAPERS[0], allow_stretch=True, keep_ratio=False)
        self.add_widget(self.bg_image)
        self.main_box = BoxLayout(orientation='vertical', padding=5, spacing=5)
        self.add_widget(self.main_box)
        top = BoxLayout(size_hint_y=None,height=50,spacing=5)
        top.add_widget(Label(text="[b]JD AI[/b]",markup=True,size_hint_x=0.4))
        btn_wall = Button(text="Wallpaper",size_hint_x=0.2,background_normal='',background_color=(0.4,0.6,1,1))
        btn_wall.bind(on_release=self.open_wallpapers)
        top.add_widget(btn_wall)
        btn_save = Button(text="Save",size_hint_x=0.2,background_normal='',background_color=(0.8,0.3,0.6,1))
        btn_save.bind(on_release=self.save_all)
        top.add_widget(btn_save)
        btn_clear = Button(text="Clear Chat", size_hint_x=0.2,
                           background_normal='', background_color=(1, 0.4, 0.3, 1))
        btn_clear.bind(on_release=self.clear_chat)
        top.add_widget(btn_clear)
        self.main_box.add_widget(top)
        self.scroll = ScrollView(size_hint=(1,1))
        self.box = BoxLayout(orientation='vertical',size_hint_y=None,spacing=10,padding=(5,5))
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        self.main_box.add_widget(self.scroll)
        bottom = BoxLayout(size_hint_y=None,height=50,spacing=5)
        self.input = TextInput(hint_text="Type message...",multiline=False)
        self.input.bind(on_text_validate=self.on_enter)
        btn_send = Button(text="Send",size_hint_x=0.2,background_normal='',background_color=(0.3,0.9,0.5,1))
        btn_send.bind(on_release=self.on_enter)
        bottom.add_widget(self.input)
        bottom.add_widget(btn_send)
        self.main_box.add_widget(bottom)
        for msg in history:
            self.add_message(msg['user'],'user')
            self.add_message(msg['ai'],'ai')

    def add_message(self,msg,who):
        b = Bubble(msg,who)
        self.box.add_widget(b)
        Clock.schedule_once(lambda dt: self.scroll.scroll_to(b),0.05)

    def on_enter(self,*args):
        txt = self.input.text.strip()
        if not txt: return
        self.add_message(txt,"user")
        self.input.text=""
        resp = respond(txt)
        self.add_message(resp,"ai")
        history.append({"user":txt,"ai":resp})

    def save_all(self,*args):
        save_json(HISTORY_FILE,history)
        save_json(KB_FILE,knowledge)
        save_json(USER_FILE,user)
        Popup(title="Saved",content=Label(text="All data saved!"),size_hint=(0.7,0.3)).open()

    def open_wallpapers(self,*args):
        grid = GridLayout(cols=3, spacing=5, padding=5, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        for url in WALLPAPERS:
            img = AsyncImage(source=url, size_hint_y=None, height=150)
            img.bind(on_touch_down=partial(self.select_wallpaper,url))
            grid.add_widget(img)
        scroll = ScrollView(size_hint=(1,1))
        scroll.add_widget(grid)
        popup = Popup(title="Select Wallpaper", content=scroll, size_hint=(0.9,0.9))
        self.wall_popup = popup
        popup.open()

    def select_wallpaper(self,url,instance,touch):
        if instance.collide_point(*touch.pos):
            user['wallpaper'] = url
            save_json(USER_FILE,user)
            self.bg_image.source = url
            self.wall_popup.dismiss()

    def clear_chat(self, *args):
        self.box.clear_widgets()
        history.clear()
        save_json(HISTORY_FILE, history)
        Popup(title="Cleared", content=Label(text="Chat history cleared."),
              size_hint=(0.7, 0.3)).open()

# ---------- LocalAI App ----------
class LocalAIApp(App):
    def build(self):
        # Start downloading wallpapers in background
        threading.Thread(target=download_all_wallpapers).start()
        return ChatUI()

if __name__=="__main__":
    LocalAIApp().run()
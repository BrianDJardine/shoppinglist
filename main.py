import json, os, shutil, requests, certifi
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, Metrics
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.spinner import SpinnerOption

class CustomSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        self.font_size = app.f_size
        self.height = app.row_height # Matches the row height to the font

# -------------------------
# List Item Row
# -------------------------
class ListItem(BoxLayout):
    def __init__(self, item_ref, text, background_color, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()

        self.item_ref = item_ref
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = app.row_height
        self.padding = [dp(8), dp(4)]
        self.spacing = dp(8)

        with self.canvas.before:
            Color(*background_color)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        icon_size = app.row_height * 0.6

        self.check_btn = Button(
            size_hint=(None, None),
            size=(icon_size, icon_size),
            pos_hint={'center_y': 0.5},
            background_normal='',
            background_color=(0.9, 0.9, 0.9, 1)
        )
        self.check_btn.bind(on_release=self.trigger_done)
        self.add_widget(self.check_btn)

        self.label = Label(
            text=text,
            markup=True,
            halign='left',
            valign='middle',
            font_size=app.f_size,
            bold=True,
            shorten=True,
            shorten_from='right',
            size_hint_x=1,
            color=(0, 0, 0, 1)
        )
        self.label.bind(size=self.label.setter('text_size'))
        self.add_widget(self.label)

        qty_box = BoxLayout(
            size_hint=(None, 1),
            width=app.row_height * 1.2,
            spacing=dp(4)
        )

        minus_btn = Button(
            text="-",
            font_size=app.f_size * 0.8,
            background_color=(0.7, 0.3, 0.3, 1)
        )
        minus_btn.bind(on_release=lambda x: app.adjust_quantity(self.item_ref, -1))

        plus_btn = Button(
            text="+",
            font_size=app.f_size * 0.8,
            background_color=(0.3, 0.7, 0.3, 1)
        )
        plus_btn.bind(on_release=lambda x: app.adjust_quantity(self.item_ref, 1))

        qty_box.add_widget(minus_btn)
        qty_box.add_widget(plus_btn)

        self.add_widget(qty_box)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def trigger_done(self, instance):
        self.check_btn.background_color = (0.2, 0.8, 0.2, 1) 
        Clock.schedule_once(lambda dt: App.get_running_app().mark_done(self.item_ref), 0.5)

# --- CATEGORY SCREEN ---
class CategoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.container = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

        #header = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10), padding=[dp(10), 0])
        header =BoxLayout(
            size_hint_y=None,
            height=App.get_running_app().row_height,
            spacing=dp(5)
        )
        with header.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            self.rect = Rectangle(size=header.size, pos=header.pos)
        header.bind(size=self._update_header_rect, pos=self._update_header_rect)

        back_btn = Button(background_normal='back.png', size_hint=(None, None), size=(dp(35), dp(35)), pos_hint={'center_y': 0.5})
        back_btn.bind(on_release=lambda x: setattr(App.get_running_app().sm, 'current', 'main'))
        header.add_widget(back_btn)
        header.add_widget(Label(text="CATEGORIES", font_size=dp(20), bold=True))
        self.container.add_widget(header)

        add_box = BoxLayout(size_hint_y=None, height=App.get_running_app().row_height, spacing=dp(5))
        self.new_cat_input = TextInput(hint_text="New Category...", multiline=False)
        add_btn = Button(text="ADD", size_hint_x=0.3, background_color=(0.2, 0.7, 0.3, 1), bold=True)
        add_btn.bind(on_release=self.add_category)
        add_box.add_widget(self.new_cat_input)
        add_box.add_widget(add_btn)
        self.container.add_widget(add_box)

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.cat_list_layout = GridLayout(cols=1, size_hint_y=None, spacing=dp(5))
        self.cat_list_layout.bind(minimum_height=self.cat_list_layout.setter('height'))

        self.scroll.add_widget(self.cat_list_layout)
        self.container.add_widget(self.scroll)
        self.add_widget(self.container)
        
    def on_pre_enter(self): 
        self.refresh_categories()

    def _update_header_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def refresh_categories(self):
        self.cat_list_layout.clear_widgets()
        app = App.get_running_app()
        if not app.categories: return
        sorted_cats = sorted(app.categories.items(), key=lambda x: x[1].get('order', 99))
        
        for name, data in sorted_cats:
            row = BoxLayout(size_hint_y=None, height=app.row_height, spacing=dp(5))
            order_box = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(45))
            up = Button(text="^"); up.bind(on_release=lambda x, n=name: self.move_cat(n, -1))
            dn = Button(text="v"); dn.bind(on_release=lambda x, n=name: self.move_cat(n, 1))
            order_box.add_widget(up); order_box.add_widget(dn)
            
            lbl = Button(text=name.upper(), font_size=app.f_size, bold=True, background_color=(0.2, 0.2, 0.2, 1), halign='left', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            lbl.bind(on_release=lambda x, n=name: self.rename_category_popup(n))
            
            row.add_widget(order_box); row.add_widget(lbl)
            if name != "Uncategorized":
                del_btn = Button(text="X", size_hint_x=None, width=dp(50), background_color=(0.8, 0.2, 0.2, 1))
                del_btn.bind(on_release=lambda x, n=name: self.delete_category(n))
                row.add_widget(del_btn)
            self.cat_list_layout.add_widget(row)

    def rename_category_popup(self, old_name):
        if old_name == "Uncategorized": return
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        inp = TextInput(text=old_name, multiline=False, size_hint_y=None, height=App.get_running_app().row_height)
        content.add_widget(inp)
        btn = Button(text="UPDATE", size_hint_y=None, height=App.get_running_app().row_height, bold=True)
        content.add_widget(btn); p = Popup(title="Rename", content=content, size_hint=(0.8, 0.4))
        def do_rename(x):
            new_name = inp.text.strip()
            app = App.get_running_app()
            if new_name and new_name != old_name:
                app.categories[new_name] = app.categories.pop(old_name)
                for list_name in app.all_lists:
                    for item in app.all_lists[list_name]:
                        if item['cat'] == old_name: item['cat'] = new_name
                app.save_data(); self.refresh_categories(); app.refresh_ui()
            p.dismiss()
        btn.bind(on_release=do_rename); p.open()

    def add_category(self, instance):
        name = self.new_cat_input.text.strip()
        if name:
            app = App.get_running_app()
            if name not in app.categories:
                orders = [d['order'] for n, d in app.categories.items() if d['order'] < 99]
                new_order = max(orders) + 1 if orders else 1
                app.categories[name] = {'order': new_order, 'keywords': []}
                app.save_data(); self.refresh_categories(); self.new_cat_input.text = ""

    def move_cat(self, name, direction):
        app = App.get_running_app()
        curr_order = app.categories[name]['order']
        target_order = curr_order + direction
        if target_order < 1 or target_order >= 99: return
        for other_name, data in app.categories.items():
            if data['order'] == target_order:
                data['order'] = curr_order
                app.categories[name]['order'] = target_order; break
        app.save_data(); self.refresh_categories(); app.refresh_ui()

    def delete_category(self, name):
        app = App.get_running_app()
        if name in app.categories:
            del app.categories[name]; app.save_data(); self.refresh_categories()

# --- SETTINGS SCREEN ---
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))
        header = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10))
        with header.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            self.rect = Rectangle(size=header.size, pos=header.pos)
        header.bind(size=self._update_header_rect, pos=self._update_header_rect)

        back_btn = Button(background_normal='back.png', size_hint=(None, None), size=(dp(35), dp(35)), pos_hint={'center_y': 0.5})
        back_btn.bind(on_release=lambda x: setattr(App.get_running_app().sm, 'current', 'main'))
        header.add_widget(back_btn)
        header.add_widget(Label(text="SETTINGS", font_size=dp(20), bold=True))
        self.layout.add_widget(header)

        self.layout.add_widget(Label(text="Display Text Size:", size_hint_y=None, height=dp(30)))
        self.font_spinner = Spinner(text="Large", values=("Smallest", "Small", "Medium", "Large"), size_hint_y=None, height=App.get_running_app().row_height)
        self.font_spinner.bind(text=lambda s, t: App.get_running_app().change_font_size(t))
        self.layout.add_widget(self.font_spinner)

        self.id_input = TextInput(multiline=False, size_hint_y=None, height=App.get_running_app().row_height, hint_text="Family ID...")
        self.layout.add_widget(self.id_input)
        save_btn = Button(text="UPDATE ID", size_hint_y=None, height=dp(55), background_color=(0.2, 0.6, 1, 1), bold=True)
        save_btn.bind(on_release=self.apply_id_change)
        self.layout.add_widget(save_btn)

        push_btn = Button(text="FORCE UPLOAD", size_hint_y=None, height=App.get_running_app().row_height, background_color=(0.2, 0.7, 0.3, 1))
        push_btn.bind(on_release=lambda x: App.get_running_app().confirm_action("Upload data?", App.get_running_app().save_data))
        self.layout.add_widget(push_btn)

        pull_btn = Button(text="FORCE DOWNLOAD", size_hint_y=None, height=App.get_running_app().row_height, background_color=(0.7, 0.5, 0.2, 1))
        pull_btn.bind(on_release=lambda x: App.get_running_app().confirm_action("Overwrite from cloud?", App.get_running_app().force_download_confirmed))
        self.layout.add_widget(pull_btn)

        self.layout.add_widget(Widget())
        self.add_widget(self.layout)

    def on_pre_enter(self):
        app = App.get_running_app()
        self.font_spinner.text = app.font_scale
        self.id_input.text = app.family_id

    def apply_id_change(self, instance):
        App.get_running_app().update_family_id(self.id_input.text.strip())

    def _update_header_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

# --- MAIN APP ---
class ShoppingApp(App):
    BASE_URL = "https://shoppinglist-eae1c-default-rtdb.europe-west1.firebasedatabase.app/protect_data/AppV1_Secure_99xCapybarasForever/"

    def build(self):
        # Initial Scaling Setup
        self.font_scale = "Large"
        self.show_completed = False
        local_path = os.path.join(self.user_data_dir, "local_settings.json")
        if os.path.exists(local_path):
            try:
                with open(local_path, 'r') as f:
                    d = json.load(f)
                    self.font_scale = d.get('font_scale', 'Large')
                    self.family_id = d.get('family_id', 'DefaultFamily')
            except: self.family_id = "DefaultFamily"
        else: self.family_id = "DefaultFamily"

        self.update_font_metrics()
        self.load_data()
        self.prediction_drop = DropDown()
        self.sm = ScreenManager()

        self.main_page = Screen(name='main')
        main_layout = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))
        
        # --- HEADER (Scrollable Icons) ---
        header_row = BoxLayout(size_hint_y=None, height=self.row_height * 0.8, spacing=dp(5))
        self.list_spinner = Spinner(text=self.active_list_name, values=list(self.all_lists.keys()),
                                    size_hint_x=0.25, background_color=(0.15, 0.15, 0.15, 1), bold=False, 
                                    font_size=self.f_size, option_cls=CustomSpinnerOption)
        self.list_spinner.bind(text=self.switch_list)
        header_row.add_widget(self.list_spinner)

        # Icon ScrollView prevents squashing on large font phones
        icon_scroll = ScrollView(
                size_hint_x=0.65,
                do_scroll_y=False
            )
        icon_row = BoxLayout(size_hint_x=None, spacing=dp(4))
        icon_row.bind(minimum_width=icon_row.setter('width'))

        def quick_btn(img, callback, tint=(1, 1, 1, 1)):
            b = Button(background_normal=img, on_release=callback, background_color=tint, 
                       size_hint=(None, None), size=(self.row_height * 0.6, self.row_height * 0.6), pos_hint={'center_y': 0.5})
            return b

        icon_row.add_widget(quick_btn('new.png', self.create_new_list, (0.2, 1, 0.2, 1))) 
        icon_row.add_widget(quick_btn('edit.png', self.rename_list_popup, (1, 1, 0.2, 1))) 
        icon_row.add_widget(quick_btn('delete.png', self.confirm_delete_list, (1, 0.3, 0.3, 1))) 
        icon_row.add_widget(quick_btn('cats.png', lambda x: setattr(self.sm, 'current', 'categories')))         
        icon_row.add_widget(quick_btn('settings.png', lambda x: setattr(self.sm, 'current', 'settings')))
        
        self.sync_btn = quick_btn('sync.png', self.sync_now)
        icon_row.add_widget(self.sync_btn)

        icon_scroll.add_widget(icon_row)
        header_row.add_widget(icon_scroll)
        main_layout.add_widget(header_row)

        # INPUT
        input_box = BoxLayout(size_hint_y=None, height=self.row_height, spacing=dp(5))
        self.item_input = TextInput(hint_text='Add item...', multiline=False, font_size=self.f_size)
        self.item_input.bind(text=self.on_type_prediction)
        add_btn = Button(text='ADD', size_hint_x=0.25, background_color=(0.2, 0.7, 0.3, 1), bold=True, on_press=self.process_addition)
        input_box.add_widget(self.item_input)
        input_box.add_widget(add_btn)
        main_layout.add_widget(input_box)

        self.list_layout = GridLayout(cols=1, size_hint_y=None, spacing=dp(6))
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll = ScrollView(); scroll.add_widget(self.list_layout)
        main_layout.add_widget(scroll)

        # STATUS
        status_bar = BoxLayout(size_hint_y=None, height=dp(25))
        self.stats_label = Label(text="0 items", font_size=dp(12), color=(0.7, 0.7, 0.7, 1))
        self.sync_label = Label(text="Sync: Never", font_size=dp(12), color=(0.7, 0.7, 0.7, 1))
        status_bar.add_widget(self.stats_label); status_bar.add_widget(self.sync_label)
        main_layout.add_widget(status_bar)        
        
        # FOOTER
        bot = BoxLayout(size_hint_y=None, height=self.row_height, spacing=dp(5))
        self.done_btn = Button(text="SHOW DONE", on_press=self.toggle_completed, bold=True, font_size=dp(14))
        del_done_btn = Button(text="DEL DONE", background_color=(0.7, 0.3, 0.3, 1), bold=True, on_press=lambda x: self.confirm_action("Delete done?", self.clear_completed), font_size=dp(14))
        clear_btn = Button(text="CLEAR", background_color=(0.9, 0.4, 0.4, 1), bold=True, on_press=lambda x: self.confirm_action("Wipe list?", self.clear_entire_list), font_size=dp(14))
        bot.add_widget(self.done_btn); bot.add_widget(del_done_btn); bot.add_widget(clear_btn)
        main_layout.add_widget(bot)

        self.main_page.add_widget(main_layout); self.sm.add_widget(self.main_page)
        self.sm.add_widget(CategoryScreen(name='categories'))
        self.sm.add_widget(SettingsScreen(name='settings'))

        self.refresh_ui(); return self.sm

    def update_font_metrics(self):
        # Neutralize system font scale
        # If user has 1.5x zoom, we divide by 1.5 to keep physical size consistent
        s = Metrics.fontscale if Metrics.fontscale > 0 else 1.0

        if self.font_scale == "Smallest":
            self.f_size, self.row_height = dp(14/s), dp(55/s)
        elif self.font_scale == "Small":
            self.f_size, self.row_height = dp(18/s), dp(65/s)
        elif self.font_scale == "Medium":
            self.f_size, self.row_height = dp(22/s), dp(75/s)
        else: # Large
            self.f_size, self.row_height = dp(26/s), dp(85/s)

    def change_font_size(self, size):
        self.font_scale = size
        self.update_font_metrics()
        self.item_input.font_size = self.f_size
        local = {'font_scale': self.font_scale, 'family_id': self.family_id}
        with open(os.path.join(self.user_data_dir, "local_settings.json"), 'w') as f:
            json.dump(local, f)
        self.refresh_ui()

    def load_data(self):
        self.categories = {'Uncategorized': {'order': 99, 'keywords': []}}
        self.all_lists = {'Groceries': [{"name": "PLACEHOLDER", "done": False, "cat": "Uncategorized"}]}
        self.active_list_name = 'Groceries'
        self.data_file = os.path.join(self.user_data_dir, f"shopping_data_{self.family_id}.json")

        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    local_data = json.load(f)
                    self.all_lists = local_data.get('all_lists', self.all_lists)
                    self.categories = local_data.get('categories', self.categories)
                    self.active_list_name = local_data.get('active_list_name', self.active_list_name)
            except: pass

    @property
    def cloud_url(self):
        return f"{self.BASE_URL}{self.family_id}.json"

    def save_data(self, instance=None):
        try:
            payload = { self.family_id: {'all_lists': self.all_lists, 'categories': self.categories, 'active_list_name': self.active_list_name} }
            requests.put(self.cloud_url, json=payload, timeout=4, verify=certifi.where())
            self.sync_label.text = f"Synced: {datetime.now().strftime('%H:%M')}"
        except: self.sync_label.text = "Offline (Local Only)"

        with open(self.data_file, 'w') as f:
            json.dump({'all_lists': self.all_lists, 'categories': self.categories, 'active_list_name': self.active_list_name}, f)

    def refresh_ui(self, *args):
        self.list_spinner.text = self.active_list_name
        self.list_spinner.values = list(self.all_lists.keys())        
        self.list_layout.clear_widgets()
        
        items_to_show = [i for i in self.all_lists.get(self.active_list_name, []) if isinstance(i, dict) and i.get('name') != "PLACEHOLDER"]
        items = sorted(items_to_show, key=lambda x: self.categories.get(x.get('cat', 'Uncategorized'), {'order': 99})['order'])
        
        curr_cat = None
        for i in items:
            if i.get('done') and not self.show_completed: continue
            if i.get('cat') != curr_cat:
                curr_cat = i.get('cat', 'Uncategorized')
                self.list_layout.add_widget(Label(text=f"-- {curr_cat.upper()} --", size_hint_y=None, height=dp(30), bold=True, font_size=dp(13)))
            
            qty = i.get('count', 1)
            txt = f"[s]{i['name']}[/s]" if i['done'] else i['name']
            if qty > 1: txt += f" (x{qty})"
            
            row = ListItem(item_ref=i, text=txt, background_color=(0.9, 0.9, 0.9, 1) if i['done'] else (1, 1, 1, 1))
            self.list_layout.add_widget(row)
        self.update_stats()

    def process_addition(self, instance):
        name = self.item_input.text.strip()
        if not name: return
        cat = None
        for cname, details in self.categories.items():
            if any(name.lower() == k.lower() for k in details.get('keywords', [])):
                cat = cname; break
        if cat: self.add_to_list(name, cat); self.item_input.text = ""
        else: self.show_category_popup(name)

    def show_category_popup(self, name):
        app = App.get_running_app()
        outer = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # 1. Neutralize the Title Label
        outer.add_widget(Label(
            text=f"Category for: {name.upper()}", 
            size_hint_y=None, 
            height=app.row_height * 0.8, 
            bold=True,
            font_size=app.f_size,
            color=(1, 1, 1, 1) # White text for the dark popup background
        ))
        
        scroll = ScrollView(size_hint=(1, 1))
        # 2. Use a dynamic height for the grid
        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        
        pop = Popup(title="Select Category", content=outer, size_hint=(0.9, 0.8))
        
        # 3. Neutralize the Category Buttons
        for cat in sorted(self.categories.keys()):
            btn = Button(
                text=cat.upper(), 
                size_hint_y=None, 
                height=app.row_height, # Matches your list row height
                font_size=app.f_size,   # Uses neutralized font
                background_color=(0.2, 0.6, 1, 1),
                halign='center',      # Center text horizontally
                valign='middle',      # Center text vertically
                text_size=(None, None) # Initialize text size
            )
            # This line tells the text it has to stay within the width of the button
            btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0] - dp(10), None)))

            btn.bind(on_release=lambda b, c=cat: self.finalize_addition(name, c, pop))
            grid.add_widget(btn)
            
        scroll.add_widget(grid)
        outer.add_widget(scroll)
        
        # 4. Neutralize the Cancel Button
        cancel = Button(
            text="CANCEL", 
            size_hint_y=None, 
            height=app.row_height, 
            font_size=app.f_size,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        cancel.bind(on_release=pop.dismiss)
        outer.add_widget(cancel)
        
        pop.open()

    def finalize_addition(self, name, cat, popup):
        if name.lower() not in [k.lower() for k in self.categories[cat].get('keywords', [])]:
            if 'keywords' not in self.categories[cat]: self.categories[cat]['keywords'] = []
            self.categories[cat]['keywords'].append(name.lower())
        self.add_to_list(name, cat); popup.dismiss(); self.item_input.text = ""
        if hasattr(self, 'prediction_drop'): self.prediction_drop.dismiss()

    def add_to_list(self, name, cat):
        target = self.all_lists[self.active_list_name]
        found = next((i for i in target if isinstance(i, dict) and i.get('name') == name.capitalize() and not i['done']), None)
        if found: found['count'] = found.get('count', 1) + 1
        else: target.append({'name': name.capitalize(), 'done': False, 'cat': cat, 'count': 1})
        self.save_data(); self.refresh_ui()

    def toggle_completed(self, instance): 
        self.show_completed = not self.show_completed
        self.done_btn.text = "HIDE DONE" if self.show_completed else "SHOW DONE"
        self.refresh_ui()

    def clear_completed(self, instance=None):
        self.all_lists[self.active_list_name] = [i for i in self.all_lists[self.active_list_name] if not i.get('done') or i.get('name') == "PLACEHOLDER"]
        self.save_data(); self.refresh_ui()

    def clear_entire_list(self):
        self.all_lists[self.active_list_name] = [{'name': 'PLACEHOLDER', 'done': False, 'cat': 'Uncategorized'}]
        self.save_data(); self.refresh_ui()

    def update_family_id(self, new_id):
        if new_id:
            self.family_id = new_id
            self.load_data(); self.refresh_ui(); self.sync_now()

    def sync_now(self, instance=None):
        try:
            res = requests.get(self.cloud_url, timeout=5, verify=certifi.where())
            if res.status_code == 200:
                data = res.json()
                if data and self.family_id in data:
                    cloud = data[self.family_id]
                    self.all_lists = cloud.get('all_lists', self.all_lists)
                    self.categories = cloud.get('categories', self.categories)
                    self.active_list_name = cloud.get('active_list_name', self.active_list_name)
                    self.refresh_ui()
                    self.sync_label.text = "Cloud Synced"
        except: self.sync_label.text = "Sync Failed"

    def force_download_confirmed(self):
        self.sync_now()

    def confirm_action(self, msg, callback):
        c = BoxLayout(orientation='vertical', padding=dp(10))
        c.add_widget(Label(text=msg))
        b = BoxLayout(size_hint_y=None, height=App.get_running_app().row_height, spacing=dp(10))
        y = Button(text="YES", on_release=lambda x: (callback(), p.dismiss()))
        n = Button(text="NO", on_release=lambda x: p.dismiss())
        b.add_widget(n); b.add_widget(y); c.add_widget(b)
        p = Popup(title="Confirm", content=c, size_hint=(0.8, 0.3)); p.open()

    def update_stats(self):
        items = [i for i in self.all_lists.get(self.active_list_name, []) if isinstance(i, dict) and i.get('name') != "PLACEHOLDER"]
        rem = len([i for i in items if not i.get('done')])
        self.stats_label.text = f"{rem}/{len(items)} items left"

    def on_start(self):
        Clock.schedule_once(self.sync_now, 1)

    # Standard Helpers
    def switch_list(self, s, t): self.active_list_name = t; self.refresh_ui()
    def mark_done(self, i): i['done'] = True; self.save_data(); self.refresh_ui()
    def adjust_quantity(self, i, a):
        i['count'] = i.get('count', 1) + a
        if i['count'] < 1: self.all_lists[self.active_list_name].remove(i)
        self.save_data(); self.refresh_ui()
    def create_new_list(self, x):
        n = f"List {len(self.all_lists)+1}"
        self.all_lists[n] = [{'name': 'PLACEHOLDER', 'done': False, 'cat': 'Uncategorized'}]
        self.active_list_name = n; self.save_data(); self.refresh_ui()
    def rename_list_popup(self, x):
        c = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        inp = TextInput(text=self.active_list_name, multiline=False, size_hint_y=None, height=App.get_running_app().row_height)
        btn = Button(text="SAVE", size_hint_y=None, height=App.get_running_app().row_height)
        c.add_widget(inp); c.add_widget(btn); p = Popup(title="Rename", content=c, size_hint=(0.8, 0.4))
        def r(x): self.all_lists[inp.text] = self.all_lists.pop(self.active_list_name); self.active_list_name = inp.text; self.save_data(); self.refresh_ui(); p.dismiss()
        btn.bind(on_release=r); p.open()
    def confirm_delete_list(self, x):
        if len(self.all_lists) > 1: self.confirm_action("Delete list?", self.delete_list)
    def delete_list(self):
        self.all_lists.pop(self.active_list_name); self.active_list_name = list(self.all_lists.keys())[0]; self.save_data(); self.refresh_ui()

    def on_type_prediction(self, i, v):
        self.prediction_drop.clear_widgets()
        if not v:
            self.prediction_drop.dismiss() # Close if text is cleared
            return
            
        hist = []
        for c in self.categories.values(): 
            hist.extend(c.get('keywords', []))
        
        matches = sorted([m for m in set(hist) if m.lower().startswith(v.lower())])
        
        if not matches:
            self.prediction_drop.dismiss()
            return

        for m in matches[:5]:
            btn = Button(text=m.capitalize(), size_hint_y=None, height=self.row_height, font_size=self.f_size, bold=True)
            btn.bind(on_release=lambda b: self.select_prediction(b.text))
            self.prediction_drop.add_widget(btn)
        
        # FIX: Only open if it's not already attached to the Window
        if not self.prediction_drop.parent:
            self.prediction_drop.open(i)
            
    def select_prediction(self, t): self.item_input.text = t; self.prediction_drop.dismiss(); self.process_addition(None)

if __name__ == '__main__':
    ShoppingApp().run()
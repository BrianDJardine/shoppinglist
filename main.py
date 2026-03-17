import json, os, shutil
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
from kivy.metrics import dp

# --- SWIPE TO DONE LOGIC ---
class SwipeItem(BoxLayout):
    def __init__(self, item_ref, text, background_color, **kwargs):
        app = App.get_running_app()
        super().__init__(**kwargs)
        self.item_ref, self.offset_x = item_ref, 0
        self.orientation = 'horizontal'
        self.size_hint_y = None
        # Use the height calculated in update_font_metrics
        self.height = app.row_height 
        self.padding, self.spacing = dp(5), dp(10)
        
        with self.canvas.before:
            Color(0.8, 0.2, 0.2, 1) 
            self.back_rect = Rectangle(size=self.size, pos=self.pos)
            self.color_instruction = Color(*background_color)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            
        self.bind(size=self._update_rect, pos=self._update_rect)

        self.minus_btn = Button(text="-", size_hint=(None, 1), width=dp(65),
                                background_color=(0.7, 0.3, 0.3, 1), font_size='30sp', bold=True)
        self.minus_btn.bind(on_release=lambda x: App.get_running_app().adjust_quantity(self.item_ref, -1))
                
        # Use dynamic font size from App
        self.label = Label(text=text, markup=True, halign='left', valign='middle', 
                           font_size=app.f_size, bold=True, color=(0, 0, 0, 1))       
        self.label.bind(size=self.label.setter('text_size'))
        
        self.plus_btn = Button(text="+", size_hint=(None, 1), width=dp(65),
                               background_color=(0.3, 0.7, 0.3, 1), font_size='30sp', bold=True)
        self.plus_btn.bind(on_release=lambda x: App.get_running_app().adjust_quantity(self.item_ref, 1))

        self.add_widget(self.minus_btn); self.add_widget(self.label); self.add_widget(self.plus_btn)

    def _update_rect(self, *args):
        self.back_rect.pos = self.pos
        self.back_rect.size = self.size
        self.rect.pos = (self.x + self.offset_x, self.y)
        self.rect.size = self.size

    def on_touch_down(self, touch):
        if self.minus_btn.collide_point(*touch.pos) or self.plus_btn.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if self.collide_point(*touch.pos):
            touch.ud['start_x'] = touch.x
            touch.grab(self); return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            dx = touch.x - touch.ud['start_x']
            if dx < 0:
                self.offset_x = dx; self._update_rect()
                if dx < -dp(180): App.get_running_app().mark_done(self.item_ref)
                return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            self.offset_x = 0; self._update_rect(); touch.ungrab(self); return True
        return super().on_touch_up(touch)

# --- CATEGORY SCREEN ---
class CategoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        self.layout.add_widget(Label(text="MANAGE CATEGORIES", font_size=dp(22), bold=True, size_hint_y=None, height=dp(40)))
        
        add_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
        self.new_cat_input = TextInput(hint_text="New Category Name...", multiline=False)
        add_btn = Button(text="ADD", size_hint_x=0.3, background_color=(0.2, 0.7, 0.3, 1), bold=True)
        add_btn.bind(on_release=self.add_category)
        add_box.add_widget(self.new_cat_input); add_box.add_widget(add_btn)
        self.layout.add_widget(add_box)

        self.cat_list_layout = GridLayout(cols=1, size_hint_y=None, spacing=dp(5))
        self.cat_list_layout.bind(minimum_height=self.cat_list_layout.setter('height'))
        scroll = ScrollView(); scroll.add_widget(self.cat_list_layout)
        self.layout.add_widget(scroll)

        back_btn = Button(text="BACK TO LIST", size_hint_y=None, height=dp(55), bold=True)
        back_btn.bind(on_release=lambda x: setattr(App.get_running_app().sm, 'current', 'main'))
        self.layout.add_widget(back_btn); self.add_widget(self.layout)

    def on_pre_enter(self): self.refresh_categories()

    def refresh_categories(self):
        self.cat_list_layout.clear_widgets()
        app = App.get_running_app()
        sorted_cats = sorted(app.categories.items(), key=lambda x: x[1].get('order', 99))
        for name, data in sorted_cats:
            row = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(5))
            
            # Ordering buttons
            order_box = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(45))
            up = Button(text="^"); up.bind(on_release=lambda x, n=name: self.move_cat(n, -1))
            dn = Button(text="v"); dn.bind(on_release=lambda x, n=name: self.move_cat(n, 1))
            order_box.add_widget(up); order_box.add_widget(dn)
            
            # Label as button for Renaming (CAPS and 21sp)
            lbl = Button(text=name.upper(), halign='left', valign='middle', 
                         font_size=dp(21), bold=True, background_color=(0,0,0,0))
            lbl.bind(size=lbl.setter('text_size'))
            lbl.bind(on_release=lambda x, n=name: self.rename_category_popup(n))
            
            del_btn = Button(text="X", size_hint_x=None, width=dp(55), background_color=(0.8, 0.2, 0.2, 1), bold=True)
            del_btn.bind(on_release=lambda x, n=name: self.delete_category(n))
            
            row.add_widget(order_box); row.add_widget(lbl)
            if name != "Uncategorized": row.add_widget(del_btn)
            self.cat_list_layout.add_widget(row)

    def rename_category_popup(self, old_name):
        if old_name == "Uncategorized": return
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        inp = TextInput(text=old_name, multiline=False, size_hint_y=None, height=dp(50))
        content.add_widget(inp)
        btn = Button(text="UPDATE NAME", size_hint_y=None, height=dp(50), bold=True)
        content.add_widget(btn); p = Popup(title="Rename Category", content=content, size_hint=(0.8, 0.4))
        
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
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        layout.add_widget(Label(text="SETTINGS & DATA", font_size=dp(24), bold=True, size_hint_y=None, height=dp(50)))
        
        # --- FONT SIZE DROPDOWN (SPINNER) ---
        layout.add_widget(Label(text="List Font Size:", size_hint_y=None, height=dp(30)))
        
        # The Spinner acts as your dropdown
        self.font_spinner = Spinner(
            text=App.get_running_app().font_scale,
            values=("Small", "Medium", "Large"),
            size_hint_y=None,
            height=dp(50),
            background_color=(0.3, 0.3, 0.3, 1),
            bold=True
        )
        self.font_spinner.bind(text=lambda spinner, text: App.get_running_app().change_font_size(text))
        layout.add_widget(self.font_spinner)
        
        # Spacer
        layout.add_widget(Widget(size_hint_y=None, height=dp(20)))

        # Existing Buttons
        m_btn = Button(text="RESTORE MASTER LIST", size_hint_y=None, height=dp(65), background_color=(0.2, 0.5, 0.8, 1), bold=True)
        m_btn.bind(on_release=lambda x: App.get_running_app().confirm_action("Reset to Master Template?", App.get_running_app().restore_from_master_file))
        layout.add_widget(m_btn)

        ex_btn = Button(text="EXPORT DATA", size_hint_y=None, height=dp(65), background_color=(0.3, 0.7, 0.3, 1), bold=True)
        ex_btn.bind(on_release=lambda x: App.get_running_app().export_data())
        layout.add_widget(ex_btn)

        im_btn = Button(text="IMPORT DATA", size_hint_y=None, height=dp(65), background_color=(0.7, 0.5, 0.2, 1), bold=True)
        im_btn.bind(on_release=lambda x: App.get_running_app().confirm_action("Overwrite with Imported Data?", App.get_running_app().import_data))
        layout.add_widget(im_btn)
        
        layout.add_widget(Widget()) 
        back_btn = Button(text="BACK TO LIST", size_hint_y=None, height=dp(60), background_color=(0.3, 0.3, 0.3, 1), bold=True)
        back_btn.bind(on_release=lambda x: setattr(App.get_running_app().sm, 'current', 'main'))
        layout.add_widget(back_btn)
        
        self.add_widget(layout)

    def on_pre_enter(self):
        # Ensure the dropdown shows the current setting when you open the screen
        self.font_spinner.text = App.get_running_app().font_scale


# --- MAIN APP ---
class ShoppingApp(App):
    def build(self):
        self.data_file = os.path.join(self.user_data_dir, "shopping_data.json")
        self.backup_file = os.path.join(self.user_data_dir, "shopping_backup.json")
        self.master_template_file = os.path.join(os.path.dirname(__file__), "master_data.json")
        
        self.show_completed = False
        self.load_data()
        self.prediction_drop = DropDown()
        self.sm = ScreenManager()
        self.f_size = dp(28)

        self.main_page = Screen(name='main')
        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        
        # HEADER
        header_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
        self.list_spinner = Spinner(text=self.active_list_name, values=list(self.all_lists.keys()),
                                    size_hint_x=0.35, background_color=(0.15, 0.15, 0.15, 1), bold=True)
        self.list_spinner.bind(text=self.switch_list)
        header_row.add_widget(self.list_spinner)

        btn_group = BoxLayout(size_hint_x=0.65, spacing=dp(4))
        def image_btn(img, callback, tint=(1, 1, 1, 1)):
            return Button(background_normal=img, on_press=callback, background_color=tint, 
                          size_hint=(None, None), size=(dp(38), dp(38)), pos_hint={'center_y': 0.5})

        btn_group.add_widget(image_btn('new.png', self.create_new_list, tint=(0.2, 1, 0.2, 1))) 
        btn_group.add_widget(image_btn('edit.png', self.rename_list_popup, tint=(1, 1, 0.2, 1))) 
        btn_group.add_widget(image_btn('delete.png', self.confirm_delete_list, tint=(1, 0.3, 0.3, 1))) 
        btn_group.add_widget(image_btn('cats.png', lambda x: setattr(self.sm, 'current', 'categories'))) 
        btn_group.add_widget(image_btn('settings.png', lambda x: setattr(self.sm, 'current', 'settings')))
        header_row.add_widget(btn_group); main_layout.add_widget(header_row)

        # INPUT
        input_box = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(5))
        
        self.item_input = TextInput(
            hint_text='Add item...', 
            multiline=False, 
            font_size=self.f_size,
            # This tells Android to keep the suggestion bar active
            input_type='text',
            input_filter=None,
            write_tab=False
        )
        self.item_input.bind(text=self.on_type_prediction)

        input_box.add_widget(self.item_input)
        input_box.add_widget(Button(text='ADD', size_hint_x=0.25, background_color=(0.2, 0.7, 0.3, 1), bold=True, on_press=self.process_addition))
        main_layout.add_widget(input_box)

        self.cat_selector = Spinner(text='Category?', size_hint_y=None, height=0, opacity=0)
        self.cat_selector.bind(text=self.on_manual_select)
        main_layout.add_widget(self.cat_selector)

        self.list_layout = GridLayout(cols=1, size_hint_y=None, spacing=dp(8))
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll = ScrollView(); scroll.add_widget(self.list_layout)
        main_layout.add_widget(scroll)

        bot = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(5))
        self.done_btn = Button(text="SHOW DONE", on_press=self.toggle_completed, bold=True)
        bot.add_widget(self.done_btn)
        bot.add_widget(Button(text="PURGE", background_color=(.7,.4,.4,1), on_press=self.clear_completed, bold=True))
        main_layout.add_widget(bot)

        self.main_page.add_widget(main_layout); self.sm.add_widget(self.main_page)
        self.sm.add_widget(CategoryScreen(name='categories'))
        self.sm.add_widget(SettingsScreen(name='settings'))
        
        self.refresh_ui(); return self.sm

    # --- DATA ---
    def load_data(self):
        self.categories = {'Uncategorized':{'order':99,'keywords':[]}}
        self.all_lists = {'Groceries':[]}
        self.active_list_name = 'Groceries'
        self.font_scale = 'Large' # Default

        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    d = json.load(f)
                    self.categories = d.get('categories', self.categories)
                    self.all_lists = d.get('all_lists', self.all_lists)
                    self.active_list_name = d.get('active_list_name', self.active_list_name)
                    self.font_scale = d.get('font_scale', 'Large')
            except:
                pass
        self.update_font_metrics()

    def update_font_metrics(self):
        if self.font_scale == "Small":
            self.f_size = dp(18)
            self.row_height = dp(65)
        elif self.font_scale == "Medium":
            self.f_size = dp(23)
            self.row_height = dp(75)
        else: # Large
            self.f_size = dp(28)
            self.row_height = dp(85)

    def change_font_size(self, size):
        # Only trigger if the size actually changed to avoid unnecessary UI refreshes
        if size != self.font_scale:
            self.font_scale = size
            self.update_font_metrics()
            self.save_data()
            self.refresh_ui()

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump({
                'categories': self.categories, 
                'all_lists': self.all_lists, 
                'active_list_name': self.active_list_name,
                'font_scale': self.font_scale
            }, f, indent=4)

    def restore_from_master_file(self):
        try:
            if os.path.exists(self.master_template_file):
                with open(self.master_template_file, 'r') as f: data = json.load(f)
                self.categories = data.get('categories', {})
                self.all_lists = data.get('all_lists', {'Groceries': []})
                self.active_list_name = data.get('active_list_name', 'Groceries')
                self.save_data(); self.list_spinner.values = list(self.all_lists.keys())
                self.list_spinner.text = self.active_list_name; self.refresh_ui(); self.notify("Master List Restored!")
            else: self.notify("master_data.json not found.")
        except Exception as e: self.notify(f"Restore Failed: {e}")

    def export_data(self):
        try:
            with open(self.data_file, 'r') as f: data = json.load(f)
            with open(self.backup_file, 'w') as f: json.dump(data, f, indent=4)
            self.notify("Data Exported Successfully!")
        except Exception as e: self.notify(f"Export Failed: {e}")

    def import_data(self):
        try:
            if os.path.exists(self.backup_file):
                with open(self.backup_file, 'r') as f: data = json.load(f)
                with open(self.data_file, 'w') as f: json.dump(data, f, indent=4)
                self.load_data(); self.list_spinner.values = list(self.all_lists.keys())
                self.list_spinner.text = self.active_list_name; self.refresh_ui(); self.notify("Data Imported!")
            else: self.notify("No Backup File Found.")
        except Exception as e: self.notify(f"Import Failed: {e}")

    # --- UI & LISTS ---
    def refresh_ui(self, *args):
        self.list_layout.clear_widgets()
        active_bg, done_bg = (1, 1, 1, 1), (0.75, 0.75, 0.75, 1)
        items = sorted(self.all_lists.get(self.active_list_name, []), 
                       key=lambda x: self.categories.get(x['cat'], {'order': 99})['order'])
        curr_cat = None
        for i in items:
            if i['done'] and not self.show_completed: continue
            if i['cat'] != curr_cat:
                curr_cat = i['cat']
                self.list_layout.add_widget(Label(text=f"-- {curr_cat.upper()} --", size_hint_y=None, height=dp(40), bold=True, color=(0.5, 0.5, 0.5, 1)))
            qty = f" [b]x{i.get('count', 1)}[/b]" if i.get('count', 1) > 1 else ""
            row = SwipeItem(item_ref=i, text=f"[s]{i['name']}{qty}[/s]" if i['done'] else f"{i['name']}{qty}", 
                background_color=(done_bg if i['done'] else active_bg))
            self.list_layout.add_widget(row)

    def create_new_list(self, instance):
        n = f"List {len(self.all_lists)+1}"; self.all_lists[n] = []
        self.list_spinner.values = list(self.all_lists.keys()); self.list_spinner.text = n; self.save_data()

    def rename_list_popup(self, instance):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        inp = TextInput(text=self.active_list_name, multiline=False, size_hint_y=None, height=dp(50))
        content.add_widget(inp); btn = Button(text="SAVE", size_hint_y=None, height=dp(50), bold=True)
        content.add_widget(btn); p = Popup(title="Rename List", content=content, size_hint=(0.8, 0.4))
        def do_rename(x):
            new_n = inp.text.strip()
            if new_n and new_n != self.active_list_name:
                self.all_lists[new_n] = self.all_lists.pop(self.active_list_name)
                self.active_list_name = new_n; self.list_spinner.values = list(self.all_lists.keys()); self.list_spinner.text = new_n; self.save_data()
            p.dismiss()
        btn.bind(on_release=do_rename); p.open()

    def confirm_delete_list(self, instance):
        if len(self.all_lists) > 1: self.confirm_action(f"Delete '{self.active_list_name}'?", self.delete_list)
        else: self.notify("Cannot delete the only list!")

    def delete_list(self):
        self.all_lists.pop(self.active_list_name); self.active_list_name = list(self.all_lists.keys())[0]
        self.list_spinner.values = list(self.all_lists.keys()); self.list_spinner.text = self.active_list_name; self.save_data(); self.refresh_ui()

    def mark_done(self, item): item['done'] = True; self.save_data(); self.refresh_ui()
    def adjust_quantity(self, item, amt):
        item['count'] = item.get('count', 1) + amt
        if item['count'] < 1: self.confirm_action(f"Remove {item['name']}?", lambda: (self.all_lists[self.active_list_name].remove(item), self.save_data(), self.refresh_ui()))
        else: self.save_data(); self.refresh_ui()

    def process_addition(self, instance):
        name = self.item_input.text.strip().lower()
        if not name: return
        cat = next((c for c, d in self.categories.items() if name in d['keywords']), "Uncategorized")
        if cat == "Uncategorized":
            self.cat_selector.values = [c for c in self.categories.keys() if c != "Uncategorized"]
            self.cat_selector.height, self.cat_selector.opacity = dp(50), 1
        else: self.add_to_list(name, cat)

    def add_to_list(self, name, cat):
        target = self.all_lists[self.active_list_name]
        found = next((i for i in target if i['name'] == name.capitalize() and not i['done']), None)
        if found: found['count'] = found.get('count', 1) + 1
        else: target.append({'name': name.capitalize(), 'cat': cat, 'done': False, 'count': 1})
        self.item_input.text = ""; self.save_data(); self.refresh_ui()

    def on_manual_select(self, spinner, value):
        if value != 'Category?':
            name = self.item_input.text.strip().lower()
            if name not in self.categories[value]['keywords']: self.categories[value]['keywords'].append(name)
            self.add_to_list(name, value); self.cat_selector.height, self.cat_selector.opacity = 0, 0

    def toggle_completed(self, instance): self.show_completed = not self.show_completed; self.done_btn.text = "HIDE DONE" if self.show_completed else "SHOW DONE"; self.refresh_ui()
    def clear_completed(self, instance): self.all_lists[self.active_list_name] = [i for i in self.all_lists[self.active_list_name] if not i['done']]; self.save_data(); self.refresh_ui()
    def switch_list(self, spinner, text): self.active_list_name = text; self.save_data(); self.refresh_ui()
    def confirm_action(self, msg, callback):
        content = BoxLayout(orientation='vertical', padding=dp(10)); content.add_widget(Label(text=msg))
        btns = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        y = Button(text="YES", on_release=lambda x: (callback(), p.dismiss()))
        n = Button(text="NO", on_release=lambda x: p.dismiss()); btns.add_widget(n); btns.add_widget(y)
        content.add_widget(btns); p = Popup(title="Confirm", content=content, size_hint=(0.8, 0.3)); p.open()
    def notify(self, text): Popup(title="Notice", content=Label(text=text), size_hint=(0.7, 0.2)).open()

    def on_type_prediction(self, instance, value):
        # 1. Clear previous suggestions from our custom list
        self.prediction_drop.clear_widgets()
        
        # If input is empty, hide our dropdown (Android bar stays)
        if not value or len(value) < 1:
            self.prediction_drop.dismiss()
            return

        # 2. Find matches from our "Master List" / Keywords history
        history = []
        for c in self.categories.values():
            history.extend(c.get('keywords', []))
            
        # Case-insensitive matching
        matches = sorted([m for m in set(history) if m.lower().startswith(value.lower())])
        
        if not matches:
            self.prediction_drop.dismiss()
            return

        # 3. Build our custom dropdown buttons
        for m in matches[:5]:
            btn = Button(text=m.capitalize(), size_hint_y=None, height=dp(60), bold=True)
            btn.bind(on_release=lambda b: self.select_prediction(b.text))
            self.prediction_drop.add_widget(btn)

        # 4. Only open our dropdown if it isn't already visible
        if not self.prediction_drop.attach_to:
            self.prediction_drop.open(instance)

    def select_prediction(self, text):
        # When you tap our dropdown, it fills the field and adds it
        self.item_input.text = text
        self.prediction_drop.dismiss()
        self.process_addition(None)

if __name__ == '__main__':
    ShoppingApp().run()
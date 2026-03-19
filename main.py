import json, os, shutil
import requests
import certifi
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
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.behaviors import ButtonBehavior
from kivy.animation import Animation
from kivy.graphics import Rotate, PushMatrix, PopMatrix
from kivy.uix.relativelayout import RelativeLayout

class ListItem(BoxLayout):
    def __init__(self, item_ref, text, background_color, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        self.item_ref = item_ref
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = app.row_height
        self.padding = [dp(10), dp(5)]
        self.spacing = dp(10)

        with self.canvas.before:
            Color(*background_color)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        # --- LEFT: ACTION BOX ---
        self.check_btn = Button(
            text="", 
            size_hint=(None, None), 
            size=(dp(45), dp(45)),
            pos_hint={'center_y': 0.5},
            background_normal='', 
            background_color=(0.9, 0.9, 0.9, 1) # Off-white/Light gray
        )
        self.check_btn.bind(on_release=self.trigger_done)
        self.add_widget(self.check_btn)

        # --- MIDDLE: ITEM TEXT ---
        self.label = Label(
            text=text, markup=True, halign='left', valign='middle', 
            font_size=app.f_size, bold=True, color=(0, 0, 0, 1)
        )
        self.label.bind(size=self.label.setter('text_size'))
        self.add_widget(self.label)

        # --- RIGHT: QUANTITY GROUP (- and +) ---
        qty_box = BoxLayout(size_hint=(None, 1), width=dp(110), spacing=dp(2))
        
        minus_btn = Button(text="-", background_color=(0.7, 0.3, 0.3, 1), font_size='22sp', bold=True)
        minus_btn.bind(on_release=lambda x: app.adjust_quantity(self.item_ref, -1))
        
        plus_btn = Button(text="+", background_color=(0.3, 0.7, 0.3, 1), font_size='22sp', bold=True)
        plus_btn.bind(on_release=lambda x: app.adjust_quantity(self.item_ref, 1))
        
        qty_box.add_widget(minus_btn)
        qty_box.add_widget(plus_btn)
        self.add_widget(qty_box)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def trigger_done(self, instance):
        # Visual feedback: Just turn the box green
        self.check_btn.background_color = (0.2, 0.8, 0.2, 1) 
        self.check_btn.text = "" 
        
        # delay
        Clock.schedule_once(lambda dt: App.get_running_app().mark_done(self.item_ref), 0.5)

# --- CATEGORY SCREEN ---
class CategoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

        # --- ENHANCED HEADER ROW ---
        header = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10), padding=[dp(10), 0])
        with header.canvas.before:
            Color(0.15, 0.15, 0.15, 1)  # Dark charcoal header background
            self.rect = Rectangle(size=header.size, pos=header.pos)
        header.bind(size=self._update_header_rect, pos=self._update_header_rect)

        back_btn = Button(
            background_normal='back.png', 
            size_hint=(None, None), 
            size=(dp(35), dp(35)), 
            pos_hint={'center_y': 0.5},
            background_color=(1, 1, 1, 1) # Ensure it stays white
        )
        back_btn.bind(on_release=lambda x: setattr(App.get_running_app().sm, 'current', 'main'))
        
        header.add_widget(back_btn)
        header.add_widget(Label(text="CATEGORIES", font_size=dp(20), bold=True, halign='left'))
        self.layout.add_widget(header)
        # ----------------------

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

        self.add_widget(self.layout)
        
    def on_pre_enter(self): self.refresh_categories()

    def _update_header_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

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
        # Main container
        self.layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(15))
        
        # --- HEADER ---
        header = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10))
        with header.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            self.rect = Rectangle(size=header.size, pos=header.pos)
        header.bind(size=self._update_header_rect, pos=self._update_header_rect)

        back_btn = Button(
            background_normal='back.png', 
            size_hint=(None, None), size=(dp(35), dp(35)), 
            pos_hint={'center_y': 0.5}
        )
        back_btn.bind(on_release=lambda x: setattr(App.get_running_app().sm, 'current', 'main'))
        header.add_widget(back_btn)
        header.add_widget(Label(text="APP SETTINGS", font_size=dp(20), bold=True, halign='left'))
        self.layout.add_widget(header)

        # --- FONT SIZE SECTION ---
        self.layout.add_widget(Label(text="Display Text Size:", size_hint_y=None, height=dp(30), color=(0.7, 0.7, 0.7, 1)))
        self.font_spinner = Spinner(
            text="Large", 
            values=("Smallest", "Small", "Medium", "Large"),
            size_hint_y=None, height=dp(50),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        self.font_spinner.bind(text=lambda s, t: App.get_running_app().change_font_size(t))
        self.layout.add_widget(self.font_spinner)

        # --- CLOUD / FAMILY ID SECTION ---
        self.layout.add_widget(Label(text="Family Sync ID:", size_hint_y=None, height=dp(30), color=(0.7, 0.7, 0.7, 1)))
        self.id_input = TextInput(
            multiline=False, size_hint_y=None, height=dp(50),
            hint_text="Enter Family Name...", padding=[dp(10), dp(12)]
        )
        self.layout.add_widget(self.id_input)

        # Update Button
        save_id_btn = Button(
            text="UPDATE & SYNC ID", size_hint_y=None, height=dp(55),
            background_color=(0.2, 0.6, 1, 1), bold=True
        )
        save_id_btn.bind(on_release=self.apply_id_change)
        self.layout.add_widget(save_id_btn)

        # --- ADVANCED CLOUD OVERRIDES ---
        self.layout.add_widget(Widget(size_hint_y=None, height=dp(20))) # Spacer
        self.layout.add_widget(Label(text="Manual Cloud Overrides:", size_hint_y=None, height=dp(30), color=(0.5, 0.5, 0.5, 1)))
        
        # Force Push (Upload)
        push_btn = Button(text="FORCE UPLOAD TO CLOUD", size_hint_y=None, height=dp(50), background_color=(0.2, 0.7, 0.3, 1))
        # Use a lambda that fetches the app at the MOMENT of the click
        push_btn.bind(on_release=lambda x: App.get_running_app().confirm_action(
            "Overwrite Cloud with Phone data?", 
            App.get_running_app().save_data
        ))
        self.layout.add_widget(push_btn)

        # Force Pull (Download)
        pull_btn = Button(text="FORCE DOWNLOAD FROM CLOUD", size_hint_y=None, height=dp(50), background_color=(0.7, 0.5, 0.2, 1))
        # Use a lambda that fetches the app at the MOMENT of the click
        pull_btn.bind(on_release=lambda x: App.get_running_app().confirm_action(
            "Wipe Phone and pull from Cloud?", 
            App.get_running_app().force_download_confirmed # Use the specific pull function
        ))
        self.layout.add_widget(pull_btn)

        self.layout.add_widget(Widget()) # Push everything to top
        self.add_widget(self.layout)

    def on_pre_enter(self):
        # Refresh values when we open the screen
        app = App.get_running_app()
        self.font_spinner.text = app.font_scale
        self.id_input.text = app.family_id

    def apply_id_change(self, instance):
        new_id = self.id_input.text.strip()
        if new_id:
            App.get_running_app().update_family_id(new_id)
        else:
            App.get_running_app().notify("Please enter a valid Family ID.")

    def _update_header_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

# --- MAIN APP ---
class ShoppingApp(App):
    # Your Firebase URL
    BASE_URL = "https://shoppinglist-eae1c-default-rtdb.europe-west1.firebasedatabase.app/"

    def build(self):
        # We need to determine the family_id BEFORE setting self.data_file
        # So we peek into local_settings.json first
        temp_id = "DefaultFamily"
        local_path = os.path.join(self.user_data_dir, "local_settings.json")
        if os.path.exists(local_path):
            try:
                with open(local_path, 'r') as f:
                    temp_id = json.load(f).get('family_id', 'DefaultFamily')
            except: pass
        
        self.family_id = temp_id
        self.data_file = os.path.join(self.user_data_dir, f"shopping_data_{self.family_id}.json")
        
        self.show_completed = False
        self.load_data()
        self.prediction_drop = DropDown()
        self.sm = ScreenManager()

        self.main_page = Screen(name='main')
        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        
        # --- HEADER ---
        header_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
        self.list_spinner = Spinner(text=self.active_list_name, values=list(self.all_lists.keys()),
                                    size_hint_x=0.35, background_color=(0.15, 0.15, 0.15, 1), bold=True)
        self.list_spinner.bind(text=self.switch_list)
        header_row.add_widget(self.list_spinner)

        btn_group = BoxLayout(size_hint_x=0.65, spacing=dp(4))

        def image_btn(img, callback, tint=(1, 1, 1, 1)):
            return Button(background_normal=img, on_release=callback, background_color=tint, 
                          size_hint=(None, None), size=(dp(38), dp(38)), pos_hint={'center_y': 0.5})

        btn_group.add_widget(image_btn('new.png', self.create_new_list, tint=(0.2, 1, 0.2, 1))) 
        btn_group.add_widget(image_btn('edit.png', self.rename_list_popup, tint=(1, 1, 0.2, 1))) 
        btn_group.add_widget(image_btn('delete.png', self.confirm_delete_list, tint=(1, 0.3, 0.3, 1))) 
        btn_group.add_widget(image_btn('cats.png', lambda x: setattr(self.sm, 'current', 'categories')))         
        btn_group.add_widget(image_btn('settings.png', lambda x: setattr(self.sm, 'current', 'settings')))
        
        # --- NEW SIMPLE SYNC BUTTON ---
        self.sync_btn = Button(
            background_normal='sync.png', 
            background_down='sync.png',
            size_hint=(None, None), 
            size=(dp(38), dp(38)), 
            pos_hint={'center_y': 0.5}
        )
        self.sync_btn.bind(on_release=self.sync_now)
        btn_group.add_widget(self.sync_btn)

        header_row.add_widget(btn_group)
        main_layout.add_widget(header_row)

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

        # --- STATUS BAR (Above Footer Buttons) ---
        status_bar = BoxLayout(size_hint_y=None, height=dp(30), padding=[dp(10), 0])

        # Left side: Item Count
        self.stats_label = Label(
            text="0 items",
            size_hint_x=0.5,
            halign='left',
            valign='middle',
            color=(0.8, 0.8, 0.8, 1),
            font_size='14sp'
        )
        self.stats_label.bind(size=self.stats_label.setter('text_size')) # Ensures alignment works

        # Right side: Last Sync
        self.sync_label = Label(
            text="Last Synced: Never",
            size_hint_x=0.5,
            halign='right',
            valign='middle',
            color=(0.6, 0.6, 0.6, 1),
            font_size='14sp'
        )
        self.sync_label.bind(size=self.sync_label.setter('text_size'))

        status_bar.add_widget(self.stats_label)
        status_bar.add_widget(self.sync_label)
        
        main_layout.add_widget(status_bar)        
        
        bot = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(5))
        
        self.done_btn = Button(text="SHOW DONE", on_press=self.toggle_completed, bold=True)

        # Darker Red for Delete Done
        del_done_btn = Button(
            text="DELETE DONE", 
            background_color=(0.7, 0.3, 0.3, 1), 
            bold=True,
            on_press=lambda x: self.confirm_action("Delete purchased items?", self.clear_completed)
        )

        # Lighter Red for Clear List
        clear_btn = Button(
            text="CLEAR LIST", 
            background_color=(0.9, 0.4, 0.4, 1), 
            bold=True,
            on_press=lambda x: self.confirm_action("Wipe ENTIRE list?", self.clear_entire_list)
        )

        bot.add_widget(self.done_btn)
        bot.add_widget(del_done_btn)
        bot.add_widget(clear_btn)
        main_layout.add_widget(bot)

        self.main_page.add_widget(main_layout); self.sm.add_widget(self.main_page)
        self.sm.add_widget(CategoryScreen(name='categories'))
        self.sm.add_widget(SettingsScreen(name='settings'))

        self.refresh_ui(); return self.sm

    # --- DATA ---
    def load_data(self):
        # 1. Set hard defaults
        self.font_scale = 'Large'
        self.family_id = "DefaultFamily"
        self.categories = {'Uncategorized': {'order': 99, 'keywords': []}}
        self.all_lists = {'Groceries': [{"name": "PLACEHOLDER", "done": False, "category": "Uncategorized"}]}
        self.active_list_name = 'Groceries'

        # 2. Load Local Settings (Font and ID)
        local_path = os.path.join(self.user_data_dir, "local_settings.json")
        if os.path.exists(local_path):
            try:
                with open(local_path, 'r') as f:
                    local_d = json.load(f)
                    self.font_scale = local_d.get('font_scale', 'Large')
                    self.family_id = local_d.get('family_id', 'DefaultFamily')
            except: pass
        
        self.update_font_metrics()

        # 3. Try to load from the phone's local storage (The "Truth" for offline use)
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    local_data = json.load(f)
                    # We use .get() to avoid crashing if a key is missing
                    self.all_lists = local_data.get('all_lists', self.all_lists)
                    self.categories = local_data.get('categories', self.categories)
                    self.active_list_name = local_data.get('active_list_name', self.active_list_name)
                print("Successfully loaded from local storage.")
            except Exception as e:
                print(f"Local storage load failed: {e}")

        # 4. Cloud Sync will happen automatically 0.5s later via on_start()

    def update_font_metrics(self):
        if self.font_scale == "Smallest":
            self.f_size, self.row_height = dp(14), dp(55)
        elif self.font_scale == "Small":
            self.f_size, self.row_height = dp(18), dp(65)
        elif self.font_scale == "Medium":
            self.f_size, self.row_height = dp(23), dp(75)
        else: # Large
            self.f_size, self.row_height = dp(28), dp(85)

    def change_font_size(self, size):
        if size != self.font_scale:
            self.font_scale = size
            self.update_font_metrics()
            self.item_input.font_size = self.f_size
            
            # Save only local settings here to avoid unnecessary cloud traffic
            local_settings = {'font_scale': self.font_scale}
            with open(os.path.join(self.user_data_dir, "local_settings.json"), 'w') as f:
                json.dump(local_settings, f)
            
            self.refresh_ui()

    def clear_entire_list(self, instance=None):
        self.all_lists[self.active_list_name] = [{
            'name': 'PLACEHOLDER', 
            'done': False, 
            'cat': 'Uncategorized',
            'count': 1
        }]        

        self.save_data()
        self.refresh_ui()

    @property
    def cloud_url(self):
        # This dynamically builds the URL based on your Family ID
        return f"{self.BASE_URL}{self.family_id}.json"

    def save_data(self, instance=None):
        # 1. Always save locally first (The 'Safety Net')
        try:
            with open(self.data_file, 'w') as f:
                json.dump({
                    'all_lists': self.all_lists,
                    'categories': self.categories,
                    'active_list_name': self.active_list_name
                }, f, indent=4)
        except Exception as e:
            print(f"Local save failed: {e}")

        # 2. Try to upload, but be quiet if it fails
        try:
            payload = {
                self.family_id: {
                    'all_lists': self.all_lists,
                    'categories': self.categories,
                    'active_list_name': self.active_list_name
                }
            }
            # Reduced timeout for faster 'failing' when offline
            requests.put(self.cloud_url, json=payload, timeout=3, verify=certifi.where())
            
            # If successful, update the label to show it's backed up
            self.sync_label.text = f"Last Synced: {datetime.now().strftime('%H:%M')}"
            self.sync_label.color = (0.6, 0.6, 0.6, 1)
            
        except Exception:
            # Instead of a popup, we just change the Status Bar color
            self.sync_label.text = "Offline (Saved Locally)"
            self.sync_label.color = (1, 0.6, 0, 1) # Orange warning color

        # 3. Keep saving your local settings (ID, Font) to the phone/PC disk
        local = {'font_scale': self.font_scale, 'family_id': self.family_id}
        local_path = os.path.join(self.user_data_dir, "local_settings.json")
        with open(local_path, 'w') as f:
            json.dump(local, f)

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

    # --- UI & LISTS ---
    def refresh_ui(self, *args):
        self.list_spinner.text = self.active_list_name
        self.list_spinner.values = list(self.all_lists.keys())        
        self.list_layout.clear_widgets()
        active_bg = (1, 1, 1, 1)
        done_bg = (0.85, 0.85, 0.85, 1)
        
        # 1. Get the raw items
        raw_items = self.all_lists.get(self.active_list_name, [])
        
        # 2. Filter out the "PLACEHOLDER" if it's a string, or if it's a dict named placeholder
        # This prevents the sorter from crashing
        items_to_show = [i for i in raw_items if isinstance(i, dict) and i.get('name') != "PLACEHOLDER"]
        
        # 3. Sort the filtered items
        items = sorted(items_to_show, 
                       key=lambda x: self.categories.get(x.get('cat', 'Uncategorized'), {'order': 99})['order'])
        
        curr_cat = None
        for i in items:
            # Standard "hide completed" check
            if i.get('done') and not self.show_completed: 
                continue
            
            # Category Header Logic
            if i.get('cat') != curr_cat:
                curr_cat = i.get('cat', 'Uncategorized')
                self.list_layout.add_widget(Label(
                    text=f"-- {curr_cat.upper()} --", 
                    size_hint_y=None, height=dp(40), 
                    bold=True, color=(0.5, 0.5, 0.5, 1)
                ))
            
            # Quantity Logic
            qty_val = i.get('count', 1)
            qty_text = f" [b]x{qty_val}[/b]" if qty_val > 1 else ""
            
            # Create the Row
            row = ListItem(
                item_ref=i, 
                text=f"[s]{i['name']}{qty_text}[/s]" if i['done'] else f"{i['name']}{qty_text}", 
                background_color=(done_bg if i['done'] else active_bg)
            )
            self.list_layout.add_widget(row)

        self.update_stats()

    def create_new_list(self, instance):
        # 1. Generate the name (List 1, List 2, etc.)
        n = f"List {len(self.all_lists) + 1}"
        
        # 2. Initialize with a dictionary placeholder 
        # This prevents Firebase from deleting the list while keeping refresh_ui happy
        self.all_lists[n] = [{
            'name': 'PLACEHOLDER', 
            'done': False, 
            'cat': 'Uncategorized',
            'count': 1
        }]

        # 3. Update the UI components
        self.list_spinner.values = list(self.all_lists.keys())
        self.list_spinner.text = n
        
        # 4. Save to Cloud and refresh the screen
        self.save_data(instance=instance)
        self.refresh_ui()

    def add_item(self, text):
        if not text: return
        
        current_list = self.all_lists[self.active_list_name]
        current_list.append(text)
        self.save_data()
        self.refresh_ui()

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
        name = self.item_input.text.strip()
        if not name: return

        # 1. Search for an existing category match
        cat = None
        for category_name, details in self.categories.items():
            keywords = details.get('keywords', [])
            if any(name.lower() == k.lower() for k in keywords):
                cat = category_name
                break
        
        # 2. Decision: Do we know the category or do we need to ask?
        if cat:
            # We found a match! Add it immediately
            self.add_to_list(name, cat)
            self.item_input.text = ""
        else:
            # No match found. Open the popup to ask the user.
            self.show_category_popup(name)
            # We don't clear the text yet so the user can see what they're categorizing

    def show_category_popup(self, name):
        content = GridLayout(cols=2, spacing=dp(10), padding=dp(10))
        popup = Popup(title=f"Category for '{name}'", content=content, size_hint=(0.9, 0.6))

        for cat in self.categories.keys():
            btn = Button(text=cat, height=dp(50), size_hint_y=None)
            # When clicked, add the item and the new keyword
            btn.bind(on_release=lambda b, c=cat: self.finalize_addition(name, c, popup))
            content.add_widget(btn)

        popup.open()

    def finalize_addition(self, name, cat, popup):
        # 1. Add the keyword to the category so the app "learns" it for next time
        if name.lower() not in [k.lower() for k in self.categories[cat].get('keywords', [])]:
            if 'keywords' not in self.categories[cat]:
                self.categories[cat]['keywords'] = []
            self.categories[cat]['keywords'].append(name.lower())
        
        # 2. Add to list and close
        self.add_to_list(name, cat)
        popup.dismiss()
        self.item_input.text = "" # Clear the input now
        if hasattr(self, 'prediction_drop'):
            self.prediction_drop.dismiss()

    def add_to_list(self, name, cat):
        target = self.all_lists[self.active_list_name]
        
        # Look for existing item (skip the placeholder while searching)
        found = next((i for i in target if isinstance(i, dict) and i.get('name') == name.capitalize() and not i['done']), None)
        
        if found:
            found['count'] = found.get('count', 1) + 1
        else:
            target.append({'name': name.capitalize(), 'done': False, 'cat': cat, 'count': 1})
        
        self.save_data()
        self.refresh_ui()

    def on_manual_select(self, spinner, value):
        if value != 'Category?':
            name = self.item_input.text.strip().lower()
            if name not in self.categories[value]['keywords']: self.categories[value]['keywords'].append(name)
            self.add_to_list(name, value); self.cat_selector.height, self.cat_selector.opacity = 0, 0

    def toggle_completed(self, instance): self.show_completed = not self.show_completed; self.done_btn.text = "HIDE DONE" if self.show_completed else "SHOW DONE"; self.refresh_ui()
    
    def clear_completed(self, instance=None): # Added =None to make it optional
        current_list = self.all_lists.get(self.active_list_name, [])
        
        # We keep items that are NOT done OR are the PLACEHOLDER
        self.all_lists[self.active_list_name] = [
            i for i in current_list 
            if not i.get('done') or i.get('name') == "PLACEHOLDER"
        ]
        
        self.save_data()
        self.refresh_ui()

    def switch_list(self, spinner, text): self.active_list_name = text; self.save_data(); self.refresh_ui()

    def confirm_action(self, msg, callback):
        content = BoxLayout(orientation='vertical', padding=dp(10))
        content.add_widget(Label(text=msg))
        btns = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        
        # We wrap the callback to ensure the popup closes
        y = Button(text="YES", on_release=lambda x: (callback(), p.dismiss()))
        n = Button(text="NO", on_release=lambda x: p.dismiss())
        
        btns.add_widget(n); btns.add_widget(y)
        content.add_widget(btns)
        p = Popup(title="Confirm", content=content, size_hint=(0.8, 0.3))
        p.open()

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

    def update_family_id(self, new_id):
        if not new_id:
            return

        # 1. Update the variable and the file path
        self.family_id = new_id
        self.data_file = os.path.join(self.user_data_dir, f"shopping_data_{self.family_id}.json")
        
        # 2. Save settings so it persists on restart
        local = {'font_scale': self.font_scale, 'family_id': self.family_id}
        local_path = os.path.join(self.user_data_dir, "local_settings.json")
        with open(local_path, 'w') as f:
            json.dump(local, f)

        # 3. Reload the data for this NEW family
        self.load_data()

        # 4. --- CRITICAL UI UPDATES ---
        # Explicitly update the spinner text and the available list names
        self.list_spinner.values = list(self.all_lists.keys())
        self.list_spinner.text = self.active_list_name
        
        # Redraw the main list items
        self.refresh_ui()
        
        # 5. Trigger cloud sync for the new ID
        self.sync_now()
        
        self.notify(f"Synced to ID: {self.family_id}")

    def sync_now(self, instance=None):
        self.sync_btn.background_color = (0.2, 1, 0.2, 1) 
        self.sync_label.text = "Syncing..."

        def reset_button_color(dt):
            self.sync_btn.background_color = (1, 1, 1, 1)

        try:
            # 1. DOWNLOAD FIRST - Check what the cloud has before we speak
            res = requests.get(self.cloud_url, timeout=10, verify=certifi.where())
            
            if res.status_code == 200:
                data = res.json()
                cloud_data = data.get(self.family_id) if data else None

                if cloud_data:
                    # CLOUD HAS DATA: Adopt the cloud's reality
                    cloud_lists = cloud_data.get('all_lists', {})
                    
                    # Update local RAM
                    self.all_lists = cloud_lists
                    self.categories = cloud_data.get('categories', self.categories)
                    
                    # CRITICAL FIX: Verify the list name exists in the data we just pulled
                    cloud_active = cloud_data.get('active_list_name')
                    if cloud_active in self.all_lists:
                        self.active_list_name = cloud_active
                    else:
                        # If the cloud's active list name is weird, pick the first valid list available
                        self.active_list_name = list(self.all_lists.keys())[0] if self.all_lists else "Groceries"

                    # Save this good cloud data to our local file immediately
                    with open(self.data_file, 'w') as f:
                        json.dump({
                            'all_lists': self.all_lists,
                            'categories': self.categories,
                            'active_list_name': self.active_list_name
                        }, f, indent=4)

                    self.refresh_ui()
                    self.sync_label.text = f"Pulled: {datetime.now().strftime('%H:%M:%S')}"
                    self.sync_label.color = (0.6, 0.6, 0.6, 1)
                
                else:
                    # CLOUD IS EMPTY: Now it is safe to upload our local data
                    has_real_content = any(
                        any(isinstance(i, dict) and i.get('name') != "PLACEHOLDER" for i in items)
                        for items in self.all_lists.values()
                    )
                    
                    if has_real_content:
                        self.save_data() # This pushes local to cloud
                        self.sync_label.text = "Cloud Initialized"
                    else:
                        self.sync_label.text = "Both Empty"

            Clock.schedule_once(reset_button_color, 1)

        except Exception as e:
            print(f"Sync failed: {e}")
            self.sync_label.text = "Offline"
            self.sync_label.color = (1, 0.6, 0, 1) 
            self.sync_btn.background_color = (1, 0.3, 0.3, 1)
            Clock.schedule_once(reset_button_color, 1)

    def update_stats(self):
        current_list = self.all_lists.get(self.active_list_name, [])
        
        # IMPROVED FILTER: Handle if the list is just [None] or contains 
        # the placeholder string/dict consistently.
        real_items = [
            i for i in current_list 
            if isinstance(i, dict) and i.get('name') != "PLACEHOLDER"
        ]
        
        total = len(real_items)
        remaining = len([i for i in real_items if not i.get('done')])
        
        if total == 0:
            self.stats_label.text = "List is empty"
        else:
            self.stats_label.text = f"{remaining}/{total} left to find"

    def on_start(self):
        # Only auto-sync if we have a family ID set
        if self.family_id and self.family_id != "DefaultFamily":
            Clock.schedule_once(self.auto_sync, 0.5)

    def auto_sync(self, dt):
        # This calls your existing sync code
        self.sync_now()

    def force_download_confirmed(self, *args):
        self.sync_label.text = "Forcing Download..."
        try:
            res = requests.get(self.cloud_url, timeout=10, verify=certifi.where())
            if res.status_code == 200:
                data = res.json()
                
                # We pull the data for your specific family_id
                # If the family_id doesn't even exist in the JSON, we use an empty dict
                cloud_data = data.get(self.family_id, {})

                # 1. OVERWRITE RAM
                # We pull from cloud_data. If a key is missing, we use safe defaults.
                self.all_lists = cloud_data.get('all_lists', {})
                self.categories = cloud_data.get('categories', self.categories)
                self.active_list_name = cloud_data.get('active_list_name', 'Groceries')

                # 2. SAFETY CHECK / PLACEHOLDER RE-ENTRY
                # If the cloud was empty or the active list doesn't exist/is empty:
                if self.active_list_name not in self.all_lists or not self.all_lists[self.active_list_name]:
                    self.all_lists[self.active_list_name] = [
                        {"name": "PLACEHOLDER", "done": False, "category": "Uncategorized"}
                    ]

                # 3. SAVE TO DISK
                with open(self.data_file, 'w') as f:
                    json.dump({
                        'all_lists': self.all_lists,
                        'categories': self.categories,
                        'active_list_name': self.active_list_name
                    }, f, indent=4)
                
                # 4. REFRESH UI
                # IMPORTANT: Ensure refresh_ui updates the Spinner text/values too!
                self.refresh_ui()
                
                self.sync_label.text = "Cloud Overwrote Phone"
                self.sync_label.color = (0.6, 0.6, 0.6, 1)
            else:
                self.sync_label.text = f"Server Error: {res.status_code}"
                
        except Exception as e:
            print(f"Force Download Error: {e}")
            self.sync_label.text = "Pull Failed"
            self.sync_label.color = (1, 0.6, 0, 1)


if __name__ == '__main__':
    ShoppingApp().run()
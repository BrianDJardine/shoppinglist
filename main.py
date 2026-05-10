import json, os, shutil, requests, certifi, uuid, threading, copy
from datetime import datetime, timedelta
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
from kivy.uix.checkbox import CheckBox

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
            color=(0, 0, 0, 1),
            size_hint_y=None,
            height=app.row_height
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
        app = App.get_running_app()

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
        header.add_widget(Label(text="CATEGORIES", font_size=dp(18), bold=True))
        self.container.add_widget(header)

        add_box = BoxLayout(size_hint_y=None, height=App.get_running_app().row_height, spacing=dp(5))
        self.new_cat_input = TextInput(hint_text="New Category...", multiline=False, font_size=app.f_size,
                                       input_type='text', input_filter=None, keyboard_suggestions=True)

        add_btn = Button(
            text='ADD', 
            size_hint_x=0.25, 
            background_color=(0.2, 0.7, 0.3, 1), 
            bold=True, 
            on_press=self.add_category,
            font_size=app.f_size
        )
        
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
        
        # Neutralizer for the icons
        s = getattr(Metrics, 'fontscale', 1.0)
        if s <= 0: s = 1.0
        # This keeps the buttons at a consistent physical size (~38dp)
        icon_btn_size = dp(38 / s) 

        sorted_cats = sorted(app.categories.items(), key=lambda x: x[1].get('order', 99))
        
        for name, data in sorted_cats:
            row = BoxLayout(size_hint_y=None, height=app.row_height, spacing=dp(5))
            
            # --- Order Buttons (PNGs) ---
            # Width is icon_btn_size * 2 + spacing
            order_box = BoxLayout(orientation='horizontal', size_hint_x=None, width=icon_btn_size * 2 + dp(4))
            
            up = Button(
                background_normal='up-arrow.png',
                size_hint=(None, None),
                size=(icon_btn_size, icon_btn_size),
                pos_hint={'center_y': 0.5}
            )
            up.bind(on_release=lambda x, n=name: self.move_cat(n, -1))
            
            dn = Button(
                background_normal='down-arrow.png',
                size_hint=(None, None),
                size=(icon_btn_size, icon_btn_size),
                pos_hint={'center_y': 0.5}
            )
            dn.bind(on_release=lambda x, n=name: self.move_cat(n, 1))
            
            order_box.add_widget(up)
            order_box.add_widget(dn)
            # ----------------------------

            lbl = Button(
                text=name.upper(), 
                font_size=app.f_size, 
                bold=True, 
                background_color=(0.2, 0.2, 0.2, 1), 
                halign='left', 
                valign='middle'
            )
            lbl.bind(size=lbl.setter('text_size'))
            lbl.bind(on_release=lambda x, n=name: self.rename_category_popup(n))
            
            row.add_widget(order_box)
            row.add_widget(lbl)
            
            if name != "Uncategorized":
                # Neutralize the Delete 'X' button size as well
                del_btn = Button(
                    text="X", 
                    size_hint_x=None, 
                    width=dp(50 / s), 
                    font_size=app.f_size,
                    bold=True,
                    background_color=(0.8, 0.2, 0.2, 1)
                )
                del_btn.bind(on_release=lambda x, n=name: self.delete_category(n))
                row.add_widget(del_btn)
                
            self.cat_list_layout.add_widget(row)

    def rename_category_popup(self, old_name):
        if old_name == "Uncategorized": return
        app = App.get_running_app()
        s_font = app.f_size

        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        inp = TextInput(text=old_name, multiline=False, size_hint_y=None, 
                        height=app.row_height, font_size=s_font, input_type='text',
                        input_filter=None, keyboard_suggestions=True)
        content.add_widget(inp)

        btn = Button(text="UPDATE", size_hint_y=None, height=app.row_height, 
                     bold=True, font_size=s_font)
        content.add_widget(btn)
        
        p = Popup(title="Rename", content=content, size_hint=(0.8, 0.4))

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
        app = App.get_running_app()
        # Use a secondary font size (75% of main)
        s_font = app.f_size * 0.75

        # ROOT LAYOUT (The main container)
        root = BoxLayout(orientation='vertical', padding=[dp(15), 0, dp(15), dp(15)])

        # HEADER (Stays fixed at the top)
        header = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(5))

        with header.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            self.header_rect = Rectangle(size=header.size, pos=header.pos)
        header.bind(size=self._update_header_rect, pos=self._update_header_rect)

        back_btn = Button(background_normal='back.png', size_hint=(None, None), size=(dp(35), dp(35)), pos_hint={'center_y': 0.5})
        back_btn.bind(on_release=lambda x: setattr(app.sm, 'current', 'main'))
        header.add_widget(back_btn)
        header.add_widget(Label(text="SETTINGS", font_size=dp(18), bold=True))
        root.add_widget(header)

        # SCROLLVIEW (For all the settings below the header)
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self.layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(15))
        self.layout.bind(minimum_height=self.layout.setter('height')) # Key for scrolling!

        self.layout.add_widget(Label(text="Display Text Size:", size_hint_y=None, height=dp(30), font_size=s_font))
        self.font_spinner = Spinner(text="Large", values=("Smallest", "Small", "Medium", "Large"), size_hint_y=None, height=app.row_height * 0.8, font_size=s_font, option_cls=CustomSpinnerOption)
        self.font_spinner.bind(text=lambda s, t: App.get_running_app().change_font_size(t))
        self.layout.add_widget(self.font_spinner)

        # --- Use By Offset Setting ---
        offset_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(10))
        offset_lbl = Label(text="Use By Days:", font_size=s_font, halign='left')
        offset_lbl.bind(size=offset_lbl.setter('text_size'))

        # Stepper Controls Container
        stepper_box = BoxLayout(size_hint_x=None, width=dp(113), spacing=dp(5))

        # Minus Button
        btn_minus = Button(
            text="-", 
            size_hint_x=None, 
            width=dp(34), 
            font_size=s_font * 1.2, # Kept ratio but based on smaller font
            bold=True
        )
        btn_minus.bind(on_release=lambda x: self.change_offset(-1))

        # The Number Display
        self.offset_display = Label(
            text=str(app.use_by_offset), 
            font_size=s_font, 
            bold=True
        )
        
        # Plus Button: 45 * 0.75 = 34
        btn_plus = Button(
            text="+", 
            size_hint_x=None, 
            width=dp(34), 
            font_size=s_font * 1.2, 
            bold=True
        )
        btn_plus.bind(on_release=lambda x: self.change_offset(1))

        stepper_box.add_widget(btn_minus)
        stepper_box.add_widget(self.offset_display)
        stepper_box.add_widget(btn_plus)

        offset_row.add_widget(offset_lbl)
        offset_row.add_widget(stepper_box)
        self.layout.add_widget(offset_row)

       # Show Dates toggle
        date_toggle_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        date_toggle_lbl = Label(text="Show Dates:", font_size=s_font, halign='left')
        date_toggle_lbl.bind(size=date_toggle_lbl.setter('text_size'))
        
        self.date_checkbox = CheckBox(
            active=app.show_dates, 
            size_hint_x=None, 
            width=dp(50),
            color=(0.2, 0.6, 1, 1) # Blueish tint
        )

        with self.date_checkbox.canvas.before:
            Color(0.3, 0.3, 0.3, 1)
            side = dp(24)
            # Initial positioning (will be updated by the bind immediately)
            self.date_checkbox.cb_rect = Rectangle(
                pos=(self.date_checkbox.center_x - side/2, self.date_checkbox.center_y - side/2),
                size=(side, side)
            )

        self.date_checkbox.bind(pos=self._update_cb_rect, size=self._update_cb_rect)
        self.date_checkbox.bind(active=self.on_toggle_dates)
        
        date_toggle_row.add_widget(date_toggle_lbl)
        date_toggle_row.add_widget(self.date_checkbox)
        self.layout.add_widget(date_toggle_row)

        # Family ID
        self.id_input = TextInput(multiline=False, size_hint_y=None, height=App.get_running_app().row_height, 
                                  hint_text="Family ID...", font_size=s_font, input_type='text',
                                  input_filter=None, keyboard_suggestions=True)
        self.layout.add_widget(self.id_input)
        save_btn = Button(text="UPDATE ID", size_hint_y=None, height=App.get_running_app().row_height, background_color=(0.2, 0.6, 1, 1), bold=True, font_size=s_font)
        save_btn.bind(on_release=self.apply_id_change)
        self.layout.add_widget(save_btn)

        # Upload
        push_btn = Button(text="FORCE UPLOAD", size_hint_y=None, height=App.get_running_app().row_height, background_color=(0.2, 0.7, 0.3, 1), font_size=s_font)
        push_btn.bind(on_release=lambda x: App.get_running_app().confirm_action("Upload data?", App.get_running_app().save_data))
        self.layout.add_widget(push_btn)

        # Download
        pull_btn = Button(text="FORCE DOWNLOAD", size_hint_y=None, height=App.get_running_app().row_height, background_color=(0.7, 0.5, 0.2, 1), font_size=s_font)
        pull_btn.bind(on_release=lambda x: App.get_running_app().confirm_action("Overwrite from cloud?", App.get_running_app().force_download_confirmed))
        self.layout.add_widget(pull_btn)

        # Add the layout to the scrollview, and scrollview to root
        scroll.add_widget(self.layout)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_toggle_dates(self, checkbox, value):
        app = App.get_running_app()
        app.show_dates = value
        app.save_settings()
        app.refresh_ui()

    def change_offset(self, direction):
        app = App.get_running_app()
        new_val = app.use_by_offset + direction
        
        if 0 <= new_val <= 9:
            app.use_by_offset = new_val
            self.offset_display.text = str(new_val)
            # Save immediately so she doesn't lose it
            app.save_settings()
            # If you want the main screen to update instantly:
            app.refresh_ui()

    def on_pre_enter(self):
        app = App.get_running_app()
        self.font_spinner.text = app.font_scale
        self.id_input.text = app.family_id
        self.offset_display.text = str(app.use_by_offset)
        self.date_checkbox.active = app.show_dates

    def apply_id_change(self, instance):
        App.get_running_app().update_family_id(self.id_input.text.strip())

    def _update_header_rect(self, instance, value):
        self.header_rect.pos = instance.pos
        self.header_rect.size = instance.size

    def _update_cb_rect(self, instance, value):
        # We want the background box to be 24dp
        side = dp(24)
        # Center the rectangle on the CheckBox's center
        instance.cb_rect.pos = (instance.center_x - side/2, instance.center_y - side/2)
        instance.cb_rect.size = (side, side)

# --- MAIN APP ---
class ShoppingApp(App):
    BASE_URL = "https://shoppinglist-eae1c-default-rtdb.europe-west1.firebasedatabase.app/protect_data/AppV1_Secure_99xCapybarasForever/"

    def build(self):
        # Initial Scaling Setup
        self.use_by_offset = 5
        self.show_dates = True
        self.font_scale = "Large"
        self.show_completed = False
        local_path = os.path.join(self.user_data_dir, "local_settings.json")
        if os.path.exists(local_path):
            try:
                with open(local_path, 'r') as f:
                    d = json.load(f)
                    self.font_scale = d.get('font_scale', 'Large')
                    self.family_id = d.get('family_id', 'DefaultFamily')
                    self.use_by_offset = d.get('use_by_offset', 5)
                    self.show_dates = d.get('show_dates', True)
            except: self.family_id = "DefaultFamily"
        else: self.family_id = "DefaultFamily"

        self.update_font_metrics()
        self.load_data()
        self.prediction_drop = DropDown()
        self.sm = ScreenManager()

        self.main_page = Screen(name='main')
        main_layout = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(6))
        
        # --- HEADER (Scrollable Icons) ---
        # Lock the header height to a consistent size
        s = getattr(Metrics, 'fontscale', 1.0)
        if s <= 0: s = 1.0
        header_height = dp(55 / s)

        #header_height = max(self.row_height * 0.8, dp(50)) 
        header_row = BoxLayout(size_hint_y=None, height=header_height)
        self.list_spinner = Spinner(text=self.active_list_name, values=list(self.all_lists.keys()),
                                    size_hint_x=0.28, background_color=(0.15, 0.15, 0.15, 1), bold=False, 
                                    font_size=self.f_size * 0.9, option_cls=CustomSpinnerOption)
        self.list_spinner.bind(text=self.switch_list)
        header_row.add_widget(self.list_spinner)

        # Icon ScrollView prevents squashing on large font phones
        icon_scroll = ScrollView(do_scroll_y=False, size_hint_x=0.72)
        icon_row = BoxLayout(size_hint_x=None, spacing=dp(2)) # Tighter spacing
        icon_row.bind(minimum_width=icon_row.setter('width'))

        def quick_btn(img, callback, tint=(1, 1, 1, 1)):
            # Get the current system scale
            s = getattr(Metrics, 'fontscale', 1.0)
            if s <= 0: s = 1.0

            #btn_dim = dp(45)
            btn_dim = dp(40 / s)

            b = Button(
                background_normal=img, 
                on_release=callback, 
                background_color=tint, 
                size_hint=(None, None), 
                size=(btn_dim, btn_dim), 
                pos_hint={'center_y': 0.5}
            )

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

        # --- DATE CALCULATOR ROW ---
        today_str = datetime.now().strftime("%a %d")
        use_by_date = (datetime.now() + timedelta(days=self.use_by_offset)).strftime("%a %d")

        # Create a layout for the dates
        self.date_row = BoxLayout(size_hint_y=None, height=self.row_height * 0.8, padding=[dp(10), 0])
        
        # Today's Label
        self.today_lbl = Label(
            text=f"Today: [color=888888]{today_str}[/color]", 
            markup=True,
            font_size=self.f_size * 0.9,
            bold=True,
            halign='left'
        )
        self.today_lbl.bind(size=self.today_lbl.setter('text_size'))
        
        # Use By Label
        self.use_by_lbl = Label(
            text=f"Use By: [color=ff5555]{use_by_date}[/color]", 
            markup=True,
            font_size=self.f_size * 0.9,
            bold=True,
            halign='right'
        )
        self.use_by_lbl.bind(size=self.use_by_lbl.setter('text_size'))

        self.date_row.add_widget(self.today_lbl)
        self.date_row.add_widget(self.use_by_lbl)
        
        # Add it to the main layout
        main_layout.add_widget(self.date_row)

        # INPUT
        input_height = self.row_height * 0.75
        input_box = BoxLayout(size_hint_y=None, height=input_height, spacing=dp(5))
        self.item_input = TextInput(
            hint_text='Add item...', 
            multiline=False, 
            font_size=self.f_size,
            size_hint_x=0.7,
            input_type='text',
            input_filter=None,
            keyboard_suggestions=True            
        )
        self.item_input.bind(text=self.on_type_prediction)

        add_btn = Button(
            text='ADD', 
            size_hint_x=0.25, 
            background_color=(0.2, 0.7, 0.3, 1), 
            bold=True, 
            on_press=self.process_addition,
            font_size=self.f_size 
        )
        
        input_box.add_widget(self.item_input)
        input_box.add_widget(add_btn)
        main_layout.add_widget(input_box)

        self.list_layout = GridLayout(cols=1, size_hint_y=None, spacing=dp(6))
        self.list_layout.bind(minimum_height=self.list_layout.setter('height'))
        scroll = ScrollView(size_hint_y=1, do_scroll_x=False) 
        scroll.add_widget(self.list_layout)

        main_layout.add_widget(scroll)

        # STATUS
        status_bar = BoxLayout(size_hint_y=None, height=dp(25))
        self.stats_label = Label(text="0 items", font_size=dp(12), color=(0.7, 0.7, 0.7, 1))
        self.sync_label = Label(text="Sync: Never", font_size=dp(12), color=(0.7, 0.7, 0.7, 1))
        status_bar.add_widget(self.stats_label); status_bar.add_widget(self.sync_label)
        main_layout.add_widget(status_bar)        
        
        # FOOTER
        bot = BoxLayout(size_hint_y=None, height=self.row_height, spacing=dp(5))

        self.done_btn = Button(text="SHOW\nDONE", halign='center', valign='middle', bold=True, font_size=dp(14))
        self.done_btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
        self.done_btn.bind(on_press=self.toggle_completed)

        del_done_btn = Button(text="DELETE\nDONE", halign='center', valign='middle', background_color=(0.7, 0.3, 0.3, 1), bold=True, font_size=dp(14))
        del_done_btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
        del_done_btn.bind(on_press=lambda x: self.confirm_action("Delete done?", self.clear_completed))
        
        clear_btn = Button(text="CLEAR\nLIST", halign='center', valign='middle', background_color=(0.9, 0.4, 0.4, 1), bold=True, font_size=dp(14))
        clear_btn.bind(size=lambda s, w: setattr(s, 'text_size', (w[0], None)))
        clear_btn.bind(on_press=lambda x: self.confirm_action("Wipe list?", self.clear_entire_list))

        bot.add_widget(self.done_btn)
        bot.add_widget(del_done_btn)
        bot.add_widget(clear_btn)

        main_layout.add_widget(bot)

        self.main_page.add_widget(main_layout); self.sm.add_widget(self.main_page)
        self.sm.add_widget(CategoryScreen(name='categories'))
        self.sm.add_widget(SettingsScreen(name='settings'))

        self.refresh_ui(); return self.sm

    def update_font_metrics(self):
        # Safety check: if Metrics isn't ready, default to 1.0
        s = getattr(Metrics, 'fontscale', 1.0)
        if s <= 0: 
            s = 1.0

        # If the text is STILL invisible, it might be too small. 
        # Let's set a 'floor' (minimum size)
        if self.font_scale == "Smallest":
            self.f_size, self.row_height = max(dp(12), dp(14/s)), max(dp(45), dp(55/s))
        elif self.font_scale == "Small":
            self.f_size, self.row_height = max(dp(14), dp(18/s)), max(dp(50), dp(65/s))
        elif self.font_scale == "Medium":
            self.f_size, self.row_height = max(dp(18), dp(22/s)), max(dp(60), dp(75/s))
        else: # Large
            self.f_size, self.row_height = max(dp(22), dp(26/s)), max(dp(70), dp(85/s))

    def change_font_size(self, size):
        self.font_scale = size
        self.update_font_metrics()
        self.item_input.font_size = self.f_size
        local = {'font_scale': self.font_scale, 'family_id': self.family_id}
        with open(os.path.join(self.user_data_dir, "local_settings.json"), 'w') as f:
            json.dump(local, f)
        self.refresh_ui()

    def save_settings(self):
        # Ensure we use the same filename as the build method
        local_path = os.path.join(self.user_data_dir, "local_settings.json")
        settings_data = {
            'font_scale': self.font_scale,
            'family_id': self.family_id,
            'use_by_offset': self.use_by_offset,
            'show_dates': self.show_dates
        }
        with open(local_path, 'w') as f:
            json.dump(settings_data, f)

    def load_data(self):
        self.categories = {'Uncategorized': {'order': 99, 'keywords': []}}
        self.all_lists = {'Groceries': [{"name": "PLACEHOLDER", "done": False, "cat": "Uncategorized"}]}
        self.active_list_name = 'Groceries'
        self.tombstones = {}  # {item_id: deletion_iso_timestamp}
        self.data_file = os.path.join(self.user_data_dir, f"shopping_data_{self.family_id}.json")

        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    local_data = json.load(f)
                    self.all_lists = local_data.get('all_lists', self.all_lists)
                    self.categories = local_data.get('categories', self.categories)
                    self.active_list_name = local_data.get('active_list_name', self.active_list_name)
                    self.tombstones = local_data.get('tombstones', {})
            except: pass

    @property
    def cloud_url(self):
        return f"{self.BASE_URL}{self.family_id}.json"

    # ------------------------------------------------------------------
    # Merge helpers
    # ------------------------------------------------------------------
    def _merge_items(self, local_items, cloud_items):
        """Merge two item lists. Items with a UUID use newest-timestamp-wins.
        Legacy items (no id) are merged by name; cloud wins on conflict."""
        def is_tracked(i): return bool(i.get('id')) and i.get('name') != 'PLACEHOLDER'
        def is_legacy(i):  return not i.get('id') and i.get('name') != 'PLACEHOLDER'

        local_tracked = {i['id']: i for i in local_items if is_tracked(i)}
        cloud_tracked = {i['id']: i for i in cloud_items if is_tracked(i)}
        local_legacy  = [i for i in local_items if is_legacy(i)]
        cloud_legacy  = [i for i in cloud_items  if is_legacy(i)]

        # Tracked: newest last_modified wins, but respect tombstones
        merged_tracked = {}
        for item_id in set(local_tracked) | set(cloud_tracked):
            l = local_tracked.get(item_id)
            c = cloud_tracked.get(item_id)
            if l and c:
                candidate = l if l.get('last_modified', '') >= c.get('last_modified', '') else c
            else:
                candidate = l or c
            # Skip if tombstoned (deletion timestamp >= item's last_modified)
            tomb_ts = self.tombstones.get(item_id, '')
            if candidate and (not tomb_ts or tomb_ts < candidate.get('last_modified', '')):
                merged_tracked[item_id] = candidate

        # Legacy: merge by name, cloud wins on conflict, local adds any missing
        legacy_by_name = {i.get('name', '').lower(): i for i in local_legacy}
        for i in cloud_legacy:
            legacy_by_name[i.get('name', '').lower()] = i

        result = [{'name': 'PLACEHOLDER', 'done': False, 'cat': 'Uncategorized'}]
        result += list(legacy_by_name.values())
        result += list(merged_tracked.values())
        return result

    def _merge_all_lists(self, local_lists, cloud_lists):
        """Merge shopping lists during a sync pull.
        Cloud is the authority for which lists exist — lists deleted on one device
        are removed from cloud via direct PUT, so the other device drops them here.
        Items within each cloud list are merged with local data (newest-wins)."""
        return {
            name: self._merge_items(local_lists.get(name, []), cloud_lists[name])
            for name in cloud_lists  # only lists cloud knows about
        }

    # ------------------------------------------------------------------
    # Save / Sync
    # ------------------------------------------------------------------
    def _save_locally(self):
        """Persist current state to the local JSON file."""
        with open(self.data_file, 'w') as f:
            json.dump({'all_lists': self.all_lists, 'categories': self.categories,
                       'active_list_name': self.active_list_name, 'tombstones': self.tombstones}, f)

    def save_data(self, instance=None):
        """Save locally immediately, then upload local state directly to cloud (no merge)."""
        self._save_locally()
        snap_lists  = copy.deepcopy(self.all_lists)
        snap_cats   = copy.deepcopy(self.categories)
        snap_active = self.active_list_name
        snap_tombs  = copy.deepcopy(self.tombstones)
        threading.Thread(target=self._upload_direct, args=(snap_lists, snap_cats, snap_active, snap_tombs), daemon=True).start()

    def _upload_direct(self, local_lists, categories, active_list_name, tombstones):
        """Background thread: PUT local state straight to cloud with no merge."""
        try:
            payload = {self.family_id: {'all_lists': local_lists, 'categories': categories,
                                        'active_list_name': active_list_name, 'tombstones': tombstones}}
            requests.put(self.cloud_url, json=payload, timeout=5, verify=certifi.where())
            now = datetime.now().strftime('%H:%M')
            Clock.schedule_once(lambda dt: (
                setattr(self.sync_label, 'text',  f'Synced: {now}'),
                setattr(self.sync_label, 'color', (0.6, 0.6, 0.6, 1))
            ))
        except Exception:
            Clock.schedule_once(lambda dt: self._set_sync_offline())

    def _set_sync_offline(self):
        self.sync_label.text  = "Offline (Local Only)"
        self.sync_label.color = (1, 0.5, 0.3, 1)

    def _set_sync_error(self, msg):
        self.sync_label.text  = msg
        self.sync_label.color = (1, 0.3, 0.3, 1)

    def refresh_ui(self, *args):

        t_str = datetime.now().strftime("%a %d")
        u_str = (datetime.now() + timedelta(days=self.use_by_offset)).strftime("%a %d")
        
        self.today_lbl.font_size = self.f_size * 0.9
        self.today_lbl.text = f"Today: [color=888888]{t_str}[/color]"
        
        self.use_by_lbl.font_size = self.f_size * 0.9
        self.use_by_lbl.text = f"Use By: [color=ff5555]{u_str}[/color]"

        if self.show_dates:
            self.date_row.height = self.row_height * 0.8
            self.date_row.opacity = 1  # Make it visible
            self.date_row.disabled = False # Re-enable touches            
        else:
            self.date_row.height = 0    # Collapse the space
            self.date_row.opacity = 0  # Hide the text
            self.date_row.disabled = True # Prevent accidental ghost-clicks

        self.item_input.height = self.row_height * 0.75

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
        if found:
            found['count'] = found.get('count', 1) + 1
            found['last_modified'] = datetime.utcnow().isoformat()
        else:
            target.append({
                'id':            str(uuid.uuid4()),
                'name':          name.capitalize(),
                'done':          False,
                'cat':           cat,
                'count':         1,
                'last_modified': datetime.utcnow().isoformat()
            })
        self.save_data(); self.refresh_ui()

    def toggle_completed(self, instance): 
        self.show_completed = not self.show_completed
        self.done_btn.text = "HIDE\nDONE" if self.show_completed else "SHOW\nDONE"
        self.refresh_ui()

    def clear_completed(self, instance=None):
        now = datetime.utcnow().isoformat()
        for item in self.all_lists.get(self.active_list_name, []):
            if item.get('done') and item.get('id'):
                self.tombstones[item['id']] = now
        self.all_lists[self.active_list_name] = [i for i in self.all_lists[self.active_list_name] if not i.get('done') or i.get('name') == "PLACEHOLDER"]
        self.save_data(); self.refresh_ui()

    def clear_entire_list(self):
        now = datetime.utcnow().isoformat()
        for item in self.all_lists.get(self.active_list_name, []):
            if item.get('id'):
                self.tombstones[item['id']] = now
        self.all_lists[self.active_list_name] = [{'name': 'PLACEHOLDER', 'done': False, 'cat': 'Uncategorized'}]
        self.save_data(); self.refresh_ui()

    def update_family_id(self, new_id):
        if new_id:
            self.family_id = new_id
            self.load_data(); self.refresh_ui(); self.sync_now()

    def sync_now(self, instance=None):
        if instance and hasattr(instance, 'background_color'):
            instance.background_color = (0.2, 1, 0.2, 1) # Green

            self.sync_label.text = "Syncing..."

            Clock.schedule_once(lambda dt: self._perform_sync(dt, instance), 0.3)

    def _perform_sync(self, dt, instance=None):
        """Kick off a manual sync in a background thread."""
        threading.Thread(target=self._do_sync, args=(instance,), daemon=True).start()

    def _background_sync(self, dt):
        """Silent background sync called every 30 seconds."""
        threading.Thread(target=self._do_sync, args=(None,), daemon=True).start()

    def _do_sync(self, button_instance):
        """Core sync logic (background thread): GET → merge tombstones → merge items → PUT → apply."""
        success = False
        try:
            res = requests.get(self.cloud_url, timeout=5, verify=certifi.where())
            if res.status_code == 200:
                data = res.json()
                if data and self.family_id in data:
                    cloud        = data[self.family_id]
                    cloud_lists  = cloud.get('all_lists', {})
                    cloud_cats   = cloud.get('categories', self.categories)
                    cloud_tombs  = cloud.get('tombstones', {})
                    # Merge tombstones: union of both, newest timestamp per ID wins
                    merged_tombs = dict(self.tombstones)
                    for tid, ts in cloud_tombs.items():
                        if tid not in merged_tombs or ts > merged_tombs[tid]:
                            merged_tombs[tid] = ts
                    self.tombstones = merged_tombs  # apply before merge so _merge_items can use them
                    merged_lists = self._merge_all_lists(self.all_lists, cloud_lists)
                    payload = {self.family_id: {'all_lists': merged_lists, 'categories': cloud_cats,
                                                'active_list_name': self.active_list_name,
                                                'tombstones': merged_tombs}}
                    requests.put(self.cloud_url, json=payload, timeout=5, verify=certifi.where())
                    ml   = merged_lists
                    cats = cloud_cats
                    now  = datetime.now().strftime('%H:%M')
                    def _apply(dt):
                        self.all_lists  = ml
                        self.categories = cats
                        self._save_locally()
                        self.sync_label.text  = f"Synced: {now}"
                        self.sync_label.color = (0.6, 0.6, 0.6, 1)
                        self.refresh_ui()
                    Clock.schedule_once(_apply)
                    success = True
            else:
                Clock.schedule_once(lambda dt: self._set_sync_error("Sync Error"))
        except Exception:
            Clock.schedule_once(lambda dt: self._set_sync_error("OFFLINE"))

        if button_instance and hasattr(button_instance, 'background_color'):
            color = (0.2, 1, 0.2, 1) if success else (1, 0.2, 0.2, 1)
            def _btn(dt):
                button_instance.background_color = color
                Clock.schedule_once(lambda d: setattr(button_instance, 'background_color', (1, 1, 1, 1)), 1.0)
            Clock.schedule_once(_btn)
            
    def force_download_confirmed(self):
        self.sync_now()

    def confirm_action(self, msg, callback):
        app = App.get_running_app()
        s_font = app.f_size

        c = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        c.add_widget(Label(text=msg, font_size=s_font, halign='center', valign='middle'))
        b = BoxLayout(size_hint_y=None, height=app.row_height, spacing=dp(10))
        y = Button(text="YES", font_size=s_font, bold=True, 
                   on_release=lambda x: (callback(), p.dismiss()))
        n = Button(text="NO", font_size=s_font, bold=True, 
                   on_release=lambda x: p.dismiss())

        b.add_widget(n)
        b.add_widget(y)
        c.add_widget(b)
        
        p = Popup(title="Confirm", content=c, size_hint=(0.8, 0.3))
        p.open()

    def update_stats(self):
        items = [i for i in self.all_lists.get(self.active_list_name, []) if isinstance(i, dict) and i.get('name') != "PLACEHOLDER"]
        rem = len([i for i in items if not i.get('done')])
        self.stats_label.text = f"{rem}/{len(items)} items left"

    def on_start(self):
        Clock.schedule_once(self.sync_now, 1)
        Clock.schedule_interval(self._background_sync, 30)

    # Standard Helpers
    def switch_list(self, s, t): self.active_list_name = t; self.refresh_ui()

    def mark_done(self, i):
        i['done'] = True
        i['last_modified'] = datetime.utcnow().isoformat()
        self.save_data(); self.refresh_ui()

    def adjust_quantity(self, i, a):
        i['count'] = i.get('count', 1) + a
        if i['count'] < 1:
            if i.get('id'):
                self.tombstones[i['id']] = datetime.utcnow().isoformat()
            self.all_lists[self.active_list_name].remove(i)
        else:
            i['last_modified'] = datetime.utcnow().isoformat()
        self.save_data(); self.refresh_ui()
    def create_new_list(self, x):
        n = f"List {len(self.all_lists)+1}"
        self.all_lists[n] = [{'name': 'PLACEHOLDER', 'done': False, 'cat': 'Uncategorized'}]
        self.active_list_name = n; self.save_data(); self.refresh_ui()

    def rename_list_popup(self, x):
        app = App.get_running_app()
        s_font = app.f_size
        
        c = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        inp = TextInput(text=self.active_list_name, multiline=False, 
                        size_hint_y=None, height=app.row_height, font_size=s_font,input_type='text',
                        input_filter=None, keyboard_suggestions=True)
        btn = Button(text="SAVE", size_hint_y=None, height=app.row_height, 
                     bold=True, font_size=s_font)
        
        c.add_widget(inp)
        c.add_widget(btn)
        p = Popup(title="Rename List", content=c, size_hint=(0.8, 0.4))
        
        def r(x): 
            self.all_lists[inp.text] = self.all_lists.pop(self.active_list_name)
            self.active_list_name = inp.text
            self.save_data(); self.refresh_ui(); p.dismiss()
            
        btn.bind(on_release=r)
        p.open()

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
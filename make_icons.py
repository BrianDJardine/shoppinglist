from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, InstructionGroup
from kivy.clock import Clock
from PIL import Image, ImageDraw
import os

class IconGenerator(App):
    def build(self):
        # We run the generation after one frame to ensure the canvas is ready
        # go back icon    
        self.create_back_icon()
        Clock.schedule_once(self.create_all_icons, 0.1)
        return Widget()

    def create_back_icon(self):
       # 1. Setup a 128x128 transparent canvas
        size = (128, 128)
        img = Image.new("RGBA", size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        color = "white" # Change to "black" if your header is light
        
        # 2. Define the thickness of the arrow shaft and head
        shaft_thickness = 18
        head_width = 45 
        
        # 3. Draw the Arrow Head (The Triangle)
        # Tip is at the far left (x=10), base is at x=55
        head_points = [
            (10, 64),          # Far left tip (centered vertically)
            (55, 64 - head_width), # Top back corner
            (55, 64 + head_width)  # Bottom back corner
        ]
        draw.polygon(head_points, fill=color)

        # 4. Draw the Arrow Shaft (The Rectangle)
        # Starts from the back of the triangle and goes to the right
        shaft_top = 64 - (shaft_thickness // 2)
        shaft_bottom = 64 + (shaft_thickness // 2)
        # [left, top, right, bottom]
        draw.rectangle([50, shaft_top, 110, shaft_bottom], fill=color)
     
        # 5. Save the file
        name = "back.png"
        img.save(name)
        print(f"File generated: {os.path.abspath(name)}")

    def create_all_icons(self, dt):
        # 1. NEW (+)
        new_ig = InstructionGroup()
        new_ig.add(Color(1, 1, 1, 1))
        new_ig.add(Line(points=[64, 30, 64, 98], width=8))
        new_ig.add(Line(points=[30, 64, 98, 64], width=8))
        self.save_icon('new.png', new_ig)

        # 2. PENCIL (✎)
        edit_ig = InstructionGroup()
        edit_ig.add(Color(1, 1, 1, 1))
        edit_ig.add(Line(points=[40, 40, 85, 85], width=12)) # Body
        edit_ig.add(Line(points=[40, 40, 30, 30], width=4))  # Tip
        edit_ig.add(Line(points=[85, 85, 95, 95], width=14)) # Eraser
        self.save_icon('edit.png', edit_ig)

        # 3. DELETE (X)
        del_ig = InstructionGroup()
        del_ig.add(Color(1, 1, 1, 1))
        del_ig.add(Line(points=[34, 34, 94, 94], width=8))
        del_ig.add(Line(points=[34, 94, 94, 34], width=8))
        self.save_icon('delete.png', del_ig)

        # 4. CATS (Hamburger)
        cat_ig = InstructionGroup()
        cat_ig.add(Color(1, 1, 1, 1))
        cat_ig.add(Line(points=[30, 40, 98, 40], width=6))
        cat_ig.add(Line(points=[30, 64, 98, 64], width=6))
        cat_ig.add(Line(points=[30, 88, 98, 88], width=6))
        self.save_icon('cats.png', cat_ig)
        
        # UP ARROW
        up_ig = InstructionGroup()
        up_ig.add(Color(1, 1, 1, 1))
        up_ig.add(Line(points=[30, 50, 64, 84, 98, 50], width=6, cap='round', joint='round'))
        self.save_icon('up.png', up_ig)

        # DOWN ARROW
        dn_ig = InstructionGroup()
        dn_ig.add(Color(1, 1, 1, 1))
        dn_ig.add(Line(points=[30, 78, 64, 44, 98, 78], width=6, cap='round', joint='round'))
        self.save_icon('down.png', dn_ig)

        # Settings
        settings_ig = InstructionGroup()
        settings_ig.add(Color(1, 1, 1, 1))
        settings_ig.add(Line(circle=(64, 64, 30), width=6))
        # Drawing 8 "teeth" for the gear
        for i in range(0, 360, 45):
            import math
            r1, r2 = 30, 45
            rad = math.radians(i)
            x1, y1 = 64 + r1 * math.cos(rad), 64 + r1 * math.sin(rad)
            x2, y2 = 64 + r2 * math.cos(rad), 64 + r2 * math.sin(rad)
            settings_ig.add(Line(points=[x1, y1, x2, y2], width=8))
        
        w = Widget(size=(128, 128))
        w.canvas.add(settings_ig)
        w.export_to_png('settings.png')

        print("\nSUCCESS: All icons created. You can close the window now.")
        self.stop() # Automatically closes the app once done

    def save_icon(self, name, instructions):
        # Create a temporary widget to host the drawing
        export_widget = Widget(size=(128, 128))
        export_widget.canvas.add(instructions)
        # Force the widget to draw itself so it can be exported
        export_widget.export_to_png(name)
        print(f"File generated: {os.path.abspath(name)}")

if __name__ == '__main__':
    IconGenerator().run()
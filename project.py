"""
Kilter Board Route Generator

A professional Python/Tkinter application for generating realistic climbing routes
on a Kilter Board (35×35 grid training wall). The system uses rule-based algorithms
to create routes with realistic difficulty ratings based on actual hold types,
wall angles, move distances, and sequence flow.

Key Features:
- Rule-based route generation mimicking real route-setting principles
- Realistic difficulty calculation from actual route characteristics (not sliders)
- Flow analysis to identify routes with smooth, climbable sequences
- Professional GUI with tooltips, error handling, and route saving
- Fully offline and rule-based (no machine learning or external APIs)

"""

import tkinter as tk
from tkinter import Canvas, Button, PhotoImage, ttk, messagebox, filedialog
import math
import random
import re
import json
from pathlib import Path
import sys

# --- CONFIGURATION ---
# Global list storing all board holds with their attributes (col, row, type, direction, grip_type, base_difficulty)
KilterBoard = []

HOLD_COLORS = {
    "start": "#00dd02",   # bright green
    "hand":  "#03ffff",   # bright blue
    "foot":  "#ffa500",   # orange
    "finish": "#ff00ff"   # bright pink
}

BOARD_ROWS = 35
BOARD_COLS = 35
CELL_SIZE = 20   # pixels per square
PADDING = 20

# --- MODERN GUI STYLES ---
BG_COLOR = "#1e1e1e"            # dark gray
FG_TEXT_COLOR_BLACK = "#000000" # black
FG_TEXT_COLOR_WHITE = "#FFFFFF" # white
ACCENT_COLOR = "#007acc"        # blue accent
ERROR_COLOR = "#ff4d4d"         # red for errors
BUTTON_COLOR = "#2a2a2a"
BUTTON_HOVER = "#3a3a3a"

def resource_path(relative_name: str) -> str:
    """
    Resolve a resource path relative to this script's directory.
    """
    return str((Path(__file__).parent / relative_name).resolve())

# --- TOOLTIP CLASS ---
class ToolTip:
    """
    Create a tooltip for a given widget.
    
    Displays helpful information when the user hovers over a widget.
    The tooltip appears after a 500ms delay and disappears when the mouse leaves.
    
    Attributes:
        widget: The Tkinter widget to attach the tooltip to
        text: The tooltip text to display
        tipwindow: The Toplevel window containing the tooltip
        id: Scheduled event ID for showing the tooltip
    """
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<ButtonPress>', self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"), wraplength=200, fg=FG_TEXT_COLOR_BLACK)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class KilterBoardGUI:
    """
    Main GUI class for the Kilter Board Route Generator.
    
    Handles all user interface components including sliders, buttons, canvas,
    and route display. Manages route generation, difficulty calculation,
    and route saving functionality.
    
    Attributes:
        root: The main Tkinter root window
        current_climb: List of Hold objects representing the current route
        canvas: Canvas widget for displaying the board and route
        scaled_img: Scaled background image of the Kilter Board
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Kilter Board – Climb Generator")
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Escape>', lambda event: root.attributes('-fullscreen', False))
        self.root.configure(bg=BG_COLOR)
        
        # Store current climb for saving
        self.current_climb = None

        width = BOARD_COLS * CELL_SIZE + PADDING * 2
        height = BOARD_ROWS * CELL_SIZE + PADDING * 2

        img = tk.PhotoImage(file=resource_path("IMG_4033.png"))
        self.scaled_img = img.subsample(2, 2)

        # Left Frame: Board Canvas
        left_frame = tk.Frame(root, bg=BG_COLOR)
        left_frame.pack(side="left", fill="both", expand=True)

        self.canvas = Canvas(left_frame, width=width, height=height, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(padx=PADDING, pady=PADDING)

        self.canvas.create_image(PADDING, PADDING, anchor="nw", image=self.scaled_img)

        # Right Frame: Controls
        right_frame = tk.Frame(root, bg=BG_COLOR, padx=20, pady=20)
        right_frame.pack(side="right", fill="y")

        # Title Label
        title_label = tk.Label(right_frame, text="Kilter Board Route Generator", font=("Segoe UI", 14, "bold"), fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        title_label.pack(pady=(0, 15))

        # Slider Section
        slider_frame = tk.Frame(right_frame, bg=BG_COLOR)
        slider_frame.pack(fill="x", pady=10)

        # Max Reach
        max_reach_label = tk.Label(slider_frame, text="Max Reach:", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        max_reach_label.grid(row=0, column=0, sticky="w", padx=5)

        self.max_reach_slider = tk.Scale(
            slider_frame,
            from_=2,
            to=20,
            orient="horizontal",
            length=200,
            bg=BUTTON_COLOR,
            fg=FG_TEXT_COLOR_WHITE,
            highlightbackground=BG_COLOR,
            troughcolor=ACCENT_COLOR,
            command=self.update_max_reach_label
        )
        self.max_reach_slider.set(12)
        self.max_reach_slider.grid(row=0, column=1, padx=5)
        ToolTip(self.max_reach_slider, "Maximum Euclidean distance between consecutive holds. Note: Final difficulty is computed from the actual route, not these sliders.")

        self.max_reach_value = tk.Label(slider_frame, text=f"{self.max_reach_slider.get()}", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        self.max_reach_value.grid(row=0, column=2, padx=5)

        # Min Reach
        min_reach_label = tk.Label(slider_frame, text="Min Reach:", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        min_reach_label.grid(row=1, column=0, sticky="w", padx=5)

        self.min_reach_slider = tk.Scale(
            slider_frame,
            from_=2,
            to=18,
            orient="horizontal",
            length=200,
            bg=BUTTON_COLOR,
            fg=FG_TEXT_COLOR_WHITE,
            highlightbackground=BG_COLOR,
            troughcolor=ACCENT_COLOR,
            command=self.update_min_reach_label
        )
        self.min_reach_slider.set(2)
        self.min_reach_slider.grid(row=1, column=1, padx=5)
        ToolTip(self.min_reach_slider, "Minimum Euclidean distance between consecutive holds. Note: Final difficulty is computed from the actual route, not these sliders.")

        self.min_reach_value = tk.Label(slider_frame, text=f"{self.min_reach_slider.get()}", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        self.min_reach_value.grid(row=1, column=2, padx=5)

        # Max Moves
        max_moves_label = tk.Label(slider_frame, text="Max Moves:", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        max_moves_label.grid(row=2, column=0, sticky="w", padx=5)

        self.max_moves_slider = tk.Scale(
            slider_frame,
            from_=2,
            to=20,
            orient="horizontal",
            length=200,
            bg=BUTTON_COLOR,
            fg=FG_TEXT_COLOR_WHITE,
            highlightbackground=BG_COLOR,
            troughcolor=ACCENT_COLOR,
            command=self.update_max_moves_label
        )
        self.max_moves_slider.set(12)
        self.max_moves_slider.grid(row=2, column=1, padx=5)
        ToolTip(self.max_moves_slider, "Maximum number of hand moves in the route. Note: Final difficulty is computed from the actual route, not these sliders.")

        self.max_moves_value = tk.Label(slider_frame, text=f"{self.max_moves_slider.get()}", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        self.max_moves_value.grid(row=2, column=2, padx=5)

        # Min Moves
        min_moves_label = tk.Label(slider_frame, text="Min Moves:", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        min_moves_label.grid(row=3, column=0, sticky="w", padx=5)

        self.min_moves_slider = tk.Scale(
            slider_frame,
            from_=2,
            to=20,
            orient="horizontal",
            length=200,
            bg=BUTTON_COLOR,
            fg=FG_TEXT_COLOR_WHITE,
            highlightbackground=BG_COLOR,
            troughcolor=ACCENT_COLOR,
            command=self.update_min_moves_label
        )
        self.min_moves_slider.set(2)
        self.min_moves_slider.grid(row=3, column=1, padx=5)
        ToolTip(self.min_moves_slider, "Minimum number of hand moves in the route. Note: Final difficulty is computed from the actual route, not these sliders.")

        self.min_moves_value = tk.Label(slider_frame, text=f"{self.min_moves_slider.get()}", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        self.min_moves_value.grid(row=3, column=2, padx=5)

        # Checkboxes
        checkbox_frame = tk.Frame(right_frame, bg=BG_COLOR)
        checkbox_frame.pack(fill="x", pady=15)

        # Crazy Mode
        self.crazy_checkbox_var = tk.BooleanVar()
        crazy_check = tk.Checkbutton(
            checkbox_frame,
            text="Remove Upward Restriction",
            variable=self.crazy_checkbox_var,
            fg=FG_TEXT_COLOR_WHITE,
            bg=BG_COLOR,
            selectcolor=BUTTON_COLOR,
            activebackground=BG_COLOR,
            activeforeground=FG_TEXT_COLOR_BLACK
        )
        crazy_check.pack(anchor="w", padx=5)
        ToolTip(crazy_check, "Allow downward or sideways moves (disable strict upward progression)")

        # Two Finishes
        self.two_finishes_checkbox_var = tk.BooleanVar()
        two_fishes_check = tk.Checkbutton(
            checkbox_frame,
            text="Allow Two Finishes",
            variable=self.two_finishes_checkbox_var,
            fg=FG_TEXT_COLOR_WHITE,
            bg=BG_COLOR,
            selectcolor=BUTTON_COLOR,
            activebackground=BG_COLOR,
            activeforeground=FG_TEXT_COLOR_BLACK
        )
        two_fishes_check.select()
        two_fishes_check.pack(anchor="w", padx=5)
        ToolTip(two_fishes_check, "Generate routes with one or two finish holds")
        
        # Difficulty Label (updated after route generation)
        self.difficulty_label = tk.Label(
            right_frame,
            text="Difficulty: Generate a route to see difficulty",
            font=("Segoe UI", 11, "bold"),
            fg=FG_TEXT_COLOR_WHITE,
            bg=BG_COLOR
        )
        self.difficulty_label.pack(pady=10)
        ToolTip(self.difficulty_label, "Final difficulty is calculated from the actual route after generation, based on hold types, wall angle, move distances, and sequence flow.")
        
        # Flow Score Label
        self.flow_label = tk.Label(
            right_frame,
            text="",
            font=("Segoe UI", 10),
            fg=FG_TEXT_COLOR_BLACK,
            bg=BG_COLOR
        )
        self.flow_label.pack(pady=5)

        # Generate Button
        button_frame = tk.Frame(right_frame, bg=BG_COLOR)
        button_frame.pack(fill="x", pady=20)

        self.button = Button(
            button_frame,
            text="Generate New Climb",
            command=self.generate_and_draw,
            bg=ACCENT_COLOR,
            fg=FG_TEXT_COLOR_BLACK,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=20,
            pady=10
        )
        self.button.pack(pady=5)

        # Hover Effect (optional)
        self.button.bind("<Enter>", lambda e: self.button.config(bg="#0066cc"))
        self.button.bind("<Leave>", lambda e: self.button.config(bg=ACCENT_COLOR))

        # Save Route Button
        self.save_button = Button(
            button_frame,
            text="Save Route",
            command=self.save_route,
            bg=BUTTON_COLOR,
            fg=FG_TEXT_COLOR_BLACK,
            font=("Segoe UI", 10),
            relief="flat",
            padx=20,
            pady=10,
            state="disabled"
        )
        self.save_button.pack(pady=5)
        self.save_button.bind("<Enter>", lambda e: self.save_button.config(bg=BUTTON_HOVER) if self.save_button['state'] == 'normal' else None)
        self.save_button.bind("<Leave>", lambda e: self.save_button.config(bg=BUTTON_COLOR) if self.save_button['state'] == 'normal' else None)

        # Reset Button
        self.reset_button = Button(
            button_frame,
            text="Reset to Defaults",
            command=self.reset_to_defaults,
            bg=BUTTON_COLOR,
            fg=FG_TEXT_COLOR_BLACK,
            font=("Segoe UI", 10),
            relief="flat",
            padx=20,
            pady=10
        )
        self.reset_button.pack(pady=5)
        self.reset_button.bind("<Enter>", lambda e: self.reset_button.config(bg=BUTTON_HOVER))
        self.reset_button.bind("<Leave>", lambda e: self.reset_button.config(bg=BUTTON_COLOR))

        # Randomize Button
        self.randomize_button = Button(
            button_frame,
            text="Randomize Parameters",
            command=self.randomize_parameters,
            bg=BUTTON_COLOR,
            fg=FG_TEXT_COLOR_BLACK,
            font=("Segoe UI", 10),
            relief="flat",
            padx=20,
            pady=10
        )
        self.randomize_button.pack(pady=5)
        self.randomize_button.bind("<Enter>", lambda e: self.randomize_button.config(bg=BUTTON_HOVER))
        self.randomize_button.bind("<Leave>", lambda e: self.randomize_button.config(bg=BUTTON_COLOR))

        # Error Labels
        self.error_label_reach = tk.Label(right_frame, text="", fg=ERROR_COLOR, bg=BG_COLOR, wraplength=300, justify="center")
        self.error_label_reach.pack(pady=5)

        self.error_label_moves = tk.Label(right_frame, text="", fg=ERROR_COLOR, bg=BG_COLOR, wraplength=300, justify="center")
        self.error_label_moves.pack(pady=5)

        # Draw empty grid once
        # self.draw_grid()

    def update_max_reach_label(self, val):
        self.max_reach_value.config(text=val)

    def update_min_reach_label(self, val):
        self.min_reach_value.config(text=val)

    def update_max_moves_label(self, val):
        self.max_moves_value.config(text=val)

    def update_min_moves_label(self, val):
        self.min_moves_value.config(text=val)

    def update_difficulty(self, climb=None):
        """
        Update the difficulty label based on the actual generated route.
        
        Calculates route difficulty using estimate_route_difficulty() and flow score
        using calculate_flow_score(). Only displays difficulty after a route is generated.
        If no route is provided, shows a message prompting the user to generate one.
        
        Args:
            climb: List of Hold objects representing the route, or None to reset display
        """
        if climb is None:
            self.difficulty_label.config(
                text="Difficulty: Generate a route to see difficulty",
                fg=FG_TEXT_COLOR_BLACK
            )
            self.flow_label.config(text="")
            return
        
        # Calculate route difficulty
        difficulty_label, difficulty_score = estimate_route_difficulty(climb)
        
        # Calculate flow score separately
        hand_holds = [h for h in climb if h.type in ("start", "hand", "finish")]
        flow_label = calculate_flow_score(climb, hand_holds)
        
        # Set color based on difficulty
        if difficulty_label == "Easy":
            color = "#00dd02"  # green
        elif difficulty_label == "Intermediate":
            color = ACCENT_COLOR  # blue
        elif difficulty_label == "Hard":
            color = "#ffa500"  # orange
        else:  # Very Hard
            color = "#ff4d4d"  # red
        
        self.difficulty_label.config(
            text=f"Difficulty: {difficulty_label} (Score: {difficulty_score:.2f})",
            fg=color
        )
        # Only show flow label if it's not empty (i.e., score ≥ 70%)
        if flow_label:
            self.flow_label.config(text=flow_label, fg=FG_TEXT_COLOR_WHITE)
        else:
            self.flow_label.config(text="")

    def reset_to_defaults(self):
        """
        Reset all sliders and checkboxes to default values.
        
        Defaults:
        - Min Reach = 2, Max Reach = 12
        - Min Moves = 2, Max Moves = 12
        - Remove Upward Restriction = Off
        - Allow Two Finishes = On
        """
        self.min_reach_slider.set(2)
        self.max_reach_slider.set(12)
        self.min_moves_slider.set(2)
        self.max_moves_slider.set(12)
        self.crazy_checkbox_var.set(False)
        self.two_finishes_checkbox_var.set(True)
        self.update_difficulty()  # Reset to default message

    def randomize_parameters(self):
        """
        Set sliders to random valid values within their ranges.
        
        Uses wider ranges than defaults to allow generation of Hard/Very Hard routes:
        - Min Reach: 2-15, Max Reach: 8-20 (ensures max > min)
        - Min Moves: 2-15, Max Moves: 10-20 (ensures max > min)
        - Two Finishes: 50% chance
        - Crazy Mode: 20% chance
        
        This function enables quick exploration of different route types.
        """
        min_reach = random.randint(2, 15)  # Wider range → harder routes possible
        max_reach = random.randint(max(min_reach + 1, 8), 20)  # Ensure max > min, and can be high
        min_moves = random.randint(2, 15)
        max_moves = random.randint(max(min_moves + 1, 10), 20)
        
        self.min_reach_slider.set(min_reach)
        self.max_reach_slider.set(max_reach)
        self.min_moves_slider.set(min_moves)
        self.max_moves_slider.set(max_moves)
        
        # Update value labels
        self.min_reach_value.config(text=str(min_reach))
        self.max_reach_value.config(text=str(max_reach))
        self.min_moves_value.config(text=str(min_moves))
        self.max_moves_value.config(text=str(max_moves))
        
        # Two Finishes: 50% chance on
        self.two_finishes_checkbox_var.set(random.random() < 0.5)
        
        # Crazy Mode: 20% chance on
        self.crazy_checkbox_var.set(random.random() < 0.2)
        
        self.update_difficulty()  # Reset to default message (since no route generated yet)


    def save_route(self):
        """
        Save the current route to a JSON file.
        
        Opens a file dialog for the user to choose save location and filename.
        Saves route data in JSON format with all hold positions and types.
        Shows success/error messages via popup dialogs.
        
        Raises:
            Shows error dialog if save fails (file permissions, disk full, etc.)
        """
        if self.current_climb is None:
            messagebox.showwarning("No Route", "Please generate a route first before saving.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Route"
        )
        
        if filename:
            try:
                route_data = {
                    "holds": [
                        {
                            "col": hold.col,
                            "row": hold.row,
                            "type": hold.type
                        }
                        for hold in self.current_climb
                    ]
                }
                with open(filename, 'w') as f:
                    json.dump(route_data, f, indent=2)
                messagebox.showinfo("Success", f"Route saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save route: {str(e)}")

    def draw_climb(self, climb):
        """
        Draws a given climb on the Kilter Board canvas.
        
        The board has non-uniform row spacing due to the physical layout:
        - Rows 1-2: Top section with 19.5px spacing
        - Rows 3-31: Middle section with 18px spacing
        - Rows 32-35: Bottom section with 39px spacing
        
        Args:
            climb: List of Hold objects representing the route to draw
        """
        # Remove previous holds, keep the background image
        self.canvas.delete("hold")

        for hold in climb:
            col = hold.col - 1     # Convert to 0-index for pixel calculations
            row = hold.row - 1
            
            # Calculate x position (uniform column spacing)
            x = PADDING + col * CELL_SIZE + CELL_SIZE / 2
            
            # Calculate y position based on row (non-uniform spacing due to board geometry)
            if row <= 1:
                # Top section: rows 1-2 have 19.5px spacing, starting at y=710
                y = 710 - (19.5 * row)
            elif row <= 31:
                # Middle section: rows 3-31 have 18px spacing, starting at y=650
                y = 650 - (18 * (row - 2))
            else:
                # Bottom section: rows 32-35 have 39px spacing, starting at y=32
                y = 32 + (39 * (34 - row))

            # Base radius for hold circles
            radius = CELL_SIZE
            color = HOLD_COLORS.get(hold.type, "white")

            # Smaller holds in top rows or even columns (matches physical board layout)
            if row <= 1 or col % 2 == 0: 
                radius *= .7
            
            self.canvas.create_oval(
                x - radius, y - radius,
                x + radius, y + radius,
                fill="",
                outline=color,
                width=3,
                tags="hold"
            )

    def generate_and_draw(self):
        """
        Generates a new route based on current slider settings and displays it.
        
        Validates input parameters, generates the route using generate_kilterclimb(),
        draws it on the canvas, calculates and displays difficulty, and enables
        the save button if generation is successful.
        
        Shows error messages (both popup and red text) if min >= max for reach or moves.
        """
        max_reach = self.max_reach_slider.get()
        min_reach = self.min_reach_slider.get()
        max_moves = self.max_moves_slider.get()-1 
        min_moves = self.min_moves_slider.get()-1
        crazy_mode = self.crazy_checkbox_var.get()
        allow_two_finishes = self.two_finishes_checkbox_var.get()

        # Clear previous errors
        self.error_label_reach.config(text="")
        self.error_label_moves.config(text="")

        # Validate inputs strictly (allow min == max as invalid)
        if min_reach >= max_reach:
            error_msg = "Min reach must be less than Max reach"
            self.error_label_reach.config(text=f"Invalid Input: {error_msg}")
            messagebox.showerror("Invalid Input", error_msg)
            return

        if min_moves >= max_moves:
            error_msg = "Min moves must be less than Max moves"
            self.error_label_moves.config(text=f"Invalid Input: {error_msg}")
            messagebox.showerror("Invalid Input", error_msg)
            return

        climb = generate_kilterclimb(min_moves=min_moves, 
            max_moves=max_moves,
            min_reach=min_reach,
            allow_two_finishes=allow_two_finishes,
            max_reach=max_reach,
            crazy_mode=crazy_mode
        )
        if climb != None:
            self.current_climb = climb
            self.draw_climb(climb)
            # Calculate and display route-based difficulty
            self.update_difficulty(climb)
            # Enable save button when a route is generated
            self.save_button.config(state="normal")
        else:
            self.current_climb = None
            self.update_difficulty()  # Reset to default message
            self.save_button.config(state="disabled")

def start_gui():
    """
    Initialize and start the GUI application.
    
    Creates the main Tkinter window, initializes the KilterBoardGUI,
    and starts the event loop. This is the entry point for the application.
    """
    root = tk.Tk()
    KilterBoardGUI(root)
    root.mainloop()

# --- CORE LOGIC (Unchanged) ---

class Hold:
    """
    Represents a single hold on the Kilter Board.
    
    Attributes:
        col: Column position (1-35)
        row: Row position (1-35)
        type: Hold type - "start", "hand", "foot", or "finish"
    """
    def __init__(self, col: int, row: int, type: str):
        self.col = col
        self.row = row
        self.type = type  # "start", "hand", "foot", "finish"

    def __repr__(self):
        return f"Hold(col={self.col}, row={self.row}, type='{self.type}')"

def reachable(h1: dict, h2: dict, max_reach: float = 14, min_reach: float = 2) -> bool:
    """
    Check if two holds are within the specified reach distance.
    
    Uses Euclidean distance to determine if a climber can move from h1 to h2.
    This mimics real climbing where reach is measured as straight-line distance.
    
    Args:
        h1: First hold dictionary with "col" and "row" keys
        h2: Second hold dictionary with "col" and "row" keys
        max_reach: Maximum allowed distance (default: 14)
        min_reach: Minimum required distance (default: 2)
    
    Returns:
        True if distance is between min_reach and max_reach (inclusive), False otherwise
    """
    dx = abs(h1["col"] - h2["col"])
    dy = abs(h1["row"] - h2["row"])
    dist = math.sqrt(dx*dx + dy*dy)
    return dist <= max_reach and dist >= min_reach

def get_start_hands(max_reach: float = 12, min_reach: float = 12) -> tuple:
    """
    Select starting hand holds for a route.
    
    Attempts to find two opposing hand holds in rows 7-13 (mid-board zone)
    that are reachable from each other. If no pair is found, returns a single
    hold. This mimics real route-setting where start holds are typically
    positioned at a comfortable height.
    
    Args:
        max_reach: Maximum distance between start holds
        min_reach: Minimum distance between start holds
    
    Returns:
        Tuple of (hold1, hold2) where hold2 may be None if no pair is found
    """
    # Filter hand holds in the start zone (rows 7-13 provide realistic starting positions)
    candidates = [
        h for h in KilterBoard
        if h["type"] == "h" and 7 <= h["row"] <= 13
    ]
    random.shuffle(candidates)
    
    # Try to find a pair of opposing holds that are reachable
    for i in range(len(candidates)):
        for j in range(i+1, len(candidates)):
            if reachable(candidates[i], candidates[j], max_reach, min_reach):
                return candidates[i], candidates[j]
    
    # Fallback: return a single hold if no pair is found
    return random.choice(candidates), None

def get_feet_candidates(below_row: int, left_col: int = 0, right_col: int = 35) -> list:
    """
    Get candidate holds for foot placement.
    
    Returns foot holds (or hand holds that can be used as feet) that are:
    - Below a specified row
    - Within a column range (left_col to right_col)
    
    This function is used to place feet below starting hands and after hand moves,
    ensuring realistic body positioning during climbs.
    
    Args:
        below_row: Only return holds with row < below_row
        left_col: Minimum column (default: 0, meaning column 1+)
        right_col: Maximum column (default: 35)
    
    Returns:
        List of hold dictionaries, shuffled randomly
    """
    # Include both foot holds ('f') and hand holds ('h') that can be used as feet
    feet = [h for h in KilterBoard if h["type"] in ("f", "h") and h["row"] < below_row and h["col"] >= left_col and h["col"] <= right_col]
    random.shuffle(feet)
    return feet

def get_next_hand_move(current_hand: dict, max_reach: float = 12, min_reach: float = 12, crazy_mode: bool = False) -> dict:
    """
    Find the next hand move from the current position.
    
    Selects a reachable hand hold that follows realistic climbing progression:
    - 75% chance: upward or same level (h["row"] >= current_hand["row"])
    - 25% chance: strictly upward (h["row"] > current_hand["row"])
    - If crazy_mode: allows any direction (downward/sideways moves)
    
    This mimics real climbing where most moves progress upward, with occasional
    lateral or same-level moves for route variety.
    
    Args:
        current_hand: Current hold dictionary with "col" and "row" keys
        max_reach: Maximum distance for the next move
        min_reach: Minimum distance for the next move
        crazy_mode: If True, allows downward/sideways moves
    
    Returns:
        Hold dictionary for the next move, or None if no valid move is found
    """
    candidates = [h for h in KilterBoard if h["type"] == "h"]
    
    if not crazy_mode:
        # 75% chance: allow same-level or upward moves (more natural)
        # 25% chance: strictly upward (more challenging)
        if random.random() > .25:
            candidates = [h for h in candidates if h["row"] >= current_hand["row"]]
        else:
            candidates = [h for h in candidates if h["row"] > current_hand["row"]]
    
    random.shuffle(candidates)
    
    # Return first reachable hold
    for h in candidates:
        if reachable(current_hand, h, max_reach, min_reach):
            return h
    
    return None

def generate_kilterclimb(
    min_moves: int = 2,
    max_moves: int = 20,
    allow_two_finishes: bool = True,
    max_reach: float = 12,
    min_reach: float = 2,
    crazy_mode: bool = False
) -> list:
    """
    Generate a complete climbing route using rule-based algorithms.
    
    Creates a route following real route-setting principles:
    1. Start holds (1-2 hands in rows 7-13) with feet below
    2. Middle progression (random number of moves within min/max range)
    3. Finish holds (1-2 hands above the last move)
    
    Each hand move has a 35% chance to add a foot hold, mimicking real
    route-setting where feet are strategically placed but not overused.
    
    Args:
        min_moves: Minimum number of hand moves (excluding start/finish)
        max_moves: Maximum number of hand moves (excluding start/finish)
        allow_two_finishes: If True, may generate 1 or 2 finish holds
        max_reach: Maximum Euclidean distance between consecutive hand holds
        min_reach: Minimum Euclidean distance between consecutive hand holds
        crazy_mode: If True, allows downward/sideways moves
    
    Returns:
        List of Hold objects representing the complete route, or None if invalid parameters
    
    Raises:
        None (returns None for invalid inputs)
    """
    # Validate input parameters
    if min_reach > max_reach:
        print("INVALID PARAMS: min_reach > max_reach")
        return None
    if min_moves > max_moves:
        print("INVALID PARAMS: min_moves > max_moves")
        return None

    climb = []
    
    # Step 1: Select starting hands (1-2 holds in rows 7-13)
    s1, s2 = get_start_hands(max_reach, min_reach)
    climb.append(Hold(s1["col"], s1["row"], "start"))
    if s2:
        climb.append(Hold(s2["col"], s2["row"], "start"))

    # Step 2: Place starting feet below the starting hands
    # Search in a column range around the start hands (±2 columns) for realistic positioning
    feet_pool = get_feet_candidates((max(s1["row"], s2["row"] if s2 else s1["row"]) - 1), 
                                    (min(s1["col"], s2["col"] if s2 else s1["col"]) - 2),
                                    (max(s1["col"], s2["col"] if s2 else s1["col"])) + 2)

    if len(feet_pool) >= 2:
        f1, f2 = random.sample(feet_pool, 2)
        climb.append(Hold(f1["col"], f1["row"], "foot"))
        climb.append(Hold(f2["col"], f2["row"], "foot"))
        last_feet = [f1, f2]
    else:
        last_feet = []

    # Step 3: Generate middle progression (hand moves)
    num_moves = random.randint(min_moves, max_moves)
    current = max(s1, s2, key=lambda h: h["row"] if h else 0)  # Start from highest hand

    for _ in range(num_moves):
        next_hand = get_next_hand_move(current, max_reach=max_reach, min_reach=min_reach, crazy_mode=crazy_mode)
        
        # Stop if no valid move found or route goes too high (row 33+ is impractical)
        if next_hand is None or next_hand["row"] >= 33:
            break
        
        climb.append(Hold(next_hand["col"], next_hand["row"], "hand"))
        current = next_hand
        
        # 35% chance to add a foot hold after each hand move
        # This mimics real route-setting where feet are strategically placed but not overused
        feet_candidates = get_feet_candidates(current["row"], current["col"] - 3, current["col"] + 3)
        if feet_candidates and random.random() < 0.35:
            f = random.choice(feet_candidates)
            climb.append(Hold(f["col"], f["row"], "foot"))
            last_feet.append(f)

    # Step 4: Select finish holds (1-2 hands above the last move)
    finishes = [
        h for h in KilterBoard
        if h["type"] == "h" and h["row"] >= current["row"]
    ]
    # Fallback: if no holds above, use any hand hold (shouldn't happen in practice)
    if not finishes:
        finishes = [h for h in KilterBoard if h["type"] == "h"]

    # Randomly select 1 or 2 finish holds based on user preference
    finish_count = random.randint(1,2) if allow_two_finishes else 1

    # Ensure first finish is reachable from the last hand move
    finishHold1 = random.choice(finishes)
    while not reachable(finishHold1, current, max_reach, min_reach):
        finishHold1 = random.choice(finishes)

    # If two finishes, ensure second is reachable from the first
    finishHold2 = None
    if finish_count == 2:
        finishHold2 = random.choice(finishes)
        while not reachable(finishHold1, finishHold2, max_reach, min_reach):
            finishHold2 = random.choice(finishes)

    climb.append(Hold(finishHold1["col"], finishHold1["row"], "finish"))
    if finish_count == 2:
        climb.append(Hold(finishHold2["col"], finishHold2["row"], "finish"))

    return climb

def estimate_route_difficulty(climb: list) -> tuple[str, float]:
    """
    Calculate realistic route difficulty based on hold types, wall angle, move distance, and sequence flow.
    Returns (difficulty_label, difficulty_score)
    
    Scoring components (weighted):
    - Average hold difficulty (40%): Mean of base_difficulty for all hand/start holds (0-5 scale)
    - Average move distance (30%): Euclidean distance between consecutive hand holds, normalized to 0-1
    - Wall angle factor (20%): Fraction of holds in rows 1-5 adds +0.5, rows 30-35 subtracts -0.3
    - Sequence flow (10%): Penalizes abrupt left/right shifts or non-upward moves
    """
    if not climb:
        return ("Easy", 0.0)
    
    # Extract hand holds (start, hand, finish types)
    hand_holds = [h for h in climb if h.type in ("start", "hand", "finish")]
    if len(hand_holds) < 2:
        return ("Easy", 0.0)
    
    # 1. Average hold difficulty (40% weight) - already on 0-5 scale
    hold_difficulties = []
    for hold in hand_holds:
        # Find the hold in KilterBoard to get its base_difficulty
        board_hold = next((h for h in KilterBoard if h["col"] == hold.col and h["row"] == hold.row and h["type"] == "h"), None)
        if board_hold and board_hold.get("base_difficulty") is not None:
            hold_difficulties.append(board_hold["base_difficulty"])
        else:
            # Default if not found (shouldn't happen, but fallback)
            hold_difficulties.append(2)  # Medium difficulty
    
    avg_hold_difficulty = sum(hold_difficulties) / len(hold_difficulties) if hold_difficulties else 2.0
    
    # 2. Average move distance (30% weight) - normalize to 0-1
    move_distances = []
    for i in range(len(hand_holds) - 1):
        h1 = hand_holds[i]
        h2 = hand_holds[i + 1]
        dx = abs(h1.col - h2.col)
        dy = abs(h1.row - h2.row)
        dist = math.sqrt(dx*dx + dy*dy)
        move_distances.append(dist)
    
    avg_move_distance = sum(move_distances) / len(move_distances) if move_distances else 5.0
    # Normalize to 0-1: typical range is 2-15, so (distance - 2) / (15 - 2) = (distance - 2) / 13
    normalized_distance = min(1.0, max(0.0, (avg_move_distance - 2) / 13.0))
    
    # 3. Wall angle factor (20% weight)
    # Rows 1-5: overhang (+0.5 per hold), Rows 30-35: slab (-0.3 per hold)
    overhang_count = sum(1 for h in hand_holds if 1 <= h.row <= 5)
    slab_count = sum(1 for h in hand_holds if 30 <= h.row <= 35)
    total_holds = len(hand_holds)
    
    # Calculate angle factor: (overhang_fraction * 0.5) - (slab_fraction * 0.3)
    overhang_fraction = overhang_count / total_holds if total_holds > 0 else 0
    slab_fraction = slab_count / total_holds if total_holds > 0 else 0
    angle_factor = (overhang_fraction * 0.5) - (slab_fraction * 0.3)
    
    # Normalize angle factor to 0-5 scale for weighted calculation
    # Range is approximately -0.3 to +0.5, so shift by +0.3 and scale to 0-5
    normalized_angle = min(5.0, max(0.0, (angle_factor + 0.3) * 6.25))
    
    # 4. Sequence flow (10% weight) - penalize abrupt shifts and non-upward moves
    flow_penalty = 0.0
    if len(hand_holds) >= 3:
        # Check for abrupt left/right shifts (zigzag pattern)
        direction_changes = 0
        for i in range(len(hand_holds) - 2):
            h1, h2, h3 = hand_holds[i], hand_holds[i+1], hand_holds[i+2]
            dir1 = "left" if h2.col < h1.col else "right" if h2.col > h1.col else "same"
            dir2 = "left" if h3.col < h2.col else "right" if h3.col > h2.col else "same"
            if dir1 != "same" and dir2 != "same" and dir1 != dir2:
                direction_changes += 1
        
        # Check for non-upward moves (downward or sideways)
        non_upward_moves = 0
        for i in range(len(hand_holds) - 1):
            if hand_holds[i+1].row <= hand_holds[i].row:  # Same row or downward
                non_upward_moves += 1
        
        # Penalize: more direction changes and non-upward moves = higher penalty
        # Normalize to 0-5 scale (max penalty if all moves are problematic)
        max_possible_changes = len(hand_holds) - 2
        max_possible_non_upward = len(hand_holds) - 1
        penalty_score = min(5.0, (direction_changes / max(max_possible_changes, 1)) * 2.5 + 
                           (non_upward_moves / max(max_possible_non_upward, 1)) * 2.5)
        flow_penalty = penalty_score
    
    # Calculate weighted composite score
    # Convert normalized_distance (0-1) to 0-5 scale for consistency: multiply by 5
    final_score = (
        avg_hold_difficulty * 0.4 +           # 0-5 scale, 40% weight
        (normalized_distance * 5.0) * 0.3 +    # 0-1 normalized to 0-5, 30% weight
        normalized_angle * 0.2 +               # 0-5 scale, 20% weight
        flow_penalty * 0.1                     # 0-5 scale, 10% weight
    )
    
    # Map final score to difficulty labels
    if final_score < 2.0:
        difficulty_label = "Easy"
    elif final_score < 3.5:
        difficulty_label = "Intermediate"
    elif final_score < 4.8:
        difficulty_label = "Hard"
    else:
        difficulty_label = "Very Hard"
    
    return (difficulty_label, final_score)

def calculate_flow_score(climb: list, hand_holds: list) -> str:
    """
    Calculate route flow score based on smooth left/right alternation and upward consistency.
    
    Flow score evaluates route quality:
    - Left/right alternation (50%): Percentage of moves that alternate sides
    - Upward consistency (50%): Percentage of moves that progress upward
    
    Routes with ≥ 70% flow score are considered to have "Good Flow" - indicating
    a smooth, climbable sequence that feels natural to climb.
    
    Args:
        climb: Complete list of Hold objects in the route
        hand_holds: Filtered list of only hand/start/finish holds (for move analysis)
    
    Returns:
        "Good Flow" if flow score ≥ 70%, otherwise empty string
    """
    if len(hand_holds) < 3:
        return ""
    
    # 1. Left/right balance (% of moves alternating sides)
    alternating_count = 0
    for i in range(len(hand_holds) - 2):
        h1, h2, h3 = hand_holds[i], hand_holds[i+1], hand_holds[i+2]
        dir1 = "left" if h2.col < h1.col else "right" if h2.col > h1.col else "same"
        dir2 = "left" if h3.col < h2.col else "right" if h3.col > h2.col else "same"
        if dir1 != "same" and dir2 != "same" and dir1 != dir2:
            alternating_count += 1
    
    alternating_ratio = alternating_count / (len(hand_holds) - 2) if len(hand_holds) > 2 else 0
    
    # 2. Upward consistency (% of moves that go upward)
    upward_moves = 0
    for i in range(len(hand_holds) - 1):
        if hand_holds[i+1].row > hand_holds[i].row:
            upward_moves += 1
    
    upward_ratio = upward_moves / (len(hand_holds) - 1) if len(hand_holds) > 1 else 0
    
    # Composite flow score (0-100%)
    flow_score_percent = (alternating_ratio * 0.5 + upward_ratio * 0.5) * 100
    
    # Only show "Good Flow" if score ≥ 70%
    if flow_score_percent >= 70:
        return "Good Flow"
    else:
        return ""

def load_kilterBoard(filepath: str):
    """
    Reads a text file where each line has the format:
        c r t
        c r t d
        c r t d grip_type base_difficulty  (for hand holds only)
    - c = column (int)
    - r = row (int)
    - t = type ('h' = hand, 'f' = foot, 'n' = none)
    - d = direction ('u','r','d','l') ONLY for hand holds
    - grip_type = one of "jug", "edge", "crimp", "sloper", "pinch", "sidepull", "undercut" (hand holds only)
    - base_difficulty = integer 0-5 (hand holds only)
    """
    global KilterBoard
    KilterBoard.clear()
    with open(filepath, "r") as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            
            c, r, t = int(parts[0]), int(parts[1]), parts[2]
            d = None
            grip_type = None
            base_difficulty = None
            
            if len(parts) >= 4:
                d = parts[3]
            
            # For hand holds, check if grip_type and base_difficulty are provided
            if t == "h" and len(parts) >= 6:
                grip_type = parts[4]
                base_difficulty = int(parts[5])
            
            KilterBoard.append({
                "col": c,
                "row": r,
                "type": t,
                "direction": d,
                "grip_type": grip_type,
                "base_difficulty": base_difficulty
            })

def main():
    if sys.version_info < (3, 7):
        print("This app requires Python 3.7+. Try: python3 project.py")
        sys.exit(1)
    load_kilterBoard(resource_path("kilterBoardLayout.txt"))
    start_gui()

if __name__ == "__main__":
    main()

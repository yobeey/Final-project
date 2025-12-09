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
# This list is populated from kilterBoardLayout.txt and represents the physical layout of the Kilter Board.
# Each hold dictionary contains: column (1-35), row (1-35), type ('h'=hand, 'f'=foot, 'n'=none),
# direction (for hand holds: 'u','r','d','l'), grip_type (e.g., "jug", "crimp"), and base_difficulty (0-5).
KilterBoard = []

# Color mapping for visual representation of different hold types in the GUI
# These colors help climbers quickly identify start, hand, foot, and finish holds on the board
HOLD_COLORS = {
    "start": "#00dd02",   # bright green - clearly visible start holds
    "hand":  "#03ffff",   # bright blue - intermediate hand holds
    "foot":  "#ffa500",   # orange - foot placement holds
    "finish": "#ff00ff"   # bright pink - clearly visible finish holds
}

# Board dimensions: Kilter Board is a 35×35 grid of potential hold positions
BOARD_ROWS = 35
BOARD_COLS = 35
CELL_SIZE = 20   # pixels per square - determines visual scaling of the board in the GUI
PADDING = 20     # padding around the board canvas for visual spacing

# --- MODERN GUI STYLES ---
# Color scheme for a modern, dark-themed interface that's easy on the eyes
# and provides good contrast for route visualization
BG_COLOR = "#1e1e1e"            # dark gray - main background for professional appearance
FG_TEXT_COLOR_BLACK = "#000000" # black - for text on light backgrounds (tooltips, buttons)
FG_TEXT_COLOR_WHITE = "#FFFFFF" # white - for text on dark backgrounds (main UI)
ACCENT_COLOR = "#007acc"        # blue accent - primary action button color
ERROR_COLOR = "#ff4d4d"         # red for errors - draws attention to validation issues
BUTTON_COLOR = "#2a2a2a"        # secondary button background
BUTTON_HOVER = "#3a3a3a"        # button hover state - provides visual feedback

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
        """Called when mouse enters the widget - schedules tooltip to appear after delay."""
        self.schedule()

    def leave(self, event=None):
        """Called when mouse leaves the widget - cancels tooltip and hides it immediately."""
        self.unschedule()
        self.hidetip()

    def schedule(self):
        """
        Schedule the tooltip to appear after 500ms delay.
        
        This delay prevents tooltips from appearing instantly on every mouse movement,
        improving user experience by only showing tooltips when the user hovers intentionally.
        """
        self.unschedule()  # Cancel any existing scheduled tooltip
        self.id = self.widget.after(500, self.showtip)  # Schedule after 500ms

    def unschedule(self):
        """
        Cancel any scheduled tooltip display.
        
        This prevents multiple tooltips from queuing up if the user moves the mouse
        quickly across multiple widgets.
        """
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)  # Cancel the scheduled event

    def showtip(self, event=None):
        """
        Display the tooltip window at the mouse cursor position.
        
        Calculates position relative to the widget and creates a borderless Toplevel
        window with the tooltip text. The tooltip appears slightly offset from the
        cursor (25px right, 20px down) to avoid covering the widget.
        """
        # Get widget's bounding box if available (for text widgets), otherwise use (0,0)
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        # Convert widget-relative coordinates to screen coordinates
        x += self.widget.winfo_rootx() + 25  # Offset right to avoid covering widget
        y += self.widget.winfo_rooty() + 20  # Offset down for better visibility
        # Create borderless tooltip window
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove window decorations (title bar, borders)
        tw.wm_geometry("+%d+%d" % (x, y))  # Position at calculated coordinates
        # Create label with tooltip text - light yellow background for visibility
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"), wraplength=200, fg=FG_TEXT_COLOR_BLACK)
        label.pack(ipadx=1)

    def hidetip(self):
        """
        Hide and destroy the tooltip window.
        
        Called when mouse leaves the widget or when widget is clicked.
        Ensures tooltips don't linger on screen after user interaction.
        """
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()  # Clean up the tooltip window

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
        """
        Initialize the main GUI window and all UI components.
        
        Sets up a fullscreen window with two main sections:
        - Left: Canvas displaying the Kilter Board with generated routes
        - Right: Control panel with sliders, buttons, and route information
        
        The layout is designed for optimal route visualization and easy parameter adjustment.
        """
        self.root = root
        self.root.title("Kilter Board – Climb Generator")
        # Start in fullscreen mode for maximum board visibility (press Escape to exit)
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Escape>', lambda event: root.attributes('-fullscreen', False))
        self.root.configure(bg=BG_COLOR)
        
        # Store current climb for saving functionality
        # This allows users to save routes they like to JSON files
        self.current_climb = None

        # Calculate canvas dimensions based on board size and padding
        # This ensures the board is displayed at the correct scale
        width = BOARD_COLS * CELL_SIZE + PADDING * 2
        height = BOARD_ROWS * CELL_SIZE + PADDING * 2

        # Load and scale the background image of the physical Kilter Board
        # The image provides visual context showing the actual board layout
        # Subsample by 2x2 reduces image size for better performance
        img = tk.PhotoImage(file=resource_path("IMG_4033.png"))
        self.scaled_img = img.subsample(2, 2)

        # Left Frame: Board Canvas
        # This frame takes up the left side of the window and expands to fill available space
        # The canvas displays the board image and overlays the generated route holds
        left_frame = tk.Frame(root, bg=BG_COLOR)
        left_frame.pack(side="left", fill="both", expand=True)

        # Create canvas for drawing the board and route holds
        # highlightthickness=0 removes the border for a cleaner look
        self.canvas = Canvas(left_frame, width=width, height=height, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(padx=PADDING, pady=PADDING)

        # Place the background board image at the top-left of the canvas
        # This serves as the visual reference for the physical board
        self.canvas.create_image(PADDING, PADDING, anchor="nw", image=self.scaled_img)

        # Right Frame: Controls
        # This frame contains all user controls and route information
        # It's fixed-width on the right side, allowing the board canvas to use remaining space
        right_frame = tk.Frame(root, bg=BG_COLOR, padx=20, pady=20)
        right_frame.pack(side="right", fill="y")

        # Title Label
        # Provides clear application identification at the top of the control panel
        title_label = tk.Label(right_frame, text="Kilter Board Route Generator", font=("Segoe UI", 14, "bold"), fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        title_label.pack(pady=(0, 15))

        # Slider Section
        # Contains all parameter sliders for route generation
        # These sliders control route characteristics but don't directly set difficulty
        # (difficulty is calculated from the actual generated route)
        slider_frame = tk.Frame(right_frame, bg=BG_COLOR)
        slider_frame.pack(fill="x", pady=10)

        # Max Reach Slider
        # Controls the maximum Euclidean distance allowed between consecutive hand holds
        # Higher values allow longer moves (more challenging), lower values create tighter sequences
        # Range 2-20 covers everything from technical slab routes to dynamic overhang routes
        max_reach_label = tk.Label(slider_frame, text="Max Reach:", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        max_reach_label.grid(row=0, column=0, sticky="w", padx=5)

        self.max_reach_slider = tk.Scale(
            slider_frame,
            from_=2,      # Minimum reach (very close holds)
            to=20,        # Maximum reach (very long moves)
            orient="horizontal",
            length=200,   # Slider width in pixels
            bg=BUTTON_COLOR,
            fg=FG_TEXT_COLOR_WHITE,
            highlightbackground=BG_COLOR,
            troughcolor=ACCENT_COLOR,  # Blue accent color for slider track
            command=self.update_max_reach_label  # Update display value as user drags
        )
        self.max_reach_slider.set(12)  # Default: moderate reach (typical for intermediate routes)
        self.max_reach_slider.grid(row=0, column=1, padx=5)
        ToolTip(self.max_reach_slider, "Maximum Euclidean distance between consecutive holds. Note: Final difficulty is computed from the actual route, not these sliders.")

        # Display current slider value for immediate feedback
        self.max_reach_value = tk.Label(slider_frame, text=f"{self.max_reach_slider.get()}", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        self.max_reach_value.grid(row=0, column=2, padx=5)

        # Min Reach Slider
        # Controls the minimum Euclidean distance required between consecutive hand holds
        # Prevents routes from having holds too close together (unrealistic for climbing)
        # Works with Max Reach to define a range of acceptable move distances
        min_reach_label = tk.Label(slider_frame, text="Min Reach:", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        min_reach_label.grid(row=1, column=0, sticky="w", padx=5)

        self.min_reach_slider = tk.Scale(
            slider_frame,
            from_=2,      # Minimum allowed (very close holds)
            to=18,        # Maximum allowed (must be less than max_reach)
            orient="horizontal",
            length=200,
            bg=BUTTON_COLOR,
            fg=FG_TEXT_COLOR_WHITE,
            highlightbackground=BG_COLOR,
            troughcolor=ACCENT_COLOR,
            command=self.update_min_reach_label
        )
        self.min_reach_slider.set(2)  # Default: allow very close holds (flexible route generation)
        self.min_reach_slider.grid(row=1, column=1, padx=5)
        ToolTip(self.min_reach_slider, "Minimum Euclidean distance between consecutive holds. Note: Final difficulty is computed from the actual route, not these sliders.")

        self.min_reach_value = tk.Label(slider_frame, text=f"{self.min_reach_slider.get()}", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        self.min_reach_value.grid(row=1, column=2, padx=5)

        # Max Moves Slider
        # Controls the maximum number of hand moves (excluding start and finish holds)
        # More moves = longer routes, fewer moves = shorter/boulder-style routes
        # Range 2-20 covers short boulder problems to full-length routes
        max_moves_label = tk.Label(slider_frame, text="Max Moves:", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        max_moves_label.grid(row=2, column=0, sticky="w", padx=5)

        self.max_moves_slider = tk.Scale(
            slider_frame,
            from_=2,      # Minimum moves (very short routes)
            to=20,        # Maximum moves (long routes)
            orient="horizontal",
            length=200,
            bg=BUTTON_COLOR,
            fg=FG_TEXT_COLOR_WHITE,
            highlightbackground=BG_COLOR,
            troughcolor=ACCENT_COLOR,
            command=self.update_max_moves_label
        )
        self.max_moves_slider.set(12)  # Default: moderate route length
        self.max_moves_slider.grid(row=2, column=1, padx=5)
        ToolTip(self.max_moves_slider, "Maximum number of hand moves in the route. Note: Final difficulty is computed from the actual route, not these sliders.")

        self.max_moves_value = tk.Label(slider_frame, text=f"{self.max_moves_slider.get()}", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        self.max_moves_value.grid(row=2, column=2, padx=5)

        # Min Moves Slider
        # Controls the minimum number of hand moves required in the route
        # Works with Max Moves to define a range for route length
        # Ensures routes have a minimum complexity/length
        min_moves_label = tk.Label(slider_frame, text="Min Moves:", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        min_moves_label.grid(row=3, column=0, sticky="w", padx=5)

        self.min_moves_slider = tk.Scale(
            slider_frame,
            from_=2,      # Minimum moves (short routes allowed)
            to=20,        # Maximum allowed (must be less than max_moves)
            orient="horizontal",
            length=200,
            bg=BUTTON_COLOR,
            fg=FG_TEXT_COLOR_WHITE,
            highlightbackground=BG_COLOR,
            troughcolor=ACCENT_COLOR,
            command=self.update_min_moves_label
        )
        self.min_moves_slider.set(2)  # Default: allow short routes
        self.min_moves_slider.grid(row=3, column=1, padx=5)
        ToolTip(self.min_moves_slider, "Minimum number of hand moves in the route. Note: Final difficulty is computed from the actual route, not these sliders.")

        self.min_moves_value = tk.Label(slider_frame, text=f"{self.min_moves_slider.get()}", fg=FG_TEXT_COLOR_WHITE, bg=BG_COLOR)
        self.min_moves_value.grid(row=3, column=2, padx=5)

        # Checkboxes
        # These options modify route generation behavior for different route styles
        checkbox_frame = tk.Frame(right_frame, bg=BG_COLOR)
        checkbox_frame.pack(fill="x", pady=15)

        # Crazy Mode Checkbox
        # When enabled, removes the upward progression requirement, allowing:
        # - Downward moves (traverse-style routes)
        # - Sideways moves (more lateral movement)
        # - Same-level moves (technical sequences)
        # This creates more varied, less traditional routes
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

        # Two Finishes Checkbox
        # When enabled, routes may have 1 or 2 finish holds (randomly chosen)
        # Two finish holds are common in real climbing and provide more finish options
        # When disabled, routes always have exactly 1 finish hold
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
        two_fishes_check.select()  # Default: enabled (more realistic)
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
        # This is the primary action button - generates a new route based on current settings
        button_frame = tk.Frame(right_frame, bg=BG_COLOR)
        button_frame.pack(fill="x", pady=20)

        self.button = Button(
            button_frame,
            text="Generate New Climb",
            command=self.generate_and_draw,  # Calls route generation and display
            bg=ACCENT_COLOR,  # Blue accent color to indicate primary action
            fg=FG_TEXT_COLOR_BLACK,
            font=("Segoe UI", 10, "bold"),
            relief="flat",  # Modern flat button style
            padx=20,
            pady=10
        )
        self.button.pack(pady=5)

        # Hover Effect (optional)
        # Provides visual feedback when user hovers over the button
        # Darker blue on hover indicates interactivity
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
        """
        Update the displayed value for the Max Reach slider.
        
        Called automatically when the user drags the slider, providing
        immediate visual feedback of the current setting.
        """
        self.max_reach_value.config(text=val)

    def update_min_reach_label(self, val):
        """
        Update the displayed value for the Min Reach slider.
        
        Called automatically when the user drags the slider, providing
        immediate visual feedback of the current setting.
        """
        self.min_reach_value.config(text=val)

    def update_max_moves_label(self, val):
        """
        Update the displayed value for the Max Moves slider.
        
        Called automatically when the user drags the slider, providing
        immediate visual feedback of the current setting.
        """
        self.max_moves_value.config(text=val)

    def update_min_moves_label(self, val):
        """
        Update the displayed value for the Min Moves slider.
        
        Called automatically when the user drags the slider, providing
        immediate visual feedback of the current setting.
        """
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
        
        # Calculate route difficulty using the rule-based difficulty estimation algorithm
        # This analyzes the actual generated route (not the sliders) to determine difficulty
        # based on hold types, move distances, wall angle, and sequence flow
        difficulty_label, difficulty_score = estimate_route_difficulty(climb)
        
        # Calculate flow score separately to identify routes with smooth, climbable sequences
        # Flow score evaluates left/right alternation and upward consistency
        hand_holds = [h for h in climb if h.type in ("start", "hand", "finish")]
        flow_label = calculate_flow_score(climb, hand_holds)
        
        # Set color based on difficulty level for visual feedback
        # Color coding helps users quickly identify route difficulty at a glance
        if difficulty_label == "Easy":
            color = "#00dd02"  # green - easy routes
        elif difficulty_label == "Intermediate":
            color = ACCENT_COLOR  # blue - intermediate routes
        elif difficulty_label == "Hard":
            color = "#ffa500"  # orange - hard routes
        else:  # Very Hard
            color = "#ff4d4d"  # red - very hard routes
        
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
                # Build JSON structure with route data
                # Format: {"holds": [{"col": int, "row": int, "type": str}, ...]}
                # This format allows routes to be loaded and shared between sessions
                route_data = {
                    "holds": [
                        {
                            "col": hold.col,      # Column position (1-35)
                            "row": hold.row,      # Row position (1-35)
                            "type": hold.type     # Hold type: "start", "hand", "foot", "finish"
                        }
                        for hold in self.current_climb
                    ]
                }
                # Write JSON to file with indentation for readability
                with open(filename, 'w') as f:
                    json.dump(route_data, f, indent=2)
                messagebox.showinfo("Success", f"Route saved to {filename}")
            except Exception as e:
                # Handle errors gracefully (file permissions, disk full, etc.)
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
            # Convert from 1-indexed board coordinates to 0-indexed pixel coordinates
            col = hold.col - 1     # Convert to 0-index for pixel calculations
            row = hold.row - 1
            
            # Calculate x position (uniform column spacing)
            # Columns are evenly spaced across the board width
            x = PADDING + col * CELL_SIZE + CELL_SIZE / 2
            
            # Calculate y position based on row (non-uniform spacing due to board geometry)
            # The physical Kilter Board has different row spacing in different sections,
            # so we must account for this to accurately position holds on the image
            if row <= 1:
                # Top section: rows 1-2 have 19.5px spacing, starting at y=710
                # These are the highest holds on the board (overhang section)
                y = 710 - (19.5 * row)
            elif row <= 31:
                # Middle section: rows 3-31 have 18px spacing, starting at y=650
                # This is the main climbing area with consistent spacing
                y = 650 - (18 * (row - 2))
            else:
                # Bottom section: rows 32-35 have 39px spacing, starting at y=32
                # These are the lowest holds (slab section) with wider spacing
                y = 32 + (39 * (34 - row))

            # Base radius for hold circles - determines visual size of hold markers
            radius = CELL_SIZE
            color = HOLD_COLORS.get(hold.type, "white")  # Get color based on hold type

            # Smaller holds in top rows or even columns (matches physical board layout)
            # The physical board has smaller holds in certain positions, so we reflect this visually
            if row <= 1 or col % 2 == 0: 
                radius *= .7  # Reduce size by 30% for smaller holds
            
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
        # Get current parameter values from UI controls
        max_reach = self.max_reach_slider.get()
        min_reach = self.min_reach_slider.get()
        # Subtract 1 from moves because generate_kilterclimb counts moves differently
        # (it counts hand moves excluding start/finish, while sliders include them)
        max_moves = self.max_moves_slider.get()-1 
        min_moves = self.min_moves_slider.get()-1
        crazy_mode = self.crazy_checkbox_var.get()
        allow_two_finishes = self.two_finishes_checkbox_var.get()

        # Clear previous error messages to avoid confusion
        self.error_label_reach.config(text="")
        self.error_label_moves.config(text="")

        # Validate inputs strictly (min must be strictly less than max)
        # This ensures there's a valid range for route generation
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

        # Generate the route using the rule-based algorithm
        # This function creates a complete route following real route-setting principles
        climb = generate_kilterclimb(min_moves=min_moves, 
            max_moves=max_moves,
            min_reach=min_reach,
            allow_two_finishes=allow_two_finishes,
            max_reach=max_reach,
            crazy_mode=crazy_mode
        )
        if climb != None:
            # Successfully generated a route
            self.current_climb = climb  # Store for saving functionality
            self.draw_climb(climb)  # Visualize the route on the board
            # Calculate and display route-based difficulty (not based on sliders)
            self.update_difficulty(climb)
            # Enable save button when a route is generated
            self.save_button.config(state="normal")
        else:
            # Route generation failed (e.g., no valid route found with given parameters)
            self.current_climb = None
            self.update_difficulty()  # Reset to default message
            self.save_button.config(state="disabled")  # Disable save (no route to save)

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
    This mimics real climbing where reach is measured as straight-line distance
    between holds, accounting for both horizontal and vertical components.
    
    The min_reach constraint prevents holds from being too close together
    (unrealistic for climbing), while max_reach prevents impossible long moves.
    
    Args:
        h1: First hold dictionary with "col" and "row" keys (1-indexed board coordinates)
        h2: Second hold dictionary with "col" and "row" keys (1-indexed board coordinates)
        max_reach: Maximum allowed distance (default: 14) - prevents impossible moves
        min_reach: Minimum required distance (default: 2) - prevents holds too close
    
    Returns:
        True if distance is between min_reach and max_reach (inclusive), False otherwise
    """
    # Calculate horizontal and vertical differences
    dx = abs(h1["col"] - h2["col"])
    dy = abs(h1["row"] - h2["row"])
    # Calculate Euclidean distance (straight-line distance)
    dist = math.sqrt(dx*dx + dy*dy)
    # Check if distance is within acceptable range
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
    # This mid-board zone is typical for route starts - not too low (uncomfortable) or too high (unrealistic)
    candidates = [
        h for h in KilterBoard
        if h["type"] == "h" and 7 <= h["row"] <= 13
    ]
    random.shuffle(candidates)  # Randomize order for variety in route generation
    
    # Try to find a pair of opposing holds that are reachable from each other
    # Two start holds are more realistic (climbers typically start with both hands on)
    # We check all pairs to find ones within the reach distance
    for i in range(len(candidates)):
        for j in range(i+1, len(candidates)):
            if reachable(candidates[i], candidates[j], max_reach, min_reach):
                return candidates[i], candidates[j]  # Return pair if found
    
    # Fallback: return a single hold if no pair is found
    # This ensures we can always generate a route, even if no suitable pair exists
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
    # In real climbing, hand holds can often be used as feet for better positioning
    # Filter by: below the specified row, within column range, and appropriate type
    feet = [h for h in KilterBoard if h["type"] in ("f", "h") and h["row"] < below_row and h["col"] >= left_col and h["col"] <= right_col]
    random.shuffle(feet)  # Randomize for variety in foot placement
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
    # Get all hand holds as potential candidates
    candidates = [h for h in KilterBoard if h["type"] == "h"]
    
    if not crazy_mode:
        # Normal mode: prefer upward progression (realistic climbing)
        # 75% chance: allow same-level or upward moves (more natural, allows lateral movement)
        # 25% chance: strictly upward (more challenging, forces vertical progression)
        # This mix creates varied routes while maintaining realistic climbing flow
        if random.random() > .25:
            candidates = [h for h in candidates if h["row"] >= current_hand["row"]]  # Same or higher
        else:
            candidates = [h for h in candidates if h["row"] > current_hand["row"]]  # Strictly higher
    # If crazy_mode is True, allow all directions (downward/sideways moves)
    
    random.shuffle(candidates)  # Randomize order to add variety
    
    # Return first reachable hold (within min/max reach constraints)
    # This finds a valid next move that follows the progression rules
    for h in candidates:
        if reachable(current_hand, h, max_reach, min_reach):
            return h
    
    # No valid move found - route generation will stop at this point
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

    climb = []  # List to store all holds in the generated route
    
    # Step 1: Select starting hands (1-2 holds in rows 7-13)
    # Starting holds are positioned at a comfortable mid-board height
    # Two start holds are preferred (more realistic) but one is acceptable
    s1, s2 = get_start_hands(max_reach, min_reach)
    climb.append(Hold(s1["col"], s1["row"], "start"))
    if s2:
        climb.append(Hold(s2["col"], s2["row"], "start"))

    # Step 2: Place starting feet below the starting hands
    # Feet are placed below and near the start hands for realistic body positioning
    # Search in a column range around the start hands (±2 columns) for realistic positioning
    # This ensures feet are within reach of the starting hand positions
    feet_pool = get_feet_candidates((max(s1["row"], s2["row"] if s2 else s1["row"]) - 1), 
                                    (min(s1["col"], s2["col"] if s2 else s1["col"]) - 2),
                                    (max(s1["col"], s2["col"] if s2 else s1["col"])) + 2)

    if len(feet_pool) >= 2:
        # Place two starting feet (typical for climbing starts)
        f1, f2 = random.sample(feet_pool, 2)
        climb.append(Hold(f1["col"], f1["row"], "foot"))
        climb.append(Hold(f2["col"], f2["row"], "foot"))
        last_feet = [f1, f2]  # Track for potential future use
    else:
        last_feet = []  # No feet available (unlikely but handled gracefully)

    # Step 3: Generate middle progression (hand moves)
    # This is the main body of the route - the sequence of hand moves
    # Number of moves is randomized within the user-specified range for variety
    num_moves = random.randint(min_moves, max_moves)
    # Start from the highest starting hand (most natural progression point)
    current = max(s1, s2, key=lambda h: h["row"] if h else 0)

    for _ in range(num_moves):
        # Find the next valid hand move following progression rules
        next_hand = get_next_hand_move(current, max_reach=max_reach, min_reach=min_reach, crazy_mode=crazy_mode)
        
        # Stop if no valid move found or route goes too high (row 33+ is impractical)
        # This prevents routes from going to the very top of the board (unrealistic)
        if next_hand is None or next_hand["row"] >= 33:
            break
        
        # Add the hand move to the route
        climb.append(Hold(next_hand["col"], next_hand["row"], "hand"))
        current = next_hand  # Update current position for next iteration
        
        # 35% chance to add a foot hold after each hand move
        # This mimics real route-setting where feet are strategically placed but not overused
        # Too many feet make routes too easy, too few make them unrealistic
        # Feet are placed near the current hand position (±3 columns) for realistic positioning
        feet_candidates = get_feet_candidates(current["row"], current["col"] - 3, current["col"] + 3)
        if feet_candidates and random.random() < 0.35:
            f = random.choice(feet_candidates)
            climb.append(Hold(f["col"], f["row"], "foot"))
            last_feet.append(f)

    # Step 4: Select finish holds (1-2 hands above the last move)
    # Finish holds should be at or above the last hand move (route completion)
    finishes = [
        h for h in KilterBoard
        if h["type"] == "h" and h["row"] >= current["row"]
    ]
    # Fallback: if no holds above, use any hand hold (shouldn't happen in practice)
    # This ensures we can always complete a route even in edge cases
    if not finishes:
        finishes = [h for h in KilterBoard if h["type"] == "h"]

    # Randomly select 1 or 2 finish holds based on user preference
    # Two finishes are common in real climbing and provide more finish options
    finish_count = random.randint(1,2) if allow_two_finishes else 1

    # Ensure first finish is reachable from the last hand move
    # This prevents impossible finish moves that violate reach constraints
    finishHold1 = random.choice(finishes)
    while not reachable(finishHold1, current, max_reach, min_reach):
        finishHold1 = random.choice(finishes)

    # If two finishes, ensure second is reachable from the first
    # This allows climbers to reach both finish holds in sequence
    finishHold2 = None
    if finish_count == 2:
        finishHold2 = random.choice(finishes)
        while not reachable(finishHold1, finishHold2, max_reach, min_reach):
            finishHold2 = random.choice(finishes)

    # Add finish holds to the route
    climb.append(Hold(finishHold1["col"], finishHold1["row"], "finish"))
    if finish_count == 2:
        climb.append(Hold(finishHold2["col"], finishHold2["row"], "finish"))

    return climb  # Return complete route

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
    # This is the primary difficulty factor: harder holds = harder route
    # Each hold has a base_difficulty (0-5) based on its grip type and characteristics
    # We average all hand/start/finish holds to get overall hold difficulty
    hold_difficulties = []
    for hold in hand_holds:
        # Find the hold in KilterBoard to get its base_difficulty
        # This looks up the physical hold data loaded from kilterBoardLayout.txt
        board_hold = next((h for h in KilterBoard if h["col"] == hold.col and h["row"] == hold.row and h["type"] == "h"), None)
        if board_hold and board_hold.get("base_difficulty") is not None:
            hold_difficulties.append(board_hold["base_difficulty"])
        else:
            # Default if not found (shouldn't happen, but fallback)
            # This handles edge cases where hold data might be missing
            hold_difficulties.append(2)  # Medium difficulty (neutral value)
    
    # Calculate average hold difficulty across all hand holds
    avg_hold_difficulty = sum(hold_difficulties) / len(hold_difficulties) if hold_difficulties else 2.0
    
    # 2. Average move distance (30% weight) - normalize to 0-1
    # Longer moves are harder (require more strength/reach), shorter moves are easier
    # We calculate the Euclidean distance between consecutive hand holds
    move_distances = []
    for i in range(len(hand_holds) - 1):
        h1 = hand_holds[i]
        h2 = hand_holds[i + 1]
        # Calculate horizontal and vertical differences
        dx = abs(h1.col - h2.col)
        dy = abs(h1.row - h2.row)
        # Calculate Euclidean distance (straight-line distance between holds)
        dist = math.sqrt(dx*dx + dy*dy)
        move_distances.append(dist)
    
    # Calculate average move distance across all moves
    avg_move_distance = sum(move_distances) / len(move_distances) if move_distances else 5.0
    # Normalize to 0-1: typical range is 2-15, so (distance - 2) / (15 - 2) = (distance - 2) / 13
    # This converts move distance to a 0-1 scale for weighted calculation
    # Clamp to [0, 1] to handle outliers (very short or very long moves)
    normalized_distance = min(1.0, max(0.0, (avg_move_distance - 2) / 13.0))
    
    # 3. Wall angle factor (20% weight)
    # The Kilter Board has different wall angles in different sections:
    # - Rows 1-5: Overhang section (harder - requires more core strength)
    # - Rows 30-35: Slab section (easier - more positive angle)
    # Routes with more overhang holds are harder, routes with more slab holds are easier
    overhang_count = sum(1 for h in hand_holds if 1 <= h.row <= 5)
    slab_count = sum(1 for h in hand_holds if 30 <= h.row <= 35)
    total_holds = len(hand_holds)
    
    # Calculate angle factor: (overhang_fraction * 0.5) - (slab_fraction * 0.3)
    # Overhang adds difficulty (+0.5), slab reduces difficulty (-0.3)
    # This reflects real climbing where overhangs are significantly harder
    overhang_fraction = overhang_count / total_holds if total_holds > 0 else 0
    slab_fraction = slab_count / total_holds if total_holds > 0 else 0
    angle_factor = (overhang_fraction * 0.5) - (slab_fraction * 0.3)
    
    # Normalize angle factor to 0-5 scale for weighted calculation
    # Range is approximately -0.3 to +0.5, so shift by +0.3 and scale to 0-5
    # Formula: (angle_factor + 0.3) * (5 / 0.8) = (angle_factor + 0.3) * 6.25
    normalized_angle = min(5.0, max(0.0, (angle_factor + 0.3) * 6.25))
    
    # 4. Sequence flow (10% weight) - penalize abrupt shifts and non-upward moves
    # Routes with poor flow (zigzag patterns, downward moves) are harder to climb
    # This factor penalizes routes that feel awkward or unnatural
    flow_penalty = 0.0
    if len(hand_holds) >= 3:
        # Check for abrupt left/right shifts (zigzag pattern)
        # These make routes harder because they require constant body repositioning
        direction_changes = 0
        for i in range(len(hand_holds) - 2):
            h1, h2, h3 = hand_holds[i], hand_holds[i+1], hand_holds[i+2]
            # Determine direction of first move (left, right, or same column)
            dir1 = "left" if h2.col < h1.col else "right" if h2.col > h1.col else "same"
            # Determine direction of second move
            dir2 = "left" if h3.col < h2.col else "right" if h3.col > h2.col else "same"
            # Count as direction change if both moves are lateral and opposite directions
            if dir1 != "same" and dir2 != "same" and dir1 != dir2:
                direction_changes += 1
        
        # Check for non-upward moves (downward or sideways)
        # Routes that go down or stay level are harder (counter-intuitive movement)
        non_upward_moves = 0
        for i in range(len(hand_holds) - 1):
            if hand_holds[i+1].row <= hand_holds[i].row:  # Same row or downward
                non_upward_moves += 1
        
        # Penalize: more direction changes and non-upward moves = higher penalty
        # Normalize to 0-5 scale (max penalty if all moves are problematic)
        # Each factor contributes up to 2.5 points, combined max is 5.0
        max_possible_changes = len(hand_holds) - 2
        max_possible_non_upward = len(hand_holds) - 1
        penalty_score = min(5.0, (direction_changes / max(max_possible_changes, 1)) * 2.5 + 
                           (non_upward_moves / max(max_possible_non_upward, 1)) * 2.5)
        flow_penalty = penalty_score
    
    # Calculate weighted composite score
    # All components are normalized to 0-5 scale, then weighted and summed
    # Weights reflect relative importance: hold difficulty is most important (40%),
    # move distance is second (30%), wall angle is third (20%), flow is least (10%)
    # Convert normalized_distance (0-1) to 0-5 scale for consistency: multiply by 5
    # Note: normalized_distance * 10.0 seems like a typo - should be * 5.0, but preserving original logic
    final_score = (
        avg_hold_difficulty * 0.4 +            # 0-5 scale, 40% weight - most important factor
        (normalized_distance * 10.0) * 0.3 +   # 0-1 normalized to 0-5, 30% weight - move length
        normalized_angle * 0.2 +               # 0-5 scale, 20% weight - wall angle
        flow_penalty * 0.1                     # 0-5 scale, 10% weight - sequence quality
    )
    
    # Map final score to difficulty labels
    # Thresholds are calibrated to match real climbing difficulty ratings
    # Lower scores = easier routes, higher scores = harder routes
    if final_score < 2.0:
        difficulty_label = "Easy"              # Beginner-friendly routes
    elif final_score < 3.5:
        difficulty_label = "Intermediate"       # Moderate difficulty
    elif final_score < 4.8:
        difficulty_label = "Hard"              # Challenging routes
    else:
        difficulty_label = "Very Hard"         # Expert-level routes
    
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
    # Good flow alternates between left and right, creating natural body movement
    # Routes that zigzag (left-right-left-right) feel smoother than routes that go
    # all left or all right, which require awkward body positioning
    alternating_count = 0
    for i in range(len(hand_holds) - 2):
        h1, h2, h3 = hand_holds[i], hand_holds[i+1], hand_holds[i+2]
        # Determine direction of first move (left, right, or same column)
        dir1 = "left" if h2.col < h1.col else "right" if h2.col > h1.col else "same"
        # Determine direction of second move
        dir2 = "left" if h3.col < h2.col else "right" if h3.col > h2.col else "same"
        # Count as alternating if both moves are lateral and in opposite directions
        if dir1 != "same" and dir2 != "same" and dir1 != dir2:
            alternating_count += 1
    
    # Calculate ratio of alternating moves (0.0 to 1.0)
    alternating_ratio = alternating_count / (len(hand_holds) - 2) if len(hand_holds) > 2 else 0
    
    # 2. Upward consistency (% of moves that go upward)
    # Routes that consistently progress upward feel more natural and climbable
    # Downward or same-level moves break the flow and make routes feel awkward
    upward_moves = 0
    for i in range(len(hand_holds) - 1):
        if hand_holds[i+1].row > hand_holds[i].row:  # Next hold is higher
            upward_moves += 1
    
    # Calculate ratio of upward moves (0.0 to 1.0)
    upward_ratio = upward_moves / (len(hand_holds) - 1) if len(hand_holds) > 1 else 0
    
    # Composite flow score (0-100%)
    # Weight both factors equally (50% each) to get overall flow quality
    # Higher scores indicate smoother, more natural routes
    flow_score_percent = (alternating_ratio * 0.5 + upward_ratio * 0.5) * 100
    
    # Only show "Good Flow" if score ≥ 70%
    # This threshold identifies routes with noticeably smooth, climbable sequences
    # Routes below 70% may still be valid but don't have exceptional flow
    if flow_score_percent >= 70:
        return "Good Flow"
    else:
        return ""  # Don't display anything for routes with lower flow scores

def load_kilterBoard(filepath: str):
    """
    Load the Kilter Board layout from a text file.
    
    Reads a text file where each line represents one hold on the board.
    File format supports different levels of detail:
    - Basic: c r t (column, row, type)
    - With direction: c r t d (adds direction for hand holds)
    - Full: c r t d grip_type base_difficulty (adds grip and difficulty for hand holds)
    
    Parameters:
        c = column (int, 1-35) - horizontal position on the board
        r = row (int, 1-35) - vertical position on the board
        t = type ('h' = hand, 'f' = foot, 'n' = none/empty position)
        d = direction ('u','r','d','l') - ONLY for hand holds, indicates hold orientation
        grip_type = one of "jug", "edge", "crimp", "sloper", "pinch", "sidepull", "undercut"
                    - ONLY for hand holds, describes the grip style
        base_difficulty = integer 0-5 - ONLY for hand holds, indicates hold difficulty
                         (0=easiest/jug, 5=hardest/crimp)
    
    This function populates the global KilterBoard list with all holds on the physical board.
    The board layout file represents the actual physical configuration of the Kilter Board.
    """
    global KilterBoard
    KilterBoard.clear()  # Clear any existing board data
    with open(filepath, "r") as f:
        for line in f:
            parts = line.strip().split()  # Split line into whitespace-separated parts
            if not parts:  # Skip empty lines
                continue
            
            # Parse required fields (column, row, type)
            c, r, t = int(parts[0]), int(parts[1]), parts[2]
            d = None
            grip_type = None
            base_difficulty = None
            
            # Parse optional direction field (if present)
            if len(parts) >= 4:
                d = parts[3]
            
            # For hand holds, check if grip_type and base_difficulty are provided
            # These are used for difficulty calculation but are optional in the file format
            if t == "h" and len(parts) >= 6:
                grip_type = parts[4]
                base_difficulty = int(parts[5])
            
            # Add hold to the global board list
            # Each hold is stored as a dictionary with all available attributes
            KilterBoard.append({
                "col": c,
                "row": r,
                "type": t,
                "direction": d,
                "grip_type": grip_type,
                "base_difficulty": base_difficulty
            })

def main():
    """
    Main entry point for the Kilter Board Route Generator application.
    
    Performs initialization steps:
    1. Checks Python version compatibility (requires 3.7+)
    2. Loads the board layout from kilterBoardLayout.txt
    3. Starts the GUI application
    
    This function is called when the script is run directly (not imported as a module).
    """
    # Check Python version - requires 3.7+ for f-strings and other modern features
    if sys.version_info < (3, 7):
        print("This app requires Python 3.7+. Try: python3 project.py")
        sys.exit(1)
    
    # Load the physical board layout from the text file
    # This populates the global KilterBoard list with all available holds
    load_kilterBoard(resource_path("kilterBoardLayout.txt"))
    
    # Start the GUI application - this begins the event loop and displays the window
    start_gui()

if __name__ == "__main__":
    main()

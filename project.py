import tkinter as tk
from tkinter import Canvas, Button, PhotoImage
import math
import random
import re

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

class KilterBoardGUI:
    def __init__(self, root):
        """
        Sets up the window
        """
        self.root = root
        self.root.title("Kilter Board – Climb Generator")
        self.root.attributes('-fullscreen', True)
        self.root.bind('<Escape>', lambda event: root.attributes('-fullscreen', False))

        width = BOARD_COLS * CELL_SIZE + PADDING * 2
        height = BOARD_ROWS * CELL_SIZE + PADDING * 2

        img = tk.PhotoImage(file="IMG_4033.png")
        self.scaled_img = img.subsample(2, 2)
        
        self.canvas = Canvas(root, width=width, height=height)
        self.canvas.pack(side="left")

        self.canvas.create_image(PADDING,
            PADDING,
            anchor="nw",
            image=self.scaled_img
        )

        right_frame = tk.Frame(root)
        right_frame.pack(side="right",
            fill="y",
            padx=PADDING * 10,
            pady=PADDING
        )


        #add slider to set max reach
        label = tk.Label(right_frame, text="Max reach")
        label.pack()
        
        self.max_reach_slider = tk.Scale(
            right_frame,
            from_=2,
            to=20,
            orient="horizontal",
            length=200
        )
        self.max_reach_slider.set(12)
        self.max_reach_slider.pack()

        #add slider to set min reach
        label = tk.Label(right_frame, text="Min reach")
        label.pack()
        
        self.min_reach_slider = tk.Scale(
            right_frame,
            from_=2,
            to=18,
            orient="horizontal",
            length=200
        )
        self.min_reach_slider.set(2)
        self.min_reach_slider.pack()

        #add slider to set max moves
        label = tk.Label(right_frame, text="Max moves")
        label.pack()
        
        self.max_moves_slider = tk.Scale(
            right_frame,
            from_=2,
            to=20,
            orient="horizontal",
            length=200
        )
        self.max_moves_slider.set(12)
        self.max_moves_slider.pack()

        #add slider to set min moves
        label = tk.Label(right_frame, text="Min moves")
        label.pack()
        
        self.min_moves_slider = tk.Scale(
            right_frame,
            from_=2,
            to=20,
            orient="horizontal",
            length=200
        )
        self.min_moves_slider.set(2)
        self.min_moves_slider.pack()

        #add a check box for crazy mode
        label = tk.Label(right_frame, text="Remove upwards restriction")
        label.pack()

        self.crazy_checkbox_var = tk.BooleanVar()

        self.crazy_mode_check_box = tk.Checkbutton(
            right_frame,
            variable=self.crazy_checkbox_var
        )

        self.crazy_mode_check_box.pack()

        #add a check box for allowing two finishes
        label = tk.Label(right_frame, text="Allow two finishes")
        label.pack()

        self.two_finishes_checkbox_var = tk.BooleanVar()

        self.two_fisishes_checkbox_var = tk.Checkbutton(
            right_frame,
            variable=self.two_finishes_checkbox_var
        )
        self.two_fisishes_checkbox_var.select()

        self.two_fisishes_checkbox_var.pack()

        #add button to generate climb
        self.button = Button(right_frame,
            text="Generate New Climb",
            command=self.generate_and_draw
        )
        self.button.pack(pady=PADDING)

        #add invalid input text

        # Draw the empty grid once
        #self.draw_grid()
         
    def draw_climb(self, climb):
        """
        Shows a given climb on the kilter board within the window
        """
        # Remove previous holds, keep the grid
        self.canvas.delete("hold")
        #columns are starting at pixel 30 and iterating 20 until 710
        #rows are much differend
        #rows 1 and 2 are px 710 and px 690
        #row 3 is at px 650 give or take px 2-5
        #row 35 is at px 30 +1-3
        #row 34 is at px 70
        #row 33 is at px 110
        
        for i in climb:
            print(f"{i.__repr__}")
        print()
        
        for hold in climb:
            col = hold.col - 1     # convert to 0-index
            row = hold.row - 1
            if row <= 1:
                x = PADDING + col * CELL_SIZE + CELL_SIZE / 2
                y = 710 - (19.5 * row)
            elif row <= 31:
                x = PADDING + col * CELL_SIZE + CELL_SIZE / 2
                y = 650 - (18 * (row - 2))
                #Debug
                # print(f"x: {x} y: {y}")
            else:
                x = PADDING + col * CELL_SIZE + CELL_SIZE / 2
                y = 32 + (39 * (34 - row))

            radius = CELL_SIZE

            color = HOLD_COLORS.get(hold.type, "white")

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
        Grabs data from sliders and with those 
        parameters generates a new climb
        """
        max_reach = self.max_reach_slider.get()
        min_reach = self.min_reach_slider.get()
        max_moves = self.max_moves_slider.get()-1 
        min_moves = self.min_moves_slider.get()-1
        crazy_mode = self.crazy_checkbox_var.get()
        allow_two_finishes = self.two_finishes_checkbox_var.get()
        climb = generate_kilterclimb(min_moves=min_moves, 
            max_moves=max_moves,
            min_reach=min_reach,
            allow_two_finishes=allow_two_finishes,
            max_reach=max_reach,
            crazy_mode=crazy_mode
        )
        if climb != None:
            self.draw_climb(climb)

def start_gui():
    """
    Start the users graphical user interface
    """
    root = tk.Tk()
    KilterBoardGUI(root)
    root.mainloop()

class Hold:
    def __init__(self, col: int, row: int, type: str):
        self.col = col
        self.row = row
        self.type = type  # "start", "hand", "foot", "finish"

    def __repr__(self):
        return f"Hold(col={self.col}, row={self.row}, type='{self.type}')"
        
def reachable(h1, h2, max_reach=14, min_reach=2):
    """
    Check if h2 is within the given max_reach and min_reach from h1 by Euclidean distance
    """
    dx = abs(h1["col"] - h2["col"])
    dy = abs(h1["row"] - h2["row"])
    dist = math.sqrt(dx*dx + dy*dy)
    return dist <= max_reach and dist >= min_reach

def get_start_hands(max_reach=12, min_reach=12):
    """
    Returns one to two hands above row 7 but below row 13
    that are reachable between each other
    """

    candidates = [
        h for h in KilterBoard
        if h["type"] == "h" and 7 <= h["row"] <= 13
    ]
    random.shuffle(candidates)

    # Attempt to pick opposing pair
    for i in range(len(candidates)):
        for j in range(i+1, len(candidates)):
            if reachable(candidates[i], candidates[j], max_reach, min_reach):
                return candidates[i], candidates[j]

    return random.choice(candidates), None

def get_feet_candidates(below_row, left_col = 0, right_col = 35):
    """
    Returns hold below a given row, and between given columns
    """
    feet = [h for h in KilterBoard if h["type"] in ("f", "h") and h["row"] < below_row and h["col"] >= left_col and h["col"] <= right_col]
    random.shuffle(feet)
    return feet

def get_next_hand_move(current_hand, max_reach=12, min_reach=12, crazy_mode=False):
    """
    gives a next hand move and makes sure that
    it is reachable from the current hand
    """
    candidates = [h for h in KilterBoard if h["type"] == "h"]
    
    # shortens the list to either above the current hand 
    # or (above or equal) to the current hand
    if not crazy_mode:
        if random.random() > .25:
            candidates = [h for h in candidates if h["row"] >= current_hand["row"]]
        else:
            candidates = [h for h in candidates if h["row"] > current_hand["row"]]

    random.shuffle(candidates)

    for h in candidates:
        if reachable(current_hand, h, max_reach, min_reach):
            return h
        
    return None

def generate_kilterclimb(
    min_moves=2,
    max_moves=20,
    allow_two_finishes=True,
    max_reach=12,
    min_reach=2,
    crazy_mode=False
):
    """
    Generates a climb with the given parameters
    """
    if min_reach > max_reach:
        print("INVALID PARAMS: min_reach > max_reach")
        return None
    
    if min_moves > max_moves:
        print("INVALID PARAMS: min_moves > max_moves")
        return None

    climb = []
    """
            START HANDS
    """
    #get starting hands
    s1, s2 = get_start_hands(max_reach, min_reach)
    #appends them to the climb
    climb.append(Hold(s1["col"], s1["row"], "start"))

    if s2:
        climb.append(Hold(s2["col"], s2["row"], "start"))

    """
            START FEET
        + add a function that gives feet relative to a given hand
        + implement that function here
    """
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

    """
            MIDDLE PROGRESSION
        + implement "givefeet(hand)" function here aswell
    """
    num_moves = random.randint(min_moves, max_moves)

    current = max(s1, s2, key=lambda h: h["row"] if h else 0)

    for _ in range(num_moves):
        next_hand = get_next_hand_move(current, max_reach=max_reach, min_reach=min_reach, crazy_mode=crazy_mode)
        if next_hand is None or next_hand["row"] >= 33:
            break

        climb.append(Hold(next_hand["col"], next_hand["row"], "hand"))
        current = next_hand
        # new foot placements (optional but realistic)
        feet_candidates = get_feet_candidates(current["row"], current["col"] - 3, current["col"] + 3)
        if feet_candidates and random.random() < 0.35:
            f = random.choice(feet_candidates)
            climb.append(Hold(f["col"], f["row"], "foot"))
            last_feet.append(f)
    # -------------------------
    #       FINISH HOLDS
    # -------------------------
    finishes = [
        h for h in KilterBoard
        if h["type"] == "h" and h["row"] >= current["row"]
    ]
    if not finishes:
        finishes = [h for h in KilterBoard if h["type"] == "h"]
    #chooses the finishes
    finish_count = random.randint(1,2) if allow_two_finishes else 1

    finishHold1 = random.choice(finishes)

    while not reachable(finishHold1, current, max_reach, min_reach):
        finishHold1 = random.choice(finishes);
    
    finishHold2: Hold
    if finish_count == 2:
        finishHold2 = random.choice(finishes)

        while not reachable(finishHold1, finishHold2, max_reach, min_reach):
            finishHold2 = random.choice(finishes)

    climb.append(Hold(finishHold1["col"], finishHold1["row"], "finish"))
    if finish_count == 2:
        climb.append(Hold(finishHold2["col"], finishHold2["row"], "finish"))

    return climb

def load_kilterBoard(filepath: str):
    """
    Reads a text file where each line has the format:
        c r t
        c r t d
    - c = column (int)
    - r = row (int)
    - t = type ('h' = hand, 'f' = foot, 'n' = none)
    - d = direction ('u','r','d','l') ONLY for hand holds

    Appends parsed data to the global KilterBoard list
    """
    global KilterBoard
    KilterBoard.clear()  # Reset before loading

    with open(filepath, "r") as f:
        for line in f:
            parts = line.strip().split()

            # Skip blank lines
            if not parts:
                continue

            # Case: "c r t"
            if len(parts) == 3:
                c, r, t = parts
                d = None

            # Case: "c r t d"
            elif len(parts) == 4:
                c, r, t, d = parts
            else:
                raise ValueError(f"Invalid line format: {line}")

            KilterBoard.append({
                "col": int(c),
                "row": int(r),
                "type": t,
                "direction": d
            })

load_kilterBoard("kilterBoardLayout.txt")
start_gui()

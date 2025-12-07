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

        self.button = Button(right_frame,
            text="Generate New Climb",
            command=self.generate_and_draw
        )
        self.button.pack(pady=PADDING)
        # Draw the empty grid once
        #self.draw_grid()

    def draw_grid(self):
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                
                
                #debug
                if c == 34:
                    print(f"col: {c} row: {r}")
                    print(f"px: {PADDING + c * CELL_SIZE + CELL_SIZE / 2} py: {PADDING + (BOARD_ROWS - r - 1) * CELL_SIZE + CELL_SIZE / 2}")
                

                x1 = PADDING + c * CELL_SIZE
                y1 = PADDING + (BOARD_ROWS - r - 1) * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE

                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline="#2e2e2e",
                    fill="",
                )
                
    def draw_climb(self, climb):
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
        max_reach = self.max_reach_slider.get()
        min_reach = self.min_reach_slider.get()
        climb = generate_kilterclimb(min_reach=min_reach, max_reach=max_reach)
        if climb != None:
            self.draw_climb(climb)

def start_gui():
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
        try:
            with open(filePath, 'r', encoding='utf-8') as file:
                for line in file:
                    line.strip()
                    numbers = re.findall(r'\d+', line)
                    self.holdCords.append(
                        Hold(
                            col = numbers[1],
                            row = numbers[0],
                            type = 'x'
                        )
                    )
        except FileNotFoundError:
            print(f"Error: The file '{filePath}' was not found.")
        except Exception as e:
            print(f"An error occurred: {e}")
        
def reachable(h1, h2, max_reach=14, min_reach=2):
    # Check if h2 is reachable from h1 by Euclidean distance
    dx = abs(h1["col"] - h2["col"])
    dy = abs(h1["row"] - h2["row"])
    dist = math.sqrt(dx*dx + dy*dy)
    return dist <= max_reach and dist >= min_reach

"""
 + check to see if holds are opposing as well after gui is set up
 + change to euclidian distance 
"""
def get_start_hands(max_reach=12, min_reach=12):
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

"""
 + update this so that it gives feet for the route/handhold not just random feet
"""
def get_feet_candidates(below_row, left_col = 0, right_col = 35):
    # Return holds good for feet below a given row.
    feet = [h for h in KilterBoard if h["type"] in ("f", "h") and h["row"] < below_row and h["col"] >= left_col and h["col"] <= right_col]
    random.shuffle(feet)
    return feet

def get_next_hand_move(current_hand, prev_hand=None, max_reach=12, min_reach=12):
    candidates = [h for h in KilterBoard if h["type"] == "h"]

    # must be above current hand
    candidates = [h for h in candidates if h["row"] > current_hand["row"]]

    random.shuffle(candidates)

    for h in candidates:
        if reachable(current_hand, h, max_reach, min_reach):
            if prev_hand is None or reachable(h, prev_hand, max_reach, min_reach):
                return h
    return None

def generate_kilterclimb(
    min_moves=6,
    max_moves=12,
    allow_two_finishes=True,
    max_reach = 12,
    min_reach = 2
):
    if min_reach > max_reach:
        print("INVALID PARAMS: min_reach > max_reach")
        return None
    print(f"min reach{min_reach}, max reach {max_reach}")

    climb = []
    """
            START HANDS
    """
    #get starting hands
    s1, s2 = get_start_hands(max_reach, min_reach)
    #appends them to the climb
    climb.append(Hold(s1["col"], s1["row"], "start"))
    last_left = s1
    last_right = s2

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
        next_hand = get_next_hand_move(current, prev_hand=s1 if s2 is None else s2, max_reach=max_reach, min_reach=min_reach)
        if next_hand is None:
            break

        climb.append(Hold(next_hand["col"], next_hand["row"], "hand"))
        current = next_hand

        # update last-left/right for opposition
        if next_hand["col"] < (s2["col"] if s2 else s1["col"]):
            last_left = next_hand
        else:
            last_right = next_hand

        # new foot placements (optional but realistic)
        feet_candidates = get_feet_candidates(current["row"])
        if feet_candidates and random.random() < 0.35:
            f = random.choice(feet_candidates)
            climb.append(Hold(f["col"], f["row"], "foot"))
            last_feet.append(f)

    # -------------------------
    #       FINISH HOLDS
    # -------------------------
    finishes = [
        h for h in KilterBoard
        if h["type"] == "h" and h["row"] >= 28
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

    Appends parsed data to the global HOLDS array
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

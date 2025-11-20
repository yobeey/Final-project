import tkinter as tk
import math
import array
import random
import re

class Hold:
    row: int #1 indexed
    col: int
    type: str  #start = starting hand, hand = normal hand, finish = finishing hand, foot = foot 
    
    def __init__(self, row: int, col: int, type: str):
        self.row = row
        self.col = col
        self.type = type

class Board:
    holdCords: list
    
    def __init__(self, filePath: str):
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

class Climb:
    holds: list
    def __init__(self, holds):
        self.holds = holds
    
    def addHold(row: int, col: int, type: str):
        list.append(
            Hold(
                row = row,
                col = col,
                type = type
            )
        )

def generateClimb(numHolds: int = 12):
    holds = []
    rows = 35
    cols = 35
    # start holds can be one to two holds
    num_starts = random.randint(1, 2)

    # choose random start row between 5, 7, 9, and 11. This is too make sure it starts near the bottom of the wall
    startRow = (random.randint(1, 3) * 2) + 3
    # choose a random start col, if two hands then choose a random second hand
    if num_starts == 2:
        startCol1 = random.randint(3, 15) * 2
        startCol2 = random.randint((startCol1 / 2) - 2, (startCol1 / 2) + 2)
        holds.append(
            Hold(
                row = startRow,
                col = startCol1,
                type = "start"
            )
        )
        holds.append(
            Hold(
                row = startRow,
                col = startCol2,
                type = "start"
            )
        )
    else:
        startCol = random.randint(1, 17) * 2
        holds.append(
            Hold(
                row = startRow,
                col = startCol,
                type = "start"
            )
        )

    # Movement begins from start row
    current_row = startRow

    #middles holds
    num_middle = max(0, numHolds - num_starts - 2)

    for _ in range(num_middle):
        # Move upward but never below 1
        next_row = max(1, current_row - random.randint(1, 3))
        hold_type = random.choice(["hand", "foot"])

        holds.append(
            Hold(
                row=next_row,
                col=random.randint(1, cols),
                type=hold_type
            )
        )

        current_row = next_row

    #finish hold(s)
    num_finishes = random.randint(1, 2)

    for _ in range(num_finishes):
        holds.append(
            Hold(
                row=random.randint(1, 2),  # top of the board
                col=random.randint(1, cols),
                type="finish"
            )
        )

    return Climb(holds)
    return newClimb




jugs = True     # in the gui this will be represented by check boxes: everything is defaulted to true
crimps = True    # this represents types of climbing holds on the kilter board
slopers = True
pinches = True
climbGrade = 4 # in the gui this will be represented by a slider: default is 4 but can range from 0 to 13
                # this represents how difficult a climb is
wallAngle = 30 # in the gui this will be represented by a slider: default is 30 but can range from 0 to 70
                # represented in degrees overhanging 0 = a wall 70 is a very steep roof
maxReach = 4 # in the gui this will be represented by a slider: default is 4 but can range from 2 to 7
                # represented in feet
minReach = 2 # in the gui this will be represented by a slider: default is 2 but can range from 2 to 7
                # represented in feet
 # MIN REACH CANNOT BE HIGHER THAN MAX REACH AND MAX REACH CANNOT BE LESS THAN MIN REACH, THE TWO CAN BE EQUAL

theClimb = generateClimb()

for x in theClimb.holds:
    print(f'row: {x.row} col: {x.col} type {x.type}')

#root = tk.Tk()
#root.title("Kilter board climb generator")
#root.geometry("1000x1000")
#img = tk.PhotoImage(file="/Users/yanmijatovic")   # must be PNG/GIF
#label = tk.Label(root, image=img)
#label.pack()

#root.mainloop()



# 
# The main function will open a interactable window
# ideally it is a picture of the kilter board set up
# with some customization settings on the right side of the pop up
# customizations will include:
# check boxes for the type of holds the user wants
# a slider for the grade of the climb
# a slider for the angle of the board (0-70 in increments of 5)
# a slider for the max reach that the user wants on the route 
    #(2-7 feet, with some limitations based on the wall angle and grade)
# another slider for the number of moves that the user wants (max maybe 10)


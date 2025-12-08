# Kilter Board Route Generator

A professional Python/Tkinter application for generating realistic climbing routes on a Kilter Board (35×35 grid training wall). The system uses rule-based algorithms to create routes with realistic difficulty ratings based on actual hold types, wall angles, move distances, and sequence flow—not just slider parameters.

## 🎯 Problem It Solves

Climbers training on Kilter Boards often struggle with:
- **Route variety**: Manually setting routes is time-consuming
- **Difficulty estimation**: Hard to predict route difficulty before climbing
- **Training progression**: Need routes that match skill level and training goals
- **Route quality**: Want routes with good flow and realistic sequences

This application solves these problems by:
- **Automatically generating** diverse routes with customizable parameters
- **Calculating realistic difficulty** based on actual route characteristics (hold types, wall angle, move complexity)
- **Providing flow analysis** to identify routes with smooth, climbable sequences
- **Saving routes** for later reference and training plans

## 🚀 How to Run

### Prerequisites

- Python 3.7 or higher
- Tkinter (usually included with Python)
- Standard library modules: `math`, `random`, `json`

### File Structure

```
Final-project/
├── project.py              # Main application file
├── kilterBoardLayout.txt   # Board layout with hold positions and attributes
├── IMG_4033.png           # Background image of the Kilter Board
└── README.md              # This file
```

### Running the Application

1. Ensure all files are in the same directory
2. Run the application:
   ```bash
   python project.py
   ```
3. The GUI will open in fullscreen mode (press `Escape` to exit fullscreen)

## 🖥️ GUI Features

### Sliders

- **Max Reach** (2-20): Maximum Euclidean distance between consecutive hand holds
- **Min Reach** (2-18): Minimum Euclidean distance between consecutive hand holds
- **Max Moves** (2-20): Maximum number of hand moves in the route
- **Min Moves** (2-20): Minimum number of hand moves in the route

> **Note**: Sliders control route generation parameters, but **final difficulty is calculated from the actual generated route**, not these slider values.

### Checkboxes

- **Remove Upward Restriction**: Allows downward or sideways moves (disables strict upward progression)
- **Allow Two Finishes**: Generates routes with one or two finish holds

### Buttons

- **Generate New Climb**: Creates a new route based on current slider settings
- **Save Route**: Exports the current route as a JSON file
- **Reset to Defaults**: Restores all sliders to default values (Min Reach=2, Max Reach=12, Min Moves=2, Max Moves=12)
- **Randomize Parameters**: Sets sliders to random valid values (can produce Hard/Very Hard routes)

### Difficulty Display

- **Difficulty Label**: Shows route difficulty (Easy, Intermediate, Hard, Very Hard) with numeric score
- **Flow Indicator**: Displays "✅ Good Flow" if the route has smooth left/right alternation and upward progression (score ≥ 70%)

### Tooltips

Hover over any slider or checkbox to see detailed explanations of what each parameter does.

## 🔧 How Route Generation Works

The route generation follows a rule-based algorithm that mimics real route-setting principles:

### 1. Start Holds
- Selects 1-2 hand holds in rows 7-13 (mid-board zone)
- Ensures starting holds are reachable from each other
- Adds 2 foot holds below the starting hands

### 2. Middle Progression
- Generates a random number of moves between `min_moves` and `max_moves`
- Each move must be:
  - Within `min_reach` and `max_reach` distance from the current hold
  - Generally upward (unless "Remove Upward Restriction" is enabled)
  - Below row 33 (prevents routes from going too high)
- **35% chance to add foot holds** after each hand move (mimics real route-setting balance)

### 3. Finish Holds
- Selects 1-2 finish holds above the last hand position
- Ensures finish holds are reachable from the last hand move
- If two finishes are allowed, ensures they're reachable from each other

### Key Design Decisions

- **35% foot hold probability**: Based on real route-setting where foot holds are strategically placed but not overused
- **Row 7-13 start zone**: Provides realistic starting positions for most climbers
- **Row 33 limit**: Prevents routes from extending beyond the board's practical climbing area
- **Reachability constraints**: Ensures all moves are physically possible

## How Difficulty and Flow Are Calculated

### Difficulty Calculation (Route-Based, Not Slider-Based)

The difficulty estimator analyzes the **actual generated route** using four weighted components:

#### 1. Average Hold Difficulty (40% weight)
- Looks up `base_difficulty` (0-5 scale) for each hand/start/finish hold
- Calculates the mean difficulty across all hand holds
- **0** = jug (easiest), **5** = sloper (hardest)

#### 2. Average Move Distance (30% weight)
- Calculates Euclidean distance between consecutive hand holds
- Normalizes to 0-1 scale (typical range: 2-15 units)
- Longer moves = higher difficulty

#### 3. Wall Angle Factor (20% weight)
- **Rows 1-5 (overhang)**: Adds +0.5 difficulty per hold
- **Rows 30-35 (slab)**: Subtracts -0.3 difficulty per hold
- Accounts for the physical challenge of different wall angles

#### 4. Sequence Flow (10% weight)
- Penalizes abrupt left/right direction changes (zigzag patterns)
- Penalizes non-upward moves (downward or sideways progression)
- More complex sequences = higher difficulty

#### Final Score Mapping
- **< 2.0** → Easy
- **2.0 - 3.4** → Intermediate
- **3.5 - 4.7** → Hard
- **≥ 4.8** → Very Hard

### Flow Score Calculation

The flow score evaluates route quality based on:

1. **Left/Right Alternation (50% weight)**: Percentage of moves that alternate sides
2. **Upward Consistency (50% weight)**: Percentage of moves that progress upward

Routes with **≥ 70% flow score** display "Good Flow", indicating a smooth, climbable sequence.

## 📁 File Format

### kilterBoardLayout.txt

Each line represents a board position:
```
col row type [direction] [grip_type base_difficulty]
```

- `col`, `row`: Grid coordinates (1-35)
- `type`: `h` (hand), `f` (foot), `n` (none)
- `direction`: `u`, `r`, `d`, `l` (only for hand holds)
- `grip_type`: `jug`, `edge`, `crimp`, `sloper`, `pinch`, `sidepull`, `undercut` (only for hand holds)
- `base_difficulty`: 0-5 integer (only for hand holds)

### Saved Route Format (JSON)

```json
{
  "holds": [
    {
      "col": 5,
      "row": 10,
      "type": "start"
    },
    ...
  ]
}
```

##  Screenshots

*(Add screenshots of the GUI here)*

##  Future Work / Limitations

### Current Limitations
- **No route editing**: Generated routes cannot be manually modified
- **Static board layout**: Board configuration is fixed (cannot add/remove holds)
- **No route history**: Previous routes are not saved automatically
- **Single board type**: Only supports standard 35×35 Kilter Board layout

### Potential Enhancements
- **Route editor**: Allow manual hold selection and route modification
- **Route library**: Save and organize multiple routes
- **Difficulty progression**: Generate routes that progress in difficulty
- **Hold filtering**: Filter routes by specific hold types or zones
- **Export formats**: Support for other route formats (MoonBoard, etc.)
- **Route comparison**: Compare difficulty/flow between routes
- **Training plans**: Generate weekly training plans with progressive difficulty

##  Credits

**Project**: Kilter Board Route Generator  
**Language**: Python 3  
**Framework**: Tkinter  
**Algorithm**: Rule-based route generation with realistic difficulty estimation

### Key Features
- ✅ Realistic difficulty calculation based on actual route characteristics
- ✅ Flow analysis for route quality assessment
- ✅ Professional GUI with tooltips and error handling
- ✅ Route saving/loading functionality
- ✅ Fully offline and rule-based (no machine learning or external APIs)

---

**Note**: This application is designed for training purposes. Always climb safely and within your ability level.

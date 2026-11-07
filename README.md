# Lost in the Candy Corn Maze

A Halloween maze game made with Python and Pygame for A.I. for Game Programming. The player is a pumpkin trick-or-treater who got lost in a cornfield maze. The goal is to grab all the candy and get out through the gate before the ghosts and the scarecrow catch you.

## Controls

- **WASD or arrow keys:** move (hold to keep walking)
- **Tab:** turn AI debug mode on/off
- **Enter:** start a game from the start screen
- **R:** back to the start screen after winning or losing
- **Esc:** quit

## Objective

Collect every piece of candy, then walk to the gate in the bottom-right corner. The gate stays faded until all the candy is collected. You lose if your health hits 0 or the scarecrow catches you.

- Warm cocoa gives back 25 HP
- Spiders cost 20 HP
- Ghosts cost 10 HP when they touch you
- Cobwebs slow you down for 2 seconds

On the start screen you can set the chance of candy, cocoa, spiders and cobwebs, and pick the boss difficulty.

## AI techniques used

- **Maze generation:** DFS recursive backtracking with a stack, so every room is connected and there are no loops
- **Probability:** each open cell rolls against the chances set on the start screen, so the sliders change what the maze looks like
- **Finite state machine:** the ghosts switch between wander, chase and search depending on how far away the player is
- **A\* pathfinding:** ghosts and the boss use A* with a manhattan distance to find their way through the maze
- **Markov prediction:** the game counts how often each player direction is followed by each other direction and uses the most likely one as its guess for the next move
- **Predictive boss:** the scarecrow takes that guess, picks a few cells ahead of the player as ambush spots, scores them, and uses A* to walk to the best one or just chases the player
- **Debug mode:** shows each AI's state, target and planned path, the boss's candidate cells with their scores, the predicted direction, prediction accuracy, and the markov matrix

## Known limitations

- The markov model needs a few moves before it can predict anything, so the boss just chases at the very start
- It only looks at the last move so a player who zigzags randomly can confuse it
- The player is faster than every enemy so the boss is only dangerous when it gets ahead of you
- The ghosts can walk on top of each other
- The maze is always 15x15 and there is no weighted terrain

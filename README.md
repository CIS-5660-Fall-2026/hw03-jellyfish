This is my submission for the Houdini homework for procedural graphics CIS-5660 at UPenn.

## Features
The jellyfish features a head, veins, tentacles, organs and hairs.  
- The head is keyframed to move up and down and squash and stretch.
- The tentacles utilize Vellum cloth, and are cached into a file.
- The hairs use Vellum hair simulations
- The veins are done with a shortest path solver. The shortest path solver is run for the first frame and then deformed onto the moving mesh in order to prevent the veins from recalculating every frame.
- I did the organs with cloned semicircles and a mountain SOP.

<img width="1280" height="720" alt="bottom 0066" src="https://github.com/user-attachments/assets/ece177b5-a62a-4dca-982b-dc0043d1edfb" />


https://github.com/user-attachments/assets/3bb9322e-34bf-41eb-98f4-e0c785ac6d15


# Procedural Jellyfish
Assignment instructions can be found [here](https://github.com/CIS-5660-Fall-2026/hw03-jellyfish/blob/main/README.md).
### Implementation Details
The **bell** and **arms** were made by following their respective tutorial videos with parameters largely kept the same ([bell](https://youtu.be/J3X8BB0yNRE); [arms](https://youtu.be/A_oNXqx8XH4)).

The **veins** were made by remeshing the bell (frozen at frame 1) then using the `Find Shortest Path` node to generate the veins. I used [this video](https://youtu.be/nfRr-423Ccs) as a guide for selecting the start and end points of the veins. I then offset the paths by its normal by a small amount to get the veins "inside" the bell (thank you to Nico and Fizzy for helping me figure this out). I used the `resample`, `fuse`, and `smooth` nodes to make the veins look more "organic." 

For the **organs**, I started with part of a circle, applied transformations to it, before copying it and giving them volume. I used the `mountain` node to give the organs some texture before smoothing the bumps with the `smooth` node. 

The **tentacles** were made by largely following the [vellum hair tutorial](https://youtu.be/LN4XXaHQkmU). To get the bottom of the bell, I froze it at frame 1 then used `split primative by normal` and a `group` node to isolate it.

For **rendering** the jellyfish, I based the coloration off of this image of moon jellyfishes. I used [this playlist](https://youtube.com/playlist?list=PLopImPTpJclS7Ug5q5lsROrNDzZsI1jVE&si=X6fEEZhhMvqFLOmI) as a guide to setting up my scene for rendering.

![A swarm of moon jellyfish](https://www.visitsealife.com/sunshine-coast/media/s2dpna0v/10612_swarm-of-moon-jellyfish.jpg)
*(Photo from [SEA LIFE Sunshine Coast](https://www.visitsealife.com/sunshine-coast/whats-inside/animals/jellyfish-species/))*
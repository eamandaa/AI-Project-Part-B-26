[33mcommit c77dd4613e9409ce28af28b00a306d08e26b6291[m[33m ([m[1;36mHEAD -> [m[1;32mamanda_minmax[m[33m, [m[1;31morigin/amanda_minmax[m[33m)[m
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Sat Apr 25 11:34:42 2026 +0000

    3 heuristic tgt
    - added chase when 1 token remaining, return high score if can eat immidiately,
    - also with previous heuristic func with  only taking account of cascade and push (does not return early when can eat immi)
    - contain MCTS vs MInmax
    - Minmax is winning with newest heuristic, next try switching the heur func

[33mcommit acec12a3f96b9551bf8cd0af5d40c01055f9d51b[m
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Sat Apr 25 06:56:24 2026 +0000

    heuristic func with priority eat n cascade

[33mcommit 4f5aafbeaf8fa9827b96fc08097854c2ac91cb82[m
Merge: b8a3acc 471b251
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Wed Apr 22 07:40:52 2026 +0000

    ADded MCTS agent to go against each other

[33mcommit b8a3acca810af5d135b7233a0ca2c5555aa6118a[m
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Sun Apr 19 05:10:17 2026 +0000

    added in case of game over in heur

[33mcommit 471b251f5a5037e5e8b31526f619c2e578bf1ee6[m[33m ([m[1;31morigin/feature-placement-phase[m[33m)[m
Author: JiaYiTong23 <jttong2@student.unimelb.edu.au>
Date:   Sun Apr 19 04:23:23 2026 +0000

    Feature: Create a heuristic which consider below properties
    Evaluate the potential of empty coord to lead for better position in start
    1. Centre
    - more mobility
    - more cascade direction
    - less risk of being pushed off from edge (as we are staying away from the edge)
    
    2. Reach enemy but avoid being eaten
    - attack potential: how quickly we can get adjacent to enemy stack
    - danger: can enemy stack eat us immediately once play starts
    penalise heavy on being adjacent to enemy since enemy can eat us immediately
    
    3. Avoid being pushed off board after placement phase
    why?
    - opponent can just cascade and pushed off the board
    - if there is forced cascade (from both ourselves or enemy), we might just fall off
    
    4. Friendly merge potential
    why? build height advantage earlier
    things to be aware: all same colours stack being too clustered
    
    - Things that hasn't been taken into consideration: Symmetry of the board

[33mcommit 0eafe6baa3ea0edf6882a16e466fb9af35dd801e[m
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Sat Apr 18 10:55:15 2026 +0000

    finalising minmax with alpha beta pruning

[33mcommit f514d8a98b4026526dc98a9b3c5b766561510746[m
Merge: 79cb910 1929cff
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Sat Apr 18 10:34:22 2026 +0000

    Merge remote-tracking branch 'origin/main' into amanda_minmax

[33mcommit 79cb9104cd858fdd34860d1dfd0a3779ca1d0d57[m
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Sat Apr 18 10:19:52 2026 +0000

    try changing placement

[33mcommit 1929cffa37950650b44138c0622bd0944d0ddc5f[m[33m ([m[1;31morigin/main[m[33m, [m[1;32mmain[m[33m)[m
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Sat Apr 18 20:16:46 2026 +1000

    add team.py

[33mcommit 8c625b884d2bf6e3fd76ffb388d5be9617163ad0[m
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Sat Apr 18 10:14:41 2026 +0000

    d=3, simple heur

[33mcommit 618e6f91cab217f483d75f493616fc82b72bf521[m
Merge: c90eb81 8cb8379
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Sat Apr 18 09:58:26 2026 +0000

    removing pycache

[33mcommit c90eb810499e50cb681b20ed4e4f5abe3432f06d[m
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Sat Apr 18 09:53:44 2026 +0000

    d=4, minmax, simple heuristic

[33mcommit 8cb83792392d8b527815b351aef1485e2d8b3541[m
Author: JiaYiTong23 <jttong2@student.unimelb.edu.au>
Date:   Sat Apr 18 00:48:44 2026 +0000

    Add .gitignore and READEME

[33mcommit 87ba6a75f83fa10ad41889fd1e4aa9b4724133e9[m
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Thu Apr 16 07:14:39 2026 +0000

    initial commit, added comments and ideas

[33mcommit 34710b2c320339dfa44e62327b46f345e5e60183[m
Author: eamandaa <eeamanda2000@gmail.com>
Date:   Tue Apr 14 02:00:25 2026 +0000

    Initial commit

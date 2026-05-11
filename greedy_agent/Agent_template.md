__REPLACE the FILE NAME with the agent.md and PUT it in each agent folder__

# Algorithm and Data Structure used 
- greedy search on agent side 
- only given additional information to guide the piece on the board 
- no further look down to other ply
## Placement phase
1. greedy search 

## Play phase
1. greedy search 

# Heurisitc description
- describe what have u considered in your heurisitc/evaluation function/ move order
- why? 
## Placement phase
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


## Play phase
1. height
2. agent being on the centre
3. penalise being at the edge
4. eating an enemy
5. kill through cascade
6. lost through cascade


# Known weaknesse
- can't think deeper on 
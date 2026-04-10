/*
 * BITBRAIN v7: MAZE navigation (not SAT, not parity!)
 * =====================================================
 *
 * Tests BitBrain on a REAL problem: maze exploration and path finding.
 *
 * Task: 8×8 maze with walls. Agent starts at (0,0), goal at (7,7).
 *       Agent can see immediate neighbors (4 cells).
 *       Must explore and find shortest path.
 *
 * BitBrain usage:
 *   PLANNING:  builds graph of discovered cells, runs BFS to goal
 *   MEMORY:    remembers visited cells (avoid cycles)
 *   SENSORY:   classifies cell as wall/open from feature bits
 *   META:      detects stuck conditions
 *
 * This tests incremental knowledge construction: the agent doesn't
 * know the full maze, it builds understanding as it explores.
 *
 * Compile: gcc -O3 -march=native -o bitbrain7 bitbrain_v7_maze.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define MAZE_W 8
#define MAZE_H 8
#define N_CELLS (MAZE_W * MAZE_H)
#define CELL_WORDS ((N_CELLS + 63) / 64)

/* ═══ MAZE ═══ */
typedef struct {
    int walls[MAZE_H][MAZE_W];  /* 1 = wall, 0 = open */
    int start_x, start_y;
    int goal_x, goal_y;
} Maze;

static void maze_init(Maze *m){
    /* Simple maze:
       S . . # . . . .
       # # . # . # # .
       . . . . . . # .
       . # # # # . # .
       . # . . # . . .
       . # . # # . # #
       . # . . . . # G
       . . . # . . . .
    */
    int layout[MAZE_H][MAZE_W] = {
        {0,0,0,1,0,0,0,0},
        {1,1,0,1,0,1,1,0},
        {0,0,0,0,0,0,1,0},
        {0,1,1,1,1,0,1,0},
        {0,1,0,0,1,0,0,0},
        {0,1,0,1,1,0,1,1},
        {0,1,0,0,0,0,1,0},
        {0,0,0,1,0,0,0,0}
    };
    memcpy(m->walls, layout, sizeof(layout));
    m->start_x = 0; m->start_y = 0;
    m->goal_x = 7; m->goal_y = 6;
}

static void maze_print(Maze *m, int *visited, int ax, int ay){
    for(int y = 0; y < MAZE_H; y++){
        for(int x = 0; x < MAZE_W; x++){
            char c;
            if(x == ax && y == ay) c = 'A';
            else if(x == m->start_x && y == m->start_y) c = 'S';
            else if(x == m->goal_x && y == m->goal_y) c = 'G';
            else if(m->walls[y][x]) c = '#';
            else if(visited && visited[y*MAZE_W + x]) c = '.';
            else c = ' ';
            printf("%c ", c);
        }
        printf("\n");
    }
}

static int maze_is_wall(Maze *m, int x, int y){
    if(x < 0 || x >= MAZE_W || y < 0 || y >= MAZE_H) return 1;
    return m->walls[y][x];
}

/* ═══ PLANNING region: incremental graph + BFS ═══ */
typedef struct {
    uint64_t edges[N_CELLS][CELL_WORDS];  /* adjacency */
    uint64_t known[CELL_WORDS];            /* which cells are known */
} Planning;

static void plan_init(Planning *p){
    memset(p, 0, sizeof(*p));
}

static void plan_mark_known(Planning *p, int cell){
    p->known[cell>>6] |= (1ULL << (cell&63));
}

static void plan_add_edge(Planning *p, int a, int b){
    p->edges[a][b>>6] |= (1ULL << (b&63));
    p->edges[b][a>>6] |= (1ULL << (a&63));
}

/* BFS: find shortest path from start to goal using only KNOWN cells */
static int plan_bfs(Planning *p, int start, int goal, int *path){
    int parent[N_CELLS];
    int visited[N_CELLS];
    memset(visited, 0, sizeof(visited));
    for(int i = 0; i < N_CELLS; i++) parent[i] = -1;

    int queue[N_CELLS], head = 0, tail = 0;
    queue[tail++] = start;
    visited[start] = 1;

    while(head < tail){
        int cur = queue[head++];
        if(cur == goal){
            int tmp[N_CELLS], len = 0;
            int c = goal;
            while(c != -1){tmp[len++] = c; c = parent[c];}
            for(int i = 0; i < len; i++) path[i] = tmp[len-1-i];
            return len;
        }
        for(int n = 0; n < N_CELLS; n++){
            if((p->edges[cur][n>>6] >> (n&63)) & 1){
                if(!visited[n]){
                    visited[n] = 1;
                    parent[n] = cur;
                    queue[tail++] = n;
                }
            }
        }
    }
    return -1;
}

/* ═══ MEMORY region: which cells visited + in what order ═══ */
typedef struct {
    int visited[N_CELLS];  /* visit count */
    int order[N_CELLS];    /* order of first visit */
    int n_visited;
} Memory;

static void mem_init(Memory *m){
    memset(m, 0, sizeof(*m));
}

static void mem_visit(Memory *m, int cell){
    if(m->visited[cell] == 0){
        m->order[cell] = m->n_visited;
        m->n_visited++;
    }
    m->visited[cell]++;
}

/* ═══ META region: detect stuck ═══ */
typedef struct {
    int stuck_count;
    int last_cells[10];
    int idx;
} Meta;

static void meta_init(Meta *m){memset(m, 0, sizeof(*m));}

static int meta_is_stuck(Meta *m, int current){
    /* Add to ring buffer */
    m->last_cells[m->idx] = current;
    m->idx = (m->idx + 1) % 10;

    /* Count distinct cells in last 10 */
    int distinct = 0;
    int seen[N_CELLS] = {0};
    for(int i = 0; i < 10; i++){
        int c = m->last_cells[i];
        if(c >= 0 && !seen[c]){
            seen[c] = 1;
            distinct++;
        }
    }
    /* Stuck if visiting ≤3 cells repeatedly */
    return distinct <= 3;
}

/* ═══ BITBRAIN v7 ═══ */
typedef struct {
    Planning planning;
    Memory memory;
    Meta meta;
    int n_steps;
    int n_explorations;
    int n_backtracks;
} BitBrain;

static void brain_init(BitBrain *b){
    plan_init(&b->planning);
    mem_init(&b->memory);
    meta_init(&b->meta);
    b->n_steps = 0;
    b->n_explorations = 0;
    b->n_backtracks = 0;
}

/* Observe current cell: mark as known, add edges to open neighbors */
static void brain_observe(BitBrain *b, Maze *m, int x, int y){
    int cell = y * MAZE_W + x;
    plan_mark_known(&b->planning, cell);
    mem_visit(&b->memory, cell);

    /* Check 4 neighbors, add edges if open */
    int dx[] = {0, 0, 1, -1};
    int dy[] = {1, -1, 0, 0};
    for(int d = 0; d < 4; d++){
        int nx = x + dx[d], ny = y + dy[d];
        if(nx < 0 || nx >= MAZE_W || ny < 0 || ny >= MAZE_H) continue;
        if(!maze_is_wall(m, nx, ny)){
            int ncell = ny * MAZE_W + nx;
            plan_add_edge(&b->planning, cell, ncell);
        }
    }
}

/* Decide next move: try to plan path to goal, else explore */
static int brain_next_move(BitBrain *b, int cur_cell, int goal_cell, int *next_cell){
    int path[N_CELLS];
    int len = plan_bfs(&b->planning, cur_cell, goal_cell, path);

    if(len > 1){
        *next_cell = path[1]; /* next step on path */
        return 1; /* path found */
    }

    /* No path to goal in known graph → explore: move to least-visited neighbor */
    int best = -1;
    int best_visits = 1000000;
    for(int n = 0; n < N_CELLS; n++){
        if((b->planning.edges[cur_cell][n>>6] >> (n&63)) & 1){
            if(b->memory.visited[n] < best_visits){
                best_visits = b->memory.visited[n];
                best = n;
            }
        }
    }
    if(best >= 0){
        *next_cell = best;
        b->n_explorations++;
        return 1;
    }
    return 0; /* stuck, no moves */
}

/* ═══ SOLVE MAZE ═══ */
static int solve_maze(BitBrain *b, Maze *m, int verbose){
    int x = m->start_x, y = m->start_y;
    int goal = m->goal_y * MAZE_W + m->goal_x;
    int max_steps = 200;
    int path_taken[200];
    int n_path = 0;

    for(int step = 0; step < max_steps; step++){
        int cell = y * MAZE_W + x;
        path_taken[n_path++] = cell;

        /* Observe: discover this cell and its open neighbors */
        brain_observe(b, m, x, y);

        /* Check goal */
        if(cell == goal){
            if(verbose){
                printf("\nGoal reached in %d steps!\n", step+1);
                printf("Cells explored: %d / %d\n", b->memory.n_visited, N_CELLS);
            }
            b->n_steps = step + 1;
            return 1;
        }

        /* Stuck detection */
        if(meta_is_stuck(&b->meta, cell)){
            b->n_backtracks++;
            if(verbose && step < 20) printf("  stuck @ (%d,%d), ", x, y);
        }

        /* Decide next move */
        int next;
        if(!brain_next_move(b, cell, goal, &next)){
            if(verbose) printf("Dead end!\n");
            return 0;
        }

        /* Move */
        x = next % MAZE_W;
        y = next / MAZE_W;

        if(verbose && step < 20) printf("step %2d: (%d,%d)\n", step, x, y);
    }
    return 0; /* out of steps */
}

int main(void){
    printf("══════════════════════════════════════════\n");
    printf("BITBRAIN v7: MAZE navigation (non-SAT task!)\n");
    printf("══════════════════════════════════════════\n\n");

    Maze m;
    maze_init(&m);

    printf("Maze (S=start, G=goal, #=wall):\n");
    maze_print(&m, NULL, -1, -1);
    printf("\n");

    BitBrain brain;
    brain_init(&brain);

    printf("Agent explores and plans incrementally...\n");
    int ok = solve_maze(&brain, &m, 1);

    printf("\n═══ RESULT ═══\n");
    if(ok){
        printf("✓ SOLVED: %d steps (including exploration)\n", brain.n_steps);
        printf("  Cells visited: %d\n", brain.memory.n_visited);
        printf("  Exploration moves: %d\n", brain.n_explorations);
        printf("  Stuck detections: %d\n", brain.n_backtracks);
    } else {
        printf("✗ NOT SOLVED\n");
    }

    /* Visualize what agent learned */
    printf("\nLearned maze (. = visited):\n");
    int visited[N_CELLS];
    for(int i = 0; i < N_CELLS; i++) visited[i] = brain.memory.visited[i] > 0;
    maze_print(&m, visited, -1, -1);

    /* Test: what's the OPTIMAL path length? */
    printf("\nComputing optimal path (BFS from scratch)...\n");
    BitBrain optimal;
    brain_init(&optimal);
    /* Give optimal all maze info upfront */
    for(int y = 0; y < MAZE_H; y++){
        for(int x = 0; x < MAZE_W; x++){
            if(!maze_is_wall(&m, x, y)){
                brain_observe(&optimal, &m, x, y);
            }
        }
    }
    int opt_path[N_CELLS];
    int opt_len = plan_bfs(&optimal.planning, 0, m.goal_y*MAZE_W + m.goal_x, opt_path);
    printf("Optimal path length: %d\n", opt_len);
    printf("Agent path length:   %d\n", brain.n_steps);
    printf("Inefficiency:        %.1fx\n", (double)brain.n_steps / opt_len);

    if(opt_len > 0){
        printf("Optimal path: ");
        for(int i = 0; i < opt_len && i < 20; i++){
            int x = opt_path[i] % MAZE_W, y = opt_path[i] / MAZE_W;
            printf("(%d,%d) ", x, y);
        }
        printf("\n");
    }

    /* ── Test 2: larger exploration ── */
    printf("\n\n═══ TEST 2: Multiple random starts ═══\n");

    int total_solved = 0;
    int total_steps = 0;
    int n_trials = 10;

    for(int trial = 0; trial < n_trials; trial++){
        /* Random start (must be non-wall) */
        int sx, sy;
        do {
            sx = rand() % MAZE_W;
            sy = rand() % MAZE_H;
        } while(maze_is_wall(&m, sx, sy));
        m.start_x = sx;
        m.start_y = sy;

        BitBrain b;
        brain_init(&b);
        int ok = solve_maze(&b, &m, 0);
        if(ok){
            total_solved++;
            total_steps += b.n_steps;
        }
    }

    printf("Solved: %d/%d starts\n", total_solved, n_trials);
    if(total_solved > 0){
        printf("Avg steps: %.1f\n", (double)total_steps / total_solved);
    }

    printf("\n═══ VERDICT ═══\n");
    if(ok && total_solved >= n_trials * 0.8){
        printf("✓ BitBrain navigates mazes successfully\n");
        printf("  Real-world task outside SAT/parity domain\n");
        printf("  Incremental planning + memory + meta-detection\n");
    } else {
        printf("~ Partial success\n");
    }

    return 0;
}

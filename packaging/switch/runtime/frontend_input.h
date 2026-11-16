#pragma once
#include <stdbool.h>

enum { SHOW_GAME = 1, SHOW_DETAILS = 2, EXIT_GAME = 4 };

/* A fresh Plus edge exits only from the diagnostic console. */
static inline unsigned ngb_view_action(bool game, bool stopped, bool a, bool b, bool plus)
{
    if (game) return b || (plus && stopped) ? SHOW_DETAILS : 0;
    if (plus) return EXIT_GAME;
    return a ? SHOW_GAME : 0;
}

#define _GNU_SOURCE

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>

typedef struct SDL_Window SDL_Window;
typedef uint32_t Uint32;

typedef struct SDL_DisplayMode {
    Uint32 format;
    int w;
    int h;
    int refresh_rate;
    void *driverdata;
} SDL_DisplayMode;

enum {
    FORCED_WIDTH = 640,
    FORCED_HEIGHT = 480
};

static void *next_symbol(const char *name)
{
    void *symbol = dlsym(RTLD_NEXT, name);

    if (symbol == NULL) {
        fprintf(stderr, "[resolution_fix] SDL symbol not found: %s\n", name);
    }

    return symbol;
}

SDL_Window *SDL_CreateWindow(const char *title, int x, int y,
                             int width, int height, Uint32 flags)
{
    typedef SDL_Window *(*function_type)(const char *, int, int, int, int,
                                         Uint32);
    static function_type real_function;

    if (real_function == NULL) {
        real_function = (function_type)next_symbol("SDL_CreateWindow");
    }
    if (real_function == NULL) {
        return NULL;
    }

    fprintf(stderr,
            "[resolution_fix] SDL_CreateWindow %dx%d -> %dx%d\n",
            width, height, FORCED_WIDTH, FORCED_HEIGHT);
    return real_function(title, x, y, FORCED_WIDTH, FORCED_HEIGHT, flags);
}

void SDL_SetWindowSize(SDL_Window *window, int width, int height)
{
    typedef void (*function_type)(SDL_Window *, int, int);
    static function_type real_function;

    if (real_function == NULL) {
        real_function = (function_type)next_symbol("SDL_SetWindowSize");
    }
    if (real_function == NULL) {
        return;
    }

    fprintf(stderr,
            "[resolution_fix] SDL_SetWindowSize %dx%d -> %dx%d\n",
            width, height, FORCED_WIDTH, FORCED_HEIGHT);
    real_function(window, FORCED_WIDTH, FORCED_HEIGHT);
}

int SDL_SetWindowDisplayMode(SDL_Window *window, const SDL_DisplayMode *mode)
{
    typedef int (*function_type)(SDL_Window *, const SDL_DisplayMode *);
    static function_type real_function;
    SDL_DisplayMode forced_mode;

    if (real_function == NULL) {
        real_function = (function_type)next_symbol("SDL_SetWindowDisplayMode");
    }
    if (real_function == NULL) {
        return -1;
    }
    if (mode == NULL) {
        return real_function(window, NULL);
    }

    forced_mode = *mode;
    forced_mode.w = FORCED_WIDTH;
    forced_mode.h = FORCED_HEIGHT;
    fprintf(stderr,
            "[resolution_fix] SDL_SetWindowDisplayMode %dx%d -> %dx%d\n",
            mode->w, mode->h, FORCED_WIDTH, FORCED_HEIGHT);
    return real_function(window, &forced_mode);
}

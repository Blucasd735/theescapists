#define _GNU_SOURCE

#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct SDL_Window SDL_Window;
typedef uint32_t Uint32;
typedef int32_t Sint32;

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

enum {
    SDL_KEYDOWN = 0x300,
    SDL_KEYUP = 0x301,
    SDLK_F10 = 0x40000043,
    SDLK_F11 = 0x40000044,
    SDLK_RIGHT = 0x4000004f,
    SDLK_LEFT = 0x40000050,
    SDLK_DOWN = 0x40000051,
    SDLK_UP = 0x40000052,
    SDL_SCANCODE_1 = 30
};

typedef struct SDL_Keysym {
    int scancode;
    Sint32 sym;
    uint16_t mod;
    Uint32 unused;
} SDL_Keysym;

typedef struct SDL_KeyboardEvent {
    Uint32 type;
    Uint32 timestamp;
    Uint32 windowID;
    uint8_t state;
    uint8_t repeat;
    uint8_t padding2;
    uint8_t padding3;
    SDL_Keysym keysym;
} SDL_KeyboardEvent;

typedef union SDL_Event {
    Uint32 type;
    SDL_KeyboardEvent key;
    uint8_t padding[56];
} SDL_Event;

static int current_item_slot;

static int environment_integer(const char *name, int default_value,
                               int minimum, int maximum)
{
    const char *text_value = getenv(name);
    char *end = NULL;
    long value;

    if (text_value == NULL || *text_value == '\0') {
        return default_value;
    }

    value = strtol(text_value, &end, 10);
    if (end == text_value || *end != '\0' || value < minimum ||
        value > maximum) {
        fprintf(stderr,
                "[control_fix] invalid %s=%s; using %d\n",
                name, text_value, default_value);
        return default_value;
    }

    return (int)value;
}

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

int SDL_PollEvent(SDL_Event *event)
{
    typedef int (*function_type)(SDL_Event *);
    static function_type real_function;

    if (real_function == NULL) {
        real_function = (function_type)next_symbol("SDL_PollEvent");
    }
    if (real_function == NULL) {
        return 0;
    }

    while (real_function(event)) {
        if (event == NULL ||
            (event->type != SDL_KEYDOWN && event->type != SDL_KEYUP)) {
            return 1;
        }

        if (environment_integer("KEY_TRACE", 0, 0, 1) != 0 &&
            event->type == SDL_KEYDOWN && event->key.repeat == 0) {
            fprintf(stderr,
                    "[key_trace] sym=%d scancode=%d window=%u\n",
                    event->key.keysym.sym, event->key.keysym.scancode,
                    event->key.windowID);
        }

        if (environment_integer("FILTER_ARROW_KEYS", 0, 0, 1) != 0 &&
            (event->key.keysym.sym == SDLK_LEFT ||
             event->key.keysym.sym == SDLK_RIGHT ||
             event->key.keysym.sym == SDLK_UP ||
             event->key.keysym.sym == SDLK_DOWN)) {
            if (event->type == SDL_KEYDOWN && event->key.repeat == 0) {
                fprintf(stderr,
                        "[key_filter] blocked arrow sym=%d scancode=%d\n",
                        event->key.keysym.sym, event->key.keysym.scancode);
            }
            continue;
        }

        if (event->key.keysym.sym == SDLK_F10 ||
            event->key.keysym.sym == SDLK_F11) {
            int maximum_slot = environment_integer("ITEM_SLOT_MAX", 6, 1, 9);

            if (current_item_slot == 0) {
                current_item_slot = environment_integer("ITEM_SLOT_START", 1,
                                                        1, maximum_slot);
            }

            if (event->type == SDL_KEYDOWN && event->key.repeat == 0) {
                if (event->key.keysym.sym == SDLK_F10) {
                    current_item_slot++;
                    if (current_item_slot > maximum_slot) {
                        current_item_slot = 1;
                    }
                } else {
                    current_item_slot--;
                    if (current_item_slot < 1) {
                        current_item_slot = maximum_slot;
                    }
                }
                fprintf(stderr, "[item_cycle] slot=%d max=%d\n",
                        current_item_slot, maximum_slot);
            }

            event->key.keysym.sym = '0' + current_item_slot;
            event->key.keysym.scancode = SDL_SCANCODE_1 + current_item_slot - 1;
            return 1;
        }

        return 1;
    }

    return 0;
}

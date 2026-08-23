import os
import sys
import json
import math
import random
import traceback

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *


# ============================================================
# CONFIG
# ============================================================

WIDTH = 1280
HEIGHT = 720

WORLD_SIZE = 32
WORLD_HEIGHT = 24

PLAYER_HEIGHT = 1.8
PLAYER_RADIUS = 0.30

WALK_SPEED = 5.0
JUMP_SPEED = 7.5
GRAVITY = 20.0

MIN_SENSITIVITY = 0.03
MAX_SENSITIVITY = 0.40
DEFAULT_SENSITIVITY = 0.12

RENDER_DISTANCE = 32

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

WORLDS_DIR = os.path.join(
    BASE_DIR,
    "worlds"
)

os.makedirs(WORLDS_DIR, exist_ok=True)


# ============================================================
# BLOCKS
# ============================================================

AIR = 0
GRASS = 1
DIRT = 2
STONE = 3
WOOD = 4
LEAVES = 5
SIGN = 6

BLOCK_COLORS = {
    GRASS: (0.30, 0.72, 0.20),
    DIRT: (0.48, 0.28, 0.12),
    STONE: (0.48, 0.48, 0.48),
    WOOD: (0.52, 0.31, 0.12),
    LEAVES: (0.12, 0.52, 0.15),
    SIGN: (0.62, 0.38, 0.14),
}


# ============================================================
# GLOBAL STATE
# ============================================================

world = {}

current_world = None
current_seed = 0

player_x = 16.5
player_y = 10.0
player_z = 16.5

velocity_y = 0.0
grounded = False

yaw = 0.0
pitch = 0.0

sensitivity = DEFAULT_SENSITIVITY

selected_block = GRASS

game_state = "menu"
menu_page = "main"
pause_page = "main"

world_names = []
selected_world = 0

world_name_input = ""

screen_w = WIDTH
screen_h = HEIGHT

font = None
big_font = None


# ============================================================
# WORLD FILES
# ============================================================

def clean_name(name):
    """Make a safe filename."""

    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-"

    result = ""

    for char in str(name):
        if char in allowed:
            result += char

    result = result.strip()

    if not result:
        result = "World"

    return result


def world_path(name):
    return os.path.join(
        WORLDS_DIR,
        clean_name(name) + ".json"
    )


def refresh_worlds():
    global world_names

    world_names = []

    try:
        for filename in os.listdir(WORLDS_DIR):

            if filename.lower().endswith(".json"):

                name = filename[:-5]

                if name:
                    world_names.append(name)

    except Exception:
        pass

    world_names.sort(
        key=lambda x: x.lower()
    )


# ============================================================
# TERRAIN
# ============================================================

def terrain_height(x, z, seed):

    value = (
        math.sin(x * 0.28 + seed * 0.001) * 2.0
        +
        math.sin(z * 0.23 + seed * 0.002) * 2.0
        +
        math.sin((x + z) * 0.13) * 1.5
    )

    return max(
        2,
        min(
            WORLD_HEIGHT - 5,
            int(7 + value)
        )
    )


def set_block(x, y, z, block):

    if not (
        0 <= x < WORLD_SIZE
        and
        0 <= y < WORLD_HEIGHT
        and
        0 <= z < WORLD_SIZE
    ):
        return

    if block == AIR:
        world.pop((x, y, z), None)
    else:
        world[(x, y, z)] = block


def get_block(x, y, z):

    return world.get(
        (x, y, z),
        AIR
    )


def make_tree(x, y, z):

    for i in range(4):
        set_block(
            x,
            y + i,
            z,
            WOOD
        )

    for dx in range(-2, 3):
        for dz in range(-2, 3):
            for dy in range(2, 4):

                if abs(dx) + abs(dz) <= 3:

                    set_block(
                        x + dx,
                        y + dy,
                        z + dz,
                        LEAVES
                    )


def generate_world(seed):

    world.clear()

    random.seed(seed)

    for x in range(WORLD_SIZE):

        for z in range(WORLD_SIZE):

            height = terrain_height(
                x,
                z,
                seed
            )

            for y in range(height + 1):

                if y == height:
                    block = GRASS

                elif y >= height - 3:
                    block = DIRT

                else:
                    block = STONE

                set_block(
                    x,
                    y,
                    z,
                    block
                )

    for x in range(2, WORLD_SIZE - 2):

        for z in range(2, WORLD_SIZE - 2):

            if random.random() < 0.035:

                h = terrain_height(
                    x,
                    z,
                    seed
                )

                make_tree(
                    x,
                    h + 1,
                    z
                )


# ============================================================
# PLAYER
# ============================================================

def set_spawn():

    global player_x
    global player_y
    global player_z
    global velocity_y
    global grounded

    x = WORLD_SIZE // 2
    z = WORLD_SIZE // 2

    y = terrain_height(
        x,
        z,
        current_seed
    ) + 1

    player_x = x + 0.5
    player_y = float(y)
    player_z = z + 0.5

    velocity_y = 0.0
    grounded = False


def collision(x, y, z):

    min_x = math.floor(
        x - PLAYER_RADIUS
    )

    max_x = math.floor(
        x + PLAYER_RADIUS
    )

    min_y = math.floor(y)

    max_y = math.floor(
        y + PLAYER_HEIGHT
    )

    min_z = math.floor(
        z - PLAYER_RADIUS
    )

    max_z = math.floor(
        z + PLAYER_RADIUS
    )

    for bx in range(
        min_x,
        max_x + 1
    ):

        for by in range(
            min_y,
            max_y + 1
        ):

            for bz in range(
                min_z,
                max_z + 1
            ):

                if get_block(
                    bx,
                    by,
                    bz
                ) != AIR:

                    return True

    return False


def move_player(dx, dy, dz):

    global player_x
    global player_y
    global player_z
    global grounded

    # X
    new_x = player_x + dx

    if not collision(
        new_x,
        player_y,
        player_z
    ):

        player_x = new_x

    # Z
    new_z = player_z + dz

    if not collision(
        player_x,
        player_y,
        new_z
    ):

        player_z = new_z

    # Y
    new_y = player_y + dy

    if not collision(
        player_x,
        new_y,
        player_z
    ):

        player_y = new_y
        return False

    if dy < 0:
        grounded = True

    return True


# ============================================================
# SAVE
# ============================================================

def save_current_world():

    if not current_world:
        return

    blocks = []

    for (x, y, z), block in world.items():

        blocks.append([
            x,
            y,
            z,
            block
        ])

    data = {
        "format": 1,

        "name": current_world,

        "seed": current_seed,

        "blocks": blocks,

        "player": {
            "x": player_x,
            "y": player_y,
            "z": player_z,
            "yaw": yaw,
            "pitch": pitch
        }
    }

    path = world_path(
        current_world
    )

    temp = path + ".tmp"

    try:

        with open(
            temp,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False
            )

        os.replace(
            temp,
            path
        )

        print(
            "Saved:",
            current_world
        )

    except Exception as error:

        print(
            "Save error:",
            error
        )

        try:
            if os.path.exists(temp):
                os.remove(temp)
        except Exception:
            pass


# ============================================================
# INVALID WORLD
# ============================================================

def make_angry_world(name):

    global current_seed
    global current_world

    current_world = name

    current_seed = random.randint(
        1,
        2_000_000_000
    )

    generate_world(
        current_seed
    )

    cx = WORLD_SIZE // 2
    cz = WORLD_SIZE // 2

    ground = terrain_height(
        cx,
        cz,
        current_seed
    ) + 1

    # Build a big sign.
    for x in range(
        cx - 8,
        cx + 9
    ):

        for y in range(
            ground,
            ground + 5
        ):

            set_block(
                x,
                y,
                cz,
                SIGN
            )

    global player_x
    global player_y
    global player_z

    player_x = cx + 0.5
    player_y = ground
    player_z = cz - 5

    save_current_world()


# ============================================================
# LOAD WORLD
# ============================================================

def load_world(name):

    global current_world
    global current_seed

    global player_x
    global player_y
    global player_z

    global yaw
    global pitch

    path = world_path(name)

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if not isinstance(
            data,
            dict
        ):
            raise ValueError(
                "JSON root is not an object."
            )

        seed = int(
            data["seed"]
        )

        blocks = data["blocks"]

        player = data["player"]

        if not isinstance(
            blocks,
            list
        ):
            raise ValueError(
                "Blocks are invalid."
            )

        if not isinstance(
            player,
            dict
        ):
            raise ValueError(
                "Player data is invalid."
            )

        new_world = {}

        for item in blocks:

            if (
                not isinstance(item, list)
                or
                len(item) != 4
            ):
                raise ValueError(
                    "Invalid block."
                )

            x = int(item[0])
            y = int(item[1])
            z = int(item[2])
            block = int(item[3])

            if not (
                0 <= x < WORLD_SIZE
                and
                0 <= y < WORLD_HEIGHT
                and
                0 <= z < WORLD_SIZE
            ):
                raise ValueError(
                    "Block outside world."
                )

            if block not in BLOCK_COLORS:
                raise ValueError(
                    "Unknown block."
                )

            new_world[
                (x, y, z)
            ] = block

        new_x = float(
            player["x"]
        )

        new_y = float(
            player["y"]
        )

        new_z = float(
            player["z"]
        )

        new_yaw = float(
            player.get(
                "yaw",
                0
            )
        )

        new_pitch = float(
            player.get(
                "pitch",
                0
            )
        )

        values = [
            new_x,
            new_y,
            new_z,
            new_yaw,
            new_pitch
        ]

        if not all(
            math.isfinite(v)
            for v in values
        ):
            raise ValueError(
                "Invalid number."
            )

        # Only replace the current world after
        # validation has succeeded.
        world.clear()

        world.update(
            new_world
        )

        current_world = name
        current_seed = seed

        player_x = new_x
        player_y = new_y
        player_z = new_z

        yaw = new_yaw

        pitch = max(
            -89,
            min(
                89,
                new_pitch
            )
        )

        print(
            "Loaded:",
            name
        )

        return True

    except Exception as error:

        print(
            "Invalid world:",
            name
        )

        print(
            "Reason:",
            error
        )

        make_angry_world(
            name
        )

        return True


# ============================================================
# CREATE WORLD
# ============================================================

def create_world(name):

    global current_world
    global current_seed

    name = clean_name(name)

    if not name:
        name = "New World"

    original = name
    number = 2

    while os.path.exists(
        world_path(name)
    ):

        name = (
            original
            +
            " "
            +
            str(number)
        )

        number += 1

    current_world = name

    current_seed = random.randint(
        1,
        2_000_000_000
    )

    generate_world(
        current_seed
    )

    set_spawn()

    save_current_world()

    return name


# ============================================================
# OPENGL SETUP
# ============================================================

def setup_opengl(w, h):

    global screen_w
    global screen_h

    screen_w = max(
        1,
        int(w)
    )

    screen_h = max(
        1,
        int(h)
    )

    glViewport(
        0,
        0,
        screen_w,
        screen_h
    )

    glMatrixMode(
        GL_PROJECTION
    )

    glLoadIdentity()

    gluPerspective(
        70,
        screen_w / screen_h,
        0.05,
        200
    )

    glMatrixMode(
        GL_MODELVIEW
    )

    glLoadIdentity()

    glEnable(
        GL_DEPTH_TEST
    )

    glEnable(
        GL_CULL_FACE
    )

    glEnable(
        GL_COLOR_MATERIAL
    )

    glEnable(
        GL_LIGHTING
    )

    glEnable(
        GL_LIGHT0
    )

    glLightfv(
        GL_LIGHT0,
        GL_POSITION,
        (50, 100, 50, 1)
    )

    glLightfv(
        GL_LIGHT0,
        GL_DIFFUSE,
        (1, 1, 1, 1)
    )

    glLightfv(
        GL_LIGHT0,
        GL_AMBIENT,
        (0.45, 0.45, 0.45, 1)
    )

    glClearColor(
        0.45,
        0.70,
        0.95,
        1
    )


# ============================================================
# 3D WORLD
# ============================================================

FACES = [
    (
        (0, 0, 1),
        [
            (0, 0, 1),
            (1, 0, 1),
            (1, 1, 1),
            (0, 1, 1)
        ]
    ),

    (
        (0, 0, -1),
        [
            (1, 0, 0),
            (0, 0, 0),
            (0, 1, 0),
            (1, 1, 0)
        ]
    ),

    (
        (-1, 0, 0),
        [
            (0, 0, 0),
            (0, 0, 1),
            (0, 1, 1),
            (0, 1, 0)
        ]
    ),

    (
        (1, 0, 0),
        [
            (1, 0, 1),
            (1, 0, 0),
            (1, 1, 0),
            (1, 1, 1)
        ]
    ),

    (
        (0, 1, 0),
        [
            (0, 1, 1),
            (1, 1, 1),
            (1, 1, 0),
            (0, 1, 0)
        ]
    ),

    (
        (0, -1, 0),
        [
            (0, 0, 0),
            (1, 0, 0),
            (1, 0, 1),
            (0, 0, 1)
        ]
    )
]


def draw_world():

    for (x, y, z), block in world.items():

        if abs(
            x - player_x
        ) > RENDER_DISTANCE:
            continue

        if abs(
            z - player_z
        ) > RENDER_DISTANCE:
            continue

        color = BLOCK_COLORS.get(
            block,
            (1, 1, 1)
        )

        glColor3f(
            *color
        )

        for normal, vertices in FACES:

            nx, ny, nz = normal

            if get_block(
                x + nx,
                y + ny,
                z + nz
            ) != AIR:
                continue

            glNormal3f(
                nx,
                ny,
                nz
            )

            glBegin(
                GL_QUADS
            )

            for vx, vy, vz in vertices:

                glVertex3f(
                    x + vx,
                    y + vy,
                    z + vz
                )

            glEnd()


# ============================================================
# RAYCAST
# ============================================================

def raycast():

    yaw_r = math.radians(yaw)
    pitch_r = math.radians(pitch)

    dx = (
        math.sin(yaw_r)
        *
        math.cos(pitch_r)
    )

    dy = math.sin(
        pitch_r
    )

    dz = (
        -math.cos(yaw_r)
        *
        math.cos(pitch_r)
    )

    eye_y = (
        player_y
        +
        PLAYER_HEIGHT * 0.85
    )

    previous = None

    for i in range(160):

        distance = i * 0.05

        x = player_x + dx * distance
        y = eye_y + dy * distance
        z = player_z + dz * distance

        block = (
            math.floor(x),
            math.floor(y),
            math.floor(z)
        )

        if get_block(*block) != AIR:

            return block, previous

        previous = block

    return None, None


# ============================================================
# BLOCK OUTLINE
# ============================================================

def draw_outline_3d(block):

    if block is None:
        return

    x, y, z = block

    vertices = [
        (x, y, z),
        (x + 1, y, z),
        (x + 1, y + 1, z),
        (x, y + 1, z),
        (x, y, z + 1),
        (x + 1, y, z + 1),
        (x + 1, y + 1, z + 1),
        (x, y + 1, z + 1)
    ]

    edges = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7)
    ]

    glDisable(
        GL_LIGHTING
    )

    glDisable(
        GL_CULL_FACE
    )

    glColor3f(
        1,
        1,
        1
    )

    glLineWidth(
        2
    )

    glBegin(
        GL_LINES
    )

    for a, b in edges:

        glVertex3fv(
            vertices[a]
        )

        glVertex3fv(
            vertices[b]
        )

    glEnd()

    glEnable(
        GL_CULL_FACE
    )

    glEnable(
        GL_LIGHTING
    )


# ============================================================
# 2D UI
# ============================================================

def begin_ui():

    glDisable(
        GL_DEPTH_TEST
    )

    glDisable(
        GL_LIGHTING
    )

    glDisable(
        GL_CULL_FACE
    )

    glEnable(
        GL_BLEND
    )

    glBlendFunc(
        GL_SRC_ALPHA,
        GL_ONE_MINUS_SRC_ALPHA
    )

    glMatrixMode(
        GL_PROJECTION
    )

    glPushMatrix()

    glLoadIdentity()

    # Top-left coordinate system.
    glOrtho(
        0,
        screen_w,
        screen_h,
        0,
        -1,
        1
    )

    glMatrixMode(
        GL_MODELVIEW
    )

    glPushMatrix()

    glLoadIdentity()


def end_ui():

    glMatrixMode(
        GL_MODELVIEW
    )

    glPopMatrix()

    glMatrixMode(
        GL_PROJECTION
    )

    glPopMatrix()

    glMatrixMode(
        GL_MODELVIEW
    )

    glDisable(
        GL_BLEND
    )

    glEnable(
        GL_DEPTH_TEST
    )

    glEnable(
        GL_CULL_FACE
    )

    glEnable(
        GL_LIGHTING
    )


def rect(x, y, w, h, color):

    glColor4f(
        *color
    )

    glBegin(
        GL_QUADS
    )

    glVertex2f(
        x,
        y
    )

    glVertex2f(
        x + w,
        y
    )

    glVertex2f(
        x + w,
        y + h
    )

    glVertex2f(
        x,
        y + h
    )

    glEnd()


# ============================================================
# TEXT
# ============================================================

def draw_text(
    text,
    x,
    y,
    color=(255, 255, 255),
    center=False,
    big=False
):
    """
    Draw text using a Pygame surface.

    The important part is that the surface is NOT flipped
    before uploading to OpenGL.

    The texture coordinates are also deliberately arranged
    to match the normal Pygame image orientation.
    """

    use_font = (
        big_font
        if big
        else font
    )

    surface = use_font.render(
        str(text),
        True,
        color
    )

    surface = surface.convert_alpha()

    w = surface.get_width()
    h = surface.get_height()

    if center:
        x -= w / 2

    # No vertical flip here.
    pixels = pygame.image.tostring(
        surface,
        "RGBA",
        False
    )

    texture = glGenTextures(
        1
    )

    glBindTexture(
        GL_TEXTURE_2D,
        texture
    )

    glTexParameteri(
        GL_TEXTURE_2D,
        GL_TEXTURE_MIN_FILTER,
        GL_LINEAR
    )

    glTexParameteri(
        GL_TEXTURE_2D,
        GL_TEXTURE_MAG_FILTER,
        GL_LINEAR
    )

    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_RGBA,
        w,
        h,
        0,
        GL_RGBA,
        GL_UNSIGNED_BYTE,
        pixels
    )

    glEnable(
        GL_TEXTURE_2D
    )

    glColor4f(
        1,
        1,
        1,
        1
    )

    glBegin(
        GL_QUADS
    )

    # Top-left
    glTexCoord2f(
        0,
        0
    )

    glVertex2f(
        x,
        y
    )

    # Top-right
    glTexCoord2f(
        1,
        0
    )

    glVertex2f(
        x + w,
        y
    )

    # Bottom-right
    glTexCoord2f(
        1,
        1
    )

    glVertex2f(
        x + w,
        y + h
    )

    # Bottom-left
    glTexCoord2f(
        0,
        1
    )

    glVertex2f(
        x,
        y + h
    )

    glEnd()

    glDisable(
        GL_TEXTURE_2D
    )

    glBindTexture(
        GL_TEXTURE_2D,
        0
    )

    glDeleteTextures(
        [texture]
    )


# ============================================================
# BUTTON
# ============================================================

def button(
    text,
    x,
    y,
    w,
    h,
    mouse
):

    mx, my = mouse

    hovered = (
        x <= mx <= x + w
        and
        y <= my <= y + h
    )

    if hovered:

        color = (
            0.25,
            0.65,
            0.25,
            1
        )

    else:

        color = (
            0.10,
            0.32,
            0.10,
            1
        )

    rect(
        x,
        y,
        w,
        h,
        color
    )

    glColor3f(
        0.75,
        0.95,
        0.75
    )

    glLineWidth(
        2
    )

    glBegin(
        GL_LINE_LOOP
    )

    glVertex2f(
        x,
        y
    )

    glVertex2f(
        x + w,
        y
    )

    glVertex2f(
        x + w,
        y + h
    )

    glVertex2f(
        x,
        y + h
    )

    glEnd()

    draw_text(
        text,
        x + w / 2,
        y + (
            h -
            font.get_height()
        ) / 2,
        center=True
    )

    return hovered


# ============================================================
# PANORAMA
# ============================================================

def draw_panorama():

    # Sky
    rect(
        0,
        0,
        screen_w,
        screen_h,
        (
            0.15,
            0.38,
            0.68,
            1
        )
    )

    # Sun
    rect(
        screen_w * 0.72,
        90,
        90,
        90,
        (
            1.0,
            0.85,
            0.30,
            1
        )
    )

    # Mountains
    glColor4f(
        0.10,
        0.25,
        0.12,
        1
    )

    glBegin(
        GL_TRIANGLES
    )

    for i in range(-2, 10):

        x = i * screen_w / 8

        glVertex2f(
            x,
            screen_h * 0.72
        )

        glVertex2f(
            x + screen_w / 8,
            screen_h * 0.35
        )

        glVertex2f(
            x + screen_w / 4,
            screen_h * 0.72
        )

    glEnd()

    # Ground
    rect(
        0,
        screen_h * 0.70,
        screen_w,
        screen_h * 0.30,
        (
            0.10,
            0.30,
            0.10,
            1
        )
    )

    # Dark overlay
    rect(
        0,
        0,
        screen_w,
        screen_h,
        (
            0,
            0,
            0,
            0.25
        )
    )


# ============================================================
# MAIN MENU
# ============================================================

def draw_main_menu():

    begin_ui()

    draw_panorama()

    draw_text(
        "PYVOXELCRAFT",
        screen_w / 2,
        90,
        center=True,
        big=True
    )

    draw_text(
        "A Pygame + PyOpenGL voxel game",
        screen_w / 2,
        160,
        center=True
    )

    mouse = pygame.mouse.get_pos()

    button(
        "PLAY",
        screen_w / 2 - 180,
        240,
        360,
        60,
        mouse
    )

    button(
        "QUIT",
        screen_w / 2 - 180,
        320,
        360,
        60,
        mouse
    )

    end_ui()


# ============================================================
# WORLD SELECT
# ============================================================

def draw_world_select():

    begin_ui()

    draw_panorama()

    draw_text(
        "SELECT WORLD",
        screen_w / 2,
        50,
        center=True,
        big=True
    )

    if not world_names:

        draw_text(
            "No worlds yet.",
            screen_w / 2,
            150,
            center=True
        )

    y = 140

    for i, name in enumerate(
        world_names[:7]
    ):

        if i == selected_world:

            rect(
                screen_w / 2 - 280,
                y,
                560,
                52,
                (
                    0.25,
                    0.60,
                    0.25,
                    1
                )
            )

        else:

            rect(
                screen_w / 2 - 280,
                y,
                560,
                52,
                (
                    0.08,
                    0.18,
                    0.08,
                    0.95
                )
            )

        draw_text(
            name,
            screen_w / 2,
            y + 13,
            center=True
        )

        y += 62

    mouse = pygame.mouse.get_pos()

    button(
        "PLAY",
        screen_w / 2 - 280,
        screen_h - 90,
        170,
        55,
        mouse
    )

    button(
        "CREATE WORLD",
        screen_w / 2 - 85,
        screen_h - 90,
        170,
        55,
        mouse
    )

    button(
        "BACK",
        screen_w / 2 + 110,
        screen_h - 90,
        170,
        55,
        mouse
    )

    end_ui()


# ============================================================
# CREATE WORLD SCREEN
# ============================================================

def draw_create_world():

    begin_ui()

    draw_panorama()

    draw_text(
        "CREATE WORLD",
        screen_w / 2,
        70,
        center=True,
        big=True
    )

    draw_text(
        "World Name",
        screen_w / 2 - 250,
        185
    )

    rect(
        screen_w / 2 - 250,
        220,
        500,
        55,
        (
            0.03,
            0.03,
            0.03,
            1
        )
    )

    display = (
        world_name_input
        if world_name_input
        else
        "Enter a world name..."
    )

    draw_text(
        display,
        screen_w / 2 - 230,
        235
    )

    mouse = pygame.mouse.get_pos()

    button(
        "CREATE",
        screen_w / 2 - 180,
        320,
        170,
        55,
        mouse
    )

    button(
        "BACK",
        screen_w / 2 + 10,
        320,
        170,
        55,
        mouse
    )

    end_ui()


# ============================================================
# PAUSE MENU
# ============================================================

def draw_pause():

    begin_ui()

    rect(
        0,
        0,
        screen_w,
        screen_h,
        (
            0,
            0,
            0,
            0.65
        )
    )

    draw_text(
        "GAME PAUSED",
        screen_w / 2,
        70,
        center=True,
        big=True
    )

    mouse = pygame.mouse.get_pos()

    if pause_page == "main":

        button(
            "RESUME",
            screen_w / 2 - 160,
            170,
            320,
            55,
            mouse
        )

        button(
            "CONTROLS",
            screen_w / 2 - 160,
            240,
            320,
            55,
            mouse
        )

        button(
            "SETTINGS",
            screen_w / 2 - 160,
            310,
            320,
            55,
            mouse
        )

        button(
            "SAVE AND QUIT",
            screen_w / 2 - 160,
            380,
            320,
            55,
            mouse
        )

    elif pause_page == "controls":

        controls = [
            "W / A / S / D  -  Move",
            "Mouse  -  Look",
            "SPACE  -  Jump",
            "LEFT CLICK  -  Break block",
            "RIGHT CLICK  -  Place block",
            "1  -  Grass",
            "2  -  Dirt",
            "3  -  Stone",
            "4  -  Wood",
            "5  -  Leaves",
            "ESC  -  Pause"
        ]

        y = 135

        for item in controls:

            draw_text(
                item,
                screen_w / 2,
                y,
                center=True
            )

            y += 34

        button(
            "BACK",
            screen_w / 2 - 120,
            screen_h - 70,
            240,
            50,
            mouse
        )

    elif pause_page == "settings":

        draw_text(
            f"Sensitivity: {sensitivity:.2f}",
            screen_w / 2,
            155,
            center=True
        )

        x = screen_w / 2 - 200
        y = 220
        w = 400

        rect(
            x,
            y,
            w,
            10,
            (
                0.15,
                0.15,
                0.15,
                1
            )
        )

        percentage = (
            sensitivity -
            MIN_SENSITIVITY
        ) / (
            MAX_SENSITIVITY -
            MIN_SENSITIVITY
        )

        rect(
            x,
            y,
            w * percentage,
            10,
            (
                0.30,
                0.80,
                0.30,
                1
            )
        )

        rect(
            x + w * percentage - 8,
            y - 8,
            16,
            26,
            (
                0.9,
                0.9,
                0.9,
                1
            )
        )

        draw_text(
            "Click the slider or use LEFT / RIGHT",
            screen_w / 2,
            270,
            center=True
        )

        button(
            "BACK",
            screen_w / 2 - 120,
            screen_h - 70,
            240,
            50,
            mouse
        )

    end_ui()


# ============================================================
# GAME DRAW
# ============================================================

def draw_game():

    glClear(
        GL_COLOR_BUFFER_BIT
        |
        GL_DEPTH_BUFFER_BIT
    )

    glMatrixMode(
        GL_MODELVIEW
    )

    glLoadIdentity()

    glRotatef(
        pitch,
        1,
        0,
        0
    )

    glRotatef(
        yaw,
        0,
        1,
        0
    )

    glTranslatef(
        -player_x,
        -(player_y + PLAYER_HEIGHT * 0.85),
        -player_z
    )

    draw_world()

    hit, _ = raycast()

    draw_outline_3d(
        hit
    )

    begin_ui()

    # Crosshair
    cx = screen_w / 2
    cy = screen_h / 2

    glColor3f(
        1,
        1,
        1
    )

    glLineWidth(
        2
    )

    glBegin(
        GL_LINES
    )

    glVertex2f(
        cx - 8,
        cy
    )

    glVertex2f(
        cx + 8,
        cy
    )

    glVertex2f(
        cx,
        cy - 8
    )

    glVertex2f(
        cx,
        cy + 8
    )

    glEnd()

    # Hotbar
    blocks = [
        GRASS,
        DIRT,
        STONE,
        WOOD,
        LEAVES
    ]

    slot = 48
    gap = 5

    total = (
        len(blocks) * slot
        +
        (len(blocks) - 1) * gap
    )

    start = (
        screen_w - total
    ) / 2

    for i, block in enumerate(blocks):

        x = start + i * (
            slot + gap
        )

        if block == selected_block:

            rect(
                x,
                screen_h - 65,
                slot,
                slot,
                (
                    0.95,
                    0.80,
                    0.15,
                    1
                )
            )

        else:

            rect(
                x,
                screen_h - 65,
                slot,
                slot,
                (
                    0.08,
                    0.08,
                    0.08,
                    1
                )
            )

        c = BLOCK_COLORS[
            block
        ]

        rect(
            x + 8,
            screen_h - 57,
            slot - 16,
            slot - 16,
            (
                c[0],
                c[1],
                c[2],
                1
            )
        )

    end_ui()


# ============================================================
# MOVEMENT
# ============================================================

def update_game(dt):

    global velocity_y
    global grounded
    global player_x
    global player_z
    global player_y

    keys = pygame.key.get_pressed()

    forward = 0
    strafe = 0

    if keys[K_w]:
        forward += 1

    if keys[K_s]:
        forward -= 1

    if keys[K_d]:
        strafe += 1

    if keys[K_a]:
        strafe -= 1

    length = math.sqrt(
        forward * forward
        +
        strafe * strafe
    )

    if length > 0:

        forward /= length
        strafe /= length

    yaw_r = math.radians(
        yaw
    )

    # Camera-relative movement.
    forward_x = math.sin(
        yaw_r
    )

    forward_z = -math.cos(
        yaw_r
    )

    right_x = math.cos(
        yaw_r
    )

    right_z = math.sin(
        yaw_r
    )

    dx = (
        forward_x * forward
        +
        right_x * strafe
    )

    dz = (
        forward_z * forward
        +
        right_z * strafe
    )

    move_player(
        dx * WALK_SPEED * dt,
        0,
        dz * WALK_SPEED * dt
    )

    velocity_y -= (
        GRAVITY * dt
    )

    old_grounded = grounded

    grounded = False

    hit = move_player(
        0,
        velocity_y * dt,
        0
    )

    if hit:

        if velocity_y < 0:

            grounded = True

        velocity_y = 0

    if player_y < -10:

        set_spawn()

    player_x = max(
        0.2,
        min(
            WORLD_SIZE - 0.2,
            player_x
        )
    )

    player_z = max(
        0.2,
        min(
            WORLD_SIZE - 0.2,
            player_z
        )
    )


# ============================================================
# GAME EVENTS
# ============================================================

def game_key(event):

    global game_state
    global pause_page
    global selected_block
    global velocity_y

    if event.key == K_ESCAPE:

        game_state = "paused"

        pause_page = "main"

        pygame.mouse.set_visible(
            True
        )

        pygame.event.set_grab(
            False
        )

    elif event.key == K_SPACE:

        if grounded:

            velocity_y = JUMP_SPEED

    elif event.key == K_1:
        selected_block = GRASS

    elif event.key == K_2:
        selected_block = DIRT

    elif event.key == K_3:
        selected_block = STONE

    elif event.key == K_4:
        selected_block = WOOD

    elif event.key == K_5:
        selected_block = LEAVES


# ============================================================
# MENU CLICK
# ============================================================

def menu_click(pos):

    global game_state
    global menu_page
    global selected_world
    global world_name_input

    mx, my = pos

    if menu_page == "main":

        if (
            screen_w / 2 - 180
            <= mx
            <= screen_w / 2 + 180
            and
            240 <= my <= 300
        ):

            refresh_worlds()

            selected_world = 0

            menu_page = "worlds"

        elif (
            screen_w / 2 - 180
            <= mx
            <= screen_w / 2 + 180
            and
            320 <= my <= 380
        ):

            pygame.quit()
            sys.exit()

    elif menu_page == "worlds":

        y = 140

        for i in range(
            min(7, len(world_names))
        ):

            if (
                screen_w / 2 - 280
                <= mx
                <= screen_w / 2 + 280
                and
                y <= my <= y + 52
            ):

                selected_world = i
                return

            y += 62

        # PLAY
        if (
            screen_w / 2 - 280
            <= mx
            <= screen_w / 2 - 110
            and
            screen_h - 90
            <= my
            <= screen_h - 35
        ):

            if world_names:

                name = world_names[
                    selected_world
                ]

                load_world(
                    name
                )

                game_state = "playing"

                pygame.mouse.set_visible(
                    False
                )

                pygame.event.set_grab(
                    True
                )

        # CREATE
        elif (
            screen_w / 2 - 85
            <= mx
            <= screen_w / 2 + 85
            and
            screen_h - 90
            <= my
            <= screen_h - 35
        ):

            world_name_input = ""

            menu_page = "create"

        # BACK
        elif (
            screen_w / 2 + 110
            <= mx
            <= screen_w / 2 + 280
            and
            screen_h - 90
            <= my
            <= screen_h - 35
        ):

            menu_page = "main"

    elif menu_page == "create":

        if (
            screen_w / 2 - 180
            <= mx
            <= screen_w / 2 - 10
            and
            320 <= my <= 375
        ):

            name = world_name_input.strip()

            if not name:
                name = "New World"

            create_world(
                name
            )

            refresh_worlds()

            game_state = "playing"

            pygame.mouse.set_visible(
                False
            )

            pygame.event.set_grab(
                True
            )

        elif (
            screen_w / 2 + 10
            <= mx
            <= screen_w / 2 + 180
            and
            320 <= my <= 375
        ):

            menu_page = "worlds"


# ============================================================
# PAUSE CLICK
# ============================================================

def pause_click(pos):

    global game_state
    global pause_page
    global sensitivity
    global menu_page

    mx, my = pos

    if pause_page == "main":

        if (
            screen_w / 2 - 160
            <= mx
            <= screen_w / 2 + 160
        ):

            if 170 <= my <= 225:

                game_state = "playing"

                pygame.mouse.set_visible(
                    False
                )

                pygame.event.set_grab(
                    True
                )

            elif 240 <= my <= 295:

                pause_page = "controls"

            elif 310 <= my <= 365:

                pause_page = "settings"

            elif 380 <= my <= 435:

                # IMPORTANT:
                # Only current_world is saved.
                save_current_world()

                refresh_worlds()

                game_state = "menu"

                menu_page = "worlds"

                pygame.mouse.set_visible(
                    True
                )

                pygame.event.set_grab(
                    False
                )

    elif pause_page == "controls":

        if (
            screen_w / 2 - 120
            <= mx
            <= screen_w / 2 + 120
            and
            screen_h - 70
            <= my
            <= screen_h - 20
        ):

            pause_page = "main"

    elif pause_page == "settings":

        slider_x = screen_w / 2 - 200
        slider_y = 220
        slider_w = 400

        if (
            slider_x
            <= mx
            <= slider_x + slider_w
            and
            slider_y - 20
            <= my
            <= slider_y + 30
        ):

            amount = (
                mx - slider_x
            ) / slider_w

            amount = max(
                0,
                min(
                    1,
                    amount
                )
            )

            sensitivity = (
                MIN_SENSITIVITY
                +
                amount *
                (
                    MAX_SENSITIVITY
                    -
                    MIN_SENSITIVITY
                )
            )

        if (
            screen_w / 2 - 120
            <= mx
            <= screen_w / 2 + 120
            and
            screen_h - 70
            <= my
            <= screen_h - 20
        ):

            pause_page = "main"


# ============================================================
# MAIN
# ============================================================

def main():

    global font
    global big_font

    global game_state
    global menu_page
    global pause_page

    global yaw
    global pitch

    global world_name_input
    global sensitivity

    pygame.init()

    pygame.display.set_caption(
        "PyVoxelCraft"
    )

    pygame.display.set_mode(
        (WIDTH, HEIGHT),
        OPENGL |
        DOUBLEBUF |
        RESIZABLE
    )

    setup_opengl(
        WIDTH,
        HEIGHT
    )

    font = pygame.font.SysFont(
        "Arial",
        24
    )

    big_font = pygame.font.SysFont(
        "Arial",
        54,
        bold=True
    )

    clock = pygame.time.Clock()

    refresh_worlds()

    # Start at the menu.
    game_state = "menu"
    menu_page = "main"

    pygame.mouse.set_visible(
        True
    )

    pygame.event.set_grab(
        False
    )

    pygame.key.start_text_input()

    running = True

    while running:

        dt = min(
            clock.tick(60) / 1000.0,
            0.05
        )

        for event in pygame.event.get():

            # ------------------------------------------------
            # QUIT
            # ------------------------------------------------

            if event.type == QUIT:

                if game_state in (
                    "playing",
                    "paused"
                ):

                    save_current_world()

                running = False

            # ------------------------------------------------
            # RESIZE
            # ------------------------------------------------

            elif event.type == WINDOWRESIZED:

                setup_opengl(
                    event.x,
                    event.y
                )

            # ------------------------------------------------
            # KEYBOARD
            # ------------------------------------------------

            elif event.type == KEYDOWN:

                if game_state == "playing":

                    game_key(
                        event
                    )

                elif game_state == "paused":

                    if event.key == K_ESCAPE:

                        game_state = "playing"

                        pygame.mouse.set_visible(
                            False
                        )

                        pygame.event.set_grab(
                            True
                        )

                    elif event.key == K_LEFT:

                        sensitivity = max(
                            MIN_SENSITIVITY,
                            sensitivity - 0.01
                        )

                    elif event.key == K_RIGHT:

                        sensitivity = min(
                            MAX_SENSITIVITY,
                            sensitivity + 0.01
                        )

                elif game_state == "menu":

                    if event.key == K_ESCAPE:

                        if menu_page == "main":

                            running = False

                        else:

                            menu_page = "main"

                    elif menu_page == "create":

                        if event.key == K_BACKSPACE:

                            world_name_input = (
                                world_name_input[:-1]
                            )

                        elif event.key == K_RETURN:

                            name = (
                                world_name_input.strip()
                            )

                            if not name:
                                name = "New World"

                            create_world(
                                name
                            )

                            refresh_worlds()

                            game_state = "playing"

                            pygame.mouse.set_visible(
                                False
                            )

                            pygame.event.set_grab(
                                True
                            )

            # ------------------------------------------------
            # TEXT INPUT
            # ------------------------------------------------

            elif event.type == TEXTINPUT:

                if (
                    game_state == "menu"
                    and
                    menu_page == "create"
                ):

                    if len(
                        world_name_input
                    ) < 30:

                        world_name_input += (
                            event.text
                        )

            # ------------------------------------------------
            # MOUSE LOOK
            # ------------------------------------------------

            elif event.type == MOUSEMOTION:

                if (
                    game_state == "playing"
                    and
                    pygame.event.get_grab()
                ):

                    dx, dy = event.rel

                    yaw += (
                        dx * sensitivity
                    )

                    # Positive mouse Y looks DOWN.
                    pitch += (
                        dy * sensitivity
                    )

                    pitch = max(
                        -89,
                        min(
                            89,
                            pitch
                        )
                    )

            # ------------------------------------------------
            # MOUSE BUTTON
            # ------------------------------------------------

            elif event.type == MOUSEBUTTONDOWN:

                if game_state == "playing":

                    hit, previous = raycast()

                    # Left click = break.
                    if event.button == 1:

                        if hit:

                            set_block(
                                *hit,
                                AIR
                            )

                    # Right click = place.
                    elif event.button == 3:

                        if (
                            hit is not None
                            and
                            previous is not None
                        ):

                            x, y, z = previous

                            # Don't place inside player.
                            if not collision(
                                x + 0.5,
                                y,
                                z + 0.5
                            ):

                                set_block(
                                    x,
                                    y,
                                    z,
                                    selected_block
                                )

                elif game_state == "menu":

                    menu_click(
                        event.pos
                    )

                elif game_state == "paused":

                    pause_click(
                        event.pos
                    )

        # ====================================================
        # UPDATE
        # ====================================================

        if game_state == "playing":

            update_game(
                dt
            )

        # ====================================================
        # DRAW
        # ====================================================

        if game_state == "menu":

            glClear(
                GL_COLOR_BUFFER_BIT |
                GL_DEPTH_BUFFER_BIT
            )

            if menu_page == "main":

                draw_main_menu()

            elif menu_page == "worlds":

                draw_world_select()

            elif menu_page == "create":

                draw_create_world()

        elif game_state == "playing":

            draw_game()

        elif game_state == "paused":

            draw_game()

            draw_pause()

        pygame.display.flip()

    pygame.quit()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except Exception:

        traceback.print_exc()

        print()
        print("=" * 50)
        print("PyVoxelCraft crashed.")
        print("=" * 50)

        try:
            input(
                "Press ENTER to close..."
            )
        except EOFError:
            pass

        pygame.quit()
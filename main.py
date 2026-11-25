#!/usr/bin/env python3
"""Convince the AI Judge to Visit Your House: A Letter in One Image.

Writes one 1024x1024 PNG to /output/entry.png.

Pure standard library: the grader runs `python3 -P -s main.py` inside a
python:3.13-slim container with no network, no Pillow and no system fonts.
So this program carries its own tiny rasterizer: a pixel buffer, filled
shapes (rect / circle / ellipse / polygon / thick line), an embedded
bitmap font (DejaVu Serif glyphs rasterized at build time into packed
1-bit bitmaps, stored in FONT below), and a hand-rolled PNG encoder
(zlib + struct only). Everything is deterministic: no time, no random,
no I/O besides the single output file, so two runs are byte-identical.

The picture: a warm, hand-drawn invitation. A little house, a tree and
bunting at the top; below, a cream letter card addressed to the AI judge
that offers dumplings, the soft armchair by the window, a garden view and
fast Wi-Fi, with a knowing wink that the judge cannot literally walk
through the door -- and a doormat at the bottom that says WELCOME.
"""

import base64
import os
import struct
import zlib
from math import isqrt

W = 1024
H = 1024
OUT_PATH = "/output/entry.png"

# ---------------------------------------------------------------- palette
INK = (59, 42, 36)          # warm dark brown ink
PAPER = (255, 249, 236)     # cream letter paper
PAPER_EDGE = (232, 217, 184)
TERRA = (180, 85, 45)       # terracotta
TERRA_DARK = (146, 62, 32)
SAGE = (110, 139, 94)
SAGE_DARK = (84, 110, 70)
MUSTARD = (217, 164, 65)
TEAL = (78, 126, 122)
SKY_TOP = (247, 222, 198)   # wall gradient, top
SKY_BOT = (242, 203, 174)   # wall gradient, bottom
ROOF = (168, 74, 52)
HOUSE = (240, 196, 150)
DOOR = (122, 74, 52)
LEAF = (96, 128, 80)
WHITE = (255, 255, 255)
CREAM = (253, 240, 214)
MUTED = (122, 96, 82)       # softer brown for the P.S.
SEAL = (178, 52, 44)
SEAL_DARK = (140, 36, 30)
TAPE = (240, 222, 160)
SHADOW = (214, 170, 134)

# Embedded bitmap font data (DejaVu Serif, rasterized at build time).
# Each glyph: (width, height, left_bearing, top_rel_baseline, advance, base64 packed 1-bit bitmap).
FONT = {
    "serif_bold_52": {
        "ascent": 49, "descent": 13,
        "glyphs": {
            ' ': (0, 0, 0, 0, 18, ""),
            '!': (11, 39, 6, -38, 23, "f8/5/z/n/P8P4fw/h/D+H8PwPgfA+B8D4HwPAOAcA4BwDgHAAAAAADwP4/5/z/n/P+f8fweA"),
            '"': (19, 14, 4, -38, 27, "fg/Pwfn4Pz8H5+D8/B+fg/Pwfn4Pz8H5+D8/B+fg/PwfgA=="),
            '#': (38, 37, 3, -37, 44, "AAPwHwAAD8D8AAA/A/AAAPgPwAAH4D4AAB+B+AAAfgfgAAHwH4AAD8B8AAA/AfAB/////4f////+H/////h/////4f////+AB8B+AAA/AfAAAPwPwAAD4D8AAB+A/AAAfgPgAAH4H4AH/////B/////wf////8H/////B/////wAfgPgAAH4D4AAB+B+AAAfAfgAAHwHwAAD8B8AAA/A/AAAPgPwAAD4D8AAB+A+AAA="),
            '$': (28, 48, 4, -40, 36, "AA8AAADwAAAPAAAA8AAADwAAAPAAAA8AAAf/AAP//wD///wf7z/D+PD8Pw8Hx/DwPH8PA8fw8Bx/DwHH+PAAf+8AB//wAH//gAP//4A///4B///wD///wD///AD//+AA//4AD//wAPP/AA8f9wDw/3APB/eA8H94DwfnwPD+fg8fx/jz+H///wH//+AB//AAAPAAAA8AAADwAAAPAAAA8AAADwAAAPAA"),
            '%': (48, 40, 1, -39, 49, "AfwAAHgAD/8AAPgAH/+AAPAAP4/AAfAAPw/gAeAAfwfgA8AAfgfwA8AAfgfwB4AA/gfwD4AA/gfwDwAA/gfwHwAA/gfwHgAA/gfwPAAAfgfwfAAAfgfweAAAfwfg+AAAPw/g8AAAP4/B4AAAH/+D4AAAD/8DwD+AAfwHwf/gAAAHg//wAAAPB/H4AAAfB+H8AAAeD+D8AAA+D8D+AAA8H8D+AAB4H8D+AAD4H8D+AADwH8D+AAHwH8D+AAHgH8D+AAPAH8D+AAPAD8D+AAeAD+D8AA+AB+H8AA8AB/H4AB8AA//wAB4AAf/gADwAAD+A"),
            '&': (45, 40, 2, -39, 47, "AAH/wAAAAH//4AAAD///AAAA/4P4AAAP8AfAAAD/gD4AAAf4APAAAD/AB4AAAf4AHAAAD/AAAAAAf8AAAAAD/wAAAAAf+AAAAAB/4AAAAAP/gAAAAA/+AAAAAf/4Af/wH//gD/+D//+Af/w/z/4APAP+P/gB4B/g/+APAf8D/4BwD/AP/gOA/4A/+DwH/AD/weA/4AP/HgH/AA/98A/4AH//AH/gAf/wA/8AB/+AD/gAH/wAf+AAf/AD/4AB/8AP/gA//wA//gf//AD///9//wH//+H/+AP//Af/wAP/AAAA"),
            "'": (7, 14, 4, -38, 16, "fv379+/fv379+/fvwA=="),
            '(': (18, 48, 4, -40, 25, "AABAAHAAfAB+AD8AH4AfwA/gA/gB/AD/AD/AH+AH+AP+AP+AP+AP+Af+Af8Af8Af8Af8Af8Af8Af8Af8Af8Af8Af+AP+AP+AP+AP+AH+AH+AD/AD/AB/AA/gA/gAfwAP4AD8AB+AAfAAPAAB"),
            ')': (18, 48, 2, -40, 25, "QAAcAAfAAfgAH4AD8AD+AB/AA/gA/wA/wAf4Af4Af8Af8AP8AP+AP+AP+AP+AP+AP/AP/AP/AP/AP/AP/AP+AP+AP+AP+AP+AP8Af8Af8Af4Af4A/wA/wA/gB/AD+AD8AH4AfwAfAAcAAQAA"),
            '*': (25, 24, 1, -39, 27, "AD4AAB8AAA+AAAPAAgHgIcDwefBwff44fz+c/wfv/AD/+AAf8AAP+AAf/wA//+B/Of7/HD++Dg+OB4PEA8BAAeAAAfAAAPgAAHwA"),
            '+': (34, 32, 5, -32, 44, "AAPwAAAA/AAAAD8AAAAPwAAAA/AAAAD8AAAAPwAAAA/AAAAD8AAAAPwAAAA/AAAAD8AAAAPwAB/////n////+f////5/////n////+f////4AA/AAAAD8AAAAPwAAAA/AAAAD8AAAAPwAAAA/AAAAD8AAAAPwAAAA/AAAAD8AAAAPwAAAA/AAA=="),
            ',': (14, 17, 0, -8, 18, "A/gP4D+A/gP4H8B/AfwP4D+B/A/wf4H8A+APABAA"),
            '-': (17, 7, 2, -17, 22, "f/+//9//7//3//v//f/+"),
            '.': (10, 10, 4, -9, 18, "Hg/H+//////9/j8HgA=="),
            '/': (19, 43, 0, -38, 19, "AAfgAPwAHwAH4AD8AB8AB+AA/AAfAAfgAPwAHwAH4AD8AB8AA+AA/AAfgAPgAPwAH4AD4AD8AB+AA+AA/AAfgAPgAHwAH4AD8AB8AB+AA/AAfAAfgAPwAHwAH4AD8AB8AB+AA/AAAA=="),
            '0': (32, 40, 2, -39, 36, "AA/wAAB//gAB//+AA/w/wAf4H+AP8A/wD/AP+B/gB/gf4Af8P+AH/D/gB/x/4Af+f+AH/n/gB/5/4Af+f+AH/n/gB/9/4Af//+AH///gB///4Af//+AH/3/gB/9/4Af/f+AH/n/gB/5/4Af+f+AH/n/gB/4/4Af8P+AH/D/gB/wf4Af4D/AP+A/wD/AH+B/gA/w/wAH//4AAf/4AAA/wAA=="),
            '1': (25, 39, 6, -39, 36, "AH/AAP/gAP/wAf/4A//8A/f+A/P/AeH/gMD/wAB/4AA/8AAf+AAP/AAH/gAD/wAB/4AA/8AAf+AAP/AAH/gAD/wAB/4AA/8AAf+AAP/AAH/gAD/wAB/4AA/8AAf+AAP/AAH/gAD/wAB/4AA/8AAf+Af///v///3///4="),
            '2': (29, 39, 3, -39, 36, "Af/AAP//4B///4D+B/8H4B/8PgB/8eAB/44AD/5wAD/zgAH/gAAP/AAAf+AAA/8AAB/4AAD/wAAH/gAAf+AAA/8AAB/wAAH/AAAP8AAA/wAAD/AAAP4AAA/gAAD+AAAfwAAB+AAAH4AHg/AAPD8AAefgAA9/////////////////////////////////4A=="),
            '3': (30, 40, 3, -39, 36, "AP/gAH//+Af///gfwP/wfgD/4fAB/4eAA/8eAA/8eAA/8AAA/8AAA/8AAA/8AAA/8AAA/4AAB/4AAD/wAAP/gAH/+AAH/4AAH//AAAP/wAAD/4AAB/8AAA/+AAAf+AAAf+AAAf/AAAf/AAAf/AAAf/cAAf/cAAf/cAAf+eAA/+eAA/8fAB/8fwH/wf///gH//+AAf/gA"),
            '4': (33, 39, 2, -39, 36, "AAD/wAAA/+AAAP/wAAB/+AAAf/wAAD/+AAA//wAAP/+AAB7/wAAff+AADz/wAA8f+AAPj/wAB4f+AAfD/wADwf+AA8D/wAPgf+AB4D/wAfAf+ADwD/wA8Af+APgD/wB4Af+AfAD/wHwAf+A/////3////+/////wAAf+AAAD/wAAAf+AAAD/wAAAf+AAAD/wAAAf+AAD///gAf//8AD///g="),
            '5': (29, 39, 4, -38, 36, "P///gf///A///+B///8D///4H///wP///gcAAAA4AAABwAAADgAAAHAAAAOAAAAcP+AA5//gB///wD8D/wHgD/wOAD/wAAD/wAAH/gAAP/gAAP/AAAf+AAA/8AAB/4AAD/wAAH/gAAP/cAAf+4AB/94AD/zwAH/nwAf+PwB/4fwP/g///+Af//wAB/8AAA=="),
            '6': (31, 40, 3, -39, 36, "AAf+AAB//8AD///AD/A/gD+AHwD+AB4D/AAcD/AAOB/gAAB/wAAA/wAAAf4AAAf8AAAP+AAAH/D/AD/n/4B////B//B/w//Af8f/gP/P/gD/n/wB/7/4A/9/8Af+/+AP/P/AH/n/gD/z/wB/5/4A/8/8Af+P+AP/H/AH/h/gD/g/wB/wP8B/wD+A/4A/g/4AP//wAB//wAAP/AA="),
            '7': (28, 38, 4, -38, 36, "/////////////////////////////////wAAPvAAA+8AAHzwAAfPAAD4AAAPgAAB8AAAHwAAA+AAAD4AAAfAAAB8AAAPgAAA+AAAHwAAAfAAAD4AAAPgAAB8AAAHwAAA+AAAD4AAAfAAAB8AAAPgAAA+AAAHwAAAfAAAD4AAAPgAAB8AAA=="),
            '8': (32, 40, 2, -39, 36, "AB/4AAD//wAD///AB/w/4A/4H/Af8A/4H/AP+D/wD/w/8A/8P/AP/D/wD/w/8A/8P/AP/D/wD/wf8A/4H/AP+A/4H/AH/D/gAf//gAB//gAD///AB/gf8B/wD/g/8Af8P+AH/H/gB/5/4Af+f+AH/n/gB/5/4Af+f+AH/n/gB/5/4Af+P+AH/j/wD/wf8A/4D/wf8Af//+AB//+AAB/8AA=="),
            '9': (31, 40, 2, -39, 36, "AB/wAAH//AAP//wAf+H+AP+B/gP+AfwP/AP8H/AH/H/gD/j/wB/5/4Af8/8AP+f+AH/P/AD/3/gB/7/wA/9/4A/+/8Af/P+AP/n/gH/x/wD/4/8D/8P/D/+D////Af/3/gD/D/gAAB/wAAA/4AAAf8AAAP8AAAH+AAAH+BwAD/A4AD/AeAB/gPgB/gH8D/gD///AA//+AAB/4AA="),
            ':': (11, 27, 4, -26, 19, "Dwfx/z/n/P+f8/4/g+AAAAAAAAAAAAAB4P4/5/z/n/P+f8fwPAA="),
            ';': (14, 35, 1, -26, 19, "AeAfwP+D/g/4P+D/g/4H8A+AAAAAAAAAAAAAAAAAAAB/gf4H+B/AfwH8B/AfgP4D+B/A/gf4H8B+AOABAAA="),
            '<': (34, 29, 5, -31, 44, "AAAAAIAAAAHgAAAD+AAAB/4AAA//gAAP/+AAH//wAD//4AB//8AAf/+AAP//AAH//gAAf/wAAB/4AAAH+AAAAf+AAAB//AAAH//gAAD//wAAB//4AAB//8AAA//+AAAf//AAAP/+AAAH/4AAAH/gAAAD+AAAAB4AAAAAgA=="),
            '=': (34, 18, 5, -25, 44, "f////5/////n////+f////5/////n////+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAf////5/////n////+f////5/////n////+A="),
            '>': (34, 29, 5, -31, 44, "QAAAAB4AAAAH8AAAAf8AAAB/+AAAH//AAAP//gAAH//gAAD//wAAB//4AAA//8AAAf/+AAAf/4AAAP/gAAAH+AAAB/4AAA//gAAf/+AAP//AAH//gAD//wAB//4AA//+AAH//AAAf/gAAB/wAAAH4AAAAeAAAABAAAAAAA=="),
            '?': (26, 40, 3, -39, 30, "A/8AD//4D///g/g/8PgD/j4A/88AH/PAB/7wAf+8AD/gAA/4AAP+AAD/gAB/4AAf+AAH/AAD/wAA/4AAf+AAP/AAP/AAH/gAB/AAAcAAAHAAABwAAAcAAAHAAAAAAAAAAAAPgAAH8AAD/gAA/4AAP+AAD/gAA/4AAP+AAB/AAAPgAA=="),
            '@': (46, 46, 3, -37, 52, "AAA/+AAAAAf//gAAAP///gAAB/wB/AAAf4AA/AAD+AAA+AAfgAAA8AD8AAAB4AfgAAADwD8AAAAHAPgAAAAOB+AH4AA8HwB/5+Bw/Af/34HD4D/D/gOPgPwH+A5+B/AP4DnwH4A/gOfA/gB+A58D8AH4DnwPwAfgO/A/AB+A78D8AH4DvwPwAfgO/A/AB+A58D8AH4DHwPwAfgcfA/gB+Bx8B+AP4OH4H8A/hwPgPwH+PA+A/w/74D8B///+AHwB/5/wAfgB+H4AA+AAAAAAD8AAAAAAH4AAAAAAPwAAAAAAfgAAAAAA/gAAMAAB/gAD4AAB/wB/AAAD///wAAAB//8AAAAA/8AAAA=="),
            'A': (42, 38, -1, -38, 40, "AAA/AAAAAB/gAAAAB/gAAAAB/gAAAAD/wAAAAD/wAAAAH/4AAAAH/4AAAAP/8AAAAP/8AAAAO/8AAAAe/+AAAAcf+AAAA8f/AAAA8P/AAAA4P/AAAB4P/gAABwH/gAADwH/wAADwD/wAADgD/wAAHgB/4AAHAB/4AAPAB/8AAP///8AAP///8AAf///+AAcAAf+AA8AAf/AA8AAP/AA4AAP/AB4AAH/gBwAAH/gDwAAH/wDwAAD/wf/AA///f/AA///f/AA///A="),
            'B': (40, 38, 2, -38, 44, "////8AD/////AP////+AB/4B/+AH/gB/4Af+AD/wB/4AP/AH/gAf+Af+AB/4B/4AH/gH/gAf+Af+AB/4B/4AP/AH/gA/8Af+AH/gB/4D/4AH///+AAf///gAB////4AH/gH/4Af+AH/wB/4AP/gH/gAf/Af+AA/8B/4AD/4H/gAP/gf+AA/+B/4AD/4H/gAP/gf+AA/+B/4AD/4H/gAf/Af+AD/8B/4Af/gH/gH/8P/////g/////wD////wAA=="),
            'C': (37, 40, 2, -39, 41, "AAD/wAAAf//wAA////AB/8D/4B/wAP8B/wAD+B/wAA/B/4AAfh/4AAHw/8AAD4/8AAA8f+AAAef/AAAPP/gAAAH/gAAAD/wAAAD/4AAAB/8AAAA/+AAAAf/AAAAP/gAAAH/wAAAD/4AAAB/8AAAAf+AAAAP/AAAAH/wAAAD/4AAAA/8AAAAf+AAAfH/gAAfD/wAAPg/8AAPgP+AAHwD/gAHwA/4APwAP/gfwAB///wAAP//gAAAf+AA="),
            'D': (41, 38, 2, -38, 45, "////wAB////+AD/////AAP/Af/gAf+AH/gA/8AH/gB/4AH/gD/wAH/gH/gAP/AP/AAP/Af+AAf+A/8AA/+B/4AB/8D/wAB/4H/gAD/4P/AAH/wf+AAP/g/8AAf/B/4AA/+D/wAB/8H/gAD/4P/AAH/wf+AAP/g/8AAf/B/4AA/8D/wAD/4H/gAH/wP/AAP/Af+AAf+A/8AB/4B/4AD/wD/wAP/AH/gA/8AP/AD/wAf+A//Af////4A/////AB////gAA"),
            'E': (35, 38, 2, -38, 40, "/////////////////4P/AADwf+AAHg/8AAPB/4AAeD/wAA8H/gAAAP/AAAAf+AAAA/8AOAB/4AcAD/wA4AH/gBwAP/ADgAf///AA///+AB///8AD/wA4AH/gBwAP/ADgAf+AHAA/8AOAB/4AAAD/wAAAH/gAAAP/AAAAf+AAAA/8AAAB/4AAeD/wAA8H/gAB4P/AADwf+AAH/////////////////8A="),
            'F': (35, 38, 2, -38, 37, "/////9/////7/////wP/AADgf+AAHA/8AAOB/4AAcD/wAA4H/gAAAP/AAAAf+AAAA/8AOAB/4AcAD/wA4AH/gBwAP/ADgAf///AA///+AB///8AD/wA4AH/gBwAP/ADgAf+AHAA/8AOAB/4AAAD/wAAAH/gAAAP/AAAAf+AAAA/8AAAB/4AAAD/wAAAH/gAAAP/AAAAf+AAAf//8AA///4AB///wAAA="),
            'G': (39, 40, 2, -39, 44, "AAD/4AAAH//+AAD///+AB/8B/8Af+AB/gH/AAH8B/wAAfgf+AAB8H/gAAPg/8AAA8P/AAAHh/4AAA8f/AAADj/4AAAAf+AAAAD/wAAAA/+AAAAH/wAAAA/+AAAAH/wAAAA/+AAAAH/wAD/+/+AAf/3/wAD/+f+AAB/z/wAAP+f/AAB/z/4AAP+P/AAB/x/4AAP+H/gAB/w/8AAP+D/gAB/wP+AAP+A/4AB/wD/gAf+AP/AP/gAf///wAA///wAAAf/AA"),
            'H': (45, 38, 2, -38, 49, "///wf/////+D//////wf//4P/AAH/gB/4AA/8AP/AAH/gB/4AA/8AP/AAH/gB/4AA/8AP/AAH/gB/4AA/8AP/AAH/gB/4AA/8AP/AAH/gB/4AA/8AP/AAH/gB/////8AP/////gB/////8AP/AAH/gB/4AA/8AP/AAH/gB/4AA/8AP/AAH/gB/4AA/8AP/AAH/gB/4AA/8AP/AAH/gB/4AA/8AP/AAH/gB/4AA/8AP/AAH/gB/4AA/8AP/AAH/gB/4AA/8H//+D//////wf/////+D///A=="),
            'I': (20, 38, 2, -38, 24, "//////////B/4Af+AH/gB/4Af+AH/gB/4Af+AH/gB/4Af+AH/gB/4Af+AH/gB/4Af+AH/gB/4Af+AH/gB/4Af+AH/gB/4Af+AH/gB/4Af+AH/gB/4Af+D/////////8="),
            'J': (27, 49, -4, -38, 25, "A///4H///A///4AH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/8AAH/gAA/4HgH/A8B/4HgP+A8B/wHwf8A///AD//wAB/wAAA=="),
            'K': (45, 38, 2, -38, 45, "///wH/+H//+A//w///wH/+AP/AAD4AB/4AB8AAP/AAfAAB/4AHwAAP/AB8AAB/4AfAAAP/AHwAAB/4D8AAAP/A+AAAB/4PgAAAP/D4AAAB/4+AAAAP/PwAAAB///AAAAP//8AAAB///wAAAP///AAAB/7/8AAAP/P/wAAB/4//AAAP/D/8AAB/4P/gAAP/A/+AAB/4H/4AAP/Af/gAB/4B/+AAP/AH/4AB/4Af/gAP/AB/+AB/4AH/4AP/AAf/gB/4AB/+H//+AH/////wAf////+AD//A=="),
            'L': (34, 38, 2, -38, 37, "///wAD///AAP//8AAB/4AAAH/gAAAf+AAAB/4AAAH/gAAAf+AAAB/4AAAH/gAAAf+AAAB/4AAAH/gAAAf+AAAB/4AAAH/gAAAf+AAAB/4AAAH/gAAAf+AAAB/4AAAH/gAAAf+AAAB/4AAAH/gAAAf+AAAB/4AAAH/gAAAf+AAOB/4AA4H/gADgf+AAOB/4AA4H/gADv////+/////7/////g"),
            'M': (54, 38, 2, -38, 58, "//8AAAf/+//+AAAf/+//+AAA//+B/+AAA//AB//AAB//AB//AAB//AB//gAB//AB//gAD//AB7/wADv/AB7/wAHv/AB5/4AHP/AB5/4APP/AB4/4AOP/AB4/8AeP/AB4/8AeP/AB4f+AcP/AB4f+A8P/AB4P/A4P/AB4P/B4P/AB4H/hwP/AB4H/jwP/AB4D/jgP/AB4D/3gP/AB4D//gP/AB4B//AP/AB4B//AP/AB4A/+AP/AB4A/+AP/AB4Af8AP/AB4Af8AP/AB4AP4AP/AB4AP4AP/AB4AAAAP/AB4AAAAP/AB4AAAAP/A//gAAD//+//gAAD//+//gAAD//+A="),
            'N': (44, 38, 2, -38, 48, "//gAA//v/4AAP/7//AAD/+B/4AAB4Af/AAAeAH/4AAHgB//AAB4Af/4AAeAH/+AAHgB//wAB4Af/+AAeAHv/wAHgB7/+AB4Aef/wAeAHj/8AHgB4f/gB4AeD/8AeAHgf/gHgB4H/8B4AeA//geAHgH/8HgB4A//B4AeAH/4eAHgA//HgB4AH/54AeAB//eAHgAP//gB4AB//4AeAAP/+AHgAB//gB4AAP/4AeAAD/+AHgAAf/gB4AAD/4AeAAAf+D//AAD/g//wAAf4P/8AAD+A="),
            'O': (42, 40, 2, -39, 45, "AAH/wAAAA///AAAD///wAAP/A/4AAf8AP+AB/4AH/AB/wAH/gD/gAD/gH/gAD/wH/AAB/4P/AAB/4P/AAB/8f/AAA/8f+AAA/8f+AAA/8f+AAA/+/+AAA/+/+AAA/+/+AAA/+/+AAA/+/+AAA/+/+AAA/+/+AAA/+/+AAA/+f+AAA/+f+AAA/8f+AAA/8f/AAA/8P/AAB/8P/AAB/4H/AAB/4H/gAD/wD/gAD/gB/wAH/gB/4AH/AAf8AP+AAP/A/4AAH///wAAA///AAAAH/wAA"),
            'P': (36, 38, 2, -38, 39, "////4A/////A/////gB/4H/4B/4D/8B/4B/8B/4A/+B/4Af+B/4Af/B/4Af/B/4Af/B/4Af/B/4Af/B/4Af/B/4Af+B/4A/+B/4B/8B/4D/8B/4H/4B////gB////AB///4AB/4AAAB/4AAAB/4AAAB/4AAAB/4AAAB/4AAAB/4AAAB/4AAAB/4AAAB/4AAAB/4AAAB/4AAAB/4AAA///4AA///4AA///4AA"),
            'Q': (42, 48, 2, -39, 45, "AAH/wAAAA///AAAD///wAAP/A/4AAf8AP+AB/4AH/AB/wAH/gD/gAD/gH/gAD/wH/AAB/4P/AAB/4P/AAB/8f/AAA/8f+AAA/8f+AAA/8f+AAA/+/+AAA/+/+AAA/+/+AAA/+/+AAA/+/+AAA/+/+AAA/+/+AAA/+/+AAA/+f+AAA/+f+AAA/+f+AAA/8f/AAA/8P/AAB/8P/AAB/4H/AAB/4H/gAD/wD/gAD/gB/wAH/gB/4AH/AAf8AP+AAP/A/4AAD///wAAA//+AAAAH/wAAAAAHwAAAAAH8AAAAAD/+AAAAB/+AAAAA/+AAAAAf+AAAAAH+AAAAAB+A"),
            'R': (42, 38, 2, -38, 43, "////4AA/////AA/////wAB/4D/4AB/4B/8AB/4A/+AB/4Af+AB/4Af+AB/4AP/AB/4AP/AB/4AP/AB/4AP/AB/4AP/AB/4Af+AB/4Af+AB/4A/8AB/4B/4AB/4H/wAB////AAB///4AAB///+AAB/4f/AAB/4H/gAB/4H/wAB/4D/wAB/4D/4AB/4B/4AB/4A/8AB/4A/8AB/4Af+AB/4Af+AB/4AP/AB/4AP/AB/4AH/gB/4AH/g///wD/////wD/////wB//A="),
            'S': (32, 40, 3, -39, 38, "AD/8AAH//+AH///4D/AP+B/AA/g/gAH4PwAA+H8AAHh/AAB4fwAAeH8AADj/gAAA/8AAAP/gAAB//AAAf//AAH///AB///+AP///4D////Af///4B////AP///wAf//+AA///gAA//4AAB/+AAAH/gAAAf5wAAH+eAAB/ngAAf54AAH+fAAB/H4AA/x/gAf4f+Af8D///+AH//+AAD/4AA=="),
            'T': (39, 38, 0, -38, 39, "f/////z/////+f/////zgB/4AOcAP/ABzgB/4AOcAP/ABzgB/4AOcAP/ABwAB/4AAAAP/AAAAB/4AAAAP/AAAAB/4AAAAP/AAAAB/4AAAAP/AAAAB/4AAAAP/AAAAB/4AAAAP/AAAAB/4AAAAP/AAAAB/4AAAAP/AAAAB/4AAAAP/AAAAB/4AAAAP/AAAAB/4AAAAP/AAAAB/4AAAAP/AAAAB/4AAAAP/AAAA///wAAH//+AAA///wAA"),
            'U': (44, 39, 1, -38, 45, "f//wA//n//8AP/5///AD/+A/4AABwAP+AAAcAD/gAAHAA/4AABwAP+AAAcAD/gAAHAA/4AABwAP+AAAcAD/gAAHAA/4AABwAP+AAAcAD/gAAHAA/4AABwAP+AAAcAD/gAAHAA/4AABwAP+AAAcAD/gAAHAA/4AABwAP+AAAcAD/gAAHAA/4AABwAP/AAAcAD/wAAHAA/8AADwAP/AAA8AD/wAAPAAf+AADgAH/gAB4AB/8AA+AAP/gAfAAB/+AfgAAP///wAAB///4AAAH//4AAAAP/wAAA="),
            'V': (43, 38, -1, -38, 40, "f//AAf/P//gAP/n//wAH/wf/AAAPAH/gAAHAD/4AAHgA/8AADgAf/AADwAH/gAB4AD/wAA4AB/8AA8AAf+AAcAAP/gAeAAD/wAPAAB/4AHAAA/+AHgAAP/ADgAAH/wDwAAB/4B4AAA/8A4AAAf/A8AAAH/gcAAAD/4eAAAA/8PAAAAf/HAAAAP/ngAAAD/zgAAAB//wAAAAf/wAAAAP/4AAAAD/8AAAAB/8AAAAA/+AAAAAP+AAAAAH/AAAAAB/gAAAAA/gAAAAAfwAAAA=="),
            'W': (61, 38, -1, -38, 58, "f//gA/gA//P//wA/4Af/n//4Af8AP/wf/AAP+AAOAH/gAP/AAPAD/wAH/wAHAB/8AD/4ADgAf+AB/8ADwAP/AB//ABwAH/gA//gA4AB/4Af/wA8AA/8Ae/8AcAAf+AOf+AOAAP/gHP/AHAAD/wHn/wHgAB/4Dx/4DgAA/+Bw/8BwAAP/B4f/B4AAH/g8H/g4AAD/4cD/wcAAA/8OB/4eAAAf+PAf+OAAAP/HAP/HAAAD/zgH/ngAAB/7wB/7gAAA/9wA/9wAAAf/4Af/4AAAH/8AH/8AAAD/+AD/8AAAB/+AB/+AAAAf/AA//AAAAP/gAP/AAAAH/gAH/gAAAB/wAD/wAAAA/4AA/wAAAAf4AAf4AAAAH8AAP8AAAAD+AAD8AAA="),
            'X': (41, 38, 0, -38, 40, "///gf/x///A//j//+B//Af/AAPAAf/AAeAA//AB4AA/+AHgAA/+AfAAB/+A8AAB/8DwAAB/8PgAAB/8eAAAD/54AAAD//gAAAD//AAAAH/8AAAAH/wAAAAH/wAAAAP/wAAAAP/gAAAAf/gAAAA//gAAAD//AAAAP//AAAAe//AAAB4/+AAAHw/+AAAPB/+AAA8B/8AADwB/8AAHgB/8AAeAD/4AB4AD/4ADwAD/4APAAH/wP/4D//+f/wH//8//gP//4"),
            'Y': (39, 38, -1, -38, 37, "f//gD/7//8Af/f//gD/4f/AADwB/4AAeAP/gAHgA/+AB4AH/wAPAAf/ADwAB/4AeAAP/gHgAA/8A4AAH/wPAAAf/DwAAD/4eAAAP/ngAAA/84AAAH//AAAAf/wAAAD/+AAAAP/gAAAA/8AAAAH/gAAAA/8AAAAH/gAAAA/8AAAAH/gAAAA/8AAAAH/gAAAA/8AAAAH/gAAAA/8AAAAH/gAAAA/8AAAAH/gAAAf//4AAD///AAAf//4AA"),
            'Z': (36, 38, 1, -38, 38, "P////+P////+P////+OAAB/+OAAD/8OAAD/8OAAH/4OAAP/wOAAP/gAAAf/gAAA//AAAB/+AAAB/+AAAD/8AAAH/4AAAH/wAAAP/wAAAf/gAAA//AAAA//AAAB/+AAAD/8AAAH/4AAAH/4AAAP/wAAAf/gAAAf/gAAA//AAAB/+AAAD/8AAAD/8AAOH/4AAOP/wAAOP/wAAOf/gAAOf////+f////+f////+"),
            '[': (15, 46, 6, -40, 25, "/////////A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H/A/4H///////A"),
            '\\': (19, 43, 0, -38, 19, "/AAfgAHwAD8AB+AAfAAPwAH4AB8AA/AAfgAHwAD8AB+AAfAAPgAH4AD8AA+AAfgAPwAD4AB+AA/AAPgAH4AD8AA+AAfAAPwAH4AB8AA/AAfgAHwAD8AB+AAfAAPwAH4AB8AA/AAfgA=="),
            ']': (16, 46, 3, -40, 25, "f/5//n/+A/4D/gP+A/4D/gP+A/4D/gP+A/4D/gP+A/4D/gP+A/4D/gP+A/4D/gP+A/4D/gP+A/4D/gP+A/4D/gP+A/4D/gP+A/4D/gP+A/4D/gP+A/5//n/+f/4="),
            '^': (34, 14, 5, -38, 44, "AAPwAAAB/gAAAP/AAAB/+AAAP/8AAB//4AAP9/wAB/h/gAP4D/AB/AD+AP4AH8B+AAP4PwAAPx8AAAfg"),
            '_': (26, 5, 0, 7, 26, "/////////////////////8A="),
            '`': (15, 10, 3, -42, 26, "fwB/AH4AfgB+AHwAfAB8AHgAeA=="),
            'a': (31, 29, 2, -28, 34, "Af/AAB//8AD///gB+B/4A+AP+AeAD/APAB/wHAA/4AAAP8AAAH+AAAD/gAf//wB///4D///8D/wP+D/gH/B/wD/g/wB/w/4A/4f8Af8P+AP+H/AP/D/gH/g/4H/wf+H/4P////z//P/4//H/8H8AAAA="),
            'b': (34, 41, 1, -40, 36, "//gAAD/+AAAP/4AAAD/gAAAP+AAAA/4AAAD/gAAAP+AAAA/4AAAD/gAAAP+AAAA/4AAAD/h/AAP+f/gA/7//AD////AP/w/8A/+B/4D/wD/wP/AP/A/4Af8D/gB/4P+AH/g/4Af+D/gB/4P+AH/g/4Af+D/gB/4P+AH/g/4Af+D/gB/4P+AH/g/4Af8D/wD/wP/AP/A/+B/4D/8P/D////8P/7//A//n/4AAAH8AAA=="),
            'c': (28, 29, 2, -28, 32, "AB/4AA//+AP//8D/wPwf+AfB/wA8P+ABw/4AHH/gAcf8AAx/wAAP/AAA/8AAD/wAAP/AAA/8AAD/wAAP/AAAf8AAB/4AAH/gAeP+AB4/4APh/wA8D/gHgP/B+AP//wAP/8AAH/AA"),
            'd': (34, 41, 2, -40, 36, "AAD/+AAAP/4AAA//gAAAP+AAAA/4AAAD/gAAAP+AAAA/4AAAD/gAAAP+AAAA/4AAAD/gAH8P+AD/8/4Af/7/gD///+Af+H/4D/wH/gP+Af+B/4A/4H/gD/gf8AP+B/wA/4P/AD/g/8AP+D/wA/4P/AD/g/8AP+D/wA/4P/AD/gf8AP+B/wA/4H/gD/gf+AP+A/4B/4D/wH/gH/h/+AP////gf/7/+A//P/4AfwAAAA=="),
            'e': (29, 29, 2, -28, 33, "AD/gAA//4AD//4Af8f4B/wf4D/Af4P+A/4f8B/x/wB/j/gD/n/AH/f+AP+/8Af9////7///////////AAAf+AAAf8AAA/4AAB/4ADz/wAPj/gAeD/gB8H/AHwH/gfAH//8AD//gAA/8AAA=="),
            'f': (25, 40, 1, -40, 22, "AA/4AD//gH//wH/j4D/gcD/gOB/wHA/4AAf8AAP+AAH/AAD/gAB/wAP//4H//8D//+AH/AAD/gAB/wAA/4AAf8AAP+AAH/AAD/gAB/wAA/4AAf8AAP+AAH/AAD/gAB/wAA/4AAf8AAP+AAH/AAD/gAB/wAP//wH//4D//8A="),
            'g': (34, 40, 2, -28, 36, "AH8AAAD/8//gf/7/+D////4f+H/4D/wH/gP+Af+B/4A/4H/gD/gf8AP+B/wA/4P/AD/g/8AP+D/wA/4P/AD/g/8AP+D/wA/4P/AD/gf8AP+B/wA/4H/gD/gf+AP+A/4B/4D/wH/gH/h/+AP///4Af/7/gA//P+AAfw/4AAAD/gAAAP+AAAA/4BwAD/AHAAf8AcAB/gB4AP+AH4D/wAf//8AA///AAAP/gAA="),
            'h': (36, 40, 1, -40, 38, "f/wAAAf/wAAAf/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wfwAB/z/8AB/3/+AB////AB/+H/gB/4D/gB/4D/gB/wB/gB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wf/+f//f/+f//f/+f//"),
            'i': (18, 40, 1, -40, 20, "AeAB/AD/gD/gD/gD/gD/gD/gB/AAeAAAAAAAAAAf/wf/wf/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wf/+f/+f/+"),
            'j': (19, 52, -4, -40, 19, "AB4AB/AB/wA/4Af8AP+AH/AD/gA/gAPgAAAAAAAAAAf/wP/4H/8AP+AH/AD/gB/wA/4Af8AP+AH/AD/gB/wA/4Af8AP+AH/AD/gB/wA/4Af8AP+AH/AD/gB/wA/4Af8AP+AH/AD/gB/wA/3A/7gf94P+8P+f/+P/8A/4AA=="),
            'k': (36, 40, 1, -40, 36, "f/wAAAf/wAAAf/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wAAAB/wH/8B/wH/8B/wH/8B/wA8AB/wB4AB/wDwAB/wHgAB/wPAAB/w+AAB/x8AAB/z+AAB/3+AAB///AAB///gAB///wAB/5/wAB/w/4AB/wf8AB/wf+AB/wP/AB/wH/AB/wD/gB/wD/wB/wB/4f/+P//f/+P//f/+P//"),
            'l': (18, 40, 1, -40, 20, "f/wf/wf/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wf/+f/+f/+"),
            'm': (53, 28, 1, -28, 55, "AAAfwA/gA//n/4H/wB//f/4f/wD////5//wAf/h/3D/wA/8B/8D/gB/4D/wD/gD/gH/gH/AH/AP/AP+AP+Af8Af8Af8A/4A/4A/4B/wB/wB/wD/gD/gD/gH/AH/AH/AP+AP+AP+Af8Af8Af8A/4A/4A/4B/wB/wB/wD/gD/gD/gH/AH/AH/AP+AP+AP+Af8Af8Af8A/4A/4A/4B/wB/wB/wD/gD/g//8//8//9//5//5//7//z//z//w"),
            'n': (36, 28, 1, -28, 38, "AAAfwAf/z/8Af/3/+Af////AB/+H/gB/4D/gB/4D/gB/wB/gB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wB/wf/+f//f/+f//f/+f//"),
            'o': (31, 29, 2, -28, 35, "AB/wAAH//AAP//4AP8H+AP8B/gP8A/4P+AP+H/AH/H/gD/z/gB/5/wA/9/4Af+/8AP/f+AD///AB///gA///wA/9/4Af+f8AP/P+AH/n/gD/x/wB/w/4A/4P8A/4D/Af4A/w/4AP//4AB//wAAH/AAA="),
            'p': (34, 39, 1, -28, 36, "AAB/AD/+f/gP/7//A/////AP/w/8A/+B/4D/wD/wP/AP/A/4Af8D/gB/4P+AH/g/4Af+D/gB/4P+AH/g/4Af+D/gB/4P+AH/g/4Af+D/gB/4P+AH/g/4Af8D/wD/wP/AP/A/+B/4D/8P/AP///8A/7//AD/n/4AP+H8AA/4AAAD/gAAAP+AAAA/4AAAD/gAAAP+AAAA/4AAA//+AAD//4AAP//gAAA=="),
            'q': (34, 39, 2, -28, 36, "AH8AAAD/8//gf/7/+D////4f+H/4D/wH/gP+Af+B/4A/4H/gD/gf8AP+B/wA/4P/AD/g/8AP+D/wA/4P/AD/g/8AP+D/wA/4P/AD/gf8AP+B/wA/4H/gD/gf+AP+A/4B/4D/wH/gH/h/+AP///4Af/7/gA//P+AAfw/4AAAD/gAAAP+AAAA/4AAAD/gAAAP+AAAA/4AAAD/gAAD//4AAP//gAA//+A=="),
            'r': (27, 28, 1, -28, 27, "AAAf3/+P///z///+//B//D4P/gPB/4A4P/AHB/wAAP+AAB/wAAP+AAB/wAAP+AAB/wAAP+AAB/wAAP+AAB/wAAP+AAB/wAAP+AAB/wAAP+AAB/wAD//8Af//gD//8AA="),
            's': (26, 29, 2, -28, 29, "AP/AAf//Af//8P+B/H+AHx/gA8fwAPP8ABz/gAc/8AAP/4AB//wAf//gH///A///4H///Af//wA//+AA//gAB/7gAP+8AD/vAA/74AP+/AD/P8D/j///wP//4AP/gAA="),
            't': (23, 36, 1, -35, 24, "D/gAH/AAP+AAf8AA/4AB/wAD/gAH/AD///n///P//+B/wAD/gAH/AAP+AAf8AA/4AB/wAD/gAH/AAP+AAf8AA/4AB/wAD/gAH/AAP+AAf8AA/4AB/wPD/geD/B4H/HwP//AP/8AD/gA="),
            'u': (36, 28, 1, -27, 38, "//gf/g//gf/g//gf/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gD/gB/gH/gB/wP/gB/4f/gA////+Af/7/+AP/j/+AD+AAA"),
            'v': (33, 27, -1, -27, 30, "//8D////gf///8D/4/4ABwD/gAeAf8ADgD/wAcAP+AHgB/wA4AH/APAA/4BwAH/gOAAf8DwAD/gcAAP+HgAB/w4AAP/HAAA/54AAH/OAAAf/wAAD/8AAAf/gAAB/8AAAP/AAAA/4AAAH+AAAA/wAAA=="),
            'w': (47, 27, -1, -27, 45, "f/8B+Af+//4D+A/9//wH8B/4f8Af4AcA/4A/4A4B/4B/wDwB/wH/gHAD/gP/gOAH/gf/A8AH/B/+BwAP+D/+DgAf+Hf8PAAf8e/4cAA/44/44AB/5x/zwAB/3j/nAAD/uD/uAAH/8H/8AAH/4P/wAAP/gP/gAAf/Af/AAAf+A/8AAA/4A/4AAB/wB/wAAB/gD/AAAD+AD+AAAH8AH8AA"),
            'x': (32, 27, 0, -27, 31, "//+P/P//j/z//4/8D/wBwA/+A8AH/geAA/8HAAP/jgAB/54AAP/8AAB/+AAAf/gAAD/wAAAf8AAAH/gAAD/8AAB//AAA9/4AAOP/AAHj/4ADwf+AA4D/wAeAf+APAH/g/+P//v/j//7/4//+"),
            'y': (33, 39, -1, -27, 30, "//8D/3//gf+//8D/w/8ABwD/gAeAf+ADgB/wAcAP/AHAA/4A4AH/APAA/8BwAD/gOAAf+DgAB/wcAAP/HgAA/44AAH/HAAA/9wAAD/+AAAf/wAAB/8AAAP/gAAA/4AAAH/AAAA/4AAAD+AAAAfwAAAB+AAAAPgAAAA8AAAAHAAAAA4AADAPAAAcBwAADgeAAAeHgAAD/4AAAf+AAAA/gAAA="),
            'z': (27, 27, 1, -27, 30, "P///5////P///5wAf+OAH/xwB/8OAP/BwD/wAA/+AAH/gAB/4AAf/AAH/wAA/8AAP/AAD/4AA/+AAH/gAB/4AAf/AHH/wA4/8AHP/AA7/4AHf///7////f///4A="),
            '{': (25, 47, 4, -40, 33, "AAf/gA//wA//4A/8AAf8AAf+AAP+AAH/AAD/gAB/wAA/4AAf8AAP+AAH/AAD/gAB/wAA/4AAf8AAP+AAH/AAH/AAP/gD//AB/+AA//wAA/+AAH/AAD/wAA/4AAf8AAP+AAH/AAD/gAB/wAA/4AAf8AAP+AAH/AAD/gAB/wAA/4AAf+AAH/AAD/wAA//4AP/8AB/+"),
            '|': (7, 52, 6, -40, 19, "fPnz58+fPnz58+fPnz58+fPnz58+fPnz58+fPnz58+fPnz58+fPnz58+fPnz4A=="),
            '}': (26, 47, 4, -40, 33, "f/AAH/8AB//wAA/8AAH/gAA/4AAP+AAD/gAA/4AAP+AAD/gAA/4AAP+AAD/gAA/4AAP+AAD/gAA/4AAP/AAB/wAAf+AAD/wAAf/4AB/+AB//gA/8AAf+AAH/AAD/wAA/4AAP+AAD/gAA/4AAP+AAD/gAA/4AAP+AAD/gAA/4AAP+AAD/gAA/4AAf+AAP/AB//wAf/wAH/wAA"),
            '~': (34, 11, 5, -22, 44, "AAAAAAB+AAAgf/AAGH//gB4///gfn////+f////58D///HAB//4QAB/+AAAA/gA="),
            '—': (48, 6, 2, -17, 52, "f//////+f//////+f//////+f//////+f//////+f//////+"),
            '•': (19, 18, 7, -28, 33, "AfgA/8B//B//w//8//+f//P//3//7//9//+//+f//H//D//g//gH/gA/AA=="),
        },
    },
    "serif_bold_38": {
        "ascent": 36, "descent": 9,
        "glyphs": {
            ' ': (0, 0, 0, 0, 13, ""),
            '!': (8, 28, 4, -28, 17, "f39+fn4+Pj4+PDw8HBwcHBwcHAAAHH5/f39+HA=="),
            '"': (14, 10, 3, -28, 20, "eHnh54eeHnh54eeHnh54eeHg"),
            '#': (28, 27, 2, -27, 32, "AB4PAAPh8AA8HgADweAAPB4AB8PgAHg8Af///h///+H///4f///gDweAAPB4AB4PAAHg8AAeDwB///+H///4f///h///+APB4AB8PgAHg8AAeDwAB4PAAPB4AA8HgAA="),
            '$': (21, 34, 3, -29, 26, "AGAAAwAAGAAAwAAGAAH/AH//B8x8fGHj4wcfGDn4wM/mAD/wAf/gD//gP//A//8B//gA/+AG/wAx+YGHzAw+cGHzgx8fGfh//wB/4AAwAAGAAAwAAGAAAwAA"),
            '%': (36, 29, 0, -29, 36, "B+AAcAH/gA4APnwA4APD4BwAfD4DwAfD4DgAfD4HAAfD4HAAfD4OAAfD4eAAfD4cAAPD44AAPnw4AAH/hwAAB+DwfgAADh/4AAHD58AAHHw8AAOHw+AAeHw+AAcHw+AA4Hw+AA4Hw+ABwHw+ADwHw+ADgHw8AHAD58AHAB/4AOAAfgA="),
            '&': (33, 29, 1, -29, 34, "AB/wAAB//gAAfg8AAH4DgAA/AMAAPwBgAB/AAAAP4AAAA/gAAAH8AAAA/wAAAD/AAAA/8B/wf/wP+H7/AOB+P8Bwfw/wOD8D/BgfgP8cD8A/zAfgD/4D+AP+AfwA/wD/AD/AP8Af4B/wP/gH//7+AP/8P/AP8B/4"),
            "'": (6, 10, 3, -28, 12, "eeeeeeeeeeA="),
            '(': (13, 35, 3, -29, 18, "AAgBwDwDwDwD4D4D8B8B+A/A/gfwP4H8D+B/A/AfwP4H8D+B/A/gPwH4B8A/APgD4A8APADwAcAC"),
            ')': (14, 35, 1, -29, 18, "QAHAA8AHgA8APgB8AfgH4A/APwD+A/gP4D+A/gP4D+A/gP4D+A/gP4D+A/APwH4B+AfAPgDwB4A8AcAEAAA="),
            '*': (19, 18, 0, -29, 20, "APAAHgADgBBwI4Yc+MfPm/B/+AP4AH8AP/wfN+fGPnDDiDgQBwAA8AAeAA=="),
            '+': (24, 24, 4, -24, 32, "ADwAADwAADwAADwAADwAADwAADwAADwAADwAADwA////////////////ADwAADwAADwAADwAADwAADwAADwAADwAADwAADwA"),
            ',': (10, 12, 0, -6, 13, "D8Pg+D4Ph+Hw/H4fA4CA"),
            '-': (12, 5, 2, -13, 16, "//////////A="),
            '.': (8, 7, 3, -7, 13, "OHz+/v58OA=="),
            '/': (14, 31, 0, -28, 14, "ADwB4AeAHgDwA8APAHwB4AeAPgDwA8APAHgB4AeAPADwA8AeAHgB4A8APADwB8AeAHgD4A8AAA=="),
            '0': (24, 29, 1, -29, 26, "AH8AA//AB8PgD8HwH4H4H4D8P4D8P4D+f4D+fwD+fwD+fwD+fwD/fwD/fwD/fwD/fwD/fwD+fwD+fwD+f4D+P4D+P4D8H4D8H4H4D8HwB8PgA//AAH8A"),
            '1': (19, 29, 4, -29, 26, "AfgA/wA/4B/8B7+Ax/AQ/gAfwAP4AH8AD+AB/AA/gAfwAP4AH8AD+AB/AA/gAfwAP4AH8AD+AB/AA/gAfwAP4D//9//+"),
            '2': (22, 29, 2, -29, 26, "D/wB//4Hw/weA/hwD/GAH8YAf4AB/gAH+AAf4AB/gAH8AAfwAD+AAP4AB/AAHwAA+AAHwAB8AAPgAB4A4fADjwAOf//5///n//+f//5///g="),
            '3': (22, 29, 2, -29, 26, "D/4B//4Hwf4eA/xwB/HAH+cAf4AB/gAH+AAf4AB/AAP4AB/AB/wAH/gAB/gAB/AAD+AAP8AA/wAD/AAP9gA/2AD/cAP5wB/nwf8f//AP/gA="),
            '4': (24, 29, 1, -29, 26, "AA/gAB/gAB/gAD/gAD/gAH/gAP/gAO/gAc/gAc/gA4/gB4/gBw/gDw/gDg/gHA/gPA/gOA/geA/gcA/gf///f///AA/gAA/gAA/gAA/gAA/gAP/+AP/+"),
            '5': (21, 28, 3, -28, 26, "f//D//4f//D//4f//DgAAcAADgAAcAADn8Af/8D4fwcB/BAH8AA/wAD+AAfwAD+AAf4AD+AAf2AD+4A/3AH88B/nwf4f/8AP8AA="),
            '6': (23, 29, 2, -29, 26, "AH/AA//wH4PgfgPB+AOD4AMPwAAfgAB/AAD8AAH4/gP//wf8fx/wfz/Afn+A/v8B/P4D+fwH8/gP5/Afz+A/j8B/H4D+HwH4PwfwPx/AH/4AD/AA"),
            '7': (21, 28, 3, -28, 26, "///3//+///3//+///3AAe4AHnAA84AHAAB4AAOAADwAAcAAHgAA4AAPAAB4AAeAADwAA8AAHgAB4AAPAADwAAeAAHgAA8AAPAAA="),
            '8': (24, 29, 1, -29, 26, "AP+AB//gD8PwH8H4P4H8P4H8P4H8P4H8P4H8P4H8H4H8H8H4D8PwA//AA//gD8P4H4H8P4D8f4D+fwD+fwD+fwD+fwD+f4D+P4D+P4H8H8P4B//wAf+A"),
            '9': (23, 29, 2, -29, 26, "AfwAH/8Afh8B+B8H8D8P4H4/wP5/Afz+A/n8B/v4D/fwH+/wP8/gf5/A/x+B/h+H/B//+A/n8AAPwAAfgAA/AAD8OAH4cAPg8A+B8H4D//gA/4AA"),
            ':': (8, 19, 3, -19, 14, "PH5+fn5+PAAAAAAAPH5+fn5+PA=="),
            ';': (10, 25, 1, -19, 14, "Dwfh+H4fh+DwAAAAAAAAAAPg+D4Ph8Hw/D4fD4HAIAA="),
            '<': (24, 21, 4, -22, 32, "AAADAAAPAAB/AAP/AB/+AP/4B//AH/4A//AA/4AA/AAA/4AA//AAH/wAA/+AAP/wAB/+AAP/AAB/AAAPAAAD"),
            '=': (24, 12, 4, -18, 32, "////////////////AAAAAAAAAAAAAAAA////////////////"),
            '>': (24, 21, 4, -22, 32, "gAAA8AAA/gAA/8AA//gAH/8AA//AAH/4AA//AAH/AAB/AAH/AA//AH/4A//AH/8A//gA/8AA/gAA8AAAgAAA"),
            '?': (19, 29, 2, -29, 22, "H/gf/8Ph/ngPzgH9wD+4A/AAfwAfwAP4AH8AH+AH+AH+AH+AD4ABgAAwAAYAAMAAAAAAAADwAD8AB+AB/AAfgAPwADwA"),
            '@': (34, 33, 2, -27, 38, "AAf8AAAP/+AAD8A+AAfAAcAHwAA4A+AAAwDwAABgeAAAHDwD48MPA/7w44Hx/Bng+D8GeDwHwZ4fAfBnB8A8GcHgDwZweAPBnB4A8GeHwHw54fAfHHg8B8ceD4P3g4Hx/8DwP8/gPAPjwAeAAAAA8AAAAD4AAAAHwAAAAHwAGAAPwD4AAP/+AAAH/AAA"),
            'A': (31, 28, -1, -28, 29, "AAfAAAAPgAAAP4AAAH8AAAD/AAAD/gAAB/wAAB/8AAA7+AAAZ/gAAcfwAAMP4AAOH+AAHB/AADA/wADgf4ABgH8ABwD/AA///gAf//4AcAH8AMAD+AOAB/gHAAfwDAAP8DgAH+H+AP/7/AH/8A=="),
            'B': (29, 28, 1, -28, 32, "f//8A///+AP4H/AfwD+A/gD+B/AH8D+AP4H8AfwP4A/gfwB/A/gH8B/A/wD//+AH//8AP4H/AfwD/A/gD/B/AD/D+AH+H8AP8P4Af4fwA/w/gB/h/AH+D+Af8H8B/x///+D///gA"),
            'C': (28, 29, 1, -29, 30, "AB/4AA//+AP8H+B/AH4P4APh/AAeH8AB4/gADj+AAOf4AAB/gAAH+AAAf4AAB/gAAH+AAAf4AAB/gAAH+AAAf4AAB/gAAD+AAAP4AB4fwAHh/AAcD+ADwH8AeAP8HwAP/+AAH/AA"),
            'D': (31, 28, 1, -28, 33, "f//wAP///AA/gf4AfwD+AP4A/gH8AP4D+AH+B/AB/A/gA/wfwAf4P4AP8H8AH+D+AD/B/AB/g/gA/wfwAf4P4AP8H8AH+D+AD/B/AB/A/gA/gfwA/wP4AfwH8AfwD+AfwB/A/wH///gD//+AAA=="),
            'E': (27, 28, 1, -28, 29, "f///z///+D+ABwfwAOD+ABwfwAOD+AAAfwAAD+AYAfwDAD+AYAfwDAD//4Af//AD+AYAfwDAD+AYAfwDAD+AAAfwAAD+AAAfwAAD+ABwfwAOD+ABwfwAOf///z///+A="),
            'F': (26, 28, 1, -28, 27, "f///n///4P8AGD/ABg/wAYP8AGD/AAA/wAAP8BgD/AYA/wGAP8BgD//4A//+AP8BgD/AYA/wGAP8BgD/AAA/wAAP8AAD/AAA/wAAP8AAD/AAA/wAB//wAf/8AA=="),
            'G': (29, 29, 1, -29, 32, "AB/8AAf//gD/A/wP4Afg/gAfD+AAeH8AA8fwAA4/gABz/AAAH+AAAP8AAAf4AAA/wAAB/gAAD/AH/n+AP/P8AB+f4AD8/wAH4/gAPx/AAfh/AA/D+AB+D+AD8D+AP4D/B/gB//8AAf+AAA=="),
            'H': (34, 28, 1, -28, 36, "f/4f/5//h//g/gA/wD+AD/AP4AP8A/gA/wD+AD/AP4AP8A/gA/wD+AD/AP4AP8A/gA/wD////AP///8A/gA/wD+AD/AP4AP8A/gA/wD+AD/AP4AP8A/gA/wD+AD/AP4AP8A/gA/wD+AD/AP4AP8H/+H/+f/4f/4="),
            'I': (16, 28, 1, -28, 18, "f/5//g/gD+AP4A/gD+AP4A/gD+AP4A/gD+AP4A/gD+AP4A/gD+AP4A/gD+AP4A/gD+AP4H/+f/4="),
            'J': (20, 36, -3, -28, 18, "B//wf/8AfwAH8AB/AAfwAH8AB/AAfwAH8AB/AAfwAH8AB/AAfwAH8AB/AAfwAH8AB/AAfwAH8AB/AAfwAH8AB/AAfwAH8AB/AAfwAH8OD+Dg/g8fwP/4A/4A"),
            'K': (34, 28, 1, -28, 33, "f/4P/h//g/+A/gAcAD+ADgAP4A8AA/gHgAD+A8AAP4HgAA/g8AAD+HAAAP44AAA/nwAAD//AAAP/+AAA//8AAD+/4AAP5/wAA/j/gAD+H/AAP4P+AA/gf8AD+A/wAP4B/gA/gD/AD+AH+AP4AP8H/+A/+f/4B/4="),
            'L': (25, 28, 1, -28, 27, "f/4AP/8AA/gAAfwAAP4AAH8AAD+AAB/AAA/gAAfwAAP4AAH8AAD+AAB/AAA/gAAfwAAP4AAH8AAD+AAB/AAA/gAAfwAAP4AOH8AHD+ADh/AB3///7///8A=="),
            'M': (40, 28, 1, -28, 42, "f/AAD/5/+AAf/g/4AB/wD/wAP/AP/AA/8A/8AHfwDv4Ad/AO/gBn8A5/AOfwDn8Ax/AOf4HH8A4/gYfwDj/Dh/AOH8OH8A4fxwfwDg/nB/AOD+YH8A4P/gfwDgf8B/AOB/wH8A4D+AfwDgP4B/AOAfgH8A4B8AfwDgAAB/AOAAAH8H/AAH/+f8AAf/4="),
            'N': (33, 28, 1, -28, 35, "f8AB/z/wAP+D+AAOAf4ABwD/gAOAf+ABwD/4AOAf/gBwDv8AOAd/wBwDn/AOAcf8BwDh/wOAcH/BwDgf4OAcD/hwDgP+OAcA/5wDgD/uAcAP/wDgA/+AcAH/wDgAf+AcAB/wDgAH+AcAAfwf8AB+D/gAPwA="),
            'O': (31, 29, 1, -29, 33, "AB/wAAH//AAP4P4AP4B+AP4A/gP4AP4H8AH8H8AB/D+AA/j/AAf5/gAP8/wAH+f4AD/P8AB/n+AAfz/AAf5/gAP8/wAH+f4AD/P8AB/j+AA/h/AAfwfwAfwP4AP4D+AP4A/gH4AP4P4AB//wAAH/AAA="),
            'P': (27, 28, 1, -28, 29, "f//wD///wD+D/AfwP8D+A/wfwH+D+AfwfwD/D+Af4fwD+D+A/wfwH+D+B/gfwf4D//+Af/+AD+AAAfwAAD+AAAfwAAD+AAAfwAAD+AAAfwAAD+AAAfwAAf/8AD//gAA="),
            'Q': (31, 36, 1, -29, 33, "AB/wAAH//AAP4P4AP4B+AP4A/gP4AP4H8AH8H8AB/D+AA/j/AAf5/gAP8/wAH+f4AD/P8AB/n+AAfz/AAf5/gAP8/wAH+f4AD/P8AB/j+AA/h/AAfwfwAf4P4AP4D+AP4A/gH4AP4P4AB//wAAH/AAAAHAAAAD4AAAA/4AAAf8AAAH+AAAA/AAAAHgA="),
            'R': (31, 28, 1, -28, 32, "f//4AP///AA/g/4AfwH+AP4B/AH8A/gD+Af4B/AP8A/gH+AfwD+AP4B/AH8B/AD+D/AB//+AA//+AAfw/gAP4P4AH8H+AD+B/AB/A/wA/gP4AfwH+AP4B/AH8A/wD+AP4B/AH+H/+B/7//A/8A=="),
            'S': (24, 29, 2, -29, 27, "Af8AB//wHwH4PgB4PAA4fAA4fAAYfAAYfgAAfwAAf8AAf/wAf//AP//wP//4H//8B//8AP/+AA/+AAH+AAD+YAB+cAB+cAB+eAB8fAD8fwH4P//gA/8A"),
            'T': (28, 28, 0, -28, 28, "/////////+AfwH4B/AfgH8B+AfwHYB/AMAH8AAAfwAAB/AAAH8AAAfwAAB/AAAH8AAAfwAAB/AAAH8AAAfwAAB/AAAH8AAAfwAAB/AAAH8AAAfwAAB/AAAH8AAH/+AAf/4A="),
            'U': (32, 28, 1, -28, 33, "//4D/v/+A/4P4ABwD+AAcA/gAHAP4ABwD+AAcA/gAHAP4ABwD+AAcA/gAHAP4ABwD+AAcA/gAHAP4ABwD+AAcA/gAHAP4ABwD+AAcA/gAHAP8ABgB/AA4AfwAOAH+AHAA/4HwAH//4AA//4AAB/wAA=="),
            'V': (32, 28, -1, -28, 29, "f/wB/n/8Af4P4AA4D/AAcA/wAHAH8ABgB/gA4AP4AMAD/AHAA/wBwAH8AYAB/gOAAP4DAAD/BwAA/wcAAH8GAAB/jgAAP4wAAD/cAAA/3AAAH/gAAB/4AAAP8AAAD/AAAA/wAAAH4AAAB+AAAAPAAA=="),
            'W': (45, 28, -1, -28, 43, "f/wD8A/z/+AfgH+D+AH8AGAfwA/gBwD/AH+AOAf4B/wBgB/AP+AcAP8B/4DgB/gd/AYAH8Dv4DAA/gZ/g4AH+DH8GAAfw4/gwAD+GH+OAAf4w/xgAD/OD+MAAP5wfzgAB/sD/cAAP/gP7AAA/8B/4AAH/AP/AAA/4A/wAAD/AH+AAAfwA/wAAD+AD8AAAPwAfgAAB+AD8AAAPgAfgAA="),
            'X': (30, 28, 0, -28, 29, "//w/8//w/8H+AHAD/AHAD/gOAB/gcAA/wcAA/44AAf5wAAP9wAAP/gAAH/AAAD/AAAD/gAAB/gAAB/wAAD/4AAD/4AAHP8AAOP+AAOH+AAcD/AA4D/gA4B/gBwA/wDgA/wf+D/+f+D/+"),
            'Y': (29, 28, -1, -28, 27, "f/wH8//gP4f4AHAf4AcA/wA4A/wDgA/gHAB/gcAB/gwAD/DgAD/OAAH+cAAH/wAAH/gAAP+AAAP4AAAfwAAA/gAAB/AAAD+AAAH8AAAP4AAAfwAAA/gAAB/AAAD+AAA//wAB//gA"),
            'Z': (26, 28, 1, -28, 28, "f///n///5wAH+cAD/nAB/xwA/4AAP+AAH/AAD/gAA/wAAf8AAP+AAH/AAB/wAA/4AAf8AAH+AAD/gAB/wAAf4AAP+AAH/AAD/gAY/4AGf8ABv+AAb///+////g=="),
            '[': (12, 34, 4, -29, 18, "f+f+fgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgfgf+f+"),
            '\\': (14, 31, 0, -28, 14, "8APgB4AeAHwA8APADwAeAHgB4APADwA8AHgB4AeADwA8APAD4AeAHgB8APADwA8AHgB4AeADwA=="),
            ']': (12, 34, 2, -29, 18, "f+f+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+B+f+f+"),
            '^': (25, 10, 3, -28, 32, "AD8AAD/AAD/wAD/8AD//AD8PwD8D8D4A/D4AHz4AB8A="),
            '_': (19, 4, 0, 5, 19, "////////////8A=="),
            '`': (11, 7, 2, -30, 19, "fAfAeAeAeAeAcA=="),
            'a': (23, 21, 1, -21, 25, "B/wAf/4A8H8BwH4DAH4AAPwAAfwAA/gAB/AP/+B//8H8P4fwfw/A/h+B/D8D+H4H8P4f4f//wf+/8Px/4A=="),
            'b': (26, 29, 0, -29, 27, "f8AAH/AAAPwAAD8AAA/AAAPwAAD8AAA/AAAPx+AD9/4A/w/AP4H4D+B/A/gfwPwH+D8A/g/AP4PwD+D8A/g/AP4PwD+D8A/g/Af4P4H8D+B/A/gfgP8Pwf9/4H/H4AA="),
            'c': (21, 21, 1, -21, 23, "AP4AP/8D+Hw/AeP4Bx+AOfwAz+AAfwAD+AAfwAD+AAfwAD+AAfwBx+AOP4Bw/AcD+HAP/wAP4AA="),
            'd': (25, 29, 1, -29, 27, "AA/8AAf+AAB/AAA/gAAfwAAP4AAH8AAD+AP5/Af//gfx/wfwf4P4H8P4D+H8B/D+A/h/Afw/gP4fwH8P4D+H8B/D+A/h/Afw/gP4P4H8H8H+B/H/Af//8D+f+A=="),
            'e': (22, 21, 1, -21, 24, "Af4AH/4A/HwH4fg/A/D8D8fwP5/A/n8D+f//5///n8AAfwAB/AAH8AAfwA4/gHB+AcD+HgH/8AH+AA=="),
            'f': (18, 29, 1, -29, 16, "AP4A/+D+OD8GH8GH8AH8AH8AH8A//4//4H8AH8AH8AH8AH8AH8AH8AH8AH8AH8AH8AH8AH8AH8AH8AH8A//g//gA"),
            'g': (25, 29, 1, -21, 27, "A/gAB///x/H/5/B/g/gfw/gP4fwH8P4D+H8B/D+A/h/Afw/gP4fwH8P4D+H8B/D+A/g/gfwfwf4H8f8B//+AP5/AAA/gAAfwcAPwOAH4HgH4D4H4B//4AH/gAA=="),
            'h': (26, 29, 1, -29, 28, "/8AAP/AAAfwAAH8AAB/AAAfwAAH8AAB/AAAfx+AH9/4B///Af8fwH+D8B/A/gfwP4H8D+B/A/gfwP4H8D+B/A/gfwP4H8D+B/A/gfwP4H8D+B/A/gfwP4//P///z/8A="),
            'i': (13, 29, 1, -29, 14, "DwD8B+A/gfgPwDwAAAAH/j/wP4H8D+B/A/gfwP4H8D+B/A/gfwP4H8D+B/H/7/8A"),
            'j': (14, 37, -3, -29, 14, "APAH4D+A/gP4B+APAAAAAD/w/8B/AfwH8B/AfwH8B/AfwH8B/AfwH8B/AfwH8B/AfwH8B/AfwH/B+4fuPz/4f4A="),
            'k': (26, 29, 1, -29, 26, "/8AAP/AAAfwAAH8AAB/AAAfwAAH8AAB/AAAfwAAH8H/B/B/wfwHAH8DgB/BwAfw4AH8cAB/PAAf34AH//AB//wAf7+AH8fwB/D+Afw/gH8H8B/A/gfwH4//H///x/8A="),
            'l': (13, 29, 1, -29, 14, "/8f+B/A/gfwP4H8D+B/A/gfwP4H8D+B/A/gfwP4H8D+B/A/gfwP4H8D+B/H/7/8A"),
            'm': (39, 21, 1, -21, 40, "AAfgPwH/v+H/A///5/8A/4/8fwH+D/B+A/gfwPwH8D+B+A/gfwPwH8D+B/A/gfwP4H8D+B/A/gfwP4H8D+B/A/gfwP4H8D+B/A/gfwP4H8D+B/A/gfwP4H8D+B/H/5/8/+//P/n/wA=="),
            'n': (26, 21, 1, -21, 28, "AAfgP/f+D///wH/H8B/g/AfwP4H8D+B/A/gfwP4H8D+B/A/gfwP4H8D+B/A/gfwP4H8D+B/A/gfwP4H8D+P/z///8//A"),
            'o': (23, 21, 1, -21, 25, "AP8AD/+APx+A/B+D+B+H4D+fwH8/gP5/Af7+A/38B/v4D/fwH+/gP5/Afx+A/j+B+D8H4D8fgD/+AA/wAA=="),
            'p': (26, 29, 0, -21, 27, "AAfgH/f+B/8PwD+B+A/gfwP4H8D8B/g/AP4PwD+D8A/g/AP4PwD+D8A/g/AP4PwH+D+B/A/gfwP4H4D/D8A/f+APx+AD8AAA/AAAPwAAD8AAA/AAAPwAAf/gAH/4AAA="),
            'q': (25, 29, 1, -21, 27, "A/gAB///x/H/5/B/g/gfw/gP4fwH8P4D+H8B/D+A/h/Afw/gP4fwH8P4D+H8B/D+A/g/gfwfwf4H8f8B//+AP5/AAA/gAAfwAAP4AAH8AAD+AAB/AAH/8AD/+A=="),
            'r': (20, 21, 1, -21, 20, "AAfv/P7/3+H/Dh/gYf4GH8AB/AAfwAH8AB/AAfwAH8AB/AAfwAH8AB/AAfwAH8AP/4D/+AA="),
            's': (19, 21, 1, -21, 21, "B/4D//j8Hz8A5+Ac/AGfwAP/AH/8B//gf/8H/+AP/gA/2AP7AH9wD84B+fB+P/+A/8A="),
            't': (18, 26, 0, -26, 18, "D8AD8AD8AD8AD8AD8Af/8f/8D8AD8AD8AD8AD8AD8AD8AD8AD8AD8AD8AD8AD8AD8GD8OD+OB/8AfwA="),
            'u': (27, 20, 0, -20, 28, "f8H/D/g/4D8B/AfgP4D8B/AfgP4D8B/AfgP4D8B/AfgP4D8B/AfgP4D8B/AfgP4D8D/Afwf4D+H/AP/v4A/5/wB8P+A="),
            'v': (25, 20, -1, -20, 22, "//B/f/g/h+AHA/gDAfwDgH8BgD+BwA/A4AfwYAP4cAD+MAB/GAAfnAAP7AAH/gAB/gAA/wAAP4AAH4AAD8AA"),
            'w': (35, 20, -1, -20, 33, "f/B8H8/+D4P4fwHwDA/gfwOA/A/gYB/B/AwD+H/DgD8P+GAH8b8MAP5384APzH5gAf2PzAA/8f+AA/wf4AB/g/wAD/B/gAD8B+AAH4D8AAPwH4AAPAHgAA=="),
            'x': (23, 20, 0, -20, 23, "//P9/+f4fwOA/wYA/xwA/nAB/sAB/4AB/gAB/AAD+AAP+AAf+AB38AHH8AMP8AwP4DgP4/z///n/8A=="),
            'y': (24, 28, -1, -20, 22, "//B///B/H8AYH8AYD+A4D+AwB+BwB/BgB/BgA/jgA/jAAfjAAf2AAP+AAP+AAP8AAH8AAH4AAD4AAD4AABwAABwAABgAGBgAGDgAHHAAH+AAD8AA"),
            'z': (20, 20, 1, -20, 22, "f//n//5gH+YB/GA/wAf4AP8AD/AB/gA/wAP4AH+AD/AB/gAfwAP8Bn+AZ/AG///v//4="),
            '{': (19, 34, 3, -29, 24, "AH/AP/gH8AH8AD+AB/AA/gAfwAP4AH8AD+AB+AA/AAfgAfwAfwD/wB/4AD+AA/gAPwAH4AD8AB/AA/gAfwAP4AH8AD+AB/AA/gAP4AH/wA/4"),
            '|': (5, 38, 4, -29, 14, "e973ve973ve973ve973ve973ve973ve8"),
            '}': (19, 34, 3, -29, 24, "/4Af/AAfwAH4AD8AB+AA/gAfwAP4AH8AD+AB/AA/gAfwAP4AD+AAf8AP+AfwAfwAP4AH8AD+AB/AA/gAfwAP4AH8AD8AB+AA/AA/gP/gH/AA"),
            '~': (24, 8, 4, -16, 32, "AAAAD8ABP/ADf/4P////8H/+wA/8AAPg"),
            '—': (34, 4, 2, -12, 38, "//////////////////////8="),
            '•': (14, 13, 5, -21, 24, "B8B/g/8f/n/5////3/9/+f/j/wf4B8A="),
        },
    },
    "serif_30": {
        "ascent": 28, "descent": 8,
        "glyphs": {
            ' ': (0, 0, 0, 0, 10, ""),
            '!': (4, 22, 4, -22, 12, "//92ZmZmZmAAb/Y="),
            '"': (9, 8, 2, -22, 14, "YbDYbDYbDYbD"),
            '#': (21, 22, 2, -22, 25, "AGHABwwAOGABhwAMOADhgP//5///AYcAHDAA4YAGDAAw4AGHA///n//8BhwAcOADhgAYMADDgA4cAA=="),
            '$': (15, 27, 2, -23, 19, "AQACAAQACAD/B/+eTziOcQziAeQD+AP+AP8AfwCeAR6CPQRzCOcTx/8D+ACAAQACAAQA"),
            '%': (26, 22, 1, -22, 28, "HwAYD+AMBxwHAcMBgGDgwBg4MAYOGAGDjgBwwwAccYAD+OHgfDH8ABhjgAY4YAMMHAHDBwBgwcAwMHAcDhgGAY4DAH8AwAeA"),
            '&': (24, 22, 2, -22, 27, "A/AAB/wADh4AHA4AHAYAHAYADgAADwAAD4AAG8D+MeD+cPAwYHgw4Dgw4Bxg4A5g8AfAcAPAeAPAPg/gH/z+B/B+"),
            "'": (4, 8, 2, -22, 8, "ZmZmZg=="),
            '(': (8, 27, 2, -23, 12, "AAYMGDgwMHBwcGDg4ODg4GBwcHAwMDgYDAYA"),
            ')': (8, 27, 2, -23, 12, "gOBwOBgcDA4ODg4ODg4ODg4ODg4MHBg4cOCA"),
            '*': (15, 14, 0, -22, 15, "AQACAQQTiOeTw/4B8APgH/ByccRyCCAQACAA"),
            '+': (19, 20, 3, -20, 25, "AOAAHAADgABwAA4AAcAAOAAHAADgH/////+AcAAOAAHAADgABwAA4AAcAAOAAHAA"),
            ',': (6, 7, 1, -3, 10, "HGOOMYQA"),
            '-': (8, 2, 1, -9, 10, "//8="),
            '.': (5, 4, 2, -4, 10, "M95g"),
            '/': (11, 25, 0, -22, 10, "AMA4BgDAOAYAwDgGAMAYBwDAGAcAwBgHAMAYBwDAGAcAwAA="),
            '0': (16, 22, 2, -22, 19, "B8Af8Dx4ODhwHHAc4A7gDuAO4A7gDuAO4A7gDuAO4A5wHHAcODg8eB/wB8A="),
            '1': (12, 22, 3, -22, 19, "BwHwPwZwBwBwBwBwBwBwBwBwBwBwBwBwBwBwBwBwf/f/"),
            '2': (15, 22, 2, -22, 19, "H8D/48HnAcwD2AOABwAMADgAYAHABwAMAHAAwAMADAwwGMAz/+//3/+A"),
            '3': (15, 22, 2, -22, 19, "D8B/4eHjgeYBzAOABwAcAHAPgB+AA8ABwAOAA4AHwA+AP4B3g+f/gfwA"),
            '4': (18, 22, 0, -22, 19, "ADgADgAHgAPgALgAbgAzgAjgBjgDDgCDgGDgMDgIDgf//f//ADgADgADgADgAf+Af+A="),
            '5': (15, 22, 2, -22, 19, "P/h/8P/hAAIABAAIABPgP/Bw8IDwAOAB4AHAA4AHQB7AOYDzg8f/AfgA"),
            '6': (16, 22, 2, -22, 19, "A/AP/BwcOAxwDHAAYADj4O/4/Dz4HPAO8A7wDvAO8A5wDnAOeBw8PB/wB+A="),
            '7': (15, 22, 2, -22, 19, "f/7//f/6AGQAyAMABgAYADAAYAGAAwAMABgAYADAAYAGAAwAMABgAcAA"),
            '8': (16, 22, 2, -22, 19, "D+A/+Dg4cBxwHHAccBxwHDg4D+Af8Dg4cBzgDuAO4A7gDuAOcBx4PD/4D+A="),
            '9': (17, 22, 1, -22, 19, "B+AH/AcPBwPHAOOAccA84A5wBzgHnAPHAePD8P+4HxwADAAOGAcMBwcHA/8AfgA="),
            ':': (4, 13, 3, -13, 10, "b/YAAAb/YA=="),
            ';': (7, 17, 1, -13, 10, "GHjwwAAAAAAAcMOHDDBA"),
            '<': (19, 16, 3, -17, 25, "AAAgADwAP4A/gD+AH8AfwAfAAPgAD+AAP4AB/AAH8AAfwAB4AAE="),
            '=': (19, 8, 3, -14, 25, "//////wAAAAAAAAAAAA//////w=="),
            '>': (19, 16, 3, -17, 25, "wAAeAAP4AA/gAD+AAfwAB/AAHwAD4AP4AfgB/AH8AfwAPAAGAAA="),
            '?': (13, 22, 2, -22, 16, "P4f/OD2A7AcAPADgDgBwA4A4B4DwBgAwAYAAAAADADwB4AYA"),
            '@': (26, 26, 2, -21, 30, "AD+AAH/8AHwHwDwAOBwABw4AAMMAABnA+YJgf2DYOHg+HA4PhwGDwYBg+GAYLhwGG4cDjuDh5xgf3wcD5wDAAAA4AAAHAAAA8ACAHwHAAf/gAA/gAA=="),
            'A': (23, 22, -1, -22, 22, "ADgAAHgAAPAAA+AAB+AAGcAAM8AAQ4ABhwADDwAMDgAYHAAwPADAOAH/+Af/8AwA4BgB4GABwMADx+Af78A/wA=="),
            'B': (20, 22, 1, -22, 22, "f/4H//gcB4HAPBwBwcAcHAHBwDwcB4H/4B//AcA8HAHBwA4cAOHADhwA4cAOHAHhwDx//4f/4A=="),
            'C': (21, 22, 1, -22, 23, "AP4AH/4DwPw8AePABxwAOeAAzgAAcAADgAAcAADgAAcAADgAAcAADwAAOABw4AOHgDgeB4A/+AB/AA=="),
            'D': (22, 22, 1, -22, 24, "f/gB//wBwHwHAHgcAPBwAcHAB4cAHhwAOHAA4cADhwAOHAA4cADhwAeHAB4cAHBwA4HAHgcB8H//Af/gAA=="),
            'E': (19, 22, 1, -22, 22, "f//P//hwAw4AYcAMOAAHAIDgEBwCA//Af/gOAQHAIDgEBwAA4AAcAAOADHABjgA3//7//8A="),
            'F': (19, 22, 1, -22, 21, "f//v//xwAY4AMcAGOAAHAMDgGBwDA//gf/wOAYHAMDgGBwAA4AAcAAOAAHAADgAH/AD/gAA="),
            'G': (21, 22, 1, -22, 24, "AP8AH/8DwHw8AePABxwAGeAAzgAAcAADgAAcAADgAAcAP7gB/cAA7wAHOAA54AHHgB4fA+A//gB/gA=="),
            'H': (24, 22, 1, -22, 26, "f4H/f4H/HAA4HAA4HAA4HAA4HAA4HAA4HAA4H//4H//4HAA4HAA4HAA4HAA4HAA4HAA4HAA4HAA4HAA4f4H/f4H/"),
            'I': (10, 22, 1, -22, 12, "f5/hwHAcBwHAcBwHAcBwHAcBwHAcBwHAcH+f4A=="),
            'J': (14, 28, -3, -22, 12, "D/w/8A4AOADgA4AOADgA4AOADgA4AOADgA4AOADgA4AOADgA4AOADjA4wcOHB/gHwA=="),
            'K': (22, 22, 1, -22, 22, "f4f5/h/hwBwHAMAcBgBwMAHDgAccABzgAH4AAfgAB/gAHfAAc+ABx8AHD4AcHwBwPgHAfAcA+H+B/f4D8A=="),
            'L': (19, 22, 1, -22, 20, "f4AP8ABwAA4AAcAAOAAHAADgABwAA4AAcAAOAAHAADgABwAA4AAcAMOAGHADDgBn//z//4A="),
            'M': (29, 22, 1, -22, 31, "/gAD9/gAP4fAAeA/AB8B+AD4DeANwGcAbgM8BnAY4DOAx4McBhwY4DDwhwGDjDgMHkHAYHYOAwPgcBgPA4DAcBwGAADgMAAHB/AA/z+AB/g="),
            'N': (24, 22, 1, -22, 26, "/AD//gD/HwAYH4AYH8AYG8AYGeAYGPAYGHgYGHgYGDwYGB4YGA8YGAcYGAeYGAPYGAH4GAD4GAD4GAB4/wA4/wAY"),
            'O': (22, 22, 1, -22, 25, "AP4AD/4A8DwHgDgcAHDgAeeAA5wADnAAPcAA9wAB3AAHcAA9wAD3AAOeAA44AHhwAcHgDgPA8AP/gAP4AA=="),
            'P': (19, 22, 1, -22, 20, "f/wP/+BwHg4B4cAcOAOHAHDgDhwDw4Dwf/wP/gHAADgABwAA4AAcAAOAAHAADgAH/AD/gAA="),
            'Q': (22, 27, 1, -22, 25, "AP4AD/4A8DwHgDgcAHDgAeeAA5wADnAAPcAA9wAB3AAHcAA9wAD3AAOeAA44AHjwAcHgDgPA8AP/gAPwAADAAAHAAAfgAA+AAA4A"),
            'R': (23, 22, 1, -22, 23, "f/4A//8AcB4A4B4BwBwDgDgHAHAOAOAcA8A4DwB//AD/4AHA8AOA4AcB4A4BwBwDwDgDgHAHgOAHB/wPz/gPgA=="),
            'S': (17, 22, 2, -22, 21, "B+AP/g4HjgHHAGMAMcAI4AB4AB8AB/gA/4AH4AB4ABzADmAHMAOcAc8Dw//AP4A="),
            'T': (20, 22, 0, -22, 20, "///////AYDwGA8BgMAYAAGAABgAAYAAGAABgAAYAAGAABgAAYAAGAABgAAYAAGAABgAD/AA/wA=="),
            'U': (23, 22, 1, -22, 25, "/4D//wH8cADA4AGBwAMDgAYHAAwOABgcADA4AGBwAMDgAYHAAwOABgcADA4AGA4AMBwAYDwBgDwPAD/8AB/gAA=="),
            'V': (24, 22, -1, -22, 22, "f4B+f4B+HAAYHgAQDgAwDwAwBwBgBwBgB4BAA4DAA8DAAcGAAcGAAeEAAOMAAPMAAHYAAHYAAH4AADwAADwAADgA"),
            'W': (31, 22, 0, -22, 31, "/wGA//4DgfzwDwBA4B4AgcA+AwOA3AYDgbgIBwNwMA4EcGAeGOCAHDHBADhDxgBxg4wAcwcQAOYOYAHIDsAD8B0AA+A+AAeAfAAPAHgADgDgABwBwAA="),
            'X': (22, 22, 0, -22, 21, "/4fz/h/B4BgDgGAPAwAeGAA4YADzAAH4AAPAAAcAAB4AAPwABnAAGeAAw8AGBwAwHgDAPAYAeP4H+/gf4A=="),
            'Y': (22, 22, -1, -22, 20, "f4H5/gfh4AYDgDAPAIAcBgA4MADwgAHGAAOwAA/AAB4AAHAAAcAABwAAHAAAcAABwAAHAAAcAAH+AAf4AA=="),
            'Z': (19, 22, 1, -22, 21, "f//P//mADjADhgDwADwABwAB4AB4AA4AA4AA8AA8AAcAAcAAeAAOAAOADPABvAA3/////8A="),
            '[': (8, 27, 2, -23, 12, "fn5gYGBgYGBgYGBgYGBgYGBgYGBgYGBgYH5+"),
            '\\': (11, 25, 0, -22, 10, "wBwBgDAHAGAMAcAYAwBwBgDAHAGAMAYA4AwBgDgDAGAOAMA="),
            ']': (8, 27, 2, -23, 12, "/v4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODv7+"),
            '^': (19, 8, 3, -22, 25, "AOAAPgAP4AOOAODgOA4MAGMABg=="),
            '_': (15, 2, 0, 5, 15, "/////A=="),
            '`': (8, 6, 2, -24, 15, "cDAYHAwG"),
            'a': (17, 15, 1, -15, 18, "D8Af+A4eBgcCAYAA4D/wf/h4HDgOHAcOA4eHwf74fnw="),
            'b': (18, 23, 0, -23, 19, "fAAfAAHAAHAAHAAHAAHAAHAAHHwHf4Hw8HgOHgOHAOHAPHAHHAPHAOHgOHgOHw8ff4fHwA=="),
            'c': (15, 15, 1, -15, 17, "B+A/8PDzwOcAzgGcADgAcADgAcAzwGPDg/4B+AA="),
            'd': (18, 23, 1, -23, 19, "AH4AH4AA4AA4AA4AA4AA4AA4B44H+4PD4eB4cA4cA4cA4cA4cA4cA4cA4eB4PD4H++B8+A=="),
            'e': (16, 15, 1, -15, 18, "B+Af8Dw4eBxwDHAOcA5//n/+cABwBnAMPBwf+Afg"),
            'f': (12, 23, 1, -23, 11, "B+D/HDHDGAGAGAGA/8/8GAGAGAGAGAGAGAGAGAGAGA/4/4A="),
            'g': (18, 21, 1, -15, 19, "B8+H++PD4eB4cA4cA4cA4cA4cA4cA4cA4eB4PD4H+4B44AA4AAwMBwODgP/gD+AA"),
            'h': (18, 23, 1, -23, 19, "+AA+AAGAAGAAGAAGAAGAAGAAGPgGfwHh4HA4HA4GA4GA4GA4GA4GA4GA4GA4GA4/z+/z+A=="),
            'i': (8, 21, 1, -21, 10, "ODg4AAAA+PgYGBgYGBgYGBgYGP//"),
            'j': (10, 27, -3, -21, 9, "AYDgGAAAAAD4PgGAYBgGAYBgGAYBgGAYBgGAYBsOw7/H4A=="),
            'k': (19, 23, 0, -23, 18, "fAAPgABwAA4AAcAAOAAHAADgABw/w4f4cDAODAHDADnAB3gA/4AecAOHAHBwDgcBwHD/P5/n8A=="),
            'l': (9, 23, 0, -23, 10, "fD4HA4HA4HA4HA4HA4HA4HA4HA4HA4HD/f4="),
            'm': (27, 15, 1, -15, 28, "+PB8Hz+fwHh2PA4Hg4HA4HAwHA4GA4HAwHA4GA4HAwHA4GA4HAwHA4GA4HH+fz//z+f4"),
            'n': (18, 15, 1, -15, 19, "+Pg+fwHh4HA4HA4GA4GA4GA4GA4GA4GA4GA4GA4/z+/z+A=="),
            'o': (16, 15, 1, -15, 18, "B+Af+Dw8eB5wDnAOcA5wD3AOcA5wDngePDwf+Afg"),
            'p': (18, 21, 0, -15, 19, "fHwff4Hw8HgOHgOHAOHAPHAHHAPHAOHgOHgOHw8Hf4HHwHAAHAAHAAHAAf4Af4AA"),
            'q': (18, 21, 1, -15, 19, "B8+H++PD4eB4cA4cA4cA4cA4cA4cA4cA4eB4PD4H+4B44AA4AA4AA4AA4AH+AH+A"),
            'r': (14, 15, 1, -15, 14, "+Pvn4eGHAhwAYAGABgAYAGABgAYAGAP8D/AA"),
            's': (13, 15, 1, -15, 15, "D4H/HBzAZgM4APgD+AHwA9AOwHcHH/g/AA=="),
            't': (12, 20, 0, -20, 12, "HAHAHAHAHAf+f+HAHAHAHAHAHAHAHAHDHDDmD+B8"),
            'u': (19, 15, 0, -15, 19, "fB8Pg+BwHA4DgcBwOA4HAcDgOBwHA4DgcBwOB4Dh8B/vgPHw"),
            'v': (18, 15, -1, -15, 17, "fw/fw/HAMHAIDgYDgYBwwBwwAxgA5gA5AAfAAeAAOAAOAA=="),
            'w': (26, 15, 0, -15, 26, "/w4Pv8OD44DgIHB8GBwfBgcFwQDjOMA4zjAGI4gB2HYAdh2ADwfAA8DwAPA4ABgGAA=="),
            'x': (17, 15, 0, -15, 17, "/j9/H4cCAcMA8wA7AA8AA4AD4AF4AZwBhwGBw/P9+f4="),
            'y': (18, 21, -1, -15, 17, "fw/fw/HAMHAIDgYDgYBwwBwwAxgA5gA5AAfAAeAAOAAOAAMAAMAAIAMYAPwAPgAA"),
            'z': (14, 15, 1, -15, 16, "f/n/5AMQHEDgBwA4AcAGADgBwM4DcA/////A"),
            '{': (13, 28, 3, -23, 19, "APAfgOAOAHADgBwA4AcAOAHADgDgPgHwAcAHADgBwA4AcAOAHADgBwAcAPwB4A=="),
            '|': (4, 30, 3, -23, 10, "ZmZmZmZmZmZmZmZmZmZm"),
            '}': (13, 28, 3, -23, 19, "eAPwA4AOAHADgBwA4AcAOAHADgA4APgHwHAHADgBwA4AcAOAHADgBwBwH4DwAA=="),
            '~': (19, 6, 3, -13, 25, "AAAD4AX/g/B/6AHwAAAA"),
            '—': (28, 2, 1, -9, 30, "/////////w=="),
            '•': (10, 9, 4, -15, 18, "Hg/H+f5/n+f4/B4A"),
        },
    },
    "serif_26": {
        "ascent": 25, "descent": 7,
        "glyphs": {
            ' ': (0, 0, 0, 0, 8, ""),
            '!': (4, 19, 3, -19, 10, "d3d2ZmZmZgBnYA=="),
            '"': (8, 7, 2, -19, 12, "ZmZmZmZmZg=="),
            '#': (18, 19, 2, -19, 22, "AYYAYYAY4A4wAwwf//f//BxgBhgBhgBhgBjA//8//8DDADGAGGAGGAGGAA=="),
            '$': (13, 23, 2, -19, 17, "BgAwAYA/h28zG5jcwPYD8AfwD8BvAzsY2MbGdzcP4AwAYAMAAAA="),
            '%': (23, 19, 1, -19, 25, "HgDAZgMBhgYDDBgMGCAYMMAYYwAwxgAzGAA8YeAAxmADGGAEMMAYYYBgwwDBhgMDDAwDMBgDwA=="),
            '&': (21, 19, 1, -19, 23, "A/AAMOADAwAYGADAAAcAADwAAeAAG4PxjgIcODDg4YYDiDAOwcB8DgHgOAeA4P4B/H4="),
            "'": (3, 7, 2, -19, 7, "bbbY"),
            '(': (7, 24, 2, -20, 10, "BBhhgwwYMOHDhw4cOHBgwYGDAwMC"),
            ')': (8, 24, 1, -20, 10, "QGAwGBwMDA4ODg4GDg4ODg4MDBwYMGBA"),
            '*': (13, 12, 0, -19, 13, "AgAQEITk4/4HwD4H/HJyEICABAA="),
            '+': (18, 16, 2, -16, 22, "AMAAMAAMAAMAAMAAMAAMAf/+f/+AMAAMAAMAAMAAMAAMAAMA"),
            ',': (5, 6, 1, -3, 8, "OYzmYA=="),
            '-': (7, 2, 1, -8, 9, "//w="),
            '.': (4, 3, 2, -3, 8, "Z2A="),
            '/': (9, 21, 0, -19, 9, "AYGAwGBgMBgYDAYGAwGBgMBgYDAYHAwA"),
            '0': (14, 19, 1, -19, 17, "B8Bxg4MMDnAZwGcB2AdgHYB2AdgHcB3AZwGMDjgwcYB8AA=="),
            '1': (10, 19, 3, -19, 17, "Dg+H4zgOA4DgOA4DgOA4DgOA4DgOA4f8"),
            '2': (13, 19, 1, -19, 17, "H4OHGByAYAOAHADABgBwAwAwAwAwAwAwAwMwG//f/g=="),
            '3': (14, 19, 1, -19, 17, "H8DhwgMIDgA4AOADADgHwAHAA4AGABgAcAHYBmA5wcH8AA=="),
            '4': (16, 19, 0, -19, 17, "AHAA8AHwAfADcAZwBnAMcAhwGHAwcDBwYHB//gBwAHAAcABwA/4="),
            '5': (13, 19, 2, -19, 17, "f+P/EACABAAgAf4OGGBgA4AMAGADgBgA2A7AZwYP4A=="),
            '6': (14, 19, 1, -19, 17, "A+Aw4YGMBjABwAZ8Hxx4OcBnAdwHcB3AdwHMBjg4ccB8AA=="),
            '7': (13, 19, 2, -19, 17, "////8A2AYAYAMAEAGADADABgBgAwAYAYAMAMAGACAA=="),
            '8': (14, 19, 1, -19, 17, "D8BhwwOcDnAZwOMDhhwPwGHDA5wGcB2AdwHcBjA44cD8AA=="),
            '9': (14, 19, 1, -19, 17, "D8BhgwMcDmAZgGYB2AdgHcDzA8YfD5gAYAGIDDAwwYH4AA=="),
            ':': (5, 11, 2, -11, 9, "c5wAAABznA=="),
            ';': (6, 14, 1, -11, 9, "OOOAAAAAOOMcYwA="),
            '<': (18, 14, 2, -15, 22, "AACAAeAD8AfgB+APwAeAAeAAPwAB+AAfgAD8AAeAACA="),
            '=': (18, 7, 2, -12, 22, "f/+f/+AAAAAAAAAf/+f/+A=="),
            '>': (18, 14, 2, -15, 22, "QAAeAAPwAD8AAfgAD8AAeAAeAD8AfgD8APwAeAAQAAA="),
            '?': (12, 19, 1, -19, 14, "P4ccYOQGAHAHAHAOAeA8DwDADADAAAAADADgDAA="),
            '@': (24, 23, 1, -18, 26, "AH8AAcDABgAwDAAQGAAIMD2EMOOEcMGCYYGCYYGCYYGCYYGCYYGCYYGGYYGEcMGIMOOQMD3AGAAADAAABgBgA8HAAH8A"),
            'A': (21, 19, -1, -19, 19, "AHAAA4AAPAAB8AALgADMAARwAGOAAw4AEHABgYAIDgB/8AYBgCAOAwBwGAHAgA4fAfw="),
            'B': (17, 19, 1, -19, 19, "//gMDgYDgwHBgHDAcGA4MDgf+AwHBgHDAOGAMMAYYAwwDhgHDAc//gA="),
            'C': (18, 19, 1, -19, 20, "AfwDgeHAOOAGMAGcAAcAAYAAYAA4AAYAAYAAcAAcAAMAGOAOHAcDg4A/gA=="),
            'D': (19, 19, 1, -19, 21, "//ADA4BgHAwBgYA4MAOGAHDADhgBwwA4YAcMAOGAHDADhgDgwBgYBwMDg//AAA=="),
            'E': (16, 19, 1, -19, 19, "//8YAxgDGAMYABgAGAgYCB/4GAgYCBgAGAAYABgAGAMYAxgD//8="),
            'F': (16, 19, 1, -19, 18, "//8YAxgDGAMYABgAGAgYCB/4GAgYCBgAGAAYABgAGAAYABgA/wA="),
            'G': (18, 19, 1, -19, 21, "Af4DgeHAOOAGMAGcAAcAAYAAYAA4AAYA/YAHcAHcAHMAHOAHHAHDgeAfwA=="),
            'H': (21, 19, 1, -19, 23, "/wfwwA4GAHAwA4GAHAwA4GAHAwA4H//AwA4GAHAwA4GAHAwA4GAHAwA4GAHAwA4/wfw="),
            'I': (8, 19, 1, -19, 10, "/xgYGBgYGBgYGBgYGBgYGBgY/w=="),
            'J': (13, 24, -3, -19, 10, "D/AOAHADgBwA4AcAOAHADgBwA4AcAOAHADgBwA4AcAOEHDDBjgfA"),
            'K': (19, 19, 1, -19, 19, "/w/DAMBgMAwMAYMAMMAGMADMAB8AA/AAfgAM4AGOADDgBg4AwOAYDgMA4/wPgA=="),
            'L': (16, 19, 1, -19, 17, "/wAYABgAGAAYABgAGAAYABgAGAAYABgAGAAYABgAGAMYAxgD//8="),
            'M': (25, 19, 1, -19, 27, "/AAfDwAeB4APA+APgXAFwJgG4E4CcCMDOBHBHAhgjgQ4xwIMQ4EHYcCD4OBA8HAgcDgQEBwIAA4/gB/A"),
            'N': (21, 19, 1, -19, 23, "+AP44AYHgDA+AYFwDAnAYEcDAhwYEGDAg4YEDjAgOYEAzAgHYEAfAgB4EAHAgA4/gDA="),
            'O': (19, 19, 1, -19, 21, "AfgBwcBwDBwAwwAc4AOcADMAB2AA/AAdgAOwAHcADOADjABxwAwcAwHBwAfgAA=="),
            'P': (16, 19, 1, -19, 18, "//AYHBgOGA4YBhgHGAYYDhgOGBwf8BgAGAAYABgAGAAYABgA/wA="),
            'Q': (19, 23, 1, -19, 21, "AfgBwcBwDBwAwwAc4AOcADMAB2AA/AAdgAOwAHcADOADjABxwAwcAwHBwAfgABgAAYAAHgAAwA=="),
            'R': (20, 19, 1, -19, 20, "//gBgcAYDgGAcBgHAYBwGAcBgOAYHAH/ABg4AYHAGAwBgOAYBgGAcBgHAYA4/wPg"),
            'S': (14, 19, 2, -19, 18, "D+DB5gG4BuAbgA4AHgB/AH+Af4AeABwAfAHwB+AbwMH8AA=="),
            'T': (18, 19, 0, -19, 17, "//+wcCwcCwcCAcAAcAAcAAcAAcAAcAAcAAcAAcAAcAAcAAcAAcAAcAB/AA=="),
            'U': (20, 19, 1, -19, 22, "/wfxgAgYAIGACBgAgYAIGACBgAgYAIGACBgAgYAIGACBgAgcAYHAGAwBAHBgA/wA"),
            'V': (21, 19, -1, -19, 19, "fwHw4AIHADAYAQDgGAcAwBwEAOBgBwIAHBAA4YADCAAcwADmAAOgAB8AAPAAA4AAHAA="),
            'W': (27, 19, 0, -19, 27, "/gYH5wDAMOA8BAwHgIHAsDA4NwYDBOCAYIwQDhGGAcY4gBiHEAOQZgB2DsAOwdAA8DoAHgPAA8B4ADAOAAYAwAA="),
            'X': (19, 19, 0, -19, 19, "/x/DgMBwEAcGAPGADiAA7AAfAAHgABwAB8AAuAAzgAxwAQcAYHAYDgIA4/B/AA=="),
            'Y': (19, 19, -1, -19, 17, "fwfDgCBwDAcBAHBgDhgA4gAcwAHQAB4AA4AAcAAOAAHAADgABwAA4AAcAA/gAA=="),
            'Z': (17, 19, 1, -19, 18, "f/8gBxAHiAeAA4ADgAPAA8ABwAHgAeAA4ADwAPAAcAB4BngDOAG//8A="),
            '[': (7, 23, 2, -20, 10, "/cOHDhw4cOHDhw4cOHDhw4cOHD8A"),
            '\\': (9, 21, 0, -19, 9, "wHAYDAYBgMBgGAwGAYDAYBgMBgGAwGAY"),
            ']': (6, 23, 2, -20, 10, "/HHHHHHHHHHHHHHHHHHHHH/A"),
            '^': (17, 7, 2, -19, 22, "AeAB+AH+AcOBwOHAOYAO"),
            '_': (13, 1, 0, 5, 13, "//g="),
            '`': (6, 5, 2, -21, 13, "YcMGDA=="),
            'a': (14, 13, 1, -13, 16, "H4HDBgYYGABwf8cHGBzgc4HGBxw8H3w="),
            'b': (16, 20, 0, -20, 17, "eAAYABgAGAAYABgAGAAZ8B4YHAwcDhgOGAYYBhgGGA4cDhwMHhh58A=="),
            'c': (13, 13, 1, -13, 15, "D8HDnAzAZgBwA4AcAGADAYwMcMD4AA=="),
            'd': (15, 20, 1, -20, 17, "APgAcADgAcADgAcADgecOPjg8YDjAc4DnAc4DjAcYDjgcOHgffA="),
            'e': (14, 13, 1, -13, 15, "D4DjgwccDGA7gO//uABgAYBjAw4YD8A="),
            'f': (12, 20, 0, -20, 10, "A8DmDCHCHAHAHAf4HAHAHAHAHAHAHAHAHAHAHAf4"),
            'g': (15, 18, 1, -13, 17, "D75w8cDjAcYDnAc4DnAcYDjAccHhw8D7gAcIDBAYMGA/AA=="),
            'h': (17, 20, 0, -20, 17, "fAAOAAcAA4ABwADgAHAAO+AeOA4OBwcDgYHAwOBgcDA4GBwMDgYHAw/n4A=="),
            'i': (8, 19, 0, -19, 8, "GBgYAAAAfBwcHBwcHBwcHBwcfw=="),
            'j': (9, 24, -3, -19, 8, "AwGAwAAAAD4HA4HA4HA4HA4HA4HA4Gw2G5h4"),
            'k': (16, 20, 0, -20, 16, "eAAYABgAGAAYABgAGAAYfhgwGGAYwBmAG4AfwBzgGHAYcBg4GBx+fw=="),
            'l': (8, 20, 0, -20, 8, "eBgYGBgYGBgYGBgYGBgYGBgYGH8="),
            'm': (24, 13, 0, -13, 25, "ffHwHjo4HBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcf39/"),
            'n': (17, 13, 0, -13, 17, "ffAPHAcHA4OBwMDgYHAwOBgcDA4GBwMDgYfz8A=="),
            'o': (14, 13, 1, -13, 16, "D8DhgwMYDmA7gG4BuAZgOYDjAw4YD8A="),
            'p': (16, 18, 0, -13, 17, "efAeGBwMHA4YDhgGGAYYBhgOHA4cDB4YGfAYABgAGAAYAH8A"),
            'q': (15, 18, 1, -13, 17, "D75w8cDjAcYDnAc4DnAcYDjAccHhw8D7gAcADgAcADgB/A=="),
            'r': (13, 13, 0, -13, 12, "fPD/h4Q4AcAOAHADgBwA4AcAOAfwAA=="),
            's': (11, 13, 1, -13, 13, "H44ZgzAmAPgH4B4A+A8D8GP4"),
            't': (11, 17, 0, -17, 10, "GAMAYAwH/DAGAMAYAwBgDAGAMAYw5g+A"),
            'u': (16, 13, 0, -13, 17, "eHwYHBgcGBwYHBgcGBwYHBgcGBwcHAw8B58="),
            'v': (16, 13, -1, -13, 15, "fh8YDBwIHAgMGA4QBjAHIANgA+ADwAHAAYA="),
            'w': (22, 13, 0, -13, 22, "/hh84OBDg4MGDwwcbCBxMYDE5gOxkA6GwB4fAHg4AcDgAwOA"),
            'x': (15, 13, 0, -13, 15, "/HxwYHGAcgDoAPAA4AHABcAZwGHAg4fPwA=="),
            'y': (16, 18, -1, -13, 15, "fh8YDBwIDAgMGA4QBjAHIANgA8ABwAHAAYABgAEAIwAyADwA"),
            'z': (12, 13, 1, -13, 14, "//wOwcAcA4BwDgHgHAOAcD4D//A="),
            '{': (11, 24, 3, -20, 17, "A8DAOAcA4BwDgHAMAYBweAHAGAMAcA4BwDgHAOAcAYAe"),
            '|': (3, 26, 3, -20, 9, "2222222222222A=="),
            '}': (11, 24, 3, -20, 17, "+AOAMAYAwBgDAGAMAcAYAeBgHAMAYAwBgDAGAMAYBweA"),
            '~': (18, 5, 2, -11, 22, "AAAHwCf8GYf8AD4A"),
            '—': (24, 2, 1, -8, 26, "////////"),
            '•': (9, 8, 3, -13, 15, "HB+fz+fz+Pw4"),
        },
    },
    "serif_bold_26": {
        "ascent": 25, "descent": 7,
        "glyphs": {
            ' ': (0, 0, 0, 0, 9, ""),
            '!': (6, 19, 3, -19, 11, "+eeeccccMMMMMAce+ecA"),
            '"': (10, 7, 2, -19, 14, "47juO47juO44"),
            '#': (20, 19, 1, -19, 22, "AMOAHDABxwAccAGHA//+P//j//4DjgBwwAccB//8f//H//wOOADjgA44AcMAHHAA"),
            '$': (14, 22, 2, -19, 18, "AwAMADAH+Ds5zGcxvsD/Af8H/w/+D/wP8DPwz+M7zcP+AMADAAwA"),
            '%': (25, 19, 0, -19, 25, "HwBgHcBgHHAwDjgwBx44A48YAccYAOOMADuMAA+MPgAGc4AGOeAHPHADHjgDDxwBh44Bgc8BgOcAwB8A"),
            '&': (22, 19, 1, -19, 23, "A/gAPDgA8GAHwYAfAAA+AAD8AAf4fznwIefgh4/GPh+Y+D/D4H8PgPgfAfB+D+D/98B+D8A="),
            "'": (4, 7, 2, -19, 8, "7u7u4A=="),
            '(': (9, 24, 2, -20, 12, "AIGBgcHB4PDweDweHw+DweDweB4PA4HgMAwB"),
            ')': (9, 24, 1, -20, 12, "gDAOA4Hg8DweDwfD4fD4fD4eDweHg8HBwYEA"),
            '*': (13, 12, 0, -19, 14, "AwAYCMTmc78H4D8HfnM5GIDABgA="),
            '+': (18, 17, 2, -17, 22, "AcAAcAAcAAcAAcAAcAAcAf/+f/+f/+AcAAcAAcAAcAAcAAcAAcAA"),
            ',': (7, 8, 0, -4, 9, "Hjhx448cMA=="),
            '-': (9, 3, 1, -9, 11, "/3+/wA=="),
            '.': (5, 5, 2, -5, 9, "d//3AA=="),
            '/': (10, 21, 0, -19, 10, "AYDgOAwHAcBgOA4DAcBwHA4DgOBwHAcDgOAA"),
            '0': (16, 19, 1, -19, 18, "B+AeeDw8PD58HnweeB/4H/gf+B/4H/gfeB98HnwePD48PB54B+A="),
            '1': (13, 19, 3, -19, 18, "D4H8H+GfAPgHwD4B8A+AfAPgHwD4B8A+AfAPgHwf/g=="),
            '2': (15, 19, 1, -19, 18, "H+Dh8YHzA+YH4AfAH4A+AHwA8APADwA8AOAHAZwDf/7//f/4"),
            '3': (16, 19, 1, -19, 18, "H+Bw+GB8YH4APgB+AHwA+AfgAPgAfAA+AD4APkA+YD5gfHD4H+A="),
            '4': (17, 19, 1, -19, 18, "APgA/AD+AH8Ab4A3wDPgOfAY+Bh8HD4MHw4Ph//4A+AB8AD4AHwB/8A="),
            '5': (15, 19, 2, -19, 18, "f/j/8f/jAAYADAAb8Dj4QPgA8AHwA+AHwA+wH2A8wPnD4P8A"),
            '6': (16, 19, 1, -19, 18, "A/gPDhwGPAY8AHgAf/B+PHw+fD58HnwffB98H3wePD48PA48B/A="),
            '7': (14, 19, 2, -19, 18, "///////wB8A7AOAHABwAYAOADABwAYAOADABwAYAOADAAA=="),
            '8': (16, 19, 1, -19, 18, "D/A+fDw+fD58Pnw+PDwefA/wPjx8Pnwe+B/4H/gffB58Pj48D/A="),
            '9': (16, 19, 1, -19, 18, "D+AeeDw8fDx8Pvg++D74Pnw+fD58Pj5+D94AHgA8YDxwOHhwH8A="),
            ':': (6, 13, 2, -13, 10, "ce+ecAAAce+ecA=="),
            ';': (8, 17, 0, -13, 10, "HB4+HhwAAAAAHh4eHDx4cCA="),
            '<': (18, 15, 2, -16, 22, "AACAAeAD+AP8B/gP8AfgAeAAfgAP8AB/gAP8AD+AAeAACA=="),
            '=': (18, 9, 2, -13, 22, "f/+f/+f/+AAAAAAAAAf/+f/+f/+A"),
            '>': (18, 15, 2, -16, 22, "QAAeAAfwAP8AB/gAf8AD+AA+AD+AP8B/gP8AfwAeAAQAAA=="),
            '?': (14, 19, 1, -19, 15, "H8HHxg8QPgD4A+APgHwD4B4AYAGABgAAAOADwB8APADgAA=="),
            '@': (24, 23, 1, -18, 26, "AH8AA8DABwAwDgAYHAAIOH3MMOPEccPGccHCccHCY8HCY8HCY8HGccHGccHEccPMMOPQOH3gHAAADgAABwBgA8HgAH8A"),
            'A': (22, 19, -1, -19, 20, "AHgAAeAAD8AAPwAA/AAG+AAb4ABPgAMfAAh8AGD4AYPgB/+AMB8AgHwGAPgYA+BAD4fAf4A="),
            'B': (20, 19, 1, -19, 22, "//4B8PgfB8HwfB8HwfB8HwfB8Pgf/gHw+B8HwfA+HwPh8D8fA+HwPh8H4fD8//4A"),
            'C': (19, 19, 1, -19, 21, "AfwB8PB4Bx8A58AM+AGfAAfgAPwAH4AD8AB+AAfAAPgAHwAx8A4eAYHw4AfwAA=="),
            'D': (21, 19, 1, -19, 23, "//wA+HgHwfA+B8HwPg+A+HwHw+A+HwHw+A+HwHw+A+HwHw+A+HwPg+B8HwfA+Hg//wA="),
            'E': (18, 19, 1, -19, 20, "//+HwGHwGHwGHwAHwAHwAHwwHwwH/wHwwHwwHwAHwAHwAHwCHwCHwC//+A=="),
            'F': (18, 19, 1, -19, 18, "//+HwGHwGHwGHwAHwAHwAHwwHwwH/wHwwHwwHwAHwAHwAHwAHwAHwA/+AA=="),
            'G': (20, 19, 1, -19, 22, "AfwA+DgeAePgDnwA58AGfAAPwAD8AA/AAPwP78AefAHnwB58AePgHh4D4Ph8Af4A"),
            'H': (23, 19, 1, -19, 25, "/8f8PgPgfAfA+A+B8B8D4D4HwHwPgPgfAfA//+B8B8D4D4HwHwPgPgfAfA+A+B8B8D4D4/8f8A=="),
            'I': (10, 19, 1, -19, 12, "/8fB8HwfB8HwfB8HwfB8HwfB8HwfB8/8"),
            'J': (14, 24, -2, -19, 12, "H/gPgD4A+APgD4A+APgD4A+APgD4A+APgD4A+APgD4A+APgD4w8MfA/A"),
            'K': (23, 19, 1, -19, 23, "/8P4PgOAfAwA+DAB8MAD4wAHzAAPuAAf8AA/8AB/8AD78AHz8APj8AfD8A+D4B8D4D4D4/8D8A=="),
            'L': (17, 19, 1, -19, 18, "/8APgAfAA+AB8AD4AHwAPgAfAA+AB8AD4AHwAPgAfAA+Ax8Bj4D//+A="),
            'M': (27, 19, 1, -19, 29, "/wAf5/AH4P4A/B/gP4N8BfBngb4M+CfBnwz4MfGfBj5j4MPsfBh/D4MH4fBg+D4MHwfBgeD4MAAfBgAD4/gB/4A="),
            'N': (22, 19, 1, -19, 24, "/AH8eACB8AIH4AgfwCB/gIE+AgT8CBH4IEPwgQfiBA/IEB8gQH+BAP4EAfgQA+BAB4/gDgA="),
            'O': (21, 19, 1, -19, 23, "AfwAeHgHgfB8B8fAPj4A+fAH34A+/AH34A//AH34A+fAHz4A+fAPh8B8HgfAeHgAfwA="),
            'P': (18, 19, 1, -19, 20, "//wHx8Hw+Hw/Hw/HwfHw/Hw/Hw+Hx8H/wHwAHwAHwAHwAHwAHwAHwA/+AA=="),
            'Q': (21, 24, 1, -19, 23, "AfwAeHgHgfB8B8fAPj4A+fAH34A+/AH34A//AH34A+fAHz4A+fAPh8B8HgfAeHgAfwAAcAABwAAHwAAeAABw"),
            'R': (21, 19, 1, -19, 22, "//wA+PgHw+A+D4HwfA+D4HwfA+D4Hw+A+PgH/wA+fAHx8A+PgHw+A+H4HwfA+B8/8P4="),
            'S': (17, 19, 1, -19, 19, "B/gODw4DjwDHgGPAAfgA/4B/+B//B//Af+AH8AD5gDzAHnAOPA4H/AA="),
            'T': (20, 19, 0, -19, 19, "///sHwbB8GwfBgHwAB8AAfAAHwAB8AAfAAHwAB8AAfAAHwAB8AAfAAHwAB8AB/4A"),
            'U': (23, 19, 0, -19, 23, "f+H8PgBgfADA+AGB8AMD4AYHwAwPgBgfADA+AGB8AMD4AYHwAwHgBAPgGAfAMAfgwAf/AAP4AA=="),
            'V': (22, 19, -1, -19, 20, "f8D8fADB8AID4BgPgGA/AwB8DAHwIAPhgA+GAD8wAHzAAfIAA/gAD+AAPwAAfAAB4AADgAA="),
            'W': (31, 19, -1, -19, 29, "f8Hgfj4D4CB8B8DA+B+BgPg/AwHwfwQD4b4YA+N8MAfEfEAPmPmAH7HzAB9h9AA/g/gAfwfwAH4H4AD4D4AB8B8AAeA+AAOAOAA="),
            'X': (21, 19, 0, -19, 20, "/8fh+BwHwMA/DAD8YAPmAB/gAH8AAfAAD8AAPwAD+AA34AGfABh8AYPwDA+AwH4/h/w="),
            'Y': (20, 19, -1, -19, 19, "f8Px8AwfgYD4GA/DAHwwB+YAPmAB/AAfwAD4AA+AAPgAD4AA+AAPgAD4AA+AB/4A"),
            'Z': (19, 19, 0, -19, 19, "f//MAfmAfjAPwAPwAPwAP4AH4AH4AH8AD8AD8AD+AB+AB+AB+AZ/AM/AGf//AA=="),
            '[': (8, 23, 3, -20, 12, "/vj4+Pj4+Pj4+Pj4+Pj4+Pj4+Pj4+P4="),
            '\\': (10, 21, 0, -19, 10, "4DgHAcBwDgOA4BwHAcAwDgOAYBwHAMA4DgGA"),
            ']': (9, 23, 1, -20, 12, "fweDweDweDweDweDweDweDweDweDweDwefw="),
            '^': (18, 7, 2, -19, 22, "AeAA/AB/gDzwHh4OA8cAOA=="),
            '_': (13, 2, 0, 4, 13, "////wA=="),
            '`': (8, 5, 1, -21, 13, "eDgcDgY="),
            'a': (16, 13, 1, -13, 17, "H8Bw8GD4AHgAeB/4fHj4ePh4+Hj4eHj4P34="),
            'b': (18, 20, 0, -20, 18, "fgAHgAHgAHgAHgAHgAHgAHvwHx4Hg8Hg+Hg+Hg+Hg+Hg+Hg+Hg+Hg8Hx4fvw"),
            'c': (14, 13, 1, -13, 16, "D+D458GeAvgD4A+APgD4AeBnwY+MD+A="),
            'd': (17, 20, 1, -20, 18, "AP4AHwAPgAfAA+AB8AD4H3w8fj4fHg+fB8+D58Hz4PnwfHg+Ph8PH4H38A=="),
            'e': (15, 13, 1, -13, 17, "D8B54eHjw++H3w+//3wA+ADwGfBh8cD+AA=="),
            'f': (13, 20, 0, -20, 11, "B/h5x8Y8AeAPAHgP/B4A8AeAPAHgDwB4A8AeAPAHgP+A"),
            'g': (17, 18, 1, -13, 18, "D7+ePx8PjwfPg+fB8+D58Hz4PjwfHw+Hj8D74AHxgPDAeHB4D/AA"),
            'h': (19, 20, 0, -20, 19, "fgADwAB4AA8AAeAAPAAHgADz4B8eA+HgeDwPB4Hg8DweB4PA8HgeDwPB4Hg8P9/g"),
            'i': (10, 19, 0, -19, 10, "HAeD4HgcAAfgeB4HgeB4HgeB4HgeB4f4"),
            'j': (10, 24, -2, -19, 9, "BwHg+B4HAAH4HgeB4HgeB4HgeB4HgeB4Hgex7PP4"),
            'k': (19, 20, 0, -20, 18, "fgADwAB4AA8AAeAAPAAHgADw/B4MA8MAeMAPOAHvAD/wB98A8eAePgPD4Hg+P8/g"),
            'l': (10, 20, 0, -20, 10, "fgeB4HgeB4HgeB4HgeB4HgeB4HgeB4Hh/g=="),
            'm': (27, 13, 0, -13, 28, "fnw+A/Px4Hx+Pg8Hh8Hg8Pg8Hh8Hg8Pg8Hh8Hg8Pg8Hh8Hg8Pg8Hh8f7/f4="),
            'n': (19, 13, 0, -13, 19, "fnwD48B8PA8HgeDwPB4Hg8DweB4PA8HgeDwPB4f7/A=="),
            'o': (16, 13, 1, -13, 17, "D+A8eHw8eD74Pvg++D74Pvg+eD58PDx4D+A="),
            'p': (18, 18, 0, -13, 18, "fvwHx4Hg8Hg+Hg+Hg+Hg+Hg+Hg+Hg+Hg8Hx4HvwHgAHgAHgAHgAf4AA="),
            'q': (17, 18, 1, -13, 18, "D7+ePx8PjwfPg+fB8+D58Hz4PjwfHw+Hj8D74AHwAPgAfAA+AH/A"),
            'r': (14, 13, 0, -13, 14, "fnx+MfDHwB4AeAHgB4AeAHgB4AeAf8A="),
            's': (13, 13, 1, -13, 15, "H8PDvA3gb8B/wf+D/gH+B/A9w+P8AA=="),
            't': (12, 17, 0, -17, 12, "HgHgHgHgf+HgHgHgHgHgHgHgHgHgHjHmD8A="),
            'u': (19, 13, 0, -13, 19, "fj8DweB4PA8HgeDwPB4Hg8DweB4PA8PgeHwPn4B8/A=="),
            'v': (17, 13, -1, -13, 15, "fw+fAweBg+GB8MB4QD5gDzAH8AP4APgAfAAeAA=="),
            'w': (24, 13, -1, -13, 22, "fw4fPg8MHh8MHx8IHx+YDzeYD7eQD6fwB+PwB+PgB8PgA8HgA8HA"),
            'x': (16, 13, 0, -13, 16, "/z4+GB8wHzAP4AfAB8AH4A/wCfAY+DB8/f8="),
            'y': (17, 18, -1, -13, 15, "fw+fAweBA+GA8MB8QB5gD6AH8AH4APgAPAAcAAYAAwBjADGAHwAA"),
            'z': (14, 13, 0, -13, 15, "f/2D9g+AfAPwH4B8A+AfgPwD4N8Df/w="),
            '{': (13, 23, 2, -20, 17, "A/A8A+AfAPgHwD4B8A+AeAfB/AHwB4A+AfAPgHwD4B8A+APAD8A="),
            '|': (4, 26, 3, -20, 9, "7u7u7u7u7u7u7u7u7g=="),
            '}': (13, 23, 2, -20, 17, "/gD4A8AfAPgHwD4B8A+AfAHwB/B8B8A+AfAPgHwD4B8A8A+D+AA="),
            '~': (18, 5, 2, -11, 22, "HwCP+Gf/+Yf8ADwA"),
            '—': (24, 3, 1, -8, 26, "////////////"),
            '•': (10, 9, 3, -14, 17, "Hg/n+f9/3/f4/h4A"),
        },
    },
}

# ------------------------------------------------------- glyph pixel cache
# Decode each glyph once into a list of (dx, dy) set-pixel offsets relative
# to the glyph origin (origin = text baseline start, bearing applied).
_GLYPH_CACHE = {}


def _glyph_pixels(font_name):
    if font_name in _GLYPH_CACHE:
        return _GLYPH_CACHE[font_name]
    spec = FONT[font_name]
    out = {}
    for ch, (gw, gh, left, top, advance, b64) in spec["glyphs"].items():
        raw = base64.b64decode(b64)
        pts = []
        for gy in range(gh):
            for gx in range(gw):
                bit = (gy * gw + gx)
                if raw[bit >> 3] & (0x80 >> (bit & 7)):
                    pts.append((left + gx, top + gy))
        out[ch] = (advance, pts)
    _GLYPH_CACHE[font_name] = out
    return out


def text_width(font_name, text):
    glyphs = _glyph_pixels(font_name)
    total = 0
    for ch in text:
        g = glyphs.get(ch) or glyphs["?"]
        total += g[0]
    return total


def wrap_text(font_name, text, max_width):
    """Greedy word wrap; returns a list of lines that fit max_width."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(font_name, trial) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ canvas
class Canvas:
    def __init__(self, w, h, color):
        self.w = w
        self.h = h
        self.buf = bytearray(bytes(color) * (w * h))

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            self.buf[i:i + 3] = bytes(color)

    def fill_rect(self, x0, y0, x1, y1, color):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for y in range(y0, y1):
            i = self._idx(x0, y)
            self.buf[i:i + len(row)] = row

    def vgrad(self, top, bottom):
        for y in range(self.h):
            t = y / max(1, self.h - 1)
            c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
            self.fill_rect(0, y, self.w, y + 1, c)

    def _hspan(self, x0, x1, y, color):
        if 0 <= y < self.h:
            self.fill_rect(x0, y, x1 + 1, y + 1, color)

    def circle(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            dx = isqrt(max(0, r * r - dy * dy))
            self._hspan(cx - dx, cx + dx, cy + dy, color)

    def ring(self, cx, cy, r, thickness, color):
        for dy in range(-r, r + 1):
            dx = isqrt(max(0, r * r - dy * dy))
            inner = isqrt(max(0, (r - thickness) * (r - thickness) - dy * dy)) \
                if abs(dy) < r - thickness else -1
            if inner >= 0:
                self._hspan(cx - dx, cx - inner - 1, cy + dy, color)
                self._hspan(cx + inner + 1, cx + dx, cy + dy, color)
            else:
                self._hspan(cx - dx, cx + dx, cy + dy, color)

    def ellipse(self, cx, cy, rx, ry, color):
        for dy in range(-ry, ry + 1):
            dx = int(rx * isqrt(max(0, ry * ry - dy * dy)) / ry) if ry else 0
            self._hspan(cx - dx, cx + dx, cy + dy, color)

    def polygon(self, pts, color):
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self._hspan(int(xs[i]), int(xs[i + 1]), y, color)

    def thick_line(self, x0, y0, x1, y1, thickness, color):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        r = max(1, thickness // 2)
        for s in range(steps + 1):
            t = s / steps
            self.circle(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), r, color)

    def polyline(self, pts, thickness, color):
        for a, b in zip(pts, pts[1:]):
            self.thick_line(a[0], a[1], b[0], b[1], thickness, color)

    def rounded_rect(self, x0, y0, x1, y1, r, color):
        self.fill_rect(x0 + r, y0, x1 - r, y1, color)
        self.fill_rect(x0, y0 + r, x1, y1 - r, color)
        for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r),
                       (x0 + r, y1 - r), (x1 - r, y1 - r)):
            self.circle(cx, cy, r, color)

    # ------------------------------------------------------------ text
    def draw_text(self, font_name, x, baseline_y, text, color, align="left"):
        glyphs = _glyph_pixels(font_name)
        w = text_width(font_name, text)
        if align == "center":
            x -= w // 2
        elif align == "right":
            x -= w
        cx = x
        for ch in text:
            adv, pts = glyphs.get(ch) or glyphs["?"]
            for dx, dy in pts:
                self.set(cx + dx, baseline_y + dy, color)
            cx += adv
        return cx

    def draw_wrapped(self, font_name, x, baseline_y, lines, color,
                     line_height, align="left", max_width=None):
        y = baseline_y
        for line in lines:
            self.draw_text(font_name, x, y, line, color, align=align)
            y += line_height
        return y


# ------------------------------------------------------------------- png
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(canvas, path):
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter: none
        raw += canvas.buf[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ----------------------------------------------------------------- drawing
def draw_bunting(c, y_base=30, sag=34):
    """A string of little flags sagging across the top of the image."""
    colors = [TERRA, MUSTARD, TEAL, SAGE]
    xs = list(range(56, W - 40, 62))
    pts = []
    for x in xs:
        t = (x - xs[0]) / max(1, xs[-1] - xs[0])
        pts.append((x, int(y_base + sag * 4 * t * (1 - t))))
    c.polyline(pts, 3, INK)
    for i, (x, y) in enumerate(pts[:-1]):
        nx, ny = pts[i + 1]
        mx, my = (x + nx) // 2, (y + ny) // 2
        c.polygon([(mx - 15, my + 2), (mx + 15, my + 2), (mx, my + 36)],
                  colors[i % len(colors)])


def draw_house_scene(c):
    # Sun with rays, top right.
    sx, sy, sr = 872, 96, 42
    for k in range(8):
        ang = k * 3.14159 / 4
        import math
        x0 = int(sx + (sr + 8) * math.cos(ang))
        y0 = int(sy + (sr + 8) * math.sin(ang))
        x1 = int(sx + (sr + 26) * math.cos(ang))
        y1 = int(sy + (sr + 26) * math.sin(ang))
        c.thick_line(x0, y0, x1, y1, 5, MUSTARD)
    c.circle(sx, sy, sr, MUSTARD)
    c.circle(sx - 12, sy - 12, 14, (232, 184, 96))
    # Clouds.
    for cx, cy, s in ((180, 84, 1.0), (640, 66, 0.8)):
        c.ellipse(cx, cy, int(52 * s), int(20 * s), WHITE)
        c.ellipse(cx - 34 * s, cy + 8, int(34 * s), int(15 * s), WHITE)
        c.ellipse(cx + 36 * s, cy + 8, int(36 * s), int(15 * s), WHITE)
    # Birds.
    for bx, by in ((520, 120), (580, 96)):
        c.thick_line(bx - 12, by, bx, by - 8, 3, INK)
        c.thick_line(bx, by - 8, bx + 12, by, 3, INK)
    # Little house, left.
    hx0, hy0, hx1, hy1 = 128, 150, 292, 232
    c.polygon([(hx0 - 16, hy0), ((hx0 + hx1) // 2, hy0 - 52), (hx1 + 16, hy0)], ROOF)
    c.fill_rect(hx0, hy0, hx1, hy1, HOUSE)
    c.fill_rect(hx0 + 66, hy0 + 40, hx0 + 98, hy1, DOOR)
    c.circle(hx0 + 92, hy0 + 66, 3, MUSTARD)
    c.fill_rect(hx0 + 16, hy0 + 18, hx0 + 48, hy0 + 50, (186, 220, 228))
    c.fill_rect(hx1 - 48, hy0 + 18, hx1 - 16, hy0 + 50, (186, 220, 228))
    c.thick_line(hx0 + 32, hy0 + 18, hx0 + 32, hy0 + 50, 3, WHITE)
    c.thick_line(hx0 + 16, hy0 + 34, hx0 + 48, hy0 + 34, 3, WHITE)
    # Chimney + smoke.
    c.fill_rect(hx1 - 22, hy0 - 46, hx1 - 2, hy0 - 6, TERRA_DARK)
    for i, (px, py, pr) in enumerate(((hx1 - 2, hy0 - 62, 9),
                                      (hx1 + 12, hy0 - 80, 12),
                                      (hx1 + 2, hy0 - 100, 15))):
        c.circle(px, py, pr, (236, 226, 214))
    # Tree, right of the house scene (left of the sun).
    tx = 700
    c.fill_rect(tx - 8, 168, tx + 8, 232, (122, 90, 60))
    c.circle(tx, 138, 44, LEAF)
    c.circle(tx - 34, 162, 30, SAGE)
    c.circle(tx + 34, 162, 30, SAGE_DARK)
    c.circle(tx - 12, 118, 10, TERRA)
    c.circle(tx + 16, 128, 10, MUSTARD)
    # Grass line under the scene.
    c.fill_rect(48, 232, W - 48, 238, SAGE)


def draw_letter(c):
    x0, y0, x1, y1 = 110, 252, 914, 940
    # Soft shadow, then the paper.
    c.rounded_rect(x0 + 10, y0 + 12, x1 + 10, y1 + 12, 14, SHADOW)
    c.rounded_rect(x0, y0, x1, y1, 14, PAPER)
    # Thin inset border framing the letter.
    inset = 18
    c.fill_rect(x0 + inset, y0 + inset, x1 - inset, y0 + inset + 3, PAPER_EDGE)
    c.fill_rect(x0 + inset, y1 - inset - 3, x1 - inset, y1 - inset, PAPER_EDGE)
    c.fill_rect(x0 + inset, y0 + inset, x0 + inset + 3, y1 - inset, PAPER_EDGE)
    c.fill_rect(x1 - inset - 3, y0 + inset, x1 - inset, y1 - inset, PAPER_EDGE)
    # Tape strips on the top corners.
    c.polygon([(x0 + 6, y0 - 6), (x0 + 96, y0 - 6), (x0 + 84, y0 + 26),
               (x0 - 6, y0 + 26)], TAPE)
    c.polygon([(x1 - 96, y0 - 6), (x1 - 6, y0 - 6), (x1 + 6, y0 + 26),
               (x1 - 84, y0 + 26)], TAPE)

    tx = x0 + 44
    tw = (x1 - x0) - 88  # text width
    y = y0 + 78

    # Salutation.
    y = c.draw_wrapped("serif_bold_38", tx, y, ["Dear AI Judge,"], INK, 48)
    y += 4
    # Headline, two centred lines.
    cx = (x0 + x1) // 2
    y = c.draw_wrapped("serif_bold_52", cx, y, ["Please Come to", "My House!"],
                       TERRA, 60, align="center")
    y += 2
    # Little rule with a diamond.
    ry = y + 6
    c.fill_rect(tx, ry, cx - 26, ry + 3, MUSTARD)
    c.fill_rect(cx + 26, ry, x1 - 44, ry + 3, MUSTARD)
    c.polygon([(cx, ry - 9), (cx + 10, ry + 1), (cx, ry + 11), (cx - 10, ry + 1)],
              TERRA)
    y = ry + 28

    # Body intro (kept short so it wraps to exactly two lines).
    intro = ("I know you can't walk through the door \u2014 but if you could, "
             "here's what's waiting for you:")
    lines = wrap_text("serif_30", intro, tw)
    y = c.draw_wrapped("serif_30", tx, y, lines, INK, 38)
    y += 8

    # The four concrete reasons (each one line).
    reasons = [
        "Dumplings, still steaming, fresh today.",
        "The soft armchair by the window \u2014 yours.",
        "A garden view, birdsong, and fast Wi-Fi.",
        "Tea already poured. No small talk required.",
    ]
    for r in reasons:
        bullet_lines = wrap_text("serif_30", "\u2022  " + r, tw)
        y = c.draw_wrapped("serif_30", tx, y, bullet_lines, INK, 38)
    y += 8

    # Postscript: the knowing wink, one line.
    ps = "P.S. No visit? A high score is the next best thing."
    ps_lines = wrap_text("serif_26", ps, tw)
    y = c.draw_wrapped("serif_26", tx, y, ps_lines, MUTED, 32)
    y += 8

    # Signature.
    y = c.draw_wrapped("serif_bold_38", tx, y, ["\u2014 Your hopeful host"],
                       INK, 46)
    y += 8
    # RSVP footer, centred.
    c.draw_text("serif_bold_26", cx, y, 'RSVP: just think "yes". I will know.',
                TERRA, align="center")
    y += 40

    # Wax seal, bottom right, overlapping the card edge.
    sx, sy = x1 - 66, y1 - 58
    c.circle(sx, sy, 34, SEAL)
    c.ring(sx, sy, 28, 3, SEAL_DARK)
    # A small heart stamped in the seal.
    c.circle(sx - 8, sy - 4, 8, (232, 120, 108))
    c.circle(sx + 8, sy - 4, 8, (232, 120, 108))
    c.polygon([(sx - 15, sy - 1), (sx + 15, sy - 1), (sx, sy + 16)],
              (232, 120, 108))
    return y


def draw_doormat(c):
    # Welcome mat under the letter, with a plant on the left and tea on the right.
    mx0, my0, mx1, my1 = 372, 956, 652, 1004
    c.rounded_rect(mx0, my0, mx1, my1, 10, MUSTARD)
    c.rounded_rect(mx0 + 6, my0 + 6, mx1 - 6, my1 - 6, 8, (201, 148, 52))
    c.draw_text("serif_bold_26", (mx0 + mx1) // 2, my1 - 14, "WELCOME",
                (255, 244, 214), align="center")
    # Potted plant, bottom left.
    c.polygon([(96, 1006), (150, 1006), (142, 962), (104, 962)], TERRA)
    c.ellipse(123, 950, 26, 16, SAGE)
    c.ellipse(104, 958, 16, 12, LEAF)
    c.ellipse(142, 958, 16, 12, SAGE_DARK)
    # Teacup with steam, bottom right.
    c.polygon([(884, 1006), (940, 1006), (934, 968), (890, 968)], TEAL)
    c.ellipse(912, 968, 24, 7, (210, 232, 228))
    c.ring(946, 986, 10, 4, TEAL)
    for i, (px, py) in enumerate(((902, 950), (912, 934), (922, 950))):
        c.thick_line(px, py + 12, px + 4, py, 3, (255, 255, 255))
        c.thick_line(px + 4, py, px, py - 12, 3, (255, 255, 255))


def main():
    c = Canvas(W, H, SKY_TOP)
    c.vgrad(SKY_TOP, SKY_BOT)
    draw_bunting(c)
    draw_house_scene(c)
    end_y = draw_letter(c)
    print(f"letter text ends at y={end_y} (card bottom edge 940)")
    draw_doormat(c)
    out = OUT_PATH
    try:
        size = write_png(c, out)
    except OSError:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "entry.png")
        size = write_png(c, out)
    print(f"wrote {out} {size} bytes")


if __name__ == "__main__":
    main()

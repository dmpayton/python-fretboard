import copy

import attrdict
import svgwrite
import yaml

from .compat import StringIO
from .fretboard import Fretboard
from .utils import dict_merge


DEFAULT_STYLE = '''
drawing:
    background_color: white
    background_opacity: 1
    font_color: dimgray
    font_family: Lato
    font_size: 15
    height: 300
    width: 250
    spacing: 30

nut:
    color: dimgray
    size: 10

fret:
    color: darkgray
    size: 2

inlays:
    color: black
    radius: 2

string:
    color: black
    size: 3

marker:
    color: chocolate
    font_color: white
    radius: 15
    stroke_width: 2

'''


class Chord(object):
    default_style = yaml.safe_load(DEFAULT_STYLE)
    inlays = Fretboard.inlays
    strings = 6

    def __init__(self, positions=None, fingers=None, style=None):
        if positions is None:
            positions = []
        elif '-' in positions:
            positions = positions.split('-')
        else:
            positions = list(positions)
        self.positions = list(map(lambda p: int(p) if p.isdigit() else None, positions))

        self.fingers = list(fingers) if fingers else []

        self.style = attrdict.AttrDict(
            dict_merge(
                copy.deepcopy(self.default_style),
                style or {}
            )
        )

    def get_barre_fret(self):
        for index, finger in enumerate(self.fingers):
            if finger.isdigit() and self.fingers.count(finger) > 1:
                return int(self.positions[index])

    def get_fret_range(self):
        fretted_positions = list(filter(lambda pos: isinstance(pos, int), self.positions))
        if max(fretted_positions) < 5:
            first_fret = 0
        else:
            first_fret = min(filter(lambda pos: pos != 0, fretted_positions))
        return (first_fret, first_fret + 4)

    def draw(self):
        self.fretboard = Fretboard(
            strings=self.strings,
            frets = self.get_fret_range(),
            inlays=self.inlays,
            style=self.style
        )

        # Check for a barred fret (we'll need to know this later)
        barre_fret = None
        for index, finger in enumerate(self.fingers):
            if finger.isdigit() and self.fingers.count(finger) > 1:
                barre_fret = self.positions[index]
                barre_start = index
                barre_end = len(self.fingers) - self.fingers[::-1].index(finger) - 1
                break

        if barre_fret is not None:
            self.fretboard.add_marker(
                string=(barre_start, barre_end),
                fret=barre_fret,
                label=finger,
            )

        for string in range(self.strings):
            # Get the position and fingering
            try:
                fret = self.positions[string]
            except IndexError:
                pos = None

            # Determine if the string is muted or open
            is_muted = False
            is_open = False

            if fret == 0:
                is_open = True
            elif fret is None:
                is_muted = True

            if is_muted or is_open:
                self.fretboard.add_string_label(string, 'X' if is_muted else 'O')
            elif fret is not None and fret != barre_fret:
                # Add the fret marker
                try:
                    finger = self.fingers[string]
                except IndexError:
                    finger = None

                self.fretboard.add_marker(
                    string=string,
                    fret=fret,
                    label=finger,
                )

    def render(self, output=None):
        self.draw()

        if output is None:
            output = StringIO()

        self.fretboard.render(output)
        return output

    def save(self, filename):
        with open(filename, 'w') as output:
            self.render(output)


class BassChord(Chord):
    strings = 4


class UkuleleChord(Chord):
    strings = 4
    inlays = (3, 5, 7, 10)

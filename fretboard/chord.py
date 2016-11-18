import copy

import attrdict
import svgwrite
import yaml

from .compat import StringIO
from .fretboard import Fretboard
from .utils import dict_merge


CHORD_STYLE = '''
string:
    muted_font_color: silver
    open_font_color: steelblue
'''


class Chord(object):
    default_style = dict_merge(
        yaml.safe_load(CHORD_STYLE),
        Fretboard.default_style
    )
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
            frets=self.get_fret_range(),
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
                self.fretboard.add_string_label(
                    string=string,
                    label='X' if is_muted else 'O',
                    font_color=self.style.string.muted_font_color if is_muted else self.style.string.open_font_color

                )
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

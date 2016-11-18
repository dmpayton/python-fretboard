import copy

import attrdict
import svgwrite
import yaml

from .compat import StringIO
from .utils import dict_merge

# fretboard = Fretboard(strings=6, frets=(3, 8))
# fretboard.add_string_label(string=1, label='X', color='')
# fretboard.add_barre(fret=1, strings=(0, 5), label='')
# fretboard.add_marker(fret=1, string=1, label='', color='')

DEFAULT_STYLE = '''
drawing:
    background_color: white
    font_color: dimgray
    font_family: Lato
    font_size: 15
    height: 300
    width: 250
    spacing: 30

nut:
    color: darkslategray
    size: 10

fret:
    color: darkgray
    size: 2

inlays:
    color: black
    radius: 2

string:
    color: darkslategray
    size: 3

marker:
    border_color: darkslategray
    color: steelblue
    font_color: white
    radius: 12
    stroke_width: 2

'''

class Fretboard(object):
    default_style = yaml.safe_load(DEFAULT_STYLE)

    # Guitars and basses have different inlay patterns than, e.g., ukulele
    # A double inlay will be added at the octave (12th fret)
    inlays = (3, 5, 7, 9)

    def __init__(self, strings=6, frets=(0, 5), inlays=None, style=None):
        self.frets = list(range(max(frets[0] - 1, 0), frets[1] + 1))
        self.strings = [attrdict.AttrDict({
            'color': None,
            'label': None,
            'font_color': None,
        }) for x in range(strings)]

        self.markers = []

        self.inlays = inlays or self.inlays

        self.layout = attrdict.AttrDict()

        self.style = attrdict.AttrDict(
            dict_merge(
                copy.deepcopy(self.default_style),
                style or {}
            )
        )

    def add_string_label(self, string, label, font_color=None):
        self.strings[string].label = label
        self.strings[string].font_color = font_color

    def add_marker(self, string, fret, color=None, label=None, font_color=None):
        self.markers.append(attrdict.AttrDict({
            'fret': fret,
            'string': string,
            'color': color,
            'label': label,
            'font_color': font_color,
        }))

    def calculate_layout(self):
        # Bounding box of our fretboard
        self.layout.update({
            'x': self.style.drawing.spacing,
            'y': self.style.drawing.spacing * 1.5,
            'width': self.style.drawing.width - (self.style.drawing.spacing * 2.25),
            'height': self.style.drawing.height - (self.style.drawing.spacing * 2),
        })

        # Spacing between the strings
        self.layout['string_space'] = self.layout.width / (len(self.strings) - 1)

        # Spacing between the frets, with room at the top and bottom for the nut
        self.layout['fret_space'] = (self.layout.height - self.style.nut.size * 2) / (len(self.frets) - 1)

    def draw_frets(self):
        top = self.layout.y + self.style.nut.size

        for index, fret in enumerate(self.frets):
            if index == 0 and self.frets[0] == 0:
                # The first fret is the nut, don't draw it.
                continue
            else:
                self.drawing.add(
                    self.drawing.line(
                        start=(self.layout.x, top + (self.layout.fret_space * index)),
                        end=(self.layout.x + self.layout.width, top + (self.layout.fret_space * index)),
                        stroke=self.style.fret.color,
                        stroke_width=self.style.fret.size,
                    )
                )

    def draw_strings(self):
        top = self.layout.y
        bottom = top + self.layout.height

        label_y = self.layout.y + self.style.drawing.font_size - self.style.drawing.spacing

        for index, string in enumerate(self.strings):
            width = self.style.string.size - ((self.style.string.size * 1 / (len(self.strings) * 1.5)) * index)

            # Offset the first and last strings, so they're not drawn outside the edge of the nut.
            offset = 0
            if index == 0:
                offset += width / 2.
            elif index == len(self.strings) - 1:
                offset -= width / 2.

            x = self.layout.x + (self.layout.string_space * index) + offset

            self.drawing.add(
                self.drawing.line(
                    start=(x, top),
                    end=(x, bottom),
                    stroke=string.color or self.style.string.color,
                    stroke_width=width
                )
            )

            # Draw the label obove the string
            if string.label is not None:
                self.drawing.add(
                    self.drawing.text(string.label,
                        insert=(x, label_y),
                        font_family=self.style.drawing.font_family,
                        font_size=self.style.drawing.font_size,
                        font_weight='bold',
                        fill=string.font_color or self.style.marker.color,
                        text_anchor='middle',
                        alignment_baseline='middle',
                    )
                )

    def draw_nut(self):
        if self.frets[0] == 0:
            top = self.layout.y + (self.style.nut.size / 2)
            self.drawing.add(
                self.drawing.line(
                    start=(self.layout.x, top),
                    end=(self.layout.x + self.layout.width, top),
                    stroke=self.style.nut.color,
                    stroke_width=self.style.nut.size,
                )
            )

    def draw_inlays(self):
        x = (self.style.drawing.spacing) - (self.style.inlays.radius * 4)

        for index, fret in enumerate(self.frets):
            if index == 0:
                continue

            y = sum((
                self.layout.y,
                self.style.nut.size,
                self.layout.fret_space * index,
            )) - self.layout.fret_space / 2

            if fret in self.inlays or fret - 12 in self.inlays:
                # Single dot inlay
                self.drawing.add(
                    self.drawing.circle(
                        center=(x, y),
                        r=self.style.inlays.radius,
                        fill=self.style.inlays.color,
                    )
                )
            elif fret > 0 and not fret % 12:
                # Double dot inlay
                self.drawing.add(
                    self.drawing.circle(
                        center=(x, y - (self.style.inlays.radius * 2)),
                        r=self.style.inlays.radius,
                        fill=self.style.inlays.color,
                    )
                )
                self.drawing.add(
                    self.drawing.circle(
                        center=(x, y + (self.style.inlays.radius * 2)),
                        r=self.style.inlays.radius,
                        fill=self.style.inlays.color,
                    )
                )

    def draw_fret_label(self):
        if self.frets[0] > 0:
            x = self.layout.width + self.style.drawing.spacing + self.style.inlays.radius
            y = self.layout.y + self.style.nut.size + (self.style.drawing.font_size * .2)
            self.drawing.add(
                self.drawing.text('{0}fr'.format(self.frets[0]),
                    insert=(x, y),
                    font_family=self.style.drawing.font_family,
                    font_size=self.style.drawing.font_size,
                    font_style='italic',
                    font_weight='bold',
                    fill=self.style.drawing.font_color,
                    text_anchor='start',
                )
            )

    def draw_markers(self):
        for marker in self.markers:
            if isinstance(marker.string, (list, tuple)):
                self.draw_barre(marker)
            else:
                self.draw_marker(marker)

    def draw_marker(self, marker):
        # Fretted position, add the marker to the fretboard.
        x = self.style.drawing.spacing + (self.layout.string_space * marker.string)
        y = sum((
            self.layout.y,
            self.style.nut.size,
            (self.layout.fret_space * (marker.fret - self.frets[0])) - (self.layout.fret_space / 2)
        ))

        self.drawing.add(
            self.drawing.circle(
                center=(x, y),
                r=self.style.marker.radius,
                fill=marker.color or self.style.marker.color,
                stroke=self.style.marker.border_color,
                stroke_width=self.style.marker.stroke_width
            )
        )

        # Draw the label
        if marker.label is not None:
            self.drawing.add(
                self.drawing.text(marker.label,
                    insert=(x, y),
                    font_family=self.style.drawing.font_family,
                    font_size=self.style.drawing.font_size,
                    font_weight='bold',
                    fill=self.style.marker.font_color,
                    text_anchor='middle',
                    alignment_baseline='central'
                )
            )

    def draw_barre(self, marker):
        start_x = self.style.drawing.spacing + (self.layout.string_space * marker.string[0])
        end_x = self.style.drawing.spacing + (self.layout.string_space * marker.string[1])

        y = sum((
            self.layout.y,
            self.style.nut.size,
            (self.layout.fret_space * (marker.fret - self.frets[0])) - (self.layout.fret_space / 2)
        ))

        # Lines don't support borders, so fake it by drawing
        # a slightly larger line behind it.
        self.drawing.add(
            self.drawing.line(
                start=(start_x, y),
                end=(end_x, y),
                stroke=self.style.marker.border_color,
                stroke_linecap='round',
                stroke_width=(self.style.marker.radius * 2) + (self.style.marker.stroke_width * 2)
            )
        )

        self.drawing.add(
            self.drawing.line(
                start=(start_x, y),
                end=(end_x, y),
                stroke=self.style.marker.color,
                stroke_linecap='round',
                stroke_width=self.style.marker.radius * 2
            )
        )

        if marker.label is not None:
            self.drawing.add(
                self.drawing.text(marker.label,
                    insert=(start_x, y),
                    font_family=self.style.drawing.font_family,
                    font_size=self.style.drawing.font_size,
                    font_weight='bold',
                    fill=self.style.marker.font_color,
                    text_anchor='middle',
                    alignment_baseline='central'
                )
            )

    def draw(self):
        self.drawing = svgwrite.Drawing(size=(
            self.style.drawing.width,
            self.style.drawing.height
        ))

        if self.style.drawing.background_color is not None:
            self.drawing.add(
                self.drawing.rect(
                    insert=(0, 0),
                    size=(
                        self.style.drawing.width,
                        self.style.drawing.height
                    ),
                    fill=self.style.drawing.background_color
                )
            )

        self.calculate_layout()
        self.draw_frets()
        self.draw_inlays()
        self.draw_fret_label()
        self.draw_strings()
        self.draw_nut()
        self.draw_markers()

    def render(self, output=None):
        self.draw()

        if output is None:
            output = StringIO()

        self.drawing.write(output)
        return output

    def save(self, filename):
        with open(filename, 'w') as output:
            self.render(output)

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
    orientation: portrait

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
    same_width: False

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

        self.inlays = inlays if inlays is not None else self.inlays

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

    def add_marker(self, string, fret, color=None, label=None, font_color=None, label_adjust=(0, 0)):
        self.markers.append(attrdict.AttrDict({
            'fret': fret,
            'string': string,
            'color': color,
            'label': label,
            'font_color': font_color,
            'label_adjust': label_adjust,
        }))

    def wipe(self):
        self.markers = []

    def calculate_layout(self):
        if self.style.drawing.orientation == 'portrait':
            neck_width = self.style.drawing.width - (self.style.drawing.spacing * 2.25)
            neck_length = self.style.drawing.height - (self.style.drawing.spacing * 2)

            layout_width = neck_width
            layout_height = neck_length
            layout_x = self.style.drawing.spacing
            layout_y = self.style.drawing.spacing * 1.5
        else:
            neck_width = self.style.drawing.height - (self.style.drawing.spacing * 2.25)
            neck_length = self.style.drawing.width - (self.style.drawing.spacing * 2)

            layout_width = neck_length
            layout_height = neck_width
            layout_x = self.style.drawing.spacing * 1.5
            layout_y = self.style.drawing.spacing

        # Bounding box of our fretboard
        self.layout.update({
            'x': layout_x,
            'y': layout_y,
            'width': layout_width,
            'height': layout_height,
        })

        # Spacing between the strings
        self.layout['string_space'] = neck_width / (len(self.strings) - 1)

        # Spacing between the frets, with room at the top and bottom for the nut
        self.layout['fret_space'] = (neck_length - self.style.nut.size * 2) / (len(self.frets) - 1)

    def get_layout_string_index(self, string_index):
        if self.style.drawing.orientation == 'portrait':
            return string_index
        else:
            return len(self.strings) - string_index - 1

    def draw_frets(self):
        for index, fret in enumerate(self.frets):
            if index == 0 and self.frets[0] == 0:
                # The first fret is the nut, don't draw it.
                continue
            else:
                if self.style.drawing.orientation == 'portrait':
                    top = self.layout.y + self.style.nut.size
                    fret_y = top + (self.layout.fret_space * index)
                    start = (self.layout.x, fret_y)
                    end=(self.layout.x + self.layout.width, fret_y)
                else:
                    left = self.layout.x + self.style.nut.size
                    fret_x = left + (self.layout.fret_space * index)
                    start=(fret_x, self.layout.y)
                    end=(fret_x, self.layout.y + self.layout.height)

                self.drawing.add(
                    self.drawing.line(
                        start=start,
                        end=end,
                        stroke=self.style.fret.color,
                        stroke_width=self.style.fret.size,
                    )
                )

    def draw_strings(self):
        for index, string in enumerate(self.strings):

            # Offset the first and last strings, so they're not drawn outside the edge of the nut.
            if self.style.string.same_width:
                string_width = self.style.string.size
            else:
                string_width = self.style.string.size - ((self.style.string.size * 1 / (len(self.strings) * 1.5)) * index)

            offset = 0
            str_index = self.get_layout_string_index(index)

            if str_index == 0:
                offset += string_width / 2.
            elif str_index == len(self.strings) - 1:
                offset -= string_width / 2.

            if self.style.drawing.orientation == 'portrait':
                label_x = self.layout.x + (self.layout.string_space * str_index) + offset
                label_y = self.layout.y + self.style.drawing.font_size - self.style.drawing.spacing
                string_start = (label_x, self.layout.y)
                string_stop = (label_x, self.layout.y + self.layout.height)

            elif self.style.drawing.orientation == 'landscape':
                label_x = self.layout.x + self.style.drawing.font_size - self.style.drawing.spacing
                label_y = self.layout.y + (self.layout.string_space * str_index) + offset
                string_start = (self.layout.x, label_y)
                string_stop = (self.layout.x + self.layout.width, label_y)

            self.drawing.add(
                self.drawing.line(
                    start=string_start,
                    end=string_stop,
                    stroke=string.color or self.style.string.color,
                    stroke_width=string_width
                )
            )

            # Draw the label obove the string
            if string.label is not None:
                self.drawing.add(
                    self.drawing.text(string.label,
                        insert=(label_x, label_y),
                        font_family=self.style.drawing.font_family,
                        font_size=self.style.drawing.font_size,
                        font_weight='bold',
                        fill=string.font_color or self.style.marker.color,
                        text_anchor='middle',
                        alignment_baseline='middle',
                    )
                )

    def draw_nut(self):
        if self.style.drawing.orientation == 'portrait':
            top = self.layout.y + (self.style.nut.size / 2)
            nut_start = (self.layout.x, top)
            nut_end = (self.layout.x + self.layout.width, top)
        else:
            left = self.layout.x + (self.style.nut.size / 2)
            nut_start = (left, self.layout.y)
            nut_end = (left, self.layout.y + self.layout.height)

        if self.frets[0] == 0:
            self.drawing.add(
                self.drawing.line(
                    start=nut_start,
                    end=nut_end,
                    stroke=self.style.nut.color,
                    stroke_width=self.style.nut.size,
                )
            )

    def draw_inlays(self):

        for index, fret in enumerate(self.frets):
            if index == 0:
                continue

            inlay_dist = self.style.nut.size + self.layout.fret_space * index - self.layout.fret_space / 2

            if self.style.drawing.orientation == 'portrait':
                x = self.style.drawing.spacing - (self.style.inlays.radius * 4)
                y = self.layout.y + inlay_dist
            else:
                x = self.layout.x + inlay_dist
                y = self.layout.y + self.layout.height + (self.style.inlays.radius * 4)

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
                if self.style.drawing.orientation == 'portrait':
                    dot_1 = (x, y - (self.style.inlays.radius * 2))
                    dot_2 = (x, y + (self.style.inlays.radius * 2))
                else:
                    dot_1 = (x - (self.style.inlays.radius * 2), y)
                    dot_2 = (x + (self.style.inlays.radius * 2), y)

                # Double dot inlay
                self.drawing.add(
                    self.drawing.circle(
                        center=dot_1,
                        r=self.style.inlays.radius,
                        fill=self.style.inlays.color,
                    )
                )
                self.drawing.add(
                    self.drawing.circle(
                        center=dot_2,
                        r=self.style.inlays.radius,
                        fill=self.style.inlays.color,
                    )
                )

    def draw_fret_label(self):
        if self.frets[0] > 0:
            if self.style.drawing.orientation == 'portrait':
                x = self.layout.width + self.style.drawing.spacing + self.style.inlays.radius
                y = self.layout.y + self.style.nut.size + (self.style.drawing.font_size * .2)
            else:
                x = self.layout.x + self.style.nut.size - (self.style.drawing.font_size * 0.75)
                y = self.layout.height + self.style.drawing.spacing + self.style.drawing.font_size * 1.0

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

    def draw_marker_label(self, label, position):
        if label is not None:
            self.drawing.add(
                self.drawing.text(label,
                    insert=position,
                    font_family=self.style.drawing.font_family,
                    font_size=self.style.drawing.font_size,
                    font_weight='bold',
                    fill=self.style.marker.font_color,
                    text_anchor='middle',
                    alignment_baseline='central'
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
        marker_string = self.get_layout_string_index(marker.string)

        if self.style.drawing.orientation == 'portrait':
            x = self.style.drawing.spacing + (self.layout.string_space * marker_string)
            y = sum((
                self.layout.y,
                self.style.nut.size,
                (self.layout.fret_space * (marker.fret - self.frets[0])) - (
                            self.layout.fret_space / 2)
            ))
        else:
            x = sum((
                self.layout.x,
                self.style.nut.size,
                (self.layout.fret_space * (marker.fret - self.frets[0])) - (
                        self.layout.fret_space / 2)
            ))
            y = self.style.drawing.spacing + (self.layout.string_space * marker_string)

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
        self.draw_marker_label(marker.label, (x+marker.label_adjust[0], y+marker.label_adjust[1]))

    def draw_barre(self, marker):
        marker_string_0 = self.get_layout_string_index(marker.string[0])
        marker_string_1 = self.get_layout_string_index(marker.string[1])

        if self.style.drawing.orientation == 'portrait':
            y = sum((
                self.layout.y,
                self.style.nut.size,
                (self.layout.fret_space * (marker.fret - self.frets[0])) - (
                        self.layout.fret_space / 2)
            ))
            start = (self.style.drawing.spacing + (self.layout.string_space * marker_string_0), y)
            end = (self.style.drawing.spacing + (self.layout.string_space * marker_string_1), y)

        else:
            x = sum((
                self.layout.x,
                self.style.nut.size,
                (self.layout.fret_space * (marker.fret - self.frets[0])) - (
                        self.layout.fret_space / 2)
            ))
            start = (x, self.style.drawing.spacing + (self.layout.string_space * marker_string_1))
            end = (x, self.style.drawing.spacing + (self.layout.string_space * marker_string_0))

        # Lines don't support borders, so fake it by drawing
        # a slightly larger line behind it.
        self.drawing.add(
            self.drawing.line(
                start=start,
                end=end,
                stroke=self.style.marker.border_color,
                stroke_linecap='round',
                stroke_width=(self.style.marker.radius * 2) + (self.style.marker.stroke_width * 2)
            )
        )

        self.drawing.add(
            self.drawing.line(
                start=start,
                end=end,
                stroke=self.style.marker.color,
                stroke_linecap='round',
                stroke_width=self.style.marker.radius * 2
            )
        )

        self.draw_marker_label(marker.label, (start[0] + marker.label_adjust[0], start[1] + marker.label_adjust[1]))

    def draw(self):
        self.drawing = svgwrite.Drawing(size=(
            self.style.drawing.width,
            self.style.drawing.height,
        ))

        if self.style.drawing.background_color is not None:
            self.drawing.add(
                self.drawing.rect(
                    insert=(0, 0),
                    size=(
                        self.style.drawing.width,
                        self.style.drawing.height,
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

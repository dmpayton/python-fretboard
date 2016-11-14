from .compat import StringIO
from .utils import dict_merge

import attrdict
import svgwrite
import yaml


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


class ChordChart(object):
    default_style = DEFAULT_STYLE

    def __init__(self, positions=None, fingers=None, style=None, strings=6):
        if positions is None:
            positions = []
        elif '-' in positions:
            positions = positions.split('-')
        else:
            positions = list(positions)
        self.positions = list(map(lambda p: int(p) if p.isdigit() else None, positions))

        self.fingers = list(fingers) if fingers else []
        self.strings = strings

        # Merge custom styles with the defaults and
        self.style = yaml.safe_load(self.default_style)
        if style is not None:
            dict_merge(self.style, yaml.safe_load(style))
        self.style = attrdict.AttrDict(self.style)

        self.drawing = svgwrite.Drawing(size=(
            self.style.drawing.width,
            self.style.drawing.height
        ))

        # Create the box that the chord chart will live in. This will make
        # positioning easier later on.
        self.chart = self.drawing.rect(
            insert=(
                self.style.drawing.spacing,
                self.style.drawing.spacing * 1.5
            ),
            size=(
                self.style.drawing.width - (self.style.drawing.spacing * 2.25),
                self.style.drawing.height - (self.style.drawing.spacing * 2)
            ),
            fill_opacity=0
        )
        self.drawing.add(self.chart)

    def calculate_layout(self):
        # Spacing between the strings
        self.string_space = self.chart.attribs['width'] / (self.strings - 1)

        # Leave space at the top and bottom for the nut and strings
        self.fret_space = (self.chart.attribs['height'] - self.style.nut.size * 2) / 5.

        # Calculate which frets are being displayed in the chart
        fretted_positions = list(filter(lambda pos: isinstance(pos, int), self.positions))
        if max(fretted_positions) < 5:
            first_fret = 0
        else:
            first_fret = min(filter(lambda pos: pos != 0, fretted_positions)) - 1
        self.frets = list(range(first_fret, first_fret + 5))

    def draw_frets(self):
        frets = self.drawing.add(self.drawing.g(id='frets'))
        top = self.chart.attribs['y'] + self.style.nut.size

        for x in range(6):
            frets.add(
                self.drawing.line(
                    start=(self.chart.attribs['x'], top + (self.fret_space * x)),
                    end=(self.chart.attribs['x'] + self.chart.attribs['width'], top + (self.fret_space * x)),
                    stroke=self.style.fret.color,
                    stroke_width=self.style.fret.size,
                )
            )

    def draw_fret_label(self):
        if self.frets[0] > 0:
            self.drawing.add(
                self.drawing.text('{0}'.format(self.frets[0]),
                    insert=(
                        (self.style.drawing.spacing * 1.5) + self.chart.attribs['width'],
                        self.chart.attribs['y'] + self.style.nut.size + (self.style.drawing.font_size * .4)
                    ),
                    font_family=self.style.drawing.font_family,
                    font_size=self.style.drawing.font_size,
                    font_weight='bold',
                    fill=self.style.drawing.font_color,
                    text_anchor='middle',
                )
            )

    def draw_inlays(self):
        x = (self.style.drawing.spacing) - (self.style.inlays.radius * 4)

        for index, fret in enumerate(self.frets + [self.frets[-1] + 1]):
            if index == 0:
                continue

            y = sum((
                self.chart.attribs['y'],
                self.style.nut.size,
                self.fret_space * index,
            )) - self.fret_space / 2

            if fret in (3, 5, 7, 9) or fret - 12 in (3, 5, 7, 9):
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

    def draw_nut(self):
        if self.frets[0] == 0:
            top = self.chart.attribs['y'] + (self.style.nut.size / 2)
            self.drawing.add(
                self.drawing.line(
                    start=(self.chart.attribs['x'], top),
                    end=(self.chart.attribs['x'] + self.chart.attribs['width'], top),
                    stroke=self.style.string.color,
                    stroke_width=self.style.nut.size,
                )
            )

    def draw_strings(self):
        strings = self.drawing.add(
            self.drawing.g(id='strings', stroke=self.style.string.color)
        )

        left = self.chart.attribs['x']
        top = self.chart.attribs['y']
        bottom = self.chart.attribs['y'] + self.chart.attribs['height']

        for x in range(self.strings):
            strings.add(
                self.drawing.line(
                    start=(left + (self.string_space * x), top),
                    end=(left + (self.string_space * x), bottom),
                    stroke_width=self.style.string.size - ((self.style.string.size * 1 / (self.strings * 1.5)) * x)
                )
            )

    def draw_markers(self):
        if not self.positions:
            return

        barre_fret = self.get_barre_fret()

        for string in range(self.strings):
            x = self.style.drawing.spacing + (self.string_space * string)
            pos = self.positions[string]
            is_muted = False
            is_open = False

            if pos == 0:
                is_open = True
            elif pos is None:
                is_muted = True

            if is_muted or is_open:
                # No marker to draw, add a simple X or O above the nut
                self.drawing.add(
                    self.drawing.text('X' if is_muted else 'O',
                        insert=(
                            x,
                            self.chart.attribs['y'] + self.style.drawing.font_size - self.style.drawing.spacing
                        ),
                        font_family=self.style.drawing.font_family,
                        font_size=self.style.drawing.font_size,
                        font_weight='bold',
                        fill=self.style.marker.color if is_open else self.style.fret.color,
                        text_anchor='middle',
                        alignment_baseline='middle',
                    )
                )
            elif pos != barre_fret:
                # Fretted position, add the marker to the fretboard.
                y = sum((
                    self.chart.attribs['y'],
                    self.style.nut.size,
                    (self.fret_space * (pos - self.frets[0])) - (self.fret_space / 2)
                ))

                self.drawing.add(
                    self.drawing.circle(
                        center=(x, y),
                        r=self.style.marker.radius,
                        fill=self.style.marker.color,
                        stroke=self.style.string.color,
                        stroke_width=self.style.marker.stroke_width
                    )
                )

                # If there's a specified finger, put it on the marker
                if self.fingers and self.fingers[string].isdigit():
                    self.drawing.add(
                        self.drawing.text(self.fingers[string],
                            insert=(x, y),
                            font_family=self.style.drawing.font_family,
                            font_size=self.style.drawing.font_size,
                            font_weight='bold',
                            fill=self.style.marker.font_color,
                            text_anchor='middle',
                            alignment_baseline='middle'
                        )
                    )

    def draw_barre(self):
        fret = None

        for index, finger in enumerate(self.fingers):
            if finger.isdigit() and self.fingers.count(finger) > 1:
                fret = self.positions[index]
                start_string = index
                end_string = len(self.fingers) - self.fingers[::-1].index(finger) - 1
                break

        # No barred fret, nothing to do.
        if fret is None:
            return

        start_x = self.style.drawing.spacing + (self.string_space * start_string)
        end_x = self.style.drawing.spacing + (self.string_space * end_string)

        y = sum((
            self.chart.attribs['y'],
            self.style.nut.size,
            (self.fret_space * (fret - self.frets[0])) - (self.fret_space / 2)
        ))

        # Lines don't support borders, so fake it by drawing
        # a slightly large line behind it.
        self.drawing.add(
            self.drawing.line(
                start=(start_x, y),
                end=(end_x, y),
                stroke=self.style.string.color,
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

        self.drawing.add(
            self.drawing.text(finger,
                insert=(start_x, y),
                font_family=self.style.drawing.font_family,
                font_size=self.style.drawing.font_size,
                font_weight='bold',
                fill=self.style.marker.font_color,
                text_anchor='middle',
                alignment_baseline='middle'
            )
        )

    def get_barre_fret(self):
        for index, finger in enumerate(self.fingers):
            if finger.isdigit() and self.fingers.count(finger) > 1:
                return int(self.positions[index])

    def draw(self):
        self.drawing.add(
            self.drawing.rect(
                insert=(0, 0),
                size=(self.style.drawing.width, self.style.drawing.height),
                fill=self.style.drawing.background_color,
                fill_opacity=self.style.drawing.background_opacity,
            )
        )

        self.calculate_layout()
        self.draw_frets()
        self.draw_inlays()
        self.draw_fret_label()
        self.draw_nut()
        self.draw_strings()
        self.draw_barre()
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

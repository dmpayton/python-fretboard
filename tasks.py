import os

import invoke
import livereload

import fretboard

server = livereload.Server()

@invoke.task
def build(ctx=None):
    chord = fretboard.ChordChart(positions='xx0232', fingers='---132')
    chord.save('demo/D.svg')

    chord = fretboard.ChordChart(positions='133211', fingers='134211')
    chord.save('demo/F.svg')

    chord = fretboard.ChordChart(positions='x-15-14-12-0-0', fingers='-321--')
    chord.save('demo/C-shape.svg')


@invoke.task(pre=[build])
def serve(ctx):
    server.watch('./fretboard/', lambda: os.system('invoke build'))

    server.serve(
        root='./demo/',
        host='localhost',
        liveport=35729,
        port=8080
    )

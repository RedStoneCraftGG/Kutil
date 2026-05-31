from midiutil import MIDIFile
import re
import os
import argparse

# Semitone intervals relative to root
_CHORD_INTERVALS = {
    '':     [0, 4, 7],        # major
    'm':    [0, 3, 7],        # minor
    '7':    [0, 4, 7, 10],    # dominant 7th
    'm7':   [0, 3, 7, 10],    # minor 7th
    'maj7': [0, 4, 7, 11],    # major 7th
    'dim':  [0, 3, 6],        # diminished
    'aug':  [0, 4, 8],        # augmented
    'sus2': [0, 2, 7],        # suspended 2nd
    'sus4': [0, 5, 7],        # suspended 4th
}

_NOTE_NAMES = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}

def resolve_chord(name, octave=4):
    """'Am7' -> [57, 60, 64, 67] (MIDI pitches, octave 4 default)"""
    m = re.match(r'^([A-G])(#|b)?(.*)$', name)
    if not m:
        raise ValueError(f"Unknown chord: {name}")
    root_name, acc, quality = m.group(1), m.group(2) or '', m.group(3)
    if quality not in _CHORD_INTERVALS:
        raise ValueError(f"Unknown chord quality: '{quality}' in '{name}'")
    root = 12 * (octave + 1) + _NOTE_NAMES[root_name]
    if acc == '#': root += 1
    elif acc == 'b': root -= 1
    return [root + i for i in _CHORD_INTERVALS[quality]]

def read_file(path):
    with open(path, "r") as f:
        raw_lines = [line for line in f if line.strip() and not line.strip().startswith("#")]

    # Merge indented continuation lines into the previous line
    merged = []
    for line in raw_lines:
        if line[0].isspace() and merged:
            merged[-1] = merged[-1].rstrip() + " " + line.strip()
        else:
            merged.append(line.strip())

    tempo, time_sig = map(int, merged[0].split())
    tracks = []

    for line in merged[1:]:
        instr_id, notes_str = line.split(maxsplit=1)
        instr_id = int(instr_id)
        notes = []
        last_pattern = None
        # Match [{...}] blocks, plain [...] blocks, @*N, @*,  @N, @@
        tokens = re.findall(r'\[\{[^\}]+\}\]|\[[^\]]+\]|@\*\d+|@\*|@@|@\d+', notes_str)

        i = 0
        while i < len(tokens):
            tok = tokens[i]

            if tok.startswith("["):
                base_pattern = []

                while i < len(tokens) and tokens[i].startswith("["):
                    tok = tokens[i]
                    octave_offset = 0
                    pitch_cents = 0

                    # --- auto chord block [{(Name)}&^] or [{(Name)}&_] ---
                    auto_chord_match = re.match(r'^\[\{(\([^)]+\))\}(&[\^_])?(\*-?\d+)?(\^-?\d+)?\]$', tok)
                    if auto_chord_match:
                        chord_expr  = auto_chord_match.group(1)   # e.g. (Cmaj7)
                        arp_dir     = auto_chord_match.group(2)   # &^ or &_ or None
                        oct_mod     = auto_chord_match.group(3)   # *N or None
                        bend_mod    = auto_chord_match.group(4)   # ^N or None
                        if oct_mod:  octave_offset = int(oct_mod[1:])
                        if bend_mod: pitch_cents   = int(bend_mod[1:])

                        chord_name = chord_expr[1:-1]  # strip parens
                        pitches = resolve_chord(chord_name, octave=4)
                        if octave_offset:
                            pitches = [p + octave_offset * 12 for p in pitches]

                        if arp_dir is None:
                            # plain chord — all notes simultaneously, dur=1
                            base_pattern.append((pitches, 1, pitch_cents))
                        else:
                            # arpeggio — each note separately, dur=1 each
                            if arp_dir == '&_':
                                pitches = list(reversed(pitches))
                            for p in pitches:
                                base_pattern.append((p, 1, pitch_cents))
                        i += 1
                        continue

                    # --- plain block [...] ---
                    block = tok[1:-1].strip()
                    modifier_match = re.search(r'(\*-?\d+)?(\^-?\d+)?$', block)
                    if modifier_match:
                        if modifier_match.group(1):
                            octave_offset = int(modifier_match.group(1)[1:])
                        if modifier_match.group(2):
                            pitch_cents = int(modifier_match.group(2)[1:])
                        block = block[:modifier_match.start()].strip()

                    if block.startswith("("):  # numeric chord
                        chord_part, dur = block.split(")")
                        pitches = list(map(int, chord_part[1:].split()))
                        if octave_offset:
                            pitches = [p + octave_offset * 12 for p in pitches]
                        base_pattern.append((pitches, int(dur), pitch_cents))
                    else:
                        note, dur = block.split()
                        if note == "None":
                            base_pattern.append((None, int(dur), 0))
                        else:
                            p = int(note)
                            if octave_offset:
                                p += octave_offset * 12
                            base_pattern.append((p, int(dur), pitch_cents))
                    i += 1

                repeat = 1
                if i < len(tokens) and tokens[i].startswith("@") and tokens[i] != "@@" and not tokens[i].startswith("@*"):
                    repeat = int(tokens[i][1:])
                    i += 1

                for _ in range(repeat):
                    notes.extend(base_pattern)
                last_pattern = base_pattern
                continue

            if tok == "@@":
                if last_pattern:
                    notes.extend(last_pattern)
                i += 1
                continue

            if tok.startswith("@*"):
                n = int(tok[2:]) if len(tok) > 2 else 1
                original = list(notes)
                for _ in range(n - 1):
                    notes.extend(original)
                i += 1
                continue

            i += 1

        tracks.append((instr_id, notes))

    return tempo, time_sig, tracks

def kutil(data, filename="output.mid", unit=0.25):
    tempo, time_sig, tracks = data
    mf = MIDIFile(len(tracks))
    num, denom = time_sig // 10, time_sig % 10

    for i, (instr_id, _) in enumerate(tracks):
        mf.addTrackName(i, 0, f"Track {i+1}")
        mf.addTempo(i, 0, tempo)
        mf.addTimeSignature(i, 0, num, denom, 24)

    for i, (instr_id, notes) in enumerate(tracks):
        channel = 9 if instr_id == 9 else i % 16
        volume = 100
        time = 0

        if channel != 9:
            mf.addProgramChange(i, channel, 0, instr_id)

        for pitch, dur, pitch_cents in notes:
            length = dur * unit

            if pitch is None:
                time += length
                continue

            if pitch_cents != 0:
                bend_value = max(-8192, min(8191, int(pitch_cents / 100 * 4096)))
                mf.addPitchWheelEvent(i, channel, time, bend_value)

            if isinstance(pitch, (list, tuple)):
                for p in pitch:
                    mf.addNote(i, channel, p, time, length, volume)
            else:
                mf.addNote(i, channel, pitch, time, length, volume)

            if pitch_cents != 0:
                mf.addPitchWheelEvent(i, channel, time + length, 0)

            time += length

    with open(filename, "wb") as f:
        mf.writeFile(f)

def main():
    parser = argparse.ArgumentParser(description="Convert file to MIDI")
    parser.add_argument("input_file", help="Input file")
    parser.add_argument("-o", "--output", help="Output file (optional)")
    args = parser.parse_args()

    input_file = args.input_file
    output_file = args.output or os.path.splitext(input_file)[0] + ".mid"

    kutil(read_file(input_file), output_file)

if __name__ == "__main__":
    main()

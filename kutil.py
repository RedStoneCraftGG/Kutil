from midiutil import MIDIFile
import re
import sys
import os
import argparse

def read_file(path):
    with open(path, "r") as f:
        lines = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    tempo, time_sig = map(int, lines[0].split())
    tracks = []

    for line in lines[1:]:
        instr_id, notes_str = line.split(maxsplit=1)
        instr_id = int(instr_id)
        notes = []
        last_pattern = None
        tokens = re.findall(r'\[[^\]]+\]|@@|@\d+', notes_str)

        i = 0
        while i < len(tokens):
            tok = tokens[i]

            if tok.startswith("["):
                base_pattern = []

                while i < len(tokens) and tokens[i].startswith("["):
                    block = tokens[i][1:-1].strip()
                    octave_offset = 0
                    pitch_cents = 0

                    modifier_match = re.search(r'(\*[-]?\d+)?(\^\d+)?$', block)
                    if modifier_match:
                        if modifier_match.group(1):
                            octave_offset = int(modifier_match.group(1)[1:])
                        if modifier_match.group(2):
                            pitch_cents = int(modifier_match.group(2)[1:])
                        block = block[:modifier_match.start()]


                    if block.startswith("("):  # chord
                        chord_part, dur = block.split(")")
                        pitches = list(map(int, chord_part[1:].split()))
                        base_pattern.append((pitches, int(dur)))
                    else:
                        note, dur = block.split()
                        if note == "None":
                            base_pattern.append((None, int(dur)))
                        else:
                            base_pattern.append((int(note), int(dur)))

                    i += 1

                repeat = 1
                if i < len(tokens) and tokens[i].startswith("@") and tokens[i] != "@@":
                    repeat = int(tokens[i][1:])
                    i += 1

                # expand the base pattern
                for _ in range(repeat):
                    notes.extend(base_pattern)

                last_pattern = base_pattern
                continue

            # repeat once more with the last pattern
            if tok == "@@":
                if last_pattern:
                    notes.extend(last_pattern)
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

        for pitch, dur in notes:
            length = dur * unit

            if pitch is None:
                time += length
            elif isinstance(pitch, (list, tuple)):
                for p in pitch:
                    mf.addNote(i, channel, p, time, length, volume)
                time += length
            else:
                mf.addNote(i, channel, pitch, time, length, volume)
                time += length

    with open(filename, "wb") as f:
        mf.writeFile(f)

def main():
    parser = argparse.ArgumentParser(description="Convert file to MIDI")
    parser.add_argument("input_file", help="Input file")
    parser.add_argument("-o", "--output", help="Output file (optional)")
    args = parser.parse_args()

    input_file = args.input_file
    if args.output:
        output_file = args.output
    else:
        base, _ = os.path.splitext(input_file)
        output_file = base + ".mid"

    byte_data = read_file(input_file)
    kutil(byte_data, output_file)

if __name__ == "__main__":
    main()
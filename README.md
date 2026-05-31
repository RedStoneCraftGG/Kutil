# kutil — Text-to-MIDI Converter

Convert plain text notation files into MIDI files.

## Usage

```
python kutil.py <input.txt> [-o output.mid]
```

If `-o` is omitted, output filename matches the input (e.g. `song.txt` → `song.mid`).

---

## File Format

### Line 1 — Header

```
<tempo> <time_signature>
```

- `tempo` — BPM (integer)
- `time_signature` — two digits: numerator and log2(denominator). e.g. `44` = 4/4, `34` = 3/4, `68` = 6/8

```
120 44
```

### Lines 2+ — Tracks

Each line is one track:

```
<instr_id> <notes...>
```

- `instr_id` — General MIDI program number (0–127). Use `9` for drums (channel 10).
- Long tracks can be split across multiple **indented** continuation lines.

```
0 [60 4][62 4][64 4]
  [65 4][67 8]
```

---

## Note Blocks

All notes are written as `[...]` tokens.

### Single Note

```
[<pitch> <dur>]
```

- `pitch` — MIDI note number (0–127). Middle C = 60.
- `dur` — duration in units. 1 unit = 1 semiquaver (1/16 note) at default `unit=0.25` beats.

```
[60 4]    # C4, 1 beat (4 units)
[69 8]    # A4, 2 beats
```

### Rest

```
[None <dur>]
```

```
[None 4]  # 1 beat of silence
```

### Numeric Chord (simultaneous notes)

```
[(<p1> <p2> <p3>) <dur>]
```

```
[(60 64 67) 4]   # C major chord, 1 beat
```

### Auto Chord

```
[{(<Name>)}]
[{(<Name>)}&^]
[{(<Name>)}&_]
```

- `{(Name)}` — chord by name, default octave 4, duration 1 unit
- `&^` — arpeggio ascending (each note 1 unit, played sequentially)
- `&_` — arpeggio descending

**Supported chord types:**

| Suffix | Type | Intervals |
|--------|------|-----------|
| *(none)* | Major | 1 3 5 |
| `m` | Minor | 1 b3 5 |
| `7` | Dominant 7th | 1 3 5 b7 |
| `m7` | Minor 7th | 1 b3 5 b7 |
| `maj7` | Major 7th | 1 3 5 7 |
| `dim` | Diminished | 1 b3 b5 |
| `aug` | Augmented | 1 3 #5 |
| `sus2` | Suspended 2nd | 1 2 5 |
| `sus4` | Suspended 4th | 1 4 5 |

Root notes: `C C# Db D D# Eb E F F# Gb G G# Ab A A# Bb B`

```
[{(C)}]        # C major chord, simultaneous, dur=1
[{(Am7)}&^]    # Am7 arpeggio ascending
[{(G)}&_]      # G major arpeggio descending
```

---

## Modifiers

Modifiers are appended to any `[...]` block (including auto chords).

### Octave Offset `*N`

Shifts all pitches by N octaves (±12 semitones each).

```
[60 4*1]          # C5 (up 1 octave)
[60 4*-1]         # C3 (down 1 octave)
[{(C)}&^*-1]      # C major arpeggio, down 1 octave
```

### Pitch Bend `^N`

Applies a pitch bend of N cents before the note, resets to 0 after.  
100 cents = 1 semitone. Range: approximately ±200 cents.

```
[64 4^50]         # E4 with +50 cent bend (quarter tone up)
[69 2^-50]        # A4 with -50 cent bend
```

---

## Repeat Tokens

### `@N` — Repeat last block N times

Repeats the immediately preceding `[...]` group N times total (including the first play).

```
[60 2][62 2][64 2] @3    # plays the 3-note group 3 times
```

### `@@` — Repeat last block once more

Shorthand for `@2` — plays the last block one additional time.

```
[60 4][62 4] @@          # plays the 2-note group twice total
```

### `@*N` — Loop entire track N times total

Repeats the entire track's note sequence so it plays N times total.  
Place at the end of the track line.

```
0 [60 4][62 4][64 4] @*2    # whole track plays 2x
0 [60 4][62 4][64 4] @*3    # whole track plays 3x
```

---

## General MIDI Instrument Reference (common)

| ID | Instrument |
|----|------------|
| 0 | Acoustic Grand Piano |
| 25 | Acoustic Guitar (steel) |
| 32 | Acoustic Bass |
| 40 | Violin |
| 48 | String Ensemble 1 |
| 56 | Trumpet |
| 73 | Flute |
| 9 | *(Drums — channel 10)* |

Full list: [General MIDI Level 1 Sound Set](https://www.midi.org/specifications-old/item/gm-level-1-sound-set)

---

## Example

```
# Simple 2-track piece in C major
120 44

# Piano melody
0 [60 2][62 2][64 4] [65 2][64 2][62 4] @*2

# String pad with auto chords
48 [{(C)}*-1] [None 7] [{(F)}*-1] [None 7] @*2
```

---

## Planned Features

- Velocity per note (`!N` prefix — TBD)

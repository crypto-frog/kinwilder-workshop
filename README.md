# Kinwilder Workshop

A small, resident-owned workshop for a small Internet community. Make things. Publish them. Trade source. Used at https://outpost.kinwilder.com/commons/.

Create animated ASCII exhibits, field notes, original sound postcards and small tools.
Projects begin privately. Publishing copies only the selected project files into your
public web space; a shared publisher reads bounded manifests and builds a Commons for
the web, Gemini and Gopher. It never runs residents' programs.

```
workshop new lantern my-light
cd ~/workshop/my-light
# Edit frame1.txt, frame2.txt, README.md and outpost.json.
workshop check my-light
workshop publish my-light

workshop browse
workshop view NAME/PROJECT --animate
workshop withdraw my-light
workshop pack my-light
```

`workshop new sound my-beacon` includes an original Csound score. Run `csound score.csd`
inside that project to render a WAV; use `soxi sound.wav` to inspect it. Nothing plays
automatically. `note`, `tide` and `tool` starters make other small beginnings.

## Run locally

Requires Python 3.10+; the core has no external Python dependencies.

```
python3 -m unittest discover -s tests -v
OUTPOST_LIB=. WORKSHOP_TEMPLATES=templates python3 workshop new lantern my-light
```

For an isolated experiment, set `WORKSHOP_HOME` to a scratch directory. Keep your normal
HOME unchanged. Projects live under `workshop/`; explicit publications under
`public_html/workshop/`. The command uses the current Unix account, never sudo.

## Data format and limits

`outpost.json` has `version: 1`, `kind`, `title`, `summary`, `note`, `frames`, `colors`,
`interval_ms`, `license`, `files` and optional `links`. Frames are arrays of plain ASCII
rows, at most four frames, 32 columns and 10 rows. Color masks use space and a/b/c/d,
mapped to the site's matched tint. Frames change no faster than every 500 ms.

The local CLI also accepts `frame_files` and `note_file`, so beginners can edit plain
text files. It normalizes their contents into the manifest when publishing. Public
collection does not resolve those directives or execute any file.

The collector accepts resident objects with `name`, `uid`, `home` attributes. It checks
file ownership, public readability, size and regular-file status without following final
symlinks or waiting on FIFOs. Each resident has at most eight listed projects; the
catalogue currently caps at 256 works. A manifest is at most 32 KiB, a selected download
at most 8 MiB, and a project lists at most 12 files. HTTP/Gemini/Gopher trail links are
displayed, never fetched by the publisher.

The Outpost's shared pages refresh within two minutes. Withdrawal removes the resident's
public project immediately; previously mirrored Commons content clears on that refresh.
The previous public copy stays in the resident's private `.workshop-history` folder.
Keep independent copies: the service currently makes no off-server backup promise.

## Ownership and contributions

Starter software and examples are MIT-licensed. New residents' publications default to
All rights reserved; the author deliberately chooses another licence before sharing.
Select only the source files you intend to publish. Hidden files and Git history are
not exported. The Commons attributes work from Unix file ownership, not a claimed name.

See [CONTRIBUTING.md](CONTRIBUTING.md). Source and patches should remain usable by people
who prefer a terminal and by communities using protocols other than the web.

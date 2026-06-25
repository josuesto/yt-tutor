# yt-tutor demo (60 seconds)

A full pass on a real 5-minute talk: ingest it, know it, ask it, look at a slide, record what
you see, and get a cited answer. Every output below is real (CNCF lightning talk `jCz9QPrJ6Eo`).

> Want the animated version? Render it with [`vhs`](https://github.com/charmbracelet/vhs):
> `vhs docs/demo.tape` produces `demo.gif`. (No recorder is bundled; the tape is the script.)

## 1. Ingest (free, no API key)

```console
$ yt-tutor ingest "https://www.youtube.com/watch?v=jCz9QPrJ6Eo" --no-vision
  metadata: 'FAQs for CFPs: A Beginners Guide to Conference Speaking' | CNCF | 5:12
  transcript: 150 caption segments (youtube_captions)
  frames: 312 @1fps -> 27 keyframes (91% deduped)
  chunks: 15 merged windows
  summary: structural overview (15 sections)
  done.
```

A 5-minute talk becomes a timestamped, multimodal store. The 312 sampled frames collapse to 27
keyframes (static slides dedupe hard), and captions cost nothing.

## 2. Know it

```console
$ yt-tutor summary jCz9QPrJ6Eo
## Chapters
- [0:24] What's a CFP?
- [1:15] What info will I need?
- [1:47] What should I talk about?
- [2:21] Why me?
- [3:34] What if I'm rejected?
  ...
```

## 3. Ask it (answers carry mm:ss and a speech/visual label)

```console
$ yt-tutor ask jCz9QPrJ6Eo "what should my talk be about"
[1:49] (speech)
  said: the best talks I've seen are where people talk about something that they're
        passionate about ... it could be some failure story, sometimes when things go
        wrong those are the best lessons ...
[1:26] (speech+visual)
  shown: Slide 'Q4: What should I talk about?' with four bullets advising how to choose a topic.
```

## 4. Look at the slide yourself (you are the vision)

```console
$ yt-tutor frames jCz9QPrJ6Eo --at 1:14
[1:14] keyframe   .../frames/frame_000075.jpg
```

The agent opens that image and reads it. No paid vision call.

## 5. Record what you see, so visuals enter search

```console
$ yt-tutor keyframes jCz9QPrJ6Eo --pending --by-salience --json   # which frames are worth it
$ yt-tutor set-vision jCz9QPrJ6Eo --at 74 --file q3-slide.json     # store what you read
$ yt-tutor rechunk jCz9QPrJ6Eo
  rechunked jCz9QPrJ6Eo: 15 chunks (5 keyframes have visual notes)
```

Now a slide's own words are searchable:

```console
$ yt-tutor search jCz9QPrJ6Eo "accessibility requirements github repos"
[1:06] ... additional information (past speaking experience, accessibility requirements,
       github repos, etc). Q3: What info ...
```

## 6. Verify before you teach

```console
$ yt-tutor verify jCz9QPrJ6Eo --lesson lesson.html
[1:14]  (read frame: 1:14 -> .../frame_000075.jpg)
    said [1:15] you need to provide a pretty standard set of information who you are a quick
                biography the talk title ...
```

One pass over every timestamp a lesson cites, with the words and the frame, so nothing reaches
a learner that the video does not actually say or show.

---

That is the whole loop: a YouTube link in, a grounded and citable tutor out, on free local compute.

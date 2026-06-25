# yt-tutor demo tape. Render to a GIF with charmbracelet/vhs:
#     vhs docs/demo.tape      ->  demo.gif
#
# Prerequisite (run once, not recorded): ingest the sample video so the read
# commands below are instant:
#     yt-tutor ingest "https://www.youtube.com/watch?v=jCz9QPrJ6Eo" --no-vision

Output demo.gif

Set Shell "bash"
Set FontSize 18
Set Width 1240
Set Height 760
Set Padding 20
Set Theme "Dracula"
Set TypingSpeed 35ms

# Hidden setup: point at the data dir holding the pre-ingested video.
Hide
Type "export YT_TUTOR_DATA_DIR=$PWD/data && clear" Enter
Show

# 1. Know the video.
Type "yt-tutor summary jCz9QPrJ6Eo | head -n 12"  Sleep 400ms  Enter
Sleep 3s

# 2. Ask it. Answers cite mm:ss and label speech vs visual.
Type "yt-tutor ask jCz9QPrJ6Eo 'what should my talk be about'"  Sleep 400ms  Enter
Sleep 4s

# 3. Pull the exact slide shown at a moment, to read it.
Type "yt-tutor frames jCz9QPrJ6Eo --at 1:14"  Sleep 400ms  Enter
Sleep 3s

# 4. A slide's own words are searchable (recorded by the agent, not a paid pass).
Type "yt-tutor search jCz9QPrJ6Eo 'accessibility requirements github repos'"  Sleep 400ms  Enter
Sleep 4s

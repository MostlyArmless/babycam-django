# Gotchas

I'm using `@gumlet/react-hls-player` to play the video feed but it depends on React 16, so to avoid needing to use `--legacy-peer-deps` every time you install a package, I added overrides in package.json for react-hls-player to use React 18 and react-dom 18.

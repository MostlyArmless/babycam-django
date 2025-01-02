# Gotchas

I'm using `@gumlet/react-hls-player` to play the video feed but it depends on React 16, so you'll always get npm errors when doing npm install unless you use `npm install --legacy-peer-deps`. This may also cause issues with other tools that try to npm install their own dependencies for you, like when I first ran the [setup for shadcn](https://ui.shadcn.com/docs/installation/vite), at the `npx shadcn@latest init` step it failed, so to fix it I had to:

```zsh
npm remove @gumlet/react-hls-player --legacy-peer-deps
npx shadcn@latest init
npm install @gumlet/react-hls-player --legacy-peer-deps
```

You'll have to do the same thing whenever you want to use the shadcn cli to add new components:

```zsh
npm remove @gumlet/react-hls-player --legacy-peer-deps
npx shadcn@latest add switch
npm install @gumlet/react-hls-player --legacy-peer-deps
```

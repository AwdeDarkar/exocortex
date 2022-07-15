import App from "./App.svelte"

const app = new App({
    target: document.body,
    props: {
        // @ts-ignore: contentTree is defined explicitly in an HTML script block
        contentTree,
    }
})

export default app

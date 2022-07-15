<script lang="ts">
    import ContentNode from "./common/component/ContentNode.svelte"
    import ASTNode from "./common/interface/ast"
    export let contentTree: any
    console.log(contentTree)

    const node: ASTNode = ASTNode.loadNode(contentTree)
     console.log(node)
</script>

<main>
    <div>
        <ContentNode node={node} />
    </div>
</main>

<style>
main {
    text-align: center;
padding: 1em;
         max-width: 240px;
margin: 0 auto;
}

@media (min-width: 640px) {
    main {
        max-width: none;
    }
}
</style>

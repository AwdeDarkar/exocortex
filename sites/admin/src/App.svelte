<script lang="ts">
    import ContentNode from "./component/ContentNode.svelte"
    import ASTNode from "./interface/ast"
    export let contentTree: any
    // console.log(contentTree)

    const node: ASTNode = ASTNode.loadNode(contentTree)
    console.log(node)
</script>

<main>
    <div>
        <ContentNode node={node} />
    </div>
</main>
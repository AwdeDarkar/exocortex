<script lang="ts">
    import type ASTNode from "../interface/ast"
    import {
        DocumentNode,
    } from "../interface/ast"

    export let node: ASTNode
    // console.log(node.blah)
</script>

{#if node instanceof DocumentNode}
    <div>
        {#each node.children as child}
            <svelte:self node={child} />
        {/each}
    </div>
{:else}
    <p>Unknown type '{node.typename}'</p>
{/if}
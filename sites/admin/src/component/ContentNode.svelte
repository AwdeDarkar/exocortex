<script lang="ts">
    import type ASTNode from "../interface/ast"
    import {
        DocumentNode,
        HeadingNode,
        ParagraphNode,
        TextNode,
        BlankLineNode,
    } from "../interface/ast"
    import HeadN from "./HeadN.svelte"

    export let node: ASTNode
</script>

{#if node instanceof DocumentNode}
    <div>
        {#each node.children as child}
            <svelte:self node={child} />
        {/each}
    </div>
{:else if node instanceof HeadingNode}
    <div>
        <HeadN level={node.level}>
            {#each node.label as label}
                <svelte:self node={label} />
            {/each}
        </HeadN>
        {#each node.children as child}
            <svelte:self node={child} />
        {/each}
    </div>
{:else if node instanceof ParagraphNode}
    <p>
        {#each node.children as child}
            <svelte:self node={child} />
        {/each}
    </p>
{:else if node instanceof TextNode}
    <span>{node.text}</span>
{:else if node instanceof BlankLineNode}
    <br />
{:else}
    <p>Unknown type '{node.typename}'</p>
{/if}